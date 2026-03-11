"""Finding Model - Analysis Results."""

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey
from typing import TYPE_CHECKING, Optional
from datetime import datetime

from app.core.database import Base
from app.models import TimestampMixin

if TYPE_CHECKING:
    from app.models.task import AssessmentTask, TaskAnalysisJob


class AnalysisFinding(Base, TimestampMixin):
    """Analysis finding result."""

    __tablename__ = "analysis_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_tasks.id", ondelete="CASCADE")
    )
    job_id: Mapped[int] = mapped_column(
        ForeignKey("task_analysis_jobs.id", ondelete="CASCADE")
    )
    job_type: Mapped[str] = mapped_column(String(20))  # idle|resource|health
    vm_name: Mapped[str] = mapped_column(String(255), default="")
    severity: Mapped[str] = mapped_column(
        String(20), default="info"
    )  # info|low|medium|high|critical
    title: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    recommendation: Mapped[str] = mapped_column(Text, default="")
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON details
    estimated_saving: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    task: Mapped["AssessmentTask"] = relationship(back_populates="findings")
    job: Mapped["TaskAnalysisJob"] = relationship(back_populates="findings")
