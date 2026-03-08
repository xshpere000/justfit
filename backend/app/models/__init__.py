"""Database Models."""

from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, DateTime, Text, BigInteger, Float, ForeignKey, Index, func
from typing import Optional, List

from app.core.database import Base


class TimestampMixin:
    """Add timestamp fields to models."""

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class Connection(Base, TimestampMixin):
    """Cloud platform connection model."""

    __tablename__ = "connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    platform: Mapped[str] = mapped_column(String(20))  # "vcenter" | "h3c-uis"
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer, default=443)
    username: Mapped[str] = mapped_column(String(100))
    # Password is stored encrypted in credentials.enc, not in database
    insecure: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="disconnected")
    last_sync: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    clusters: Mapped[List["Cluster"]] = relationship(
        back_populates="connection", cascade="all, delete-orphan"
    )
    hosts: Mapped[List["Host"]] = relationship(
        back_populates="connection", cascade="all, delete-orphan"
    )
    vms: Mapped[List["VM"]] = relationship(
        back_populates="connection", cascade="all, delete-orphan"
    )


# Import other models
from .resource import Cluster, Host, VM
from .metric import VMMetric
from .task import AssessmentTask, TaskVMSnapshot, TaskAnalysisJob, TaskLog
from .finding import AnalysisFinding
from .report import TaskReport
from .settings import Settings as SettingsModel

__all__ = [
    "Connection",
    "Cluster",
    "Host",
    "VM",
    "VMMetric",
    "AssessmentTask",
    "TaskVMSnapshot",
    "TaskAnalysisJob",
    "TaskLog",
    "AnalysisFinding",
    "TaskReport",
    "SettingsModel",
]
