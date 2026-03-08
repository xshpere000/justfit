"""Analysis API Router."""

from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.analysis import AnalysisService
from app.schemas.analysis import AnalysisRequest, CustomModeUpdateRequest


router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/modes")
async def get_analysis_modes(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get all analysis modes.

    Returns:
        All available analysis mode configurations
    """
    service = AnalysisService(db)
    modes = await service.get_modes()

    return {
        "success": True,
        "data": modes,
    }


@router.get("/modes/{mode}")
async def get_analysis_mode(
    mode: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get specific analysis mode configuration.

    Args:
        mode: Mode name (safe, saving, aggressive, custom)
        db: Database session

    Returns:
        Mode configuration
    """
    if mode not in ["safe", "saving", "aggressive", "custom"]:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_MODE", "message": f"Invalid mode: {mode}"},
        )

    service = AnalysisService(db)
    mode_config = await service.get_mode(mode)

    return {
        "success": True,
        "data": mode_config,
    }


@router.put("/modes/custom")
async def update_custom_mode(
    request: CustomModeUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update custom analysis mode.

    Args:
        request: Custom mode update request
        db: Database session

    Returns:
        Success response
    """
    service = AnalysisService(db)
    await service.update_custom_mode(request.analysis_type, request.config, request.task_id)

    return {
        "success": True,
        "message": "Custom mode updated",
    }


@router.post("/tasks/{task_id}/zombie")
async def run_zombie_analysis(
    task_id: int,
    request: Optional[AnalysisRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Run zombie VM analysis on a task.

    Args:
        task_id: Task ID
        request: Analysis request (mode and optional config)
        db: Database session

    Returns:
        Analysis results
    """
    mode = request.mode if request else None
    logger.info(
        "zombie_analysis_requested",
        task_id=task_id,
        mode=mode,
    )

    service = AnalysisService(db)

    # Get configuration based on mode
    config = None
    if request and request.config:
        config = request.config
    elif request and request.mode:
        mode_config = await service.get_mode(request.mode)
        config = mode_config.get("zombie", {})

    result = await service.run_zombie_analysis(task_id, config)

    if not result.get("success"):
        error_code = result.get("error", {}).get("code", "ANALYSIS_ERROR")
        error_msg = result.get("error", {}).get("message", "Analysis failed")
        logger.error(
            "zombie_analysis_failed",
            task_id=task_id,
            error_code=error_code,
            error_msg=error_msg,
        )
        raise HTTPException(status_code=400, detail={"code": error_code, "message": error_msg})

    findings_count = len(result.get("data", []))
    logger.info(
        "zombie_analysis_success",
        task_id=task_id,
        findings_count=findings_count,
    )

    return {
        "success": True,
        "data": result.get("data", []),
    }


@router.get("/tasks/{task_id}/zombie")
async def get_zombie_results(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get zombie VM analysis results.

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        Zombie analysis results
    """
    service = AnalysisService(db)
    result = await service.get_analysis_results(task_id, "zombie")

    return result


@router.post("/tasks/{task_id}/rightsize")
async def run_rightsize_analysis(
    task_id: int,
    request: Optional[AnalysisRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Run right-size analysis on a task.

    Args:
        task_id: Task ID
        request: Analysis request (mode and optional config)
        db: Database session

    Returns:
        Analysis results
    """
    mode = request.mode if request else None
    logger.info(
        "rightsize_analysis_requested",
        task_id=task_id,
        mode=mode,
    )

    service = AnalysisService(db)

    # Get configuration based on mode
    config = None
    if request and request.config:
        config = request.config
    elif request and request.mode:
        mode_config = await service.get_mode(request.mode)
        config = mode_config.get("rightsize", {})

    result = await service.run_rightsize_analysis(task_id, config)

    if not result.get("success"):
        error_code = result.get("error", {}).get("code", "ANALYSIS_ERROR")
        error_msg = result.get("error", {}).get("message", "Analysis failed")
        logger.error(
            "rightsize_analysis_failed",
            task_id=task_id,
            error_code=error_code,
            error_msg=error_msg,
        )
        raise HTTPException(status_code=400, detail={"code": error_code, "message": error_msg})

    findings_count = len(result.get("data", []))
    logger.info(
        "rightsize_analysis_success",
        task_id=task_id,
        findings_count=findings_count,
    )

    return {
        "success": True,
        "data": result.get("data", []),
    }


@router.get("/tasks/{task_id}/rightsize")
async def get_rightsize_results(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get right-size analysis results.

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        Right-size analysis results
    """
    service = AnalysisService(db)
    result = await service.get_analysis_results(task_id, "rightsize")

    return result


@router.post("/tasks/{task_id}/tidal")
async def run_tidal_analysis(
    task_id: int,
    request: Optional[AnalysisRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Run tidal pattern analysis on a task.

    Args:
        task_id: Task ID
        request: Analysis request (mode and optional config)
        db: Database session

    Returns:
        Analysis results
    """
    mode = request.mode if request else None
    logger.info(
        "tidal_analysis_requested",
        task_id=task_id,
        mode=mode,
    )

    service = AnalysisService(db)

    # Get configuration based on mode
    config = None
    if request and request.config:
        config = request.config
    elif request and request.mode:
        mode_config = await service.get_mode(request.mode)
        config = mode_config.get("tidal", {})

    result = await service.run_tidal_analysis(task_id, config)

    if not result.get("success"):
        error_code = result.get("error", {}).get("code", "ANALYSIS_ERROR")
        error_msg = result.get("error", {}).get("message", "Analysis failed")
        logger.error(
            "tidal_analysis_failed",
            task_id=task_id,
            error_code=error_code,
            error_msg=error_msg,
        )
        raise HTTPException(status_code=400, detail={"code": error_code, "message": error_msg})

    findings_count = len(result.get("data", []))
    logger.info(
        "tidal_analysis_success",
        task_id=task_id,
        findings_count=findings_count,
    )

    return {
        "success": True,
        "data": result.get("data", []),
    }


@router.get("/tasks/{task_id}/tidal")
async def get_tidal_results(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get tidal pattern analysis results.

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        Tidal analysis results
    """
    service = AnalysisService(db)
    result = await service.get_analysis_results(task_id, "tidal")

    return result


@router.post("/tasks/{task_id}/health")
async def run_health_analysis_task(
    task_id: int,
    request: Optional[AnalysisRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Run health score analysis on a task.

    Args:
        task_id: Task ID
        request: Analysis request (mode and optional config)
        db: Database session

    Returns:
        Health score results
    """
    mode = request.mode if request else None
    logger.info(
        "health_analysis_requested",
        task_id=task_id,
        mode=mode,
    )

    service = AnalysisService(db)

    # Get configuration based on mode
    config = None
    if request and request.config:
        config = request.config
    elif request and request.mode:
        mode_config = await service.get_mode(request.mode)
        config = mode_config.get("health", {})

    result = await service.run_health_analysis(task_id, config)

    if not result.get("success"):
        error_msg = str(result.get("error", "Analysis failed"))
        logger.error(
            "health_analysis_failed",
            task_id=task_id,
            error=error_msg,
        )
        raise HTTPException(status_code=400, detail={"code": "ANALYSIS_ERROR", "message": error_msg})

    health_score = result.get("data", {}).get("overallScore")
    logger.info(
        "health_analysis_success",
        task_id=task_id,
        health_score=health_score,
    )

    return {
        "success": True,
        "data": result.get("data"),
    }


@router.get("/tasks/{task_id}/health")
async def get_health_results_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get health score analysis results for a task.

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        Health score results
    """
    service = AnalysisService(db)
    result = await service.get_analysis_results(task_id, "health")

    return result
