"""Connector Base - Abstract interface for cloud platforms.

数据单位规范（所有连接器必须遵守）:
    - CPU: MHz (兆赫兹)
    - Memory: bytes (字节)
    - Disk I/O: bytes/s (字节/秒)
    - Network I/O: bytes/s (字节/秒)

各平台 API 初始单位转换:
    VMware vCenter:
        - cpu.usagemhz: MHz (无需转换)
        - mem.consumed: KB → bytes (* 1024)
        - virtualDisk.read/write: KB/s → bytes/s (* 1024)
        - net.bytesRx/bytesTx: KB/s → bytes/s (* 1024)

    H3C UIS:
        - cpu: 百分比 → MHz (需乘以 host_cpu_mhz / 100)
        - memory: 百分比 → bytes (需乘以 vm_memory_bytes / 100)
        - diskSpVm rate: KB/s → bytes/s (* 1024)
        - netSpVm rate: Mbps → bytes/s (* 125000，注意是 1Mbps=125000 bytes/s)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class ClusterInfo:
    """集群信息.

    Attributes:
        name: 集群名称
        datacenter: 所属数据中心
        total_cpu: CPU 总频率 (MHz)
        total_memory: 内存总量 (bytes)
        num_hosts: 主机数量
        num_vms: 虚拟机数量
        cluster_key: 集群唯一标识
    """

    name: str
    datacenter: str
    total_cpu: int  # MHz
    total_memory: int  # bytes
    num_hosts: int
    num_vms: int
    cluster_key: str


@dataclass
class HostInfo:
    """主机信息.

    Attributes:
        name: 主机名称
        datacenter: 所属数据中心
        ip_address: 管理 IP 地址
        cpu_cores: CPU 物理核心数
        cpu_mhz: 单核频率 (MHz)
        memory_bytes: 内存容量 (bytes)
        num_vms: 虚拟机数量
        power_state: 电源状态
        overall_status: 整体状态
    """

    name: str
    datacenter: str
    ip_address: str
    cpu_cores: int
    cpu_mhz: int  # Single core frequency in MHz
    memory_bytes: int
    num_vms: int
    power_state: str
    overall_status: str


@dataclass
class VMInfo:
    """虚拟机信息.

    Attributes:
        name: 虚拟机名称
        datacenter: 所属数据中心
        uuid: 虚拟机 UUID
        cpu_count: CPU 数量 (vCPU)
        memory_bytes: 内存容量 (bytes)
        power_state: 电源状态 (poweredOn/poweredOff/suspended)
        guest_os: 客户操作系统
        ip_address: IP 地址
        host_name: 运行主机名称
        host_ip: 运行主机 IP
        connection_state: 连接状态
        overall_status: 整体状态
        vm_create_time: 创建时间
        uptime_duration: 开机时长（秒）
        downtime_duration: 关机时长（秒）
    """

    name: str
    datacenter: str
    uuid: str
    cpu_count: int
    memory_bytes: int
    power_state: str
    guest_os: str
    ip_address: str
    host_name: str
    host_ip: str
    connection_state: str
    overall_status: str
    vm_create_time: Optional[datetime] = None
    uptime_duration: Optional[int] = None  # seconds
    downtime_duration: Optional[int] = None  # seconds


@dataclass
class VMMetrics:
    """虚拟机性能指标.

    所有速率类指标统一使用 bytes/s 作为存储单位，便于前端按需转换显示。

    Attributes:
        cpu_mhz: CPU 使用量 (MHz) - 不是百分比，是实际使用的 MHz 数
        memory_bytes: 内存使用量 (bytes) - 不是百分比，是实际使用的字节数
        disk_read_bytes_per_sec: 磁盘读取速率 (bytes/s)
        disk_write_bytes_per_sec: 磁盘写入速率 (bytes/s)
        net_rx_bytes_per_sec: 网络接收速率 (bytes/s)
        net_tx_bytes_per_sec: 网络发送速率 (bytes/s)
        cpu_samples: CPU 样本数（用于置信度计算）
        memory_samples: 内存样本数
        disk_samples: 磁盘样本数
        network_samples: 网络样本数
        hourly_series: 按小时聚合的时间序列数据（可选）

    hourly_series 格式:
        [(hour_timestamp_ms, cpu_avg, cpu_min, cpu_max,
          memory_avg, memory_min, memory_max,
          disk_read_avg, disk_write_avg,
          net_rx_avg, net_tx_avg), ...]

        注意: hourly_series 中的磁盘和网络单位也是 bytes/s，
              CPU 单位是 MHz，内存单位是 bytes
    """

    # 速率指标 - 统一使用 bytes/s (除了 CPU 和内存)
    cpu_mhz: float                      # MHz (实际使用的频率，非百分比)
    memory_bytes: float                 # bytes (实际使用的内存量，非百分比)
    disk_read_bytes_per_sec: float      # bytes/s
    disk_write_bytes_per_sec: float     # bytes/s
    net_rx_bytes_per_sec: float         # bytes/s
    net_tx_bytes_per_sec: float         # bytes/s

    # 样本数 - 用于置信度计算
    cpu_samples: int
    memory_samples: int
    disk_samples: int
    network_samples: int

    # 按小时聚合的时间序列数据（可选）
    # 格式：[(hour_timestamp_ms, cpu_avg, cpu_min, cpu_max, memory_avg, memory_min, memory_max,
    #         disk_read_avg, disk_write_avg, net_rx_avg, net_tx_avg), ...]
    # 单位：cpu/memory=bytes, disk/net=bytes/s
    hourly_series: Optional[List[tuple]] = None


class Connector(ABC):
    """Abstract base class for cloud platform connectors."""

    @abstractmethod
    async def close(self) -> None:
        """Close connection."""
        pass

    @abstractmethod
    async def test_connection(self) -> dict:
        """Test connection to platform.

        Returns:
            Dictionary with success status and message
        """
        pass

    @abstractmethod
    async def get_clusters(self) -> List[ClusterInfo]:
        """Get all clusters.

        Returns:
            List of cluster information
        """
        pass

    @abstractmethod
    async def get_hosts(self) -> List[HostInfo]:
        """Get all hosts.

        Returns:
            List of host information
        """
        pass

    @abstractmethod
    async def get_vms(self) -> List[VMInfo]:
        """Get all virtual machines.

        Returns:
            List of VM information
        """
        pass

    @abstractmethod
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
        """Get VM performance metrics.

        Args:
            datacenter: Datacenter name
            vm_name: VM name
            vm_uuid: VM UUID
            start_time: Start of time range
            end_time: End of time range
            cpu_count: Number of CPUs for normalization
            total_memory_bytes: Total memory in bytes (for percentage to bytes conversion)

        Returns:
            VM metrics
        """
        pass
