"""Report Model."""

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, DateTime, ForeignKey
from typing import TYPE_CHECKING

from app.core.database import Base
from app.models import TimestampMixin

if TYPE_CHECKING:
    from app.models.task import AssessmentTask


class TaskReport(Base, TimestampMixin):
    """Generated report for a task."""

    __tablename__ = "task_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_tasks.id", ondelete="CASCADE")
    )
    format: Mapped[str] = mapped_column(String(10))  # "excel" | "pdf"
    file_path: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)

    task: Mapped["AssessmentTask"] = relationship(back_populates="reports")
