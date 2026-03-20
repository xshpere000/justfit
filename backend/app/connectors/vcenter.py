"""vCenter Connector - VMware vSphere/vCenter platform adapter.

数据单位转换说明（所有指标统一转换为 VMMetrics 定义的存储单位）:
    vCenter API 原始单位    →  存储单位              转换公式
    ──────────────────────────────────────────────────────────────
    CPU (usagemhz)    MHz  →  MHz                   无需转换
    Memory (consumed) KB   →  bytes                 * 1024
    Disk (read/write) KB/s →  bytes/s              * 1024
    Network (bytesRx/Tx) KB/s →  bytes/s          * 1024

重要说明:
    1. 磁盘和网络 I/O 只在使用 20 秒间隔时可用（vCenter 限制）
    2. virtualDisk 组是 VM 级别计数器，disk 组是主机级别
    3. memory_bytes 存储的是 bytes（不是 MB），需注意单位
"""

import asyncio
import socket
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict
from collections import defaultdict

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
        timeout: int = 10,
    ) -> None:
        """Initialize vCenter connector.

        Args:
            host: vCenter host
            port: vCenter port
            username: Username
            password: Password
            insecure: Skip SSL verification
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.insecure = insecure
        self.timeout = timeout
        self._service_instance: Optional[vim.ServiceInstance] = None
        self._content: Optional[vim.ServiceInstanceContent] = None
        self._counter_map_cache: Optional[dict] = None  # 缓存 perfCounter 映射，避免每台VM重复调用

    async def _connect(self) -> vim.ServiceInstanceContent:
        """Establish connection to vCenter.

        Returns:
            Service instance content
        """
        if self._content is not None:
            return self._content

        loop = asyncio.get_running_loop()

        def _do_connect() -> vim.ServiceInstance:
            # 设置 socket 超时（SmartConnect 内部使用 SSL socket）
            socket.setdefaulttimeout(self.timeout)
            return SmartConnect(
                host=self.host,
                port=self.port,
                user=self.username,
                pwd=self.password,
                disableSslCertValidation=self.insecure,
            )

        try:
            # 使用 asyncio.wait_for 添加超时控制
            self._service_instance = await asyncio.wait_for(
                loop.run_in_executor(None, _do_connect),
                timeout=self.timeout
            )
            self._content = self._service_instance.RetrieveContent()
            logger.info("vcenter_connected", host=self.host)
            return self._content
        except asyncio.TimeoutError:
            logger.error("vcenter_connection_timeout", host=self.host, timeout=self.timeout)
            raise ConnectionError(f"连接 {self.host}:{self.port} 超时（{self.timeout}秒）")
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
        loop = asyncio.get_running_loop()

        def _fetch() -> List[ClusterInfo]:
            cluster_view = content.viewManager.CreateContainerView(
                content.rootFolder, [vim.ClusterComputeResource], True
            )
            clusters = []
            for cluster in cluster_view.view:
                total_cpu = sum(host.summary.hardware.cpuMhz * host.summary.hardware.numCpuThreads
                              for host in cluster.host)
                total_memory = sum(host.summary.hardware.memorySize
                                for host in cluster.host)

                total_storage = 0
                used_storage = 0
                seen_datastores = set()
                if cluster.datastore:
                    for ds in cluster.datastore:
                        try:
                            ds_id = ds.info.url if ds.info and ds.info.url else ds.name
                            if ds_id in seen_datastores:
                                continue
                            seen_datastores.add(ds_id)
                            capacity = ds.summary.capacity or 0
                            free_space = ds.summary.freeSpace or 0
                            total_storage += capacity
                            used_storage += capacity - free_space
                        except Exception:
                            pass

                cluster_key = f"{cluster.name}"
                if cluster.parent and hasattr(cluster.parent, 'name'):
                    cluster_key = f"{cluster.parent.name}:{cluster.name}"

                clusters.append(ClusterInfo(
                    name=cluster.name,
                    datacenter=self._get_datacenter_name(cluster),
                    total_cpu=int(total_cpu),
                    total_memory=int(total_memory),
                    total_storage=int(total_storage),
                    used_storage=int(used_storage),
                    num_hosts=len(cluster.host) if cluster.host else 0,
                    num_vms=sum(len(h.vm) for h in cluster.host if h.vm) if cluster.host else 0,
                    cluster_key=cluster_key,
                ))

            cluster_view.Destroy()
            return clusters

        clusters = await loop.run_in_executor(None, _fetch)
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
        loop = asyncio.get_running_loop()

        def _fetch() -> List[HostInfo]:
            host_view = content.viewManager.CreateContainerView(
                content.rootFolder, [vim.HostSystem], True
            )
            hosts = []
            for host in host_view.view:
                ip_address = self._get_host_ip(host)
                cluster_name = ""
                if host.parent and isinstance(host.parent, vim.ClusterComputeResource):
                    cluster_name = host.parent.name

                hosts.append(HostInfo(
                    name=host.name,
                    datacenter=self._get_datacenter_name(host),
                    cluster_name=cluster_name,
                    ip_address=ip_address,
                    cpu_cores=host.summary.hardware.numCpuCores,
                    cpu_mhz=host.summary.hardware.cpuMhz,
                    memory_bytes=host.summary.hardware.memorySize,
                    num_vms=len(host.vm) if host.vm else 0,
                    power_state=host.summary.runtime.connectionState,
                    overall_status=host.summary.overallStatus,
                ))

            host_view.Destroy()
            return hosts

        hosts = await loop.run_in_executor(None, _fetch)
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

        # 将 VM 列表转为 list（避免迭代器问题）
        vm_list = list(vm_view.view)
        vm_view.Destroy()

        # 并发处理所有 VM 信息提取
        vms = await self._fetch_vms_concurrent(vm_list)

        logger.info("vcenter_get_vms_success", count=len(vms))
        return vms

    async def _fetch_vms_concurrent(self, vm_list: List) -> List[VMInfo]:
        """并发提取 VM 信息，使用 host IP 缓存。

        Args:
            vm_list: VM 对象列表

        Returns:
            VM 信息列表
        """
        # Host IP 缓存：多个 VM 可能共享同一个 host
        host_ip_cache: Dict[str, str] = {}

        # 先收集所有唯一的 host（用于缓存预热）
        unique_hosts = {}
        for vm in vm_list:
            try:
                if vm.runtime and vm.runtime.host and hasattr(vm.runtime.host, 'name'):
                    host_name = vm.runtime.host.name
                    if host_name and host_name not in unique_hosts:
                        unique_hosts[host_name] = vm.runtime.host
            except Exception:
                pass

        # 并发预加载所有 host IP（最多 10 个并发）
        if unique_hosts:
            semaphore = asyncio.Semaphore(10)

            async def load_host_ip(host_name: str, host_obj) -> None:
                async with semaphore:
                    try:
                        ip = await asyncio.get_running_loop().run_in_executor(
                            None, lambda: self._get_host_ip(host_obj)
                        )
                        host_ip_cache[host_name] = ip
                    except Exception:
                        host_ip_cache[host_name] = ""

            await asyncio.gather(*[
                load_host_ip(name, obj) for name, obj in unique_hosts.items()
            ])
            logger.debug("vcenter_host_ip_cache_loaded", count=len(host_ip_cache))

        # 并发提取 VM 信息（最多 20 个并发）
        semaphore = asyncio.Semaphore(20)

        async def extract_vm_info(vm: vim.VirtualMachine) -> Optional[VMInfo]:
            """提取单个 VM 的信息（在线程池中执行同步操作）"""
            # 使用 run_in_executor 在线程池中执行属性访问
            loop = asyncio.get_running_loop()

            def _extract() -> Optional[VMInfo]:
                try:
                    power_state_str = vm.runtime.powerState if vm.runtime else ""
                    connection_state_str = vm.runtime.connectionState if vm.runtime else ""

                    # 检查连接状态，忽略孤立、未连接等异常状态
                    if connection_state_str and connection_state_str.lower() in ["orphaned", "disconnected", "inaccessible", "invalid"]:
                        return None

                    # 获取时间信息
                    create_time = vm.config.createDate if vm.config else None

                    # 计算开机时长
                    uptime_duration = None
                    downtime_duration = None

                    if vm.summary and vm.summary.quickStats:
                        uptime_seconds = vm.summary.quickStats.uptimeSeconds
                        if uptime_seconds is not None and uptime_seconds > 0:
                            uptime_duration = uptime_seconds

                    # 计算关机时长
                    if power_state_str and power_state_str.lower() in ["poweredoff", "powered off"]:
                        boot_time = vm.runtime.bootTime if vm.runtime else None
                        if boot_time is None:
                            downtime_duration = 2592000  # 30天
                        else:
                            now = datetime.now(timezone.utc)
                            if boot_time.tzinfo is None:
                                boot_time = boot_time.replace(tzinfo=timezone.utc)
                            duration = now - boot_time
                            downtime_duration = int(duration.total_seconds())

                    # 采集磁盘使用量
                    disk_usage_bytes = 0
                    if vm.summary and vm.summary.storage:
                        disk_usage_bytes = vm.summary.storage.committed or 0

                    # 从缓存获取 host IP
                    host_ip = ""
                    if vm.runtime and vm.runtime.host and hasattr(vm.runtime.host, 'name'):
                        host_name = vm.runtime.host.name
                        host_ip = host_ip_cache.get(host_name, "")

                    return VMInfo(
                        name=vm.name,
                        datacenter=self._get_datacenter_name(vm),
                        uuid=vm.config.uuid,
                        cpu_count=vm.config.hardware.numCPU,
                        memory_bytes=vm.config.hardware.memoryMB * 1024 * 1024,
                        power_state=vm.runtime.powerState,
                        guest_os=vm.summary.guest.guestFullName if vm.summary.guest else None,
                        ip_address=vm.summary.guest.ipAddress if vm.summary.guest else None,
                        host_name=vm.runtime.host.name if vm.runtime and vm.runtime.host else None,
                        host_ip=host_ip,
                        connection_state=vm.runtime.connectionState if vm.runtime else "",
                        overall_status=vm.summary.overallStatus,
                        disk_usage_bytes=disk_usage_bytes,
                        vm_create_time=create_time,
                        uptime_duration=uptime_duration,
                        downtime_duration=downtime_duration,
                    )
                except Exception as e:
                    logger.warning("vcenter_vm_extract_failed", vm_name="unknown", error=str(e))
                    return None

            async with semaphore:
                try:
                    return await loop.run_in_executor(None, _extract)
                except Exception as e:
                    logger.warning("vcenter_vm_extract_coroutine_failed", vm_name="unknown", error=str(e))
                    return None

        # 并发提取所有 VM 信息
        results = await asyncio.gather(*[extract_vm_info(vm) for vm in vm_list])

        # 过滤掉 None 值（被过滤的 VM）
        vms = [vm for vm in results if vm is not None]
        return vms

    async def get_vm_metrics(
        self,
        datacenter: str,
        vm_name: str,
        vm_uuid: str,
        start_time: datetime,
        end_time: datetime,
        cpu_count: int,
        total_memory_bytes: int = 0,  # 参数用于接口一致性，暂不使用
    ) -> VMMetrics:
        """Get VM performance metrics using hybrid strategy.

        Hybrid approach:
        1. Try PerfManager for full metrics (CPU, memory, disk, network)
        2. Fall back to quickStats for basic metrics (CPU, memory only)
        3. Combine data from both sources for maximum coverage

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

        # Get VM power state
        vm_power_state = vm.runtime.powerState if vm.runtime else None
        logger.info("vcenter_vm_power_state", vm_name=vm_name, power_state=str(vm_power_state))

        # Step 1: Try to get full metrics from PerfManager
        # This works for running VMs and provides disk/network I/O
        perf_metrics = await self._get_perf_manager_metrics(
            vm=vm,
            vm_name=vm_name,
            cpu_count=cpu_count,
            content=content,
            start_time=start_time,
            end_time=end_time,
        )

        # Step 2: If PerfManager succeeded, check if we have usable data
        if perf_metrics:
            # Check if we have any meaningful data
            has_data = (
                perf_metrics.cpu_samples > 0 or
                perf_metrics.memory_samples > 0 or
                perf_metrics.disk_samples > 0 or
                perf_metrics.network_samples > 0 or
                perf_metrics.hourly_series is not None  # 有 hourly_series 数据也应该返回
            )

            if has_data:
                logger.info(
                    "vcenter_metrics_from_perf_manager",
                    vm_name=vm_name,
                    cpu_mhz=perf_metrics.cpu_mhz,
                    cpu_samples=perf_metrics.cpu_samples,
                    memory_samples=perf_metrics.memory_samples,
                    disk_samples=perf_metrics.disk_samples,
                    network_samples=perf_metrics.network_samples,
                    hourly_series_hours=len(perf_metrics.hourly_series) if perf_metrics.hourly_series else 0,
                )
                return perf_metrics

        # Step 3: Fall back to quickStats for basic metrics
        logger.info("vcenter_fallback_to_quick_stats", vm_name=vm_name)
        quick_metrics = await self._get_quick_stats_metrics(
            vm=vm,
            vm_name=vm_name,
            cpu_count=cpu_count,
        )

        # Step 4: Combine data - use quickStats for CPU/memory, zeros for I/O
        return quick_metrics

    async def _get_perf_manager_metrics(
        self,
        vm: vim.VirtualMachine,
        vm_name: str,
        cpu_count: int,
        content: vim.ServiceInstanceContent,
        start_time: datetime,
        end_time: datetime,
    ) -> Optional[VMMetrics]:
        """Get full metrics from PerfManager including disk and network I/O.

        Uses hybrid query strategy:
        - CPU/Memory: Use historical intervals (300s, 1800s, etc.) for better coverage
        - Disk/Network: Use 20s interval (vCenter only provides I/O data at this interval)

        Args:
            vm: Virtual machine object
            vm_name: VM name
            cpu_count: Number of CPUs
            content: vCenter service content
            start_time: Start of time range for historical data
            end_time: End of time range for historical data

        Returns:
            VMMetrics or None if PerfManager fails
        """
        loop = asyncio.get_running_loop()
        perf_manager = content.perfManager

        if not perf_manager:
            logger.warning("vcenter_no_perf_manager", vm_name=vm_name)
            return None

        # Build counter ID map
        counter_ids = await self._build_counter_map(perf_manager, vm_name)

        # Check if we found essential counters
        required_counters = ['cpu', 'memory']
        missing_counters = [c for c in required_counters if c not in counter_ids]
        if missing_counters:
            logger.warning(
                "vcenter_missing_required_counters",
                vm_name=vm_name,
                missing=missing_counters,
            )
            return None

        # Optional counters for I/O
        has_disk = 'disk_read' in counter_ids and 'disk_write' in counter_ids
        has_network = 'net_rx' in counter_ids and 'net_tx' in counter_ids

        logger.info(
            "vcenter_counter_availability",
            vm_name=vm_name,
            has_cpu='cpu' in counter_ids,
            has_memory='memory' in counter_ids,
            has_disk=has_disk,
            has_network=has_network,
        )

        # 固定使用天级（86400s）采集 CPU/内存，与 UIS 保持一致
        time_diff_seconds = (end_time - start_time).total_seconds()
        time_diff_days = time_diff_seconds / 86400
        historical_interval = 86400

        logger.info(
            "vcenter_daily_query_strategy",
            vm_name=vm_name,
            days_requested=f"{time_diff_days:.1f}",
            historical_interval=historical_interval,
        )

        # Query 1: CPU and Memory with daily interval
        cpu_memory_metric_ids = [
            vim.PerformanceManager.MetricId(counterId=counter_ids['cpu'], instance=""),
            vim.PerformanceManager.MetricId(counterId=counter_ids['memory'], instance=""),
        ]

        cpu_memory_stats = await self._query_perf_stats(
            perf_manager, vm, cpu_memory_metric_ids,
            interval_id=historical_interval,
            max_sample=min(10000, int(time_diff_seconds / historical_interval) + 10),
            start_time=start_time,
            end_time=end_time,
        )

        # Query 2: Disk and Network with 20s interval
        # vCenter only provides I/O data at 20s interval
        io_metric_ids = []
        if has_disk:
            io_metric_ids.extend([
                vim.PerformanceManager.MetricId(counterId=counter_ids['disk_read'], instance=""),
                vim.PerformanceManager.MetricId(counterId=counter_ids['disk_write'], instance=""),
            ])
        if has_network:
            io_metric_ids.extend([
                vim.PerformanceManager.MetricId(counterId=counter_ids['net_rx'], instance=""),
                vim.PerformanceManager.MetricId(counterId=counter_ids['net_tx'], instance=""),
            ])

        io_stats = None
        if io_metric_ids:
            io_stats = await self._query_perf_stats(
                perf_manager, vm, io_metric_ids,
                interval_id=20,
                max_sample=300,  # 300 samples * 20s = ~1.6 hours
                start_time=start_time,
                end_time=end_time,
            )

        # Check if we have at least some data
        if not cpu_memory_stats:
            logger.warning("vcenter_no_cpu_memory_data", vm_name=vm_name)
            return None

        # Extract metric values
        cpu_values, memory_values = self._extract_metric_values(
            cpu_memory_stats, counter_ids.get('cpu'), counter_ids.get('memory')
        )

        disk_read_values, disk_write_values, net_rx_values, net_tx_values = [], [], [], []
        if io_stats:
            disk_read_values, disk_write_values = self._extract_metric_values(
                io_stats, counter_ids.get('disk_read'), counter_ids.get('disk_write')
            )
            net_rx_values, net_tx_values = self._extract_metric_values(
                io_stats, counter_ids.get('net_rx'), counter_ids.get('net_tx')
            )

        # Get host CPU and VM memory for unit conversion
        host_cpu_mhz = 0
        if vm.runtime and vm.runtime.host:
            host_cpu_mhz = vm.runtime.host.summary.hardware.cpuMhz

        vm_memory_mb = vm.summary.config.memorySizeMB if vm.summary and vm.summary.config else 0

        # Calculate averages — filter out negative values (vCenter uses negatives for unavailable counters)
        cpu_avg = sum(cpu_values) / len(cpu_values) if cpu_values else 0
        memory_avg = sum(memory_values) / len(memory_values) if memory_values else 0
        disk_read_valid = [v for v in disk_read_values if v >= 0]
        disk_write_valid = [v for v in disk_write_values if v >= 0]
        net_rx_valid = [v for v in net_rx_values if v >= 0]
        net_tx_valid = [v for v in net_tx_values if v >= 0]
        disk_read_avg = sum(disk_read_valid) / len(disk_read_valid) if disk_read_valid else 0
        disk_write_avg = sum(disk_write_valid) / len(disk_write_valid) if disk_write_valid else 0
        net_rx_avg = sum(net_rx_valid) / len(net_rx_valid) if net_rx_valid else 0
        net_tx_avg = sum(net_tx_valid) / len(net_tx_valid) if net_tx_valid else 0

        # Build hourly series (using CPU/Memory historical data)
        hourly_series = self._build_hourly_series(
            cpu_memory_stats, counter_ids, cpu_values, memory_values,
            disk_read_values, disk_write_values, net_rx_values, net_tx_values,
        )

        # ============================================================
        # 单位转换 - 统一转换为 VMMetrics 定义的存储单位
        # ============================================================
        # CPU: cpu.usagemhz 返回值已经是 MHz，无需转换
        cpu_mhz = cpu_avg if cpu_avg > 0 else 0

        # Memory: mem.consumed 返回 KB，转换为 bytes
        # 注意：VMMetrics.memory_bytes 的单位是 bytes，不是 MB
        memory_bytes_value = memory_avg * 1024 if memory_avg > 0 else 0

        # Disk: virtualDisk.read/write 返回 KB/s，转换为 bytes/s
        disk_read_bytes_per_sec = int(disk_read_avg * 1024)
        disk_write_bytes_per_sec = int(disk_write_avg * 1024)

        # Network: net.bytesRx/bytesTx 返回 KB/s，转换为 bytes/s
        net_rx_bytes_per_sec = int(net_rx_avg * 1024)
        net_tx_bytes_per_sec = int(net_tx_avg * 1024)

        metrics = VMMetrics(
            cpu_mhz=cpu_mhz,
            memory_bytes=memory_bytes_value,         # bytes (不是 MB)
            disk_read_bytes_per_sec=disk_read_bytes_per_sec,
            disk_write_bytes_per_sec=disk_write_bytes_per_sec,
            net_rx_bytes_per_sec=net_rx_bytes_per_sec,
            net_tx_bytes_per_sec=net_tx_bytes_per_sec,
            cpu_samples=len(cpu_values),
            memory_samples=len(memory_values),
            disk_samples=len(disk_read_values),
            network_samples=len(net_rx_values),
            hourly_series=hourly_series if hourly_series else None,
        )

        logger.info(
            "vcenter_perf_manager_success",
            vm_name=vm_name,
            cpu_mhz=metrics.cpu_mhz,
            memory_mb=metrics.memory_bytes // (1024 * 1024),  # 转换为 MB 用于日志
            disk_read_kb=metrics.disk_read_bytes_per_sec // 1024,    # 转换为 KB 用于日志
            disk_write_kb=metrics.disk_write_bytes_per_sec // 1024,
            net_rx_kb=metrics.net_rx_bytes_per_sec // 1024,
            net_tx_kb=metrics.net_tx_bytes_per_sec // 1024,
            cpu_samples=metrics.cpu_samples,
            disk_samples=metrics.disk_samples,
            network_samples=metrics.network_samples,
            hourly_series_hours=len(hourly_series) if hourly_series else 0,
        )

        return metrics

    async def _query_perf_stats(
        self,
        perf_manager: vim.PerformanceManager,
        vm: vim.VirtualMachine,
        metric_ids: List,
        interval_id: int,
        max_sample: int,
        start_time: datetime = None,
        end_time: datetime = None,
    ) -> Optional[vim.PerformanceManager.EntityMetric]:
        """Query performance stats from vCenter.

        Args:
            perf_manager: Performance manager
            vm: Virtual machine
            metric_ids: List of MetricId to query
            interval_id: Sampling interval in seconds
            max_sample: Maximum number of samples
            start_time: Start time for historical data (optional)
            end_time: End time for historical data (optional)

        Returns:
            EntityMetric or None
        """
        loop = asyncio.get_running_loop()

        query_spec_params = {
            "entity": vm,
            "metricId": metric_ids,
            "intervalId": interval_id,
            "maxSample": max_sample,
        }

        if start_time and end_time:
            query_spec_params["startTime"] = start_time
            query_spec_params["endTime"] = end_time

        query_spec = vim.PerformanceManager.QuerySpec(**query_spec_params)

        try:
            perf_stats = await loop.run_in_executor(
                None,
                lambda: perf_manager.QueryStats(querySpec=[query_spec])
            )
            if perf_stats and perf_stats[0]:
                return perf_stats[0]
            return None
        except Exception as e:
            logger.warning(
                "vcenter_query_stats_failed",
                vm_name=vm.name,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def _extract_metric_values(
        self,
        stats: vim.PerformanceManager.EntityMetric,
        counter_id1: int,
        counter_id2: int = None,
    ) -> tuple:
        """Extract metric values from stats.

        Args:
            stats: Performance stats
            counter_id1: First counter ID to extract
            counter_id2: Second counter ID to extract (optional)

        Returns:
            Tuple of (values1, values2) or (values1,) if counter_id2 is None
        """
        values1, values2 = [], []

        if not stats or not stats.value:
            return (values1, values2) if counter_id2 else (values1,)

        for stat in stats.value:
            if stat.id.counterId == counter_id1:
                values1 = [v for v in (stat.value or []) if v is not None]
            elif counter_id2 and stat.id.counterId == counter_id2:
                values2 = [v for v in (stat.value or []) if v is not None]

        return (values1, values2) if counter_id2 else (values1,)

    def _build_hourly_series(
        self,
        stats: vim.PerformanceManager.EntityMetric,
        counter_ids: dict,
        cpu_values: List[float],
        memory_values: List[float],
        disk_read_values: List[float],
        disk_write_values: List[float],
        net_rx_values: List[float],
        net_tx_values: List[float],
    ) -> Optional[List[tuple]]:
        """Build hourly time series from sample data.

        Args:
            stats: Performance stats with sample info
            counter_ids: Counter ID mapping
            cpu_values: CPU values list
            memory_values: Memory values list
            disk_read_values: Disk read values list
            disk_write_values: Disk write values list
            net_rx_values: Network RX values list
            net_tx_values: Network TX values list

        Returns:
            List of hourly tuples or None
        """
        from collections import defaultdict

        sample_infos = stats.sampleInfo if stats.sampleInfo else []
        if not sample_infos:
            return None

        # Map counter IDs to their value lists
        value_map = {
            counter_ids.get('cpu'): cpu_values,
            counter_ids.get('memory'): memory_values,
            counter_ids.get('disk_read'): disk_read_values,
            counter_ids.get('disk_write'): disk_write_values,
            counter_ids.get('net_rx'): net_rx_values,
            counter_ids.get('net_tx'): net_tx_values,
        }

        # Build a mapping from sample index to all metric values
        counter_to_values = {}
        for stat in stats.value:
            counter_to_values[stat.id.counterId] = stat.value or []

        # Aggregate by hour
        hour_buckets = defaultdict(lambda: {
            "cpu": [], "memory": [], "disk_read": [],
            "disk_write": [], "net_rx": [], "net_tx": []
        })

        for idx, sample_info in enumerate(sample_infos):
            if sample_info.timestamp:
                timestamp_dt = sample_info.timestamp.replace(minute=0, second=0, microsecond=0)

                # Extract values at this index for each counter
                cpu_val = counter_to_values.get(counter_ids.get('cpu'), [])[idx] if counter_ids.get('cpu') in counter_to_values else (cpu_values[idx] if idx < len(cpu_values) else 0)
                mem_val = counter_to_values.get(counter_ids.get('memory'), [])[idx] if counter_ids.get('memory') in counter_to_values else (memory_values[idx] if idx < len(memory_values) else 0)
                disk_read_val = counter_to_values.get(counter_ids.get('disk_read'), [])[idx] if counter_ids.get('disk_read') in counter_to_values else (disk_read_values[idx] if idx < len(disk_read_values) else 0)
                disk_write_val = counter_to_values.get(counter_ids.get('disk_write'), [])[idx] if counter_ids.get('disk_write') in counter_to_values else (disk_write_values[idx] if idx < len(disk_write_values) else 0)
                net_rx_val = counter_to_values.get(counter_ids.get('net_rx'), [])[idx] if counter_ids.get('net_rx') in counter_to_values else (net_rx_values[idx] if idx < len(net_rx_values) else 0)
                net_tx_val = counter_to_values.get(counter_ids.get('net_tx'), [])[idx] if counter_ids.get('net_tx') in counter_to_values else (net_tx_values[idx] if idx < len(net_tx_values) else 0)

                bucket = hour_buckets[timestamp_dt]
                # CPU: usagemhz 返回 MHz，无需转换
                bucket["cpu"].append(cpu_val if cpu_val and cpu_val > 0 else 0)
                # Memory: mem.consumed 返回 KB，转换为 bytes (与 VMMetrics.memory_bytes 单位一致)
                bucket["memory"].append(mem_val * 1024 if mem_val and mem_val > 0 else 0)  # KB to bytes
                # Disk: KB/s to bytes/s
                bucket["disk_read"].append(disk_read_val * 1024 if disk_read_val and disk_read_val > 0 else 0)
                bucket["disk_write"].append(disk_write_val * 1024 if disk_write_val and disk_write_val > 0 else 0)
                # Network: KB/s to bytes/s
                bucket["net_rx"].append(net_rx_val * 1024 if net_rx_val and net_rx_val > 0 else 0)
                bucket["net_tx"].append(net_tx_val * 1024 if net_tx_val and net_tx_val > 0 else 0)

        # Calculate stats for each hour
        hourly_series = []
        for hour_dt in sorted(hour_buckets.keys()):
            bucket = hour_buckets[hour_dt]
            timestamp_ms = int(hour_dt.timestamp() * 1000)

            cpu_vals = bucket["cpu"]
            mem_vals = bucket["memory"]
            disk_read_vals = bucket["disk_read"]
            disk_write_vals = bucket["disk_write"]
            net_rx_vals = bucket["net_rx"]
            net_tx_vals = bucket["net_tx"]

            hourly_series.append((
                timestamp_ms,
                sum(cpu_vals) / len(cpu_vals) if cpu_vals else 0,
                min(cpu_vals) if cpu_vals else 0,
                max(cpu_vals) if cpu_vals else 0,
                sum(mem_vals) / len(mem_vals) if mem_vals else 0,
                min(mem_vals) if mem_vals else 0,
                max(mem_vals) if mem_vals else 0,
                sum(disk_read_vals) / len(disk_read_vals) if disk_read_vals else 0,
                sum(disk_write_vals) / len(disk_write_vals) if disk_write_vals else 0,
                sum(net_rx_vals) / len(net_rx_vals) if net_rx_vals else 0,
                sum(net_tx_vals) / len(net_tx_vals) if net_tx_vals else 0,
            ))

        return hourly_series if hourly_series else None

    async def _get_quick_stats_metrics(
        self,
        vm: vim.VirtualMachine,
        vm_name: str,
        cpu_count: int,
    ) -> VMMetrics:
        """Get basic metrics from quickStats (CPU and memory only)."""
        loop = asyncio.get_running_loop()

        def _fetch():
            if not (vm.summary and vm.summary.quickStats):
                return None, 0, 0
            qs = vm.summary.quickStats
            host_cpu_mhz = 0
            if vm.runtime and vm.runtime.host and vm.runtime.host.summary:
                host_cpu_mhz = vm.runtime.host.summary.hardware.cpuMhz
            cpu_usage_mhz = qs.overallCpuUsage if qs.overallCpuUsage else 0
            memory_usage_bytes = (qs.guestMemoryUsage or 0) * 1024 * 1024
            return True, cpu_usage_mhz, memory_usage_bytes

        ok, cpu_usage_mhz, memory_usage_bytes = await loop.run_in_executor(None, _fetch)

        if not ok:
            logger.warning("vcenter_no_quick_stats", vm_name=vm_name)
            cpu_usage_mhz = 0
            memory_usage_bytes = 0

        logger.info(
            "vcenter_quick_stats_success",
            vm_name=vm_name,
            cpu_mhz=cpu_usage_mhz,
            memory_mb=memory_usage_bytes // (1024 * 1024),
        )

        return VMMetrics(
            cpu_mhz=cpu_usage_mhz,
            memory_bytes=memory_usage_bytes,
            disk_read_bytes_per_sec=0,
            disk_write_bytes_per_sec=0,
            net_rx_bytes_per_sec=0,
            net_tx_bytes_per_sec=0,
            cpu_samples=1,
            memory_samples=1,
            disk_samples=0,
            network_samples=0,
        )

    async def _build_counter_map(
        self,
        perf_manager: vim.PerformanceManager,
        vm_name: str,
    ) -> dict[str, int]:
        """Build counter ID map from PerfManager.

        Args:
            perf_manager: Performance manager
            vm_name: VM name for logging

        Returns:
            Dictionary mapping counter names to IDs
        """
        # 缓存：perfCounter 在同一连接内不会变化，无需每台VM重复获取
        if self._counter_map_cache is not None:
            return self._counter_map_cache

        loop = asyncio.get_running_loop()

        def _fetch_counters():
            return perf_manager.perfCounter

        counter_info = await loop.run_in_executor(None, _fetch_counters)
        if not counter_info:
            logger.warning("vcenter_no_counter_info", vm_name=vm_name)
            return {}

        counter_ids = {}
        counter_sample = []

        for counter in counter_info:
            group_key = counter.groupInfo.key if counter.groupInfo else ""
            name_key = counter.nameInfo.key if counter.nameInfo else ""
            rollup_type = counter.rollupType if hasattr(counter, 'rollupType') else None

            if len(counter_sample) < 10:
                unit_info = counter.unitInfo if hasattr(counter, 'unitInfo') else {}
                counter_sample.append({
                    "group": group_key,
                    "name": name_key,
                    "rollup": str(rollup_type),
                    "unit": str(unit_info) if unit_info else "",
                    "key": counter.key
                })

            if rollup_type != vim.PerformanceManager.CounterInfo.RollupType.average:
                continue

            if group_key == 'cpu' and name_key == 'usagemhz':
                counter_ids['cpu'] = counter.key
            elif group_key == 'mem' and name_key == 'consumed':
                counter_ids['memory'] = counter.key
            elif group_key == 'virtualDisk' and name_key == 'read':
                counter_ids['disk_read'] = counter.key
            elif group_key == 'virtualDisk' and name_key == 'write':
                counter_ids['disk_write'] = counter.key
            elif group_key == 'net' and name_key == 'bytesRx':
                counter_ids['net_rx'] = counter.key
            elif group_key == 'net' and name_key == 'bytesTx':
                counter_ids['net_tx'] = counter.key

        logger.info(
            "vcenter_counter_sample",
            vm_name=vm_name,
            sample=counter_sample[:5],
        )
        logger.info(
            "vcenter_counter_ids_found",
            vm_name=vm_name,
            counters=list(counter_ids.keys()),
        )

        self._counter_map_cache = counter_ids
        return counter_ids

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

        loop = asyncio.get_running_loop()
        search_index = content.searchIndex

        def _find():
            return search_index.FindByUuid(None, vm_uuid, True, False)

        return await loop.run_in_executor(None, _find)
