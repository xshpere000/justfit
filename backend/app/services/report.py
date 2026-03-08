"""Report Service - Handles report generation and storage."""

import structlog
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TaskReport, AssessmentTask
from app.report.builder import ReportBuilder
from app.report.excel import ExcelReportGenerator
from app.report.pdf import PDFReportGenerator
from app.config import settings


logger = structlog.get_logger()


class ReportService:
    """Service for report generation operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize report service.

        Args:
            db: Database session
        """
        self.db = db

    async def generate_report(
        self,
        task_id: int,
        report_format: str = "excel",
        font_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate report for a task.

        Args:
            task_id: Task ID
            report_format: Report format (excel or pdf)
            font_path: Optional font path for PDF generation

        Returns:
            Report generation result
        """
        # Verify task exists
        task = await self._get_task(task_id)
        if not task:
            return {
                "success": False,
                "error": {"code": "TASK_NOT_FOUND", "message": "Task not found"},
            }

        # Build report data
        builder = ReportBuilder(self.db)
        report_data = await builder.build_task_report_data(task_id)

        if not report_data:
            return {
                "success": False,
                "error": {"code": "NO_DATA", "message": "No data available for report"},
            }

        # Generate report file
        try:
            output_dir = Path(settings.DATA_DIR) / "reports"
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            connection_name = report_data.get("connection", {}).get("name", "unknown")
            safe_name = self._sanitize_filename(connection_name)

            if report_format == "excel":
                filename = f"{safe_name}_{timestamp}.xlsx"
                output_path = output_dir / filename

                generator = ExcelReportGenerator()
                file_path = generator.generate(report_data, str(output_path))

            elif report_format == "pdf":
                filename = f"{safe_name}_{timestamp}.pdf"
                output_path = output_dir / filename

                generator = PDFReportGenerator(font_path=font_path)
                file_path = generator.generate(report_data, str(output_path))

            else:
                return {
                    "success": False,
                    "error": {"code": "INVALID_FORMAT", "message": f"Invalid format: {report_format}"},
                }

            # Get file size
            file_size = Path(file_path).stat().st_size

            # Save report record to database
            report = TaskReport(
                task_id=task_id,
                format=report_format,
                file_path=str(file_path),
                file_size=file_size,
                created_at=datetime.utcnow(),
            )
            self.db.add(report)
            await self.db.commit()
            await self.db.refresh(report)

            logger.info(
                "report_generated",
                task_id=task_id,
                format=report_format,
                file_path=str(file_path),
                file_size=file_size,
            )

            return {
                "success": True,
                "data": {
                    "reportId": report.id,
                    "taskId": task_id,
                    "format": report_format,
                    "filePath": str(file_path),
                    "fileSize": file_size,
                    "createdAt": report.created_at.isoformat(),
                },
            }

        except ImportError as e:
            return {
                "success": False,
                "error": {"code": "MISSING_DEPENDENCY", "message": str(e)},
            }
        except Exception as e:
            logger.error("report_generation_failed", task_id=task_id, error=str(e))
            return {
                "success": False,
                "error": {"code": "GENERATION_ERROR", "message": str(e)},
            }

    async def get_report(
        self,
        report_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Get report by ID.

        Args:
            report_id: Report ID

        Returns:
            Report data or None
        """
        query = select(TaskReport).where(TaskReport.id == report_id)
        result = await self.db.execute(query)
        report = result.scalar_one_or_none()

        if not report:
            return None

        return {
            "id": report.id,
            "taskId": report.task_id,
            "format": report.format,
            "filePath": report.file_path,
            "fileSize": report.file_size,
            "createdAt": report.created_at.isoformat() if report.created_at else None,
        }

    async def list_reports(
        self,
        task_id: int,
    ) -> list[Dict[str, Any]]:
        """List reports for a task.

        Args:
            task_id: Task ID

        Returns:
            List of report data
        """
        query = (
            select(TaskReport)
            .where(TaskReport.task_id == task_id)
            .order_by(TaskReport.created_at.desc())
        )
        result = await self.db.execute(query)
        reports = result.scalars().all()

        return [
            {
                "id": r.id,
                "taskId": r.task_id,
                "format": r.format,
                "filePath": r.file_path,
                "fileSize": r.file_size,
                "createdAt": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
        ]

    async def delete_report(
        self,
        report_id: int,
    ) -> bool:
        """Delete a report.

        Args:
            report_id: Report ID

        Returns:
            True if deleted, False otherwise
        """
        query = select(TaskReport).where(TaskReport.id == report_id)
        result = await self.db.execute(query)
        report = result.scalar_one_or_none()

        if not report:
            return False

        # Delete file
        try:
            file_path = Path(report.file_path)
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.warning("failed_to_delete_report_file", path=report.file_path, error=str(e))

        # Delete database record
        await self.db.delete(report)
        await self.db.commit()

        return True

    async def _get_task(self, task_id: int) -> Optional[AssessmentTask]:
        """Get task by ID."""
        query = select(AssessmentTask).where(AssessmentTask.id == task_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename for safe file system usage.

        Args:
            name: Original name

        Returns:
            Sanitized filename
        """
        # Replace invalid characters with underscore
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, "_")

        # Remove leading/trailing spaces and dots
        name = name.strip(". ")

        # Limit length
        if len(name) > 50:
            name = name[:50]

        return name or "report"
