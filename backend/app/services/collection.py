"""Collection Service - ETL pipeline for resource data."""

import asyncio
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models import Connection, Cluster, Host, VM, TaskVMSnapshot
from app.repositories.connection import ConnectionRepository
from app.repositories.base import BaseRepository
from app.models.resource import Cluster as ClusterModel, Host as HostModel, VM as VMModel
from app.connectors.base import Connector, ClusterInfo, HostInfo, VMInfo
from app.core.errors import NotFoundError, AppError


logger = structlog.get_logger()


class CollectionService:
    """Service for collecting resources from cloud platforms."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize collection service.

        Args:
            session: Database session
        """
        self.session = session
        self.connection_repo = ConnectionRepository(session)

    async def collect_resources(
        self,
        connection_id: int,
        selected_vm_keys: Optional[List[str]] = None,
    ) -> dict:
        """Collect resources (clusters, hosts, VMs) from connection.

        Args:
            connection_id: Connection ID
            selected_vm_keys: Optional list of VM keys to collect (filters VMs only)

        Returns:
            Collection summary with counts
        """
        # Get connection
        connection = await self.connection_repo.get_by_id(connection_id)
        if not connection:
            raise NotFoundError(f"Connection {connection_id} not found")

        # Get connector from service
        from app.services.connection import ConnectionService
        conn_service = ConnectionService(self.session)
        connector = await conn_service.get_connector(connection_id)

        try:
            # Delete existing resources for this connection
            await self._delete_existing_resources(connection_id)

            # Collect clusters
            clusters = await self._collect_clusters(connection_id, connector)

            # Collect hosts
            hosts = await self._collect_hosts(connection_id, connector)

            # Collect VMs
            vms = await self._collect_vms(connection_id, connector, selected_vm_keys)

            # Update connection status
            await self.connection_repo.update_status(connection_id, "connected", last_sync="now")

            logger.info(
                "resources_collected",
                connection_id=connection_id,
                clusters=len(clusters),
                hosts=len(hosts),
                vms=len(vms),
            )

            return {
                "success": True,
                "clusters": len(clusters),
                "hosts": len(hosts),
                "vms": len(vms),
            }
        except Exception as e:
            logger.error("collection_failed", connection_id=connection_id, error=str(e))
            await self.connection_repo.update_status(connection_id, "disconnected")
            raise AppError("COLLECTION_FAILED", f"Collection failed: {str(e)}")

    async def _delete_existing_resources(self, connection_id: int) -> None:
        """Delete existing resources for connection.

        Args:
            connection_id: Connection ID
        """
        from sqlalchemy import delete

        # Delete in order: VMs, Hosts, Clusters (respecting FKs)
        await self.session.execute(
            delete(VMModel).where(VMModel.connection_id == connection_id)
        )
        await self.session.execute(
            delete(HostModel).where(HostModel.connection_id == connection_id)
        )
        await self.session.execute(
            delete(ClusterModel).where(ClusterModel.connection_id == connection_id)
        )
        await self.session.flush()

    async def _collect_clusters(
        self,
        connection_id: int,
        connector: Connector,
    ) -> List[ClusterModel]:
        """Collect clusters from connector.

        Args:
            connection_id: Connection ID
            connector: Platform connector

        Returns:
            List of cluster models
        """
        cluster_infos = await connector.get_clusters()
        clusters = []

        for info in cluster_infos:
            # 在 cluster_key 前添加 connection_id，确保不同连接可以有相同名称的集群
            unique_cluster_key = f"conn{connection_id}:{info.cluster_key}"
            cluster = ClusterModel(
                connection_id=connection_id,
                name=info.name,
                datacenter=info.datacenter,
                total_cpu=info.total_cpu,
                total_memory=info.total_memory,
                num_hosts=info.num_hosts,
                num_vms=info.num_vms,
                cluster_key=unique_cluster_key,
                collected_at=datetime.now(),
            )
            self.session.add(cluster)
            clusters.append(cluster)

        await self.session.flush()
        return clusters

    async def _collect_hosts(
        self,
        connection_id: int,
        connector: Connector,
    ) -> List[HostModel]:
        """Collect hosts from connector.

        Args:
            connection_id: Connection ID
            connector: Platform connector

        Returns:
            List of host models
        """
        host_infos = await connector.get_hosts()
        hosts = []

        for info in host_infos:
            host = HostModel(
                connection_id=connection_id,
                name=info.name,
                datacenter=info.datacenter,
                ip_address=info.ip_address,
                cpu_cores=info.cpu_cores,
                cpu_mhz=info.cpu_mhz,
                memory_bytes=info.memory_bytes,
                num_vms=info.num_vms,
                power_state=info.power_state,
                overall_status=info.overall_status,
                collected_at=datetime.now(),
            )
            self.session.add(host)
            hosts.append(host)

        await self.session.flush()
        return hosts

    async def _collect_vms(
        self,
        connection_id: int,
        connector: Connector,
        selected_vm_keys: Optional[List[str]] = None,
    ) -> List[VMModel]:
        """Collect VMs from connector.

        Args:
            connection_id: Connection ID
            connector: Platform connector
            selected_vm_keys: Optional list of VM keys to collect (filters VMs)

        Returns:
            List of VM models
        """
        # 准备筛选集合：统一转换为带前缀的格式
        filter_keys: Optional[set] = None
        if selected_vm_keys:
            filter_keys = set()
            for key in selected_vm_keys:
                if key.startswith(f"conn{connection_id}:"):
                    filter_keys.add(key)
                else:
                    filter_keys.add(f"conn{connection_id}:{key}")

        vm_infos = await connector.get_vms()
        vms = []

        for info in vm_infos:
            # 生成 VM 的唯一 key
            base_vm_key = self._generate_vm_key(info)
            unique_vm_key = f"conn{connection_id}:{base_vm_key}"

            # 如果有筛选条件，跳过不在列表中的 VM
            if filter_keys and unique_vm_key not in filter_keys:
                continue

            vm = VMModel(
                connection_id=connection_id,
                name=info.name,
                datacenter=info.datacenter,
                uuid=info.uuid,
                vm_key=unique_vm_key,
                cpu_count=info.cpu_count,
                memory_bytes=info.memory_bytes,
                power_state=info.power_state,
                guest_os=info.guest_os,
                ip_address=info.ip_address,
                host_name=info.host_name,
                host_ip=info.host_ip,
                connection_state=info.connection_state,
                overall_status=info.overall_status,
                vm_create_time=info.vm_create_time,
                uptime_duration=info.uptime_duration,
                downtime_duration=info.downtime_duration,
                collected_at=datetime.now(),
            )
            self.session.add(vm)
            vms.append(vm)

        await self.session.flush()
        return vms

    def _generate_vm_key(self, vm_info: VMInfo) -> str:
        """Generate unique VM key.

        Args:
            vm_info: VM information

        Returns:
            VM key in format "uuid:<lowercase_uuid>" or "<datacenter>:<name>"
        """
        if vm_info.uuid:
            return f"uuid:{vm_info.uuid.lower()}"
        if vm_info.datacenter:
            return f"{vm_info.datacenter}:{vm_info.name}"
        return vm_info.name

    async def get_collectable_vms(
        self,
        connection_id: int,
    ) -> List[dict]:
        """Get list of VMs available for collection.

        Args:
            connection_id: Connection ID

        Returns:
            List of VM info
        """
        # Check if resources are collected
        connection = await self.connection_repo.get_by_id(connection_id)
        if not connection:
            raise NotFoundError(f"Connection {connection_id} not found")

        # Query VMs from database
        from sqlalchemy import select
        from app.models import VM as VMModel

        result = await self.session.execute(
            select(VMModel).where(VMModel.connection_id == connection_id)
        )
        vms = result.scalars().all()

        return [
            {
                "id": vm.id,
                "name": vm.name,
                "datacenter": vm.datacenter,
                "vmKey": vm.vm_key,
                "cpuCount": vm.cpu_count,
                "memoryGb": round(vm.memory_bytes / (1024**3), 2),
                "powerState": vm.power_state,
                "connectionState": vm.connection_state,
                "hostIp": vm.host_ip,
            }
            for vm in vms
        ]
