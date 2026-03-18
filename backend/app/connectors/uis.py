"""H3C UIS Connector - H3C UIS cloud platform adapter.

数据单位转换说明（所有指标统一转换为 VMMetrics 定义的存储单位）:
    UIS API 原始单位         →  存储单位              转换公式
    ──────────────────────────────────────────────────────────────
    CPU (百分比)      %     →  MHz                   % × cpu_count × host_cpu_mhz / 100
    Memory (百分比)   %     →  bytes                 % × vm_memory_bytes / 100
    Disk (rate)       KB/s  →  bytes/s              * 1024
    Network (rate)    Mbps  →  bytes/s              * 125000 (1 Mbps = 125000 bytes/s)

注意: 网络接口返回的是 Mbps（不是 MB/s），转换时需注意！
      1 Mbps = 1,000,000 bits/s = 125,000 bytes/s
"""

import asyncio
from datetime import datetime, timedelta, timezone
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

        login_params = {
            "encrypt": "false",
            "loginType": "authorCenter",
            "name": self.username,
            "password": self.password
        }

        response = await client.post(
            "/spring_check",
            params=login_params,
            headers={"Content-Type": "application/json"}
        )

        response.raise_for_status()

        # 检查登录是否成功
        login_info = response.json()
        if login_info.get('loginFailErrorCode'):
            error_msg = login_info.get('loginFailMessage', 'Unknown error')
            logger.error("uis_login_failed", host=self.host, error=error_msg)
            raise Exception(f"UIS login failed: {error_msg}")

        logger.info("uis_logged_in", host=self.host)

    async def close(self) -> None:
        """Close connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("uis_disconnected", host=self.host)

    async def _get_offline_vms(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get offline (powered off) VMs with shutdown time information.

        Args:
            start_time: Query start time
            end_time: Query end time

        Returns:
            List of offline VM data
        """
        client = await self._get_client()

        try:
            params = {
                'startTime': start_time.strftime('%Y-%m-%d 00:00:00'),
                'endTime': end_time.strftime('%Y-%m-%d 23:59:59'),
                'offset': 0,
                'limit': 1000
            }

            response = await client.get(
                "/resource/queryVmOffList",
                params=params
            )
            response.raise_for_status()
            data = response.json()

            if data.get("success"):
                return data.get("data", [])
            else:
                logger.warning("uis_query_offline_vms_failed", message=data.get("failureMessage"))
                return []
        except Exception as e:
            logger.error("uis_query_offline_vms_error", error=str(e))
            return []

    async def _get_running_vms(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get running VMs with boot time information.

        Args:
            start_time: Query start time
            end_time: Query end time

        Returns:
            List of running VM data
        """
        client = await self._get_client()

        try:
            params = {
                'startTime': start_time.strftime('%Y-%m-%d 00:00:00'),
                'endTime': end_time.strftime('%Y-%m-%d 23:59:59'),
                'offset': 0,
                'limit': 1000
            }

            # 尝试运行中VM列表API（推测的路径）
            response = await client.get(
                "/resource/queryVmRunningList",
                params=params
            )

            # 如果这个API不存在，返回空列表
            if response.status_code == 404:
                logger.info("uis_running_vm_api_not_found", message="Running VM API not available")
                return []

            response.raise_for_status()
            data = response.json()

            if data.get("success"):
                return data.get("data", [])
            else:
                logger.warning("uis_query_running_vms_failed", message=data.get("failureMessage"))
                return []
        except Exception as e:
            logger.debug("uis_query_running_vms_error", error=str(e))
            return []

    def _parse_datetime(self, datetime_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from UIS API.

        Args:
            datetime_str: Datetime string in ISO format or Unix timestamp (seconds/milliseconds)

        Returns:
            Parsed datetime or None
        """
        if not datetime_str:
            return None

        try:
            # Case 1: ISO 8601 format with 'T'
            if isinstance(datetime_str, str) and 'T' in datetime_str:
                from datetime import datetime as dt
                if datetime_str.endswith('Z'):
                    return dt.fromisoformat(datetime_str.replace('Z', '+00:00'))
                else:
                    return dt.fromisoformat(datetime_str)

            # Case 2: UIS format with space separator: "2026-03-06 21:44:26"
            elif isinstance(datetime_str, str) and ' ' in datetime_str and ':' in datetime_str:
                from datetime import datetime as dt
                # Parse "YYYY-MM-DD HH:MM:SS" format
                return dt.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')

            # Case 3: Unix timestamp (auto-detect seconds or milliseconds)
            # 如果值小于 10000000000（2286年），认为是秒；否则认为是毫秒
            elif isinstance(datetime_str, (int, float)):
                timestamp = datetime_str
                if timestamp < 10000000000:
                    # 秒
                    return datetime.fromtimestamp(timestamp, tz=timezone.utc)
                else:
                    # 毫秒
                    return datetime.fromtimestamp(timestamp / 1000.0, tz=timezone.utc)

            # Case 4: Unix timestamp string (auto-detect)
            elif isinstance(datetime_str, str):
                timestamp = int(datetime_str)
                if timestamp < 10000000000:
                    # 秒
                    return datetime.fromtimestamp(timestamp, tz=timezone.utc)
                else:
                    # 毫秒
                    return datetime.fromtimestamp(timestamp / 1000.0, tz=timezone.utc)
        except Exception as e:
            logger.warning("uis_datetime_parse_failed", value=str(datetime_str), error=str(e))

        return None

    async def test_connection(self) -> dict:
        """Test connection to UIS.

        Returns:
            Dictionary with success status and message
        """
        try:
            client = await self._get_client()
            # 使用正确的 API 路径（base_url 已经包含 /uis）
            response = await client.get(
                "/uis/btnSeries/resourceDetail",
                params={'offset': 0, 'limit': 1}
            )
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
        client = await self._get_client()

        try:
            # 直接调用 API，不传参数获取所有集群
            response = await client.get(
                "/uis/cluster/clusterInfo/detail"
            )

            if response.status_code != 200:
                logger.error("uis_get_clusters_failed", status_code=response.status_code)
                return []

            data = response.json()

            # 响应格式: {"data": [集群1, 集群2, ...]}
            if not isinstance(data, dict) or not data.get("data"):
                logger.warning("uis_get_clusters_invalid_response", response=str(data)[:200])
                return []

            cluster_list = data.get("data", [])
            clusters = []

            for detail in cluster_list:
                try:
                    # 解析存储和内存（带单位）
                    storage_str = detail.get("storage", "0GB")
                    memory_str = detail.get("memory", "0GB")

                    memory_bytes = self._parse_storage_string(memory_str)

                    # 计算 CPU 总量（核数转 MHz）
                    # 假设每个 CPU 核心频率约为 2600 MHz
                    cpu_cores = detail.get("cpu", 0)
                    cpu_mhz = cpu_cores * 2600  # 估算值

                    # 生成集群唯一标识
                    cluster_id = detail.get("id")
                    cluster_key = str(cluster_id) if cluster_id else f"cluster_{len(clusters)}"

                    # 采集存储池信息
                    total_storage = 0
                    used_storage = 0
                    try:
                        sf_response = await client.get(
                            "/uis/cluster/shareFile",
                            params={"clusterId": cluster_id, "sfOnly": "true"}
                        )
                        if sf_response.status_code == 200:
                            sf_data = sf_response.json()
                            if sf_data.get("success"):
                                for pool in sf_data.get("data", []):
                                    max_size_mb = pool.get("maxSize", 0)
                                    remain_size_mb = pool.get("remainSize", 0)
                                    total_storage += int(max_size_mb) * 1024 * 1024  # MB → bytes
                                    used_storage += int(max_size_mb - remain_size_mb) * 1024 * 1024
                    except Exception as e:
                        logger.warning("uis_get_cluster_storage_failed", cluster_id=cluster_id, error=str(e))

                    clusters.append(ClusterInfo(
                        name=detail.get("name", ""),
                        datacenter="",  # UIS 可能没有 datacenter 概念
                        total_cpu=cpu_mhz,
                        total_memory=memory_bytes,
                        total_storage=total_storage,
                        used_storage=used_storage,
                        num_hosts=detail.get("hostNum", 0),
                        num_vms=detail.get("vmTotal", 0),
                        cluster_key=cluster_key,
                    ))
                except Exception as e:
                    logger.warning("uis_parse_cluster_failed", detail=str(detail), error=str(e))
                    continue

            logger.info("uis_get_clusters_success", count=len(clusters))
            return clusters

        except Exception as e:
            logger.error("uis_get_clusters_error", error=str(e))
            return []

    def _parse_storage_string(self, storage_str: str) -> int:
        """解析存储字符串（带单位）为字节数。

        Args:
            storage_str: 存储字符串，如 "11.49GB", "1024MB", "1.5TB"

        Returns:
            存储字节数
        """
        if not storage_str:
            return 0

        storage_str = storage_str.strip().upper()

        # 提取数值和单位
        import re
        match = re.match(r'([\d.]+)(\w+)', storage_str)
        if not match:
            return 0

        value = float(match.group(1))
        unit = match.group(2)

        # 转换为字节
        multipliers = {
            'B': 1,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024,
            'TB': 1024 * 1024 * 1024 * 1024,
        }

        multiplier = multipliers.get(unit, 1)
        return int(value * multiplier)

    async def get_hosts(self) -> List[HostInfo]:
        """Get all hosts.

        Returns:
            List of host information
        """
        client = await self._get_client()

        try:
            # 并行调用三个 API：主机详情、主机状态、集群详情
            detail_response, summary_response, cluster_response = await asyncio.gather(
                client.get("/uis/host/detail"),
                client.get("/uis/host/summary"),
                client.get("/uis/cluster/clusterInfo/detail"),
                return_exceptions=True
            )

            # 处理主机详情响应
            if isinstance(detail_response, Exception) or detail_response.status_code != 200:
                logger.error("uis_get_hosts_failed", status_code=getattr(detail_response, 'status_code', 'error'))
                return []

            detail_data = detail_response.json()

            # 响应格式: {"data": [主机1, 主机2, ...]}
            if not isinstance(detail_data, dict) or not detail_data.get("data"):
                logger.warning("uis_get_hosts_invalid_response", response=str(detail_data)[:200])
                return []

            host_list = detail_data.get("data", [])

            # 处理主机状态响应，创建 hostId -> hostStatus 映射
            host_status_map = {}
            if not isinstance(summary_response, Exception) and summary_response.status_code == 200:
                summary_data = summary_response.json()
                if isinstance(summary_data, dict) and summary_data.get("data"):
                    for summary in summary_data.get("data", []):
                        host_id = summary.get("hostId")
                        host_status = summary.get("hostStatus")
                        if host_id is not None:
                            # hostStatus: 0=不正常, 1=正常
                            # 映射到标准状态字符串
                            host_status_map[host_id] = "green" if host_status == 1 else "red"

            # 处理集群数据，创建 cluster_id -> cluster_name 映射
            cluster_name_map = {}
            if not isinstance(cluster_response, Exception) and cluster_response.status_code == 200:
                cluster_data = cluster_response.json()
                if isinstance(cluster_data, dict) and cluster_data.get("data"):
                    for cluster in cluster_data.get("data", []):
                        cid = cluster.get("id")
                        if cid is not None:
                            cluster_name_map[cid] = cluster.get("name", "")

            hosts = []

            for host_data in host_list:
                try:
                    # 解析内存（带单位）
                    memory_str = host_data.get("memorySizeFormat")
                    memory_bytes = self._parse_storage_string(memory_str) if memory_str else 0

                    # 解析磁盘（带单位）
                    disk_str = host_data.get("diskSizeFormat")
                    # 注意：diskSizeFormat 可能为 null，尝试从其他字段获取
                    if not disk_str:
                        # 尝试从 storage 字段获取
                        storage_str = host_data.get("storage")
                        if storage_str and isinstance(storage_str, str):
                            # storage 可能是 "677.08GB" 这样的格式
                            disk_str = storage_str
                    disk_bytes = self._parse_storage_string(disk_str) if disk_str else 0

                    # CPU 频率（已经是 MHz）
                    cpu_mhz = host_data.get("cpuFrequence", 0)

                    # CPU 核心数
                    cpu_cores = host_data.get("cpuCount", 0)

                    # VM 数量
                    num_vms = host_data.get("vmNum", 0)

                    # 获取主机状态（从 summary 数据中获取）
                    host_id = host_data.get("id")
                    overall_status = host_status_map.get(host_id, "")

                    # 获取集群名称
                    cluster_id = host_data.get("clusterId")
                    cluster_name = cluster_name_map.get(cluster_id, "") if cluster_id is not None else ""

                    # 构造 HostInfo
                    hosts.append(HostInfo(
                        name=host_data.get("name", ""),
                        datacenter="",  # UIS 可能没有 datacenter 概念
                        cluster_name=cluster_name,
                        ip_address=host_data.get("ip", ""),
                        cpu_cores=cpu_cores,
                        cpu_mhz=cpu_mhz,
                        memory_bytes=memory_bytes,
                        num_vms=num_vms,
                        # UIS API 未提供主机电源状态字段
                        # 已测试的 API: /uis/host/detail, /uis/host/summary 均未返回 power_state
                        # 如需此字段，请联系 UIS 管理员获取相关 API 文档
                        power_state="",
                        overall_status=overall_status,  # 从 summary API 获取 hostStatus 映射
                    ))
                except Exception as e:
                    logger.warning("uis_parse_host_failed", host_data=str(host_data), error=str(e))
                    continue

            logger.info("uis_get_hosts_success", count=len(hosts))
            return hosts

        except Exception as e:
            logger.error("uis_get_hosts_error", error=str(e))
            return []

    async def get_vms(self) -> List[VMInfo]:
        """Get all virtual machines.

        Returns:
            List of VM information
        """
        client = await self._get_client()

        # Step 1: 获取基础VM列表
        try:
            response = await client.get(
                "/uis/btnSeries/resourceDetail",
                params={'offset': 0, 'limit': 1000}
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.error("uis_get_vms_failed", error=str(e))
            return []

        if not data.get("success"):
            logger.error("uis_get_vms_api_error", message=data.get("failureMessage"))
            return []

        # Step 2: 并行获取主机、集群、VM状态数据
        vm_status_map = {}  # vm_id -> {"overall_status": ..., "connection_state": ..., "host_id": ..., "cluster_id": ...}
        host_map = {}  # host_id -> host_info
        cluster_map = {}  # cluster_id -> cluster_info

        try:
            # 并行获取所有需要的数据
            hosts_response, clusters_response, status_response = await asyncio.gather(
                client.get("/uis/host/detail"),
                client.get("/uis/cluster/clusterInfo/detail"),
                client.get("/uis/vm/list/summary"),
                return_exceptions=True
            )

            # 处理主机数据，创建 host_id -> host_info 映射
            if not isinstance(hosts_response, Exception) and hosts_response.status_code == 200:
                hosts_data = hosts_response.json()
                if isinstance(hosts_data, dict) and hosts_data.get("data"):
                    for host in hosts_data.get("data", []):
                        host_id = host.get("id")
                        if host_id is not None:
                            host_map[host_id] = host

            # 处理集群数据，创建 cluster_id -> cluster_info 映射
            if not isinstance(clusters_response, Exception) and clusters_response.status_code == 200:
                clusters_data = clusters_response.json()
                if isinstance(clusters_data, dict) and clusters_data.get("data"):
                    for cluster in clusters_data.get("data", []):
                        cluster_id = cluster.get("id")
                        if cluster_id is not None:
                            cluster_map[cluster_id] = cluster

            # 处理VM状态数据，同时保存 hostId 和 clusterId
            if not isinstance(status_response, Exception) and status_response.status_code == 200:
                status_data = status_response.json()
                if status_data.get("statusType") == "OK":
                    entity = status_data.get("entity", {})
                    vm_status_list = entity.get("data", [])

                    # 映射 vmStatus 到标准 overall_status
                    # vmStatus: running→green, shutOff→gray, paused→yellow, unknown/ha_exception→red
                    overall_status_mapping = {
                        "running": "green",
                        "shutOff": "gray",
                        "paused": "yellow",
                        "unknown": "red",
                        "ha_exception": "red",
                    }

                    # 映射 vmStatus 到 connection_state
                    # unknown→disconnected(异常), 其他→connected(已连接)
                    connection_state_mapping = {
                        "unknown": "disconnected",
                    }
                    # 默认为 connected
                    default_connection_state = "connected"

                    for vm_info in vm_status_list:
                        vm_id = vm_info.get("id")
                        vm_status = vm_info.get("vmStatus")
                        if vm_id is not None:
                            vm_status_map[vm_id] = {
                                "overall_status": overall_status_mapping.get(vm_status, ""),
                                "connection_state": connection_state_mapping.get(vm_status, default_connection_state),
                                "host_id": vm_info.get("hostId"),  # 保存 hostId 用于关联主机 IP
                                "cluster_id": vm_info.get("clusterId"),  # 保存 clusterId 用于关联集群名称
                            }

                    logger.info("uis_vm_status_retrieved", count=len(vm_status_map))
        except Exception as e:
            logger.debug("uis_vm_status_fetch_failed", error=str(e))

        # Step 3: 并发获取所有VM的summary信息（包含时间字段）
        now = datetime.now(timezone.utc)
        vm_time_info = {}

        vm_list = data.get("data", [])
        logger.info("uis_fetching_vm_summaries", vm_count=len(vm_list))

        # 使用 Semaphore 限制并发数，避免过载 UIS API
        semaphore = asyncio.Semaphore(10)

        async def fetch_vm_summary(vm_data: dict) -> None:
            """并发获取单个 VM 的 summary 信息"""
            vm_id = vm_data.get("id")
            if not vm_id:
                return

            async with semaphore:
                try:
                    resp = await client.get(f"/uis/vm/{vm_id}/summary")
                    if resp.status_code == 200:
                        summary_data = resp.json()
                        if summary_data.get("success") and summary_data.get("data"):
                            summary = summary_data["data"]

                            # 初始化 vm_time_info
                            if vm_id not in vm_time_info:
                                vm_time_info[vm_id] = {}

                            # 提取磁盘使用量（storage 字段，如 "120.00GB"）
                            storage_str = summary.get("storage")
                            if storage_str and isinstance(storage_str, str):
                                vm_time_info[vm_id]['disk_usage_bytes'] = self._parse_storage_string(storage_str)

                            # 提取创建时间
                            create_time_str = summary.get("createTime")
                            if create_time_str:
                                create_time = self._parse_datetime(create_time_str)
                                vm_time_info[vm_id]['vm_create_time'] = create_time

                            # 对于开机VM，使用 uptime（分钟）转换为秒
                            uptime_minutes = summary.get("uptime")
                            if uptime_minutes is not None and uptime_minutes > 0:
                                uptime_duration = uptime_minutes * 60
                                vm_time_info[vm_id]['uptime_duration'] = uptime_duration
                                logger.debug("uis_vm_uptime_retrieved",
                                           vm_id=vm_id,
                                           uptime_minutes=uptime_minutes,
                                           uptime_seconds=uptime_duration)

                            # 对于关机VM，使用 lastOffTime 计算关机时长
                            last_off_time_timestamp = summary.get("lastOffTime")
                            if last_off_time_timestamp and last_off_time_timestamp > 0:
                                last_off_time = self._parse_datetime(last_off_time_timestamp)
                                if last_off_time:
                                    if last_off_time.tzinfo is None:
                                        last_off_time = last_off_time.replace(tzinfo=timezone.utc)

                                    downtime = now - last_off_time
                                    downtime_duration = int(downtime.total_seconds())
                                    vm_time_info[vm_id]['downtime_duration'] = downtime_duration
                                    logger.debug("uis_vm_downtime_calculated",
                                               vm_id=vm_id,
                                               last_off_time=last_off_time.isoformat(),
                                               downtime_seconds=downtime_duration)
                except Exception as e:
                    logger.debug("uis_vm_summary_failed", vm_id=vm_id, error=str(e))

        # 并发执行所有 VM summary 请求
        await asyncio.gather(*[fetch_vm_summary(vm_data) for vm_data in vm_list], return_exceptions=True)

        # Step 3: 构建VM信息列表
        vms = []
        for vm_data in data.get("data", []):
            vm_id = vm_data.get("id")
            status = vm_data.get("status", "").lower()

            # 从时间信息映射中获取数据
            time_info = vm_time_info.get(vm_id, {})

            # 确定电源状态
            if status == "running":
                power_state = "poweredon"
            elif status == "shutoff" or status == "shutoff":
                power_state = "poweredoff"
            else:
                power_state = status

            # 直接从API获取时长，不需要计算
            create_time = time_info.get('vm_create_time')
            uptime_duration = time_info.get('uptime_duration')  # 开机VM的uptime（秒）
            downtime_duration = time_info.get('downtime_duration')  # 关机VM的offPeriod（秒）

            # 从状态映射中获取健康状态、连接状态和关联ID
            status_info = vm_status_map.get(vm_id, {})
            overall_status = status_info.get("overall_status", "")
            connection_state = status_info.get("connection_state", "")
            vm_host_id = status_info.get("host_id")
            vm_cluster_id = status_info.get("cluster_id")

            # 通过 host_id 获取主机 IP
            host_ip = ""
            if vm_host_id is not None:
                host_info = host_map.get(vm_host_id)
                if host_info:
                    host_ip = host_info.get("ip", "")

            # 通过 cluster_id 获取集群名称作为 datacenter
            datacenter = ""
            if vm_cluster_id is not None:
                cluster_info = cluster_map.get(vm_cluster_id)
                if cluster_info:
                    datacenter = cluster_info.get("name", "")

            # 从 VM summary 获取磁盘使用量（storage 字段，如 "120.00GB"）
            disk_usage_bytes = time_info.get('disk_usage_bytes', 0)

            vms.append(VMInfo(
                name=vm_data.get("name", ""),
                datacenter=datacenter,  # 从 cluster_id 关联的集群名称
                uuid=str(vm_id),  # 使用 id 作为 uuid
                cpu_count=vm_data.get("cpu", 0),
                memory_bytes=vm_data.get("mem", 0) * 1024 * 1024,  # MB to bytes
                power_state=power_state,
                guest_os=vm_data.get("system", ""),
                ip_address=vm_data.get("ip", ""),
                host_name=vm_data.get("host", ""),
                host_ip=host_ip,  # 通过 host_id 从主机映射中获取
                connection_state=connection_state,  # 从 vmStatus 映射：unknown→disconnected, 其他→connected
                overall_status=overall_status,  # 从 vmStatus 映射：running→green, shutOff→gray, etc.
                disk_usage_bytes=disk_usage_bytes,
                vm_create_time=create_time,
                uptime_duration=uptime_duration,
                downtime_duration=downtime_duration,
            ))

        logger.info("uis_get_vms_success", count=len(vms))
        return vms

    async def get_vm_metrics(
        self,
        datacenter: str,
        vm_name: str,
        vm_uuid: str,
        start_time: datetime,
        end_time: datetime,
        cpu_count: int,
        total_memory_bytes: int = 0,
    ) -> VMMetrics:
        """Get VM performance metrics with daily time series data.

        UIS API 数据采集策略（重要！请仔细阅读）：
        ----------------------------------------
        1. 数据粒度限制：
           - UIS 平台只保留最近约 30 小时的小时级历史数据
           - 超过 30 小时的数据，只有天级粒度可用
           - 因此本方法统一使用天级数据采集（cycle=1）

        2. cycle 参数说明：
           - cycle=0: 小时级数据
             * 时间格式: 'YYYY-MM-DD HH' (包含小时)
             * 数据限制: 最多返回 30 个小时数据点
             * 适用场景: 最近 1-2 天的查询
             * ❌ 问题: 查询 7 天只返回最近 30 小时（约 1.25 天）

           - cycle=1: 天级数据
             * 时间格式: 'YYYY-MM-DD' (只到日期)
             * 数据保留: 虚拟机运行期间的所有天数
             * 适用场景: 3 天以上的长期查询 ✅
             * 示例: 查询 7 天返回 7 天数据（如果 VM 运行了 7 天）

        3. 实测数据（2026-03-10 测试）：
           查询 7 天，cycle=0: 返回 31 个小时数据点（1.25 天）❌
           查询 7 天，cycle=1: 返回 4 个天数据点（4 天）✅
           结论: UIS 平台小时级数据只保留约 30 小时

        4. API 响应结构（嵌套格式）：
           [
             {
               "title": "平均值",
               "list": [
                 {"name": "2026-03-07", "rate": 34.57, "id": null, "medicalVm": false},
                 {"name": "2026-03-08", "rate": 1.21, ...}
               ]
             },
             {
               "title": "最大值",
               "list": [...]
             }
           ]
           → 只使用"平均值"的数据

        5. 对分析器的影响：
           ✅ 闲置VM检测: 无影响（30天平均值一致）
           ✅ 平台健康评分: 无影响（基于当前状态）
           ⚠️  资源闲置优化: 中等影响（错过日内峰值）
           ❌ 使用模式识别: 受限（无法识别日内模式）

        6. 最佳实践：
           - 统一使用 cycle=1（天级）获取 30 天数据
           - 不使用 cycle=0（数据量太少，只 30 小时）
           - 在报告中标明"基于天级数据"

        Args:
            datacenter: Datacenter name (not used for UIS)
            vm_name: VM name (not used for UIS)
            vm_uuid: VM UUID (used as domainId)
            start_time: Start of time range
            end_time: End of time range
            cpu_count: Number of CPUs for normalization

        Returns:
            VM metrics with raw_series containing all data points
        """
        client = await self._get_client()

        try:
            # 统一使用天级数据采集（cycle=1）
            # 原因: UIS 平台小时级数据只保留最近约 30 小时
            #      对于 7 天以上的查询，cycle=0 只能返回 1.25 天的数据
            #      使用 cycle=1 可以获取完整的天级历史数据
            cycle = 1
            start_time_str = start_time.strftime('%Y-%m-%d')
            end_time_str = end_time.strftime('%Y-%m-%d')

            logger.info(
                "uis_metrics_collection",
                vm_uuid=vm_uuid,
                cycle=1,
                granularity="daily",
                start_time=start_time_str,
                end_time=end_time_str,
                note="UIS platform only retains ~30 hours of hourly data, using daily for 30-day queries"
            )

            # domainId should be the VM ID as integer
            try:
                domain_id = int(vm_uuid)
            except (ValueError, TypeError):
                logger.error("uis_invalid_vm_uuid", vm_uuid=vm_uuid, error="Cannot convert to int")
                return VMMetrics(
                    cpu_mhz=0.0, memory_bytes=0.0,
                    disk_read_bytes_per_sec=0.0, disk_write_bytes_per_sec=0.0,
                    net_rx_bytes_per_sec=0.0, net_tx_bytes_per_sec=0.0,
                    cpu_samples=0, memory_samples=0, disk_samples=0, network_samples=0,
                )

            # 获取主机 CPU 频率（用于与 vCenter 保持单位一致）
            host_cpu_mhz = 2600  # 默认值
            try:
                hosts_response = await client.get("/uis/host/detail")
                if hosts_response.status_code == 200:
                    hosts_data = hosts_response.json()
                    if isinstance(hosts_data, dict) and hosts_data.get("data"):
                        # 使用第一个主机的 CPU 频率（UIS 环境通常频率一致）
                        for host in hosts_data.get("data", []):
                            host_freq = host.get("cpuFrequence", 0)
                            if host_freq > 0:
                                host_cpu_mhz = host_freq
                                logger.debug("uis_host_cpu_mhz_found", host_cpu_mhz=host_cpu_mhz)
                                break
            except Exception as e:
                logger.warning("uis_fetch_host_cpu_failed", error=str(e))

            # Helper function to extract raw time series from UIS API response
            def extract_raw_series(data: list) -> Dict[str, float]:
                """从 UIS API 响应中提取原始时间序列数据

                UIS API 返回嵌套结构：
                [
                  {"title": "平均值", "list": [{"name": "2026-03-07", "rate": 34.57}, ...]},
                  {"title": "最大值", "list": [...]}
                ]

                我们只使用"平均值"的数据。

                返回格式: {时间字符串: 值}
                """
                time_series = {}
                if not data or not isinstance(data, list):
                    return time_series

                # UIS API 返回嵌套结构，需要找到"平均值"的数据
                for stat_item in data:
                    if not isinstance(stat_item, dict):
                        continue

                    # 查找"平均值"或"平均"的数据
                    title = stat_item.get("title", "")
                    if "平均" not in title:
                        continue

                    # 获取内层的 list
                    inner_list = stat_item.get("list")
                    if not inner_list or not isinstance(inner_list, list):
                        continue

                    # 提取时间序列数据
                    for data_point in inner_list:
                        if not isinstance(data_point, dict):
                            continue

                        time_str = data_point.get("name") or data_point.get("time", "")
                        rate = data_point.get("rate")

                        if time_str and rate is not None and rate >= 0:
                            time_series[time_str] = rate

                    # 找到平均值后就退出
                    break

                return time_series

            # 获取主机信息以获取 CPU 频率（创建主机 IP -> 频率的映射）
            host_cpu_mhz_map = {}  # host_ip -> cpu_mhz
            default_cpu_mhz = 2600
            try:
                hosts_response = await client.get("/uis/host/detail")
                if hosts_response.status_code == 200:
                    hosts_data = hosts_response.json()
                    if isinstance(hosts_data, dict) and hosts_data.get("data"):
                        for host in hosts_data.get("data", []):
                            host_ip = host.get("ip", "")
                            host_freq = host.get("cpuFrequence", 0)
                            if host_ip and host_freq > 0:
                                host_cpu_mhz_map[host_ip] = host_freq
                                logger.debug("uis_host_cpu_mhz", host_ip=host_ip, cpu_mhz=host_freq)
            except Exception as e:
                logger.warning("uis_fetch_host_cpu_failed", error=str(e))

            # 获取 VM 的 host IP
            vm_host_ip = ""
            try:
                vm_summary_response = await client.get(f"/uis/vm/{domain_id}/summary")
                if vm_summary_response.status_code == 200:
                    summary_data = vm_summary_response.json()
                    if summary_data.get("success") and summary_data.get("data"):
                        summary = summary_data["data"]
                        # UIS API 可能返回 hostIp 或类似字段
                        vm_host_ip = summary.get("hostIp") or summary.get("host_ip") or ""
                        logger.debug("uis_vm_host_ip", vm_uuid=vm_uuid, host_ip=vm_host_ip)
            except Exception as e:
                logger.warning("uis_fetch_vm_host_failed", vm_uuid=vm_uuid, error=str(e))

            # 根据 VM 所在主机 IP 获取 CPU 频率
            host_cpu_mhz = host_cpu_mhz_map.get(vm_host_ip, default_cpu_mhz)
            if vm_host_ip and host_cpu_mhz == default_cpu_mhz:
                logger.warning("uis_host_cpu_not_found", host_ip=vm_host_ip, using_default=default_cpu_mhz)

            logger.info("uis_using_cpu_mhz", vm_uuid=vm_uuid, host_ip=vm_host_ip, cpu_mhz=host_cpu_mhz)

            # Fetch CPU metrics
            cpu_time_series = {}

            try:
                cpu_response = await client.get(
                    "/uis/report/cpuMemVm",
                    params={
                        "domainId": domain_id,
                        "cycle": cycle,
                        "startTime": start_time_str,
                        "endTime": end_time_str,
                        "type": 0  # CPU
                    }
                )
                if cpu_response.status_code == 200:
                    cpu_data = cpu_response.json()
                    cpu_time_series = extract_raw_series(cpu_data)
            except Exception as e:
                logger.warning("uis_fetch_cpu_failed", vm_uuid=vm_uuid, error=str(e))

            # Fetch Memory metrics
            memory_time_series = {}
            try:
                mem_response = await client.get(
                    "/uis/report/cpuMemVm",
                    params={
                        "domainId": domain_id,
                        "cycle": cycle,
                        "startTime": start_time_str,
                        "endTime": end_time_str,
                        "type": 1  # Memory
                    }
                )
                if mem_response.status_code == 200:
                    mem_data = mem_response.json()
                    memory_time_series = extract_raw_series(mem_data)
            except Exception as e:
                logger.warning("uis_fetch_memory_failed", vm_uuid=vm_uuid, error=str(e))

            # Fetch Disk Read metrics
            disk_read_time_series = {}
            try:
                disk_read_response = await client.get(
                    "/uis/report/diskVm",
                    params={
                        "domainId": domain_id,
                        "cycle": cycle,
                        "startTime": start_time_str,
                        "endTime": end_time_str,
                        "type": 0  # Read
                    }
                )
                if disk_read_response.status_code == 200:
                    disk_read_data = disk_read_response.json()
                    disk_read_time_series = extract_raw_series(disk_read_data)
            except Exception as e:
                logger.warning("uis_fetch_disk_read_failed", vm_uuid=vm_uuid, error=str(e))

            # Fetch Disk Write metrics
            disk_write_time_series = {}
            try:
                disk_write_response = await client.get(
                    "/uis/report/diskVm",
                    params={
                        "domainId": domain_id,
                        "cycle": cycle,
                        "startTime": start_time_str,
                        "endTime": end_time_str,
                        "type": 1  # Write
                    }
                )
                if disk_write_response.status_code == 200:
                    disk_write_data = disk_write_response.json()
                    disk_write_time_series = extract_raw_series(disk_write_data)
            except Exception as e:
                logger.warning("uis_fetch_disk_write_failed", vm_uuid=vm_uuid, error=str(e))

            # Fetch Network Receive metrics
            net_rx_time_series = {}
            try:
                net_rx_response = await client.get(
                    "/uis/report/netSpVm",
                    params={
                        "domainId": domain_id,
                        "cycle": cycle,
                        "startTime": start_time_str,
                        "endTime": end_time_str,
                        "type": 0  # Receive
                    }
                )
                if net_rx_response.status_code == 200:
                    net_rx_data = net_rx_response.json()
                    net_rx_time_series = extract_raw_series(net_rx_data)
            except Exception as e:
                logger.warning("uis_fetch_net_rx_failed", vm_uuid=vm_uuid, error=str(e))

            # Fetch Network Transmit metrics
            net_tx_time_series = {}
            try:
                net_tx_response = await client.get(
                    "/uis/report/netSpVm",
                    params={
                        "domainId": domain_id,
                        "cycle": cycle,
                        "startTime": start_time_str,
                        "endTime": end_time_str,
                        "type": 1  # Transmit
                    }
                )
                if net_tx_response.status_code == 200:
                    net_tx_data = net_tx_response.json()
                    net_tx_time_series = extract_raw_series(net_tx_data)
            except Exception as e:
                logger.warning("uis_fetch_net_tx_failed", vm_uuid=vm_uuid, error=str(e))

            # 数据量检查和日志
            logger.info(
                "uis_api_response_summary",
                vm_uuid=vm_uuid,
                cycle=1,
                granularity="daily",
                cpu_points=len(cpu_time_series),
                memory_points=len(memory_time_series)
            )

            # 构建 hourly_series（格式与 vCenter 一致）
            hourly_series = []

            # 收集所有时间点（取各指标时间点的并集）
            all_time_keys = set()
            all_time_keys.update(cpu_time_series.keys())
            all_time_keys.update(memory_time_series.keys())
            all_time_keys.update(disk_read_time_series.keys())
            all_time_keys.update(disk_write_time_series.keys())
            all_time_keys.update(net_rx_time_series.keys())
            all_time_keys.update(net_tx_time_series.keys())

            # 按时间排序
            sorted_times = sorted(all_time_keys)

            # 构建按小时聚合的时间序列数据
            for time_str in sorted_times:
                try:
                    # 解析时间字符串 (格式: "yyyy-MM-dd HH" 或 "yyyy-MM-dd")
                    if " " in time_str:
                        dt = datetime.strptime(time_str, "%Y-%m-%d %H")
                    else:
                        dt = datetime.strptime(time_str, "%Y-%m-%d")
                        # 如果只有日期，默认使用 00:00
                        dt = dt.replace(hour=0, minute=0, second=0)

                    timestamp_ms = int(dt.timestamp() * 1000)

                    # 获取该时间点的各指标值（如果没有则用0）
                    cpu_rate = cpu_time_series.get(time_str, 0)
                    memory_rate = memory_time_series.get(time_str, 0)
                    disk_read_rate = disk_read_time_series.get(time_str, 0)
                    disk_write_rate = disk_write_time_series.get(time_str, 0)
                    net_rx_rate = net_rx_time_series.get(time_str, 0)
                    net_tx_rate = net_tx_time_series.get(time_str, 0)

                    # ============================================================
                    # 单位转换 - 统一转换为 VMMetrics 定义的存储单位
                    # ============================================================
                    # CPU: 百分比 × cpu_count × host_cpu_mhz / 100 → MHz
                    cpu_value = (cpu_rate / 100.0) * cpu_count * host_cpu_mhz if cpu_rate > 0 and cpu_count > 0 else 0.0

                    # Memory: 百分比 × vm_memory_bytes / 100 → bytes
                    # 注意：VMMetrics.memory_bytes 的单位是 bytes，不是 MB
                    memory_value = (memory_rate / 100.0) * total_memory_bytes if total_memory_bytes > 0 else 0.0

                    # Disk: KBps to bytes/s (1 KB = 1024 bytes)
                    disk_read_value = disk_read_rate * 1024
                    disk_write_value = disk_write_rate * 1024

                    # Network: Mbps to bytes/s (1 Mbps = 1,000,000 bits/s = 125,000 bytes/s)
                    net_rx_value = net_rx_rate * 125000
                    net_tx_value = net_tx_rate * 125000

                    # UIS API 每小时只返回一个值，所以 avg=min=max=该值
                    hourly_series.append((
                        timestamp_ms,
                        cpu_value, cpu_value, cpu_value,  # avg, min, max
                        memory_value, memory_value, memory_value,
                        disk_read_value, disk_write_value,
                        net_rx_value, net_tx_value,
                    ))
                except Exception as e:
                    logger.warning("uis_parse_time_failed", time_str=time_str, error=str(e))
                    continue

            # 计算总体平均值（用于兼容性）
            cpu_avg = sum(cpu_time_series.values()) / len(cpu_time_series) if cpu_time_series else 0
            memory_avg = sum(memory_time_series.values()) / len(memory_time_series) if memory_time_series else 0
            disk_read_avg = sum(disk_read_time_series.values()) / len(disk_read_time_series) if disk_read_time_series else 0
            disk_write_avg = sum(disk_write_time_series.values()) / len(disk_write_time_series) if disk_write_time_series else 0
            net_rx_avg = sum(net_rx_time_series.values()) / len(net_rx_time_series) if net_rx_time_series else 0
            net_tx_avg = sum(net_tx_time_series.values()) / len(net_tx_time_series) if net_tx_time_series else 0

            logger.info(
                "uis_vm_metrics_with_hourly_series",
                vm_uuid=vm_uuid,
                hours_count=len(hourly_series),
                cpu_points=len(cpu_time_series),
                memory_points=len(memory_time_series),
            )

            # ============================================================
            # 单位转换 - 统一转换为 VMMetrics 定义的存储单位
            # ============================================================
            # CPU: 百分比 × cpu_count × host_cpu_mhz / 100 → MHz
            cpu_mhz_value = cpu_avg / 100 * cpu_count * host_cpu_mhz if cpu_avg > 0 and cpu_count > 0 else 0.0

            # Memory: 百分比 × vm_memory_bytes / 100 → bytes
            # 注意：VMMetrics.memory_bytes 的单位是 bytes，不是 MB
            memory_bytes_value = memory_avg / 100 * total_memory_bytes if memory_avg > 0 and total_memory_bytes > 0 else 0.0

            # Disk: KBps to bytes/s
            disk_read_bytes_per_sec = disk_read_avg * 1024
            disk_write_bytes_per_sec = disk_write_avg * 1024

            # Network: Mbps to bytes/s
            net_rx_bytes_per_sec = net_rx_avg * 125000
            net_tx_bytes_per_sec = net_tx_avg * 125000

            return VMMetrics(
                cpu_mhz=cpu_mhz_value,
                memory_bytes=memory_bytes_value,              # bytes (不是 MB)
                disk_read_bytes_per_sec=disk_read_bytes_per_sec,
                disk_write_bytes_per_sec=disk_write_bytes_per_sec,
                net_rx_bytes_per_sec=net_rx_bytes_per_sec,
                net_tx_bytes_per_sec=net_tx_bytes_per_sec,
                cpu_samples=len(cpu_time_series),
                memory_samples=len(memory_time_series),
                disk_samples=len(disk_read_time_series) + len(disk_write_time_series),
                network_samples=len(net_rx_time_series) + len(net_tx_time_series),
                hourly_series=hourly_series if hourly_series else None,
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
