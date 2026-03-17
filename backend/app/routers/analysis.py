"""Analysis API Router."""

from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.analysis import AnalysisService
from app.schemas.analysis import (
    AnalysisRequest,
    ModesResponse,
    ModeResponse
)


router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/modes", response_model=ModesResponse)
async def get_analysis_modes(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get all analysis modes.

    Returns:
        All available analysis mode configurations with camelCase keys
    """
    service = AnalysisService(db)
    modes = await service.get_modes()

    # response_model automatically converts snake_case to camelCase via alias_generator
    return {"success": True, "data": modes}


@router.get("/modes/{mode}", response_model=ModeResponse)
async def get_analysis_mode(
    mode: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get specific analysis mode configuration.

    Args:
        mode: Mode name (safe, saving, aggressive, custom)
        db: Database session

    Returns:
        Mode configuration with camelCase keys
    """
    if mode not in ["safe", "saving", "aggressive", "custom"]:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_MODE", "message": f"Invalid mode: {mode}"},
        )

    service = AnalysisService(db)
    mode_config = await service.get_mode(mode)

    # response_model automatically converts snake_case to camelCase via alias_generator
    return {"success": True, "data": mode_config}


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
    service = AnalysisService(db)
    mode = request.mode if request else None
    logger.info(
        "health_analysis_requested",
        task_id=task_id,
        mode=mode,
    )

    # Get configuration
    config = None
    if request and request.config is not None and len(request.config) > 0:
        # 请求中直接指定了配置（非空字典）
        config = request.config
        logger.info("using_request_config", task_id=task_id, config_keys=list(config.keys()) if config else [])
    else:
        # 从任务 config 中读取配置
        task = await service._get_task(task_id)
        if task and task.config:
            import json
            try:
                task_config = json.loads(task.config)
                task_mode = task_config.get("mode")
                request_mode = mode or task_mode

                logger.info("health_analysis_from_task_config", task_id=task_id, task_mode=task_mode, request_mode=mode)

                if request_mode == "custom":
                    # custom 模式：合并基础预设配置 + 用户自定义配置
                    base_mode = task_config.get("baseMode", "saving")
                    custom_config = task_config.get("customConfig", {})
                    mode_config = service.merge_mode_config(base_mode, custom_config)
                    config = mode_config.get("health", {})
                    logger.info(
                        "using_custom_health_config",
                        task_id=task_id,
                        base_mode=base_mode,
                        config=config
                    )
                elif request_mode:
                    # 预设模式
                    mode_config = await service.get_mode(request_mode)
                    config = mode_config.get("health", {})
                    logger.info("using_preset_health_config", task_id=task_id, mode=request_mode)
            except json.JSONDecodeError as e:
                logger.error("failed_to_parse_task_config", task_id=task_id, error=str(e))
        else:
            logger.info("no_task_config_found", task_id=task_id, has_task=bool(task), has_config=bool(task.config if task else None))

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


@router.post("/tasks/{task_id}/idle")
async def run_idle_analysis(
    task_id: int,
    request: Optional[AnalysisRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Run idle detection analysis on a task.

    Args:
        task_id: Task ID
        request: Analysis request (mode and optional config)
        db: Database session

    Returns:
        Idle detection results
    """
    mode = request.mode if request else None
    logger.info(
        "idle_analysis_requested",
        task_id=task_id,
        mode=mode,
    )

    service = AnalysisService(db)

    # Get configuration
    config = None
    if request and request.config is not None and len(request.config) > 0:
        # 请求中直接指定了配置（非空字典）
        config = request.config
        logger.info("using_request_config", task_id=task_id, config_keys=list(config.keys()) if config else [])
    else:
        # 从任务 config 中读取配置
        task = await service._get_task(task_id)
        if task and task.config:
            import json
            task_config = json.loads(task.config)
            task_mode = task_config.get("mode")
            request_mode = mode or task_mode

            if request_mode == "custom":
                # custom 模式：合并基础预设配置 + 用户自定义配置
                base_mode = task_config.get("baseMode", "saving")
                custom_config = task_config.get("customConfig", {})
                mode_config = service.merge_mode_config(base_mode, custom_config)
                config = mode_config.get("idle", {})
                logger.info(
                    "using_custom_idle_config",
                    task_id=task_id,
                    base_mode=base_mode,
                    config=config
                )
            elif request_mode:
                # 预设模式
                mode_config = await service.get_mode(request_mode)
                config = mode_config.get("idle", {})
                logger.info(
                    "using_preset_idle_config",
                    task_id=task_id,
                    mode=request_mode
                )

    result = await service.run_idle_analysis(task_id, config)

    if not result.get("success"):
        error_code = result.get("error", {}).get("code", "ANALYSIS_ERROR")
        error_msg = result.get("error", {}).get("message", "Analysis failed")
        logger.error(
            "idle_analysis_failed",
            task_id=task_id,
            error_code=error_code,
            error_msg=error_msg,
        )
        raise HTTPException(status_code=400, detail={"code": error_code, "message": error_msg})

    findings_count = len(result.get("data", []))
    logger.info(
        "idle_analysis_success",
        task_id=task_id,
        findings_count=findings_count,
    )

    return {
        "success": True,
        "data": result.get("data", []),
    }


@router.get("/tasks/{task_id}/idle")
async def get_idle_results(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get idle detection analysis results.

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        Idle detection results
    """
    service = AnalysisService(db)
    result = await service.get_analysis_results(task_id, "idle")

    return result


@router.post("/tasks/{task_id}/resource")
async def run_resource_analysis(
    task_id: int,
    request: Optional[AnalysisRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Run resource analysis (Resource Optimization + Tidal Detection) on a task.

    Args:
        task_id: Task ID
        request: Analysis request (mode and optional config)
        db: Database session

    Returns:
        Resource analysis results with resourceOptimization and tidal
    """
    mode = request.mode if request else None
    logger.info(
        "resource_analysis_requested",
        task_id=task_id,
        mode=mode,
    )

    service = AnalysisService(db)

    # Get configuration
    config = None
    if request and request.config is not None and len(request.config) > 0:
        # 请求中直接指定了配置（非空字典）
        config = request.config
        logger.info("using_request_config", task_id=task_id, config_keys=list(config.keys()) if config else [])
    else:
        # 从任务 config 中读取配置
        task = await service._get_task(task_id)
        if task and task.config:
            import json
            task_config = json.loads(task.config)
            task_mode = task_config.get("mode")
            request_mode = mode or task_mode

            if request_mode == "custom":
                # custom 模式：合并基础预设配置 + 用户自定义配置
                base_mode = task_config.get("baseMode", "saving")
                custom_config = task_config.get("customConfig", {})
                mode_config = service.merge_mode_config(base_mode, custom_config)
                resource_config = mode_config.get("resource", {})
                config = {
                    "rightsize": resource_config.get("rightsize", {}),
                    "usage_pattern": resource_config.get("usage_pattern", {}),
                }
                logger.info(
                    "using_custom_resource_config",
                    task_id=task_id,
                    base_mode=base_mode,
                    config_keys=list(config.keys()) if config else []
                )
            elif request_mode:
                # 预设模式
                mode_config = await service.get_mode(request_mode)
                resource_config = mode_config.get("resource", {})
                config = {
                    "rightsize": resource_config.get("rightsize", {}),
                    "usage_pattern": resource_config.get("usage_pattern", {}),
                }
                logger.info(
                    "using_preset_resource_config",
                    task_id=task_id,
                    mode=request_mode
                )

    result = await service.run_resource_analysis(task_id, config)

    if not result.get("success"):
        error_code = result.get("error", {}).get("code", "ANALYSIS_ERROR")
        error_msg = result.get("error", {}).get("message", "Analysis failed")
        logger.error(
            "resource_analysis_failed",
            task_id=task_id,
            error_code=error_code,
            error_msg=error_msg,
        )
        raise HTTPException(status_code=400, detail={"code": error_code, "message": error_msg})

    data = result.get("data", {})
    summary = data.get("summary", {})
    logger.info(
        "resource_analysis_success",
        task_id=task_id,
        resource_optimization_count=summary.get("resourceOptimizationCount", 0),
        tidal_count=summary.get("tidalCount", 0),
    )

    return {
        "success": True,
        "data": data,
    }


@router.get("/tasks/{task_id}/resource")
async def get_resource_results(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get resource analysis results.

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        Resource analysis results
    """
    service = AnalysisService(db)
    result = await service.get_analysis_results(task_id, "resource")

    return result


@router.get("/tasks/{task_id}/summary")
async def get_analysis_summary(
    task_id: int,
    optimizations: str = "resource,idle",
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """计算优化后可释放的资源和物理主机。

    Args:
        task_id: Task ID
        optimizations: 逗号分隔的优化项，可选值: resource, idle
        db: Database session

    Returns:
        当前资源总量、节省量、可释放主机列表
    """
    enabled = [o.strip() for o in optimizations.split(",") if o.strip() in ("resource", "idle")]
    service = AnalysisService(db)
    result = await service.calculate_host_freeability(task_id, enabled)

    if not result.get("success"):
        error_msg = str(result.get("error", "Failed to calculate summary"))
        raise HTTPException(status_code=400, detail={"code": "SUMMARY_ERROR", "message": error_msg})

    return result
