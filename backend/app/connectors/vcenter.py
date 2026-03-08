"""vCenter Connector - VMware vSphere/vCenter platform adapter."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional

import structlog
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

from .base import Connector, ClusterInfo, HostInfo, VMInfo, VMMetrics


logger = structlog.get_logger()


class VCenterConnector(Connector):
    """Connector for VMware vCenter/vSphere."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        insecure: bool = False,
    ) -> None:
        """Initialize vCenter connector.

        Args:
            host: vCenter host
            port: vCenter port
            username: Username
            password: Password
            insecure: Skip SSL verification
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.insecure = insecure
        self._service_instance: Optional[vim.ServiceInstance] = None
        self._content: Optional[vim.ServiceInstanceContent] = None

    async def _connect(self) -> vim.ServiceInstanceContent:
        """Establish connection to vCenter.

        Returns:
            Service instance content
        """
        if self._content is not None:
            return self._content

        loop = asyncio.get_event_loop()

        def _do_connect() -> vim.ServiceInstance:
            return SmartConnect(
                host=self.host,
                port=self.port,
                user=self.username,
                pwd=self.password,
                disableSslCertValidation=self.insecure,
            )

        try:
            self._service_instance = await loop.run_in_executor(None, _do_connect)
            self._content = self._service_instance.RetrieveContent()
            logger.info("vcenter_connected", host=self.host)
            return self._content
        except Exception as e:
            logger.error("vcenter_connection_failed", host=self.host, error=str(e))
            raise

    async def close(self) -> None:
        """Close connection to vCenter."""
        if self._service_instance:
            Disconnect(self._service_instance)
            self._service_instance = None
            self._content = None
            logger.info("vcenter_disconnected", host=self.host)

    async def test_connection(self) -> dict:
        """Test connection to vCenter.

        Returns:
            Dictionary with success status and message
        """
        try:
            await self._connect()
            return {"success": True, "message": "Connected to vCenter"}
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {str(e)}"}

    async def get_clusters(self) -> List[ClusterInfo]:
        """Get all clusters.

        Returns:
            List of cluster information
        """
        logger.debug("vcenter_get_clusters_starting")
        await self._connect()
        content = self._content

        cluster_view = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.ClusterComputeResource], True
        )

        clusters = []
        for cluster in cluster_view.view:
            # Calculate totals
            total_cpu = sum(host.summary.hardware.cpuMhz * host.summary.hardware.numCpuThreads
                          for host in cluster.host)
            total_memory = sum(host.summary.hardware.memorySize
                            for host in cluster.host)

            # Generate cluster key
            cluster_key = f"{cluster.name}"
            if cluster.parent and hasattr(cluster.parent, 'name'):
                cluster_key = f"{cluster.parent.name}:{cluster.name}"

            clusters.append(ClusterInfo(
                name=cluster.name,
                datacenter=self._get_datacenter_name(cluster),
                total_cpu=int(total_cpu),
                total_memory=int(total_memory),
                num_hosts=len(cluster.host) if cluster.host else 0,
                num_vms=getattr(cluster.summary, 'numVMs', getattr(cluster.summary, 'numVm', 0)),
                cluster_key=cluster_key,
            ))

        cluster_view.Destroy()
        logger.info("vcenter_get_clusters_success", count=len(clusters))
        return clusters

    async def get_hosts(self) -> List[HostInfo]:
        """Get all hosts.

        Returns:
            List of host information
        """
        logger.debug("vcenter_get_hosts_starting")
        await self._connect()
        content = self._content

        host_view = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.HostSystem], True
        )

        hosts = []
        for host in host_view.view:
            # Get IP from vmk0 (management network)
            ip_address = self._get_host_ip(host)

            hosts.append(HostInfo(
                name=host.name,
                datacenter=self._get_datacenter_name(host),
                ip_address=ip_address,
                cpu_cores=host.summary.hardware.numCpuCores,
                cpu_mhz=host.summary.hardware.cpuMhz,
                memory_bytes=host.summary.hardware.memorySize,
                num_vms=len(host.vm) if host.vm else 0,
                power_state=host.summary.runtime.connectionState,
                overall_status=host.summary.overallStatus,
            ))

        host_view.Destroy()
        logger.info("vcenter_get_hosts_success", count=len(hosts))
        return hosts

    async def get_vms(self) -> List[VMInfo]:
        """Get all virtual machines.

        Returns:
            List of VM information
        """
        logger.debug("vcenter_get_vms_starting")
        await self._connect()
        content = self._content

        vm_view = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.VirtualMachine], True
        )

        vms = []
        for vm in vm_view.view:
            # Generate vm_key
            vm_key = self._generate_vm_key(vm)

            vms.append(VMInfo(
                name=vm.name,
                datacenter=self._get_datacenter_name(vm),
                uuid=vm.config.uuid,
                cpu_count=vm.config.hardware.numCPU,
                memory_bytes=vm.config.hardware.memoryMB * 1024 * 1024,
                power_state=vm.runtime.powerState,
                guest_os=vm.summary.guest.guestFullName,
                ip_address=vm.summary.guest.ipAddress or "",
                host_name=vm.runtime.host.name if vm.runtime.host else "",
                host_ip="",  # Will be filled by caller
                connection_state=vm.runtime.connectionState,
                overall_status=vm.summary.overallStatus,
            ))

        vm_view.Destroy()
        logger.info("vcenter_get_vms_success", count=len(vms))
        return vms

    async def get_vm_metrics(
        self,
        datacenter: str,
        vm_name: str,
        vm_uuid: str,
        start_time: datetime,
        end_time: datetime,
        cpu_count: int,
    ) -> VMMetrics:
        """Get VM performance metrics.

        Args:
            datacenter: Datacenter name
            vm_name: VM name
            vm_uuid: VM UUID
            start_time: Start of time range
            end_time: End of time range
            cpu_count: Number of CPUs for normalization

        Returns:
            VM metrics
        """
        logger.debug(
            "vcenter_get_vm_metrics_starting",
            vm_name=vm_name,
            vm_uuid=vm_uuid,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
        )

        await self._connect()
        content = self._content

        # Find VM by UUID
        vm = await self._find_vm_by_uuid(vm_uuid)
        if not vm:
            logger.error("vcenter_vm_not_found", vm_uuid=vm_uuid, vm_name=vm_name)
            raise ValueError(f"VM not found: {vm_uuid}")

        # First try to use quickStats (simpler, always available)
        if vm.summary and vm.summary.quickStats:
            qs = vm.summary.quickStats
            # Get host CPU for MHz calculation
            host_cpu_mhz = 0
            if vm.runtime and vm.runtime.host:
                host_cpu_mhz = vm.runtime.host.summary.hardware.cpuMhz

            # Get VM memory for percentage calculation
            vm_memory_bytes = vm.summary.config.memorySizeMB * 1024 * 1024 if vm.summary.config.memorySizeMB else 0

            # Calculate values from quickStats
            cpu_usage_mhz = qs.overallCpuUsage * 1000000 if qs.overallCpuUsage else 0  # MHz to Hz
            cpu_usage_percent = qs.overallCpuUsage / (cpu_count * host_cpu_mhz) * 100 if host_cpu_mhz > 0 and qs.overallCpuUsage else 0
            memory_usage_bytes = (qs.guestMemoryUsage or 0) * 1024 * 1024  # MB to bytes
            memory_usage_percent = (qs.guestMemoryUsage / vm.summary.config.memorySizeMB * 100) if vm.summary.config.memorySizeMB else 0

            logger.info(
                "vcenter_quick_stats",
                vm_name=vm_name,
                cpu_usage=qs.overallCpuUsage,
                guest_memory=qs.guestMemoryUsage,
                host_cpu_mhz=host_cpu_mhz,
            )

            return VMMetrics(
                cpu_mhz=qs.overallCpuUsage if qs.overallCpuUsage else 0,
                memory_bytes=memory_usage_bytes,
                disk_read_bytes_per_sec=0,  # Not available in quickStats
                disk_write_bytes_per_sec=0,  # Not available in quickStats
                net_rx_bytes_per_sec=0,  # Not available in quickStats
                net_tx_bytes_per_sec=0,  # Not available in quickStats
                cpu_samples=1,
                memory_samples=1,
                disk_samples=0,
                network_samples=0,
            )

        # Fall back to PerfManager if quickStats not available
        logger.warning("vcenter_no_quick_stats", vm_name=vm_name)

        # Use realtime interval (20 seconds) for full metrics
        # Historical interval only provides CPU and memory
        loop = asyncio.get_event_loop()

        # Get metrics using PerfManager
        perf_manager = content.perfManager

        # Define metric counters
        counter_info = perf_manager.perfCounter
        logger.info("vcenter_perf_counters", count=len(counter_info) if counter_info else 0)

        counter_keys = {
            'cpu': 'cpu.usage.average',
            'memory': 'mem.usage.average',
            'disk_read': 'disk.read.average',
            'disk_write': 'disk.write.average',
            'net_rx': 'net.received.average',
            'net_tx': 'net.transmitted.average',
        }

        # Build counter ID map
        counter_ids = {}
        counter_sample = []
        for counter in counter_info:
            group_key = counter.groupInfo.key if counter.groupInfo else ""
            name_key = counter.nameInfo.key if counter.nameInfo else ""
            # Collect sample of first counters
            if len(counter_sample) < 5:
                counter_sample.append({"group": group_key, "name": name_key, "key": counter.key})
            if group_key == 'cpu' and name_key == 'usage':
                counter_ids['cpu'] = counter.key
            elif group_key == 'mem' and name_key == 'usage':
                counter_ids['memory'] = counter.key
            elif group_key == 'disk' and name_key == 'read':
                counter_ids['disk_read'] = counter.key
            elif group_key == 'disk' and name_key == 'write':
                counter_ids['disk_write'] = counter.key
            elif group_key == 'net' and name_key == 'received':
                counter_ids['net_rx'] = counter.key
            elif group_key == 'net' and name_key == 'transmitted':
                counter_ids['net_tx'] = counter.key

        logger.info("vcenter_counter_sample", sample=counter_sample[:3])
        logger.info("vcenter_counter_ids", found=list(counter_ids.keys()))

        # Check if we found CPU counter
        if 'cpu' not in counter_ids:
            logger.warning("cpu_counter_not_found", counter_keys=list(counter_ids.keys()))
            # Return zero metrics if counter not found
            return VMMetrics(
                cpu_mhz=0,
                memory_bytes=0,
                disk_read_bytes_per_sec=0,
                disk_write_bytes_per_sec=0,
                net_rx_bytes_per_sec=0,
                net_tx_bytes_per_sec=0,
                cpu_samples=0,
                memory_samples=0,
                disk_samples=0,
                network_samples=0,
            )

        # Create query spec for all realtime metrics
        # Note: Don't set startTime/endTime for realtime metrics, vCenter will return latest data
        metric_ids = [
            vim.PerformanceManager.MetricId(counterId=counter_ids['cpu'], instance="*"),
            vim.PerformanceManager.MetricId(counterId=counter_ids['memory'], instance="*"),
            vim.PerformanceManager.MetricId(counterId=counter_ids['disk_read'], instance="*"),
            vim.PerformanceManager.MetricId(counterId=counter_ids['disk_write'], instance="*"),
            vim.PerformanceManager.MetricId(counterId=counter_ids['net_rx'], instance="*"),
            vim.PerformanceManager.MetricId(counterId=counter_ids['net_tx'], instance="*"),
        ]
        spec = vim.PerformanceManager.QuerySpec(
            entity=vm,
            metricId=metric_ids,
            intervalId=20,  # Realtime interval (20 seconds)
            #startTime=start_time,
            #endTime=end_time,
        )

        try:
            perf_stats = await loop.run_in_executor(None, perf_manager.QueryStats, [spec])
            logger.info("vcenter_query_stats_result", vm_name=vm_name, has_stats=len(perf_stats) if perf_stats else 0)
        except Exception as e:
            logger.warning("vcenter_query_stats_failed", vm_name=vm_name, error=str(e))
            perf_stats = []

        # Initialize metrics
        cpu_values = []
        memory_values = []
        disk_read_values = []
        disk_write_values = []
        net_rx_values = []
        net_tx_values = []

        if perf_stats and perf_stats[0]:
            for stat in perf_stats[0].value:
                counter_id = stat.id.counterId
                values = stat.value if stat.value else []

                if counter_id == counter_ids['cpu']:
                    cpu_values = values
                elif counter_id == counter_ids['memory']:
                    memory_values = values
                elif counter_id == counter_ids['disk_read']:
                    disk_read_values = values
                elif counter_id == counter_ids['disk_write']:
                    disk_write_values = values
                elif counter_id == counter_ids['net_rx']:
                    net_rx_values = values
                elif counter_id == counter_ids['net_tx']:
                    net_tx_values = values

        # Calculate averages
        cpu_avg = sum(cpu_values) / len(cpu_values) if cpu_values else 0
        memory_avg = sum(memory_values) / len(memory_values) if memory_values else 0
        disk_read_avg = sum(disk_read_values) / len(disk_read_values) if disk_read_values else 0
        disk_write_avg = sum(disk_write_values) / len(disk_write_values) if disk_write_values else 0
        net_rx_avg = sum(net_rx_values) / len(net_rx_values) if net_rx_values else 0
        net_tx_avg = sum(net_tx_values) / len(net_tx_values) if net_tx_values else 0

        # Get host CPU for MHz calculation
        host_cpu_mhz = 0
        if vm.runtime.host:
            host_cpu_mhz = vm.runtime.host.summary.hardware.cpuMhz

        # Get VM memory for percentage calculation
        vm_memory_bytes = vm.summary.config.memorySizeMB * 1024 * 1024 if vm.summary.config.memorySizeMB else 0

        # Convert to appropriate units
        cpu_mhz = cpu_avg * host_cpu_mhz / 100 if host_cpu_mhz > 0 else 0
        memory_bytes = memory_avg * vm_memory_bytes / 100 if vm_memory_bytes > 0 else 0

        metrics = VMMetrics(
            cpu_mhz=cpu_mhz,
            memory_bytes=memory_bytes,
            disk_read_bytes_per_sec=disk_read_avg * 1024,  # KB to bytes
            disk_write_bytes_per_sec=disk_write_avg * 1024,
            net_rx_bytes_per_sec=net_rx_avg * 1024,
            net_tx_bytes_per_sec=net_tx_avg * 1024,
            cpu_samples=len(cpu_values),
            memory_samples=len(memory_values),
            disk_samples=len(disk_read_values),
            network_samples=len(net_rx_values),
        )

        logger.info(
            "vcenter_get_vm_metrics_success",
            vm_name=vm_name,
            cpu_samples=len(cpu_values),
            cpu_avg=cpu_avg,
            memory_avg=memory_avg,
        )

        return metrics

    def _get_datacenter_name(self, entity) -> str:
        """Get datacenter name for an entity.

        Args:
            entity: vSphere entity

        Returns:
            Datacenter name
        """
        parent = entity.parent
        while parent:
            if isinstance(parent, vim.Datacenter):
                return parent.name
            parent = parent.parent
        return ""

    def _get_host_ip(self, host: vim.HostSystem) -> str:
        """Get host IP from management network interface.

        Args:
            host: Host system

        Returns:
            IP address
        """
        try:
            # Try to get IP from vmk0 (management network)
            if host.config and host.config.network and host.config.network.vnic:
                for vnic in host.config.network.vnic:
                    if vnic.device == "vmk0" and vnic.spec.ip:
                        return vnic.spec.ip.ipAddress
        except Exception:
            pass

        # Fallback to ManagementServerIp
        if host.summary.managementServerIp:
            return host.summary.managementServerIp

        return ""

    def _generate_vm_key(self, vm: vim.VirtualMachine) -> str:
        """Generate unique key for VM.

        Args:
            vm: Virtual machine

        Returns:
            VM key in format "uuid:<lowercase_uuid>"
        """
        if vm.config and vm.config.uuid:
            return f"uuid:{vm.config.uuid.lower()}"
        return vm.name

    async def _find_vm_by_uuid(self, vm_uuid: str) -> Optional[vim.VirtualMachine]:
        """Find VM by UUID.

        Args:
            vm_uuid: VM UUID

        Returns:
            VM object or None
        """
        await self._connect()
        content = self._content

        loop = asyncio.get_event_loop()
        search_index = content.searchIndex

        def _find():
            return search_index.FindByUuid(None, vm_uuid, True, False)

        return await loop.run_in_executor(None, _find)
