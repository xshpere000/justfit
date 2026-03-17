"""Resource Models - Cluster, Host, VM."""

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, ForeignKey, DateTime
from typing import TYPE_CHECKING, Optional, List
from datetime import datetime

from app.core.database import Base
from app.models import TimestampMixin

if TYPE_CHECKING:
    from app.models.connection import Connection
    from app.models.metric import VMMetric


class Cluster(Base, TimestampMixin):
    """Cluster model."""

    __tablename__ = "clusters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    connection_id: Mapped[int] = mapped_column(
        ForeignKey("connections.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(255))
    datacenter: Mapped[str] = mapped_column(String(255), default="")
    total_cpu: Mapped[int] = mapped_column(Integer, default=0)  # MHz
    total_memory: Mapped[int] = mapped_column(BigInteger, default=0)  # bytes
    num_hosts: Mapped[int] = mapped_column(Integer, default=0)
    num_vms: Mapped[int] = mapped_column(Integer, default=0)
    cluster_key: Mapped[str] = mapped_column(String(255), unique=True)  # Idempotent key
    collected_at: Mapped[datetime] = mapped_column(default=datetime.now)

    connection: Mapped["Connection"] = relationship(back_populates="clusters")


class Host(Base, TimestampMixin):
    """Host model."""

    __tablename__ = "hosts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    connection_id: Mapped[int] = mapped_column(
        ForeignKey("connections.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(255))
    datacenter: Mapped[str] = mapped_column(String(255), default="")
    cluster_name: Mapped[str] = mapped_column(String(255), default="")
    ip_address: Mapped[str] = mapped_column(String(50), default="")
    cpu_cores: Mapped[int] = mapped_column(Integer, default=0)
    cpu_mhz: Mapped[int] = mapped_column(Integer, default=0)  # Single core frequency
    memory_bytes: Mapped[int] = mapped_column(BigInteger, default=0)  # Total memory in bytes
    num_vms: Mapped[int] = mapped_column(Integer, default=0)
    power_state: Mapped[str] = mapped_column(String(20), default="")
    overall_status: Mapped[str] = mapped_column(String(20), default="")
    collected_at: Mapped[datetime] = mapped_column(default=datetime.now)

    connection: Mapped["Connection"] = relationship(back_populates="hosts")


class VM(Base, TimestampMixin):
    """Virtual Machine model."""

    __tablename__ = "vms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    connection_id: Mapped[int] = mapped_column(
        ForeignKey("connections.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(255))
    datacenter: Mapped[str] = mapped_column(String(255), default="")
    uuid: Mapped[str] = mapped_column(String(100), default="")
    vm_key: Mapped[str] = mapped_column(String(255), unique=True)  # Idempotent key
    cpu_count: Mapped[int] = mapped_column(Integer, default=0)
    memory_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    power_state: Mapped[str] = mapped_column(String(20), default="")
    guest_os: Mapped[str] = mapped_column(String(100), default="")
    ip_address: Mapped[str] = mapped_column(String(50), default="")
    host_name: Mapped[str] = mapped_column(String(255), default="")
    host_ip: Mapped[str] = mapped_column(String(50), default="")
    connection_state: Mapped[str] = mapped_column(String(20), default="")
    overall_status: Mapped[str] = mapped_column(String(20), default="")
    vm_create_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="VM创建时间"
    )
    uptime_duration: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="开机时长（秒），仅开机VM有值"
    )
    downtime_duration: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="关机时长（秒），仅关机VM有值"
    )

    collected_at: Mapped[datetime] = mapped_column(default=datetime.now)

    connection: Mapped["Connection"] = relationship(back_populates="vms")
    metrics: Mapped[List["VMMetric"]] = relationship(
        back_populates="vm", cascade="all, delete-orphan"
    )
