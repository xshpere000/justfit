"""Task Models - Assessment Task, Analysis Job, VM Snapshot."""

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey
from typing import TYPE_CHECKING, Optional
from datetime import datetime

from app.core.database import Base
from app.models import TimestampMixin

if TYPE_CHECKING:
    from app.models.connection import Connection
    from app.models.metric import VMMetric
    from app.models.finding import AnalysisFinding
    from app.models.report import TaskReport


class AssessmentTask(Base, TimestampMixin):
    """Assessment task model."""

    __tablename__ = "assessment_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(20))  # "collection" | "analysis"
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending|running|completed|failed|cancelled
    progress: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    connection_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("connections.id", ondelete="SET NULL"), nullable=True
    )
    config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON config
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON result
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    connection: Mapped[Optional["Connection"]] = relationship()
    metrics: Mapped[list["VMMetric"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    analysis_jobs: Mapped[list["TaskAnalysisJob"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    findings: Mapped[list["AnalysisFinding"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    vm_snapshots: Mapped[list["TaskVMSnapshot"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    reports: Mapped[list["TaskReport"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    logs: Mapped[list["TaskLog"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class TaskVMSnapshot(Base):
    """VM snapshot at collection time."""

    __tablename__ = "task_vm_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_tasks.id", ondelete="CASCADE")
    )
    vm_name: Mapped[str] = mapped_column(String(255))
    vm_key: Mapped[str] = mapped_column(String(255))
    datacenter: Mapped[str] = mapped_column(String(255), default="")
    cpu_count: Mapped[int] = mapped_column(Integer, default=0)
    memory_bytes: Mapped[int] = mapped_column(Integer, default=0)  # Use Integer instead of BigInteger
    power_state: Mapped[str] = mapped_column(String(20), default="")
    host_ip: Mapped[str] = mapped_column(String(50), default="")

    task: Mapped["AssessmentTask"] = relationship(back_populates="vm_snapshots")


class TaskAnalysisJob(Base):
    """Individual analysis job within a task."""

    __tablename__ = "task_analysis_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_tasks.id", ondelete="CASCADE")
    )
    job_type: Mapped[str] = mapped_column(String(20))  # idle|resource|health
    status: Mapped[str] = mapped_column(String(20), default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    task: Mapped["AssessmentTask"] = relationship(back_populates="analysis_jobs")
    findings: Mapped[list["AnalysisFinding"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class TaskLog(Base, TimestampMixin):
    """Task execution log."""

    __tablename__ = "task_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_tasks.id", ondelete="CASCADE")
    )
    level: Mapped[str] = mapped_column(String(10))  # debug|info|warn|error
    message: Mapped[str] = mapped_column(Text)

    task: Mapped["AssessmentTask"] = relationship(back_populates="logs")
