"""Connector Base - Abstract interface for cloud platforms."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class ClusterInfo:
    """Cluster information."""

    name: str
    datacenter: str
    total_cpu: int  # MHz
    total_memory: int  # bytes
    num_hosts: int
    num_vms: int
    cluster_key: str


@dataclass
class HostInfo:
    """Host information."""

    name: str
    datacenter: str
    ip_address: str
    cpu_cores: int
    cpu_mhz: int  # Single core frequency
    memory_bytes: int
    num_vms: int
    power_state: str
    overall_status: str


@dataclass
class VMInfo:
    """Virtual Machine information."""

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


@dataclass
class VMMetrics:
    """VM performance metrics."""

    cpu_mhz: float
    memory_bytes: float
    disk_read_bytes_per_sec: float
    disk_write_bytes_per_sec: float
    net_rx_bytes_per_sec: float
    net_tx_bytes_per_sec: float

    # Sample counts for confidence calculation
    cpu_samples: int
    memory_samples: int
    disk_samples: int
    network_samples: int


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
        pass
