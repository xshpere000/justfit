"""Report API Router."""

from typing import Any, Dict, Optional
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.report import ReportService
from app.services.task import TaskService
from app.schemas.report import ReportCreateRequest


router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/tasks/{task_id}/reports")
async def generate_report(
    task_id: int,
    request: ReportCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Generate a report for a task.

    Args:
        task_id: Task ID
        request: Report creation request
        db: Database session

    Returns:
        Report generation result
    """
    logger.info(
        "generate_report_requested",
        task_id=task_id,
        report_format=request.format,
    )

    # 添加日志记录
    task_service = TaskService(db)
    format_name = "Excel" if request.format == "xlsx" else "PDF"
    await task_service.add_log(task_id, "info", f"开始生成{format_name}格式报告...")

    service = ReportService(db)

    result = await service.generate_report(
        task_id=task_id,
        report_format=request.format,
    )

    if not result.get("success"):
        error_code = result.get("error", {}).get("code", "REPORT_ERROR")
        error_msg = result.get("error", {}).get("message", "Report generation failed")
        logger.error(
            "generate_report_failed",
            task_id=task_id,
            report_format=request.format,
            error_code=error_code,
            error_msg=error_msg,
        )
        await task_service.add_log(task_id, "error", f"报告生成失败：{error_msg}")
        raise HTTPException(status_code=400, detail={"code": error_code, "message": error_msg})

    logger.info(
        "generate_report_success",
        task_id=task_id,
        report_format=request.format,
        report_id=result.get("data", {}).get("id"),
    )
    await task_service.add_log(task_id, "info", f"{format_name}报告生成完成")

    return result


@router.get("/tasks/{task_id}/reports")
async def list_reports(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get reports for a task.

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        List of reports
    """
    service = ReportService(db)
    reports = await service.list_reports(task_id)

    return {
        "success": True,
        "data": reports,
    }


@router.get("/{report_id}")
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get report details.

    Args:
        report_id: Report ID
        db: Database session

    Returns:
        Report details
    """
    service = ReportService(db)
    report = await service.get_report(report_id)

    if not report:
        raise HTTPException(
            status_code=404,
            detail={"code": "REPORT_NOT_FOUND", "message": "Report not found"},
        )

    return {
        "success": True,
        "data": report,
    }


@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Download a report file.

    Args:
        report_id: Report ID
        db: Database session

    Returns:
        Report file download
    """
    service = ReportService(db)
    report = await service.get_report(report_id)

    if not report:
        raise HTTPException(
            status_code=404,
            detail={"code": "REPORT_NOT_FOUND", "message": "Report not found"},
        )

    file_path = Path(report["filePath"])

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail={"code": "FILE_NOT_FOUND", "message": "Report file not found"},
        )

    # Determine media type
    media_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if report["format"] == "excel"
        else "application/pdf"
    )

    # Extract filename from path
    filename = file_path.name

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
    )


@router.delete("/{report_id}")
async def delete_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Delete a report.

    Args:
        report_id: Report ID
        db: Database session

    Returns:
        Success response
    """
    service = ReportService(db)
    deleted = await service.delete_report(report_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"code": "REPORT_NOT_FOUND", "message": "Report not found"},
        )

    return {
        "success": True,
        "message": "Report deleted",
    }
