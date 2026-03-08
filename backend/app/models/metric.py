"""Metric Model - VM Performance Metrics."""

from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Index
from typing import TYPE_CHECKING

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.task import AssessmentTask
    from app.models.resource import VM


class VMMetric(Base):
    """VM performance metric - isolated by task."""

    __tablename__ = "vm_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_tasks.id", ondelete="CASCADE"),
        index=True,
    )
    vm_id: Mapped[int] = mapped_column(
        ForeignKey("vms.id", ondelete="CASCADE"),
        index=True,
    )
    metric_type: Mapped[str] = mapped_column(String(20))  # cpu|memory|disk_read|disk_write|net_rx|net_tx
    value: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime)

    vm: Mapped["VM"] = relationship(back_populates="metrics")
    task: Mapped["AssessmentTask"] = relationship(back_populates="metrics")

    __table_args__ = (
        Index("ix_metrics_task_vm_type", "task_id", "vm_id", "metric_type"),
    )
