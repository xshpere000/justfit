"""H3C UIS Connector - H3C UIS cloud platform adapter."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

import httpx
import structlog

from .base import Connector, ClusterInfo, HostInfo, VMInfo, VMMetrics


logger = structlog.get_logger()


class UISConnector(Connector):
    """Connector for H3C UIS cloud platform."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        insecure: bool = False,
    ) -> None:
        """Initialize UIS connector.

        Args:
            host: UIS host
            port: UIS port
            username: Username
            password: Password
            insecure: Skip SSL verification
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.insecure = insecure
        self._base_url = f"https://{host}:{port}/uis"
        self._client: Optional[httpx.AsyncClient] = None
        self._host_cache: Dict[int, str] = {}  # host_id -> host_ip

    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client with active session.

        Returns:
            HTTP client
        """
        if self._client is not None:
            return self._client

        verify = not self.insecure

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            verify=verify,
            timeout=30.0,
            follow_redirects=True,
        )

        # Login to establish session
        await self._login()

        return self._client

    async def _login(self) -> None:
        """Login to UIS platform."""
        client = self._client

        response = await client.post(
            "/spring_check",
            data={
                "username": self.username,
                "password": self.password,
            },
        )
        response.raise_for_status()
        logger.info("uis_logged_in", host=self.host)

    async def close(self) -> None:
        """Close connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("uis_disconnected", host=self.host)

    async def test_connection(self) -> dict:
        """Test connection to UIS.

        Returns:
            Dictionary with success status and message
        """
        try:
            client = await self._get_client()
            response = await client.get("/vm/list/summary")
            response.raise_for_status()
            return {"success": True, "message": "Connected to UIS"}
        except Exception as e:
            logger.error("uis_connection_failed", host=self.host, error=str(e))
            return {"success": False, "message": f"Connection failed: {str(e)}"}

    async def get_clusters(self) -> List[ClusterInfo]:
        """Get all clusters.

        Returns:
            List of cluster information
        """
        # UIS may not have cluster concept, return empty list
        # or map to equivalent resource group
        return []

    async def get_hosts(self) -> List[HostInfo]:
        """Get all hosts.

        Returns:
            List of host information
        """
        client = await self._get_client()

        try:
            response = await client.get("/host/list")
            response.raise_for_status()
            data = response.json()

            # Build host cache for IP mapping
            self._host_cache.clear()

            hosts = []
            if data.get("success") and data.get("data"):
                for host_data in data["data"]:
                    host_id = host_data.get("hostId", 0)
                    host_ip = host_data.get("hostIp", "")
                    self._host_cache[host_id] = host_ip

                    hosts.append(HostInfo(
                        name=host_data.get("hostName", ""),
                        datacenter="",
                        ip_address=host_ip,
                        cpu_cores=host_data.get("cpuCores", 0),
                        cpu_mhz=host_data.get("cpuFrequency", 0),
                        memory_bytes=host_data.get("memorySize", 0) * 1024 * 1024 * 1024,
                        num_vms=host_data.get("vmCount", 0),
                        power_state="online" if host_data.get("status") == "running" else "offline",
                        overall_status="",
                    ))

            return hosts
        except Exception as e:
            logger.error("uis_get_hosts_failed", error=str(e))
            return []

    async def get_vms(self) -> List[VMInfo]:
        """Get all virtual machines.

        Returns:
            List of VM information
        """
        client = await self._get_client()

        try:
            response = await client.get("/vm/list/summary")
            response.raise_for_status()
            data = response.json()

            vms = []
            if data.get("success") and data.get("data"):
                for vm_data in data["data"]:
                    # Get host IP from cache
                    host_id = vm_data.get("hostId", 0)
                    host_ip = self._host_cache.get(host_id, "")

                    vms.append(VMInfo(
                        name=vm_data.get("vmName", ""),
                        datacenter="",
                        uuid=vm_data.get("vmUuid", ""),
                        cpu_count=vm_data.get("cpuCount", 0),
                        memory_bytes=vm_data.get("memorySize", 0) * 1024 * 1024 * 1024,
                        power_state=vm_data.get("powerStatus", "").lower(),
                        guest_os=vm_data.get("osType", ""),
                        ip_address=vm_data.get("ipAddress", ""),
                        host_name=vm_data.get("hostName", ""),
                        host_ip=host_ip,
                        connection_state="",
                        overall_status="",
                    ))

            return vms
        except Exception as e:
            logger.error("uis_get_vms_failed", error=str(e))
            return []

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
        client = await self._get_client()

        try:
            # Call UIS VM report API
            response = await client.post(
                "/vm/report",
                json={
                    "vmUuid": vm_uuid,
                    "startTime": start_time.isoformat(),
                    "endTime": end_time.isoformat(),
                },
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("success"):
                # Return empty metrics
                return VMMetrics(
                    cpu_mhz=0.0,
                    memory_bytes=0.0,
                    disk_read_bytes_per_sec=0.0,
                    disk_write_bytes_per_sec=0.0,
                    net_rx_bytes_per_sec=0.0,
                    net_tx_bytes_per_sec=0.0,
                    cpu_samples=0,
                    memory_samples=0,
                    disk_samples=0,
                    network_samples=0,
                )

            report = data.get("data", {})

            # Convert percentages to absolute values
            cpu_usage = report.get("cpuUsage", 0) / 100.0 * cpu_count
            memory_usage = report.get("memoryUsage", 0)

            return VMMetrics(
                cpu_mhz=cpu_usage,
                memory_bytes=memory_usage * 1024 * 1024,
                disk_read_bytes_per_sec=report.get("diskRead", 0.0) * 1024,
                disk_write_bytes_per_sec=report.get("diskWrite", 0.0) * 1024,
                net_rx_bytes_per_sec=report.get("netRx", 0.0) * 1024,
                net_tx_bytes_per_sec=report.get("netTx", 0.0) * 1024,
                cpu_samples=1 if cpu_usage > 0 else 0,
                memory_samples=1 if memory_usage > 0 else 0,
                disk_samples=1,
                network_samples=1,
            )
        except Exception as e:
            logger.error("uis_get_vm_metrics_failed", vm_uuid=vm_uuid, error=str(e))
            return VMMetrics(
                cpu_mhz=0.0,
                memory_bytes=0.0,
                disk_read_bytes_per_sec=0.0,
                disk_write_bytes_per_sec=0.0,
                net_rx_bytes_per_sec=0.0,
                net_tx_bytes_per_sec=0.0,
                cpu_samples=0,
                memory_samples=0,
                disk_samples=0,
                network_samples=0,
            )
