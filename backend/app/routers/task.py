"""Task Management API Router."""

import asyncio
from typing import Any, Optional
import json

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import NotFoundError, ValidationError, error_response, AppError
from app.services.task import TaskService


router = APIRouter()
logger = structlog.get_logger(__name__)


def _task_to_dict(task, lite: bool = False) -> dict:
    """Convert task model to dict.

    Args:
        lite: If True, return only essential fields for list view (lighter payload)
    """
    import json

    # 解析 config JSON
    config = {}
    if task.config:
        try:
            config = json.loads(task.config) if isinstance(task.config, str) else task.config
        except:
            config = {}

    # 解析 result JSON
    result = {}
    if task.result:
        try:
            result = json.loads(task.result) if isinstance(task.result, str) else task.result
        except:
            result = {}

    # 解析 analysisResults 从 result 中
    analysis_results = result.get("analysisResults", {})
    if not analysis_results and isinstance(result, dict):
        # 如果没有 analysisResults，检查各个分析类型是否存在
        analysis_results = {
            "zombie": bool(result.get("zombieResult")),
            "rightsize": bool(result.get("rightsizeResult")),
            "tidal": bool(result.get("tidalResult")),
            "health": bool(result.get("healthResult")),
        }

    # 基础字段（列表和详情都返回）
    base_dict = {
        "id": task.id,
        "name": task.name,
        "type": task.type,
        "status": task.status,
        "progress": task.progress,
        "error": task.error,
        "connectionId": task.connection_id,
        "currentStep": result.get("currentStep", ""),
        "analysisResults": analysis_results,
        "createdAt": task.created_at.isoformat() if task.created_at else None,
        "startedAt": task.started_at.isoformat() if task.started_at else None,
        "completedAt": task.completed_at.isoformat() if task.completed_at else None,
        # 卡片显示所需字段
        "platform": config.get("platform", "vcenter"),
        "connectionName": config.get("connectionName", ""),
        "connectionHost": config.get("connectionHost", ""),
        "selectedVMCount": config.get("selectedVMCount", 0),
        "collectedVMCount": result.get("collectedVMCount", config.get("selectedVMCount", 0)),
    }

    # 如果是 lite 模式，只返回基础字段
    if lite:
        return base_dict

    # 详情模式：额外返回完整配置和VM列表
    base_dict.update({
        "selectedVMs": config.get("selectedVMs", []),
        "config": config,
    })

    return base_dict


@router.post("", response_model=dict)
async def create_task(
    data: dict,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new assessment task.

    The task will be created immediately and execution will start in the background.

    Returns the lite version of task (only essential fields).
    """
    import asyncio

    task_name = data.get("name", "New Task")
    task_type = data.get("type", "collection")
    connection_id = data.get("connectionId")

    logger.info(
        "create_task_requested",
        name=task_name,
        type=task_type,
        connection_id=connection_id,
    )

    service = TaskService(db)

    try:
        task = await service.create_task(
            name=task_name,
            task_type=task_type,
            connection_id=connection_id,
            config=data.get("config"),
        )
        logger.info(
            "create_task_success",
            task_id=task.id,
            name=task.name,
            type=task.type,
            connection_id=task.connection_id,
        )

        # 添加初始日志
        await service.add_log(task.id, "info", "任务已创建，准备开始执行...")

        # 提交事务，确保任务记录已保存
        await db.commit()

        # 在后台执行任务采集（不阻塞HTTP响应）
        # 使用 asyncio.create_task 而不是 BackgroundTasks
        asyncio.create_task(
            execute_collection_task(
                task.id,
                connection_id,
                data.get("config", {})
            )
        )

        logger.info(
            "create_task_background_started",
            task_id=task.id,
        )

        # 立即返回任务信息（lite模式，只返回必要字段）
        return {
            "success": True,
            "data": _task_to_dict(task, lite=True),
        }
    except (NotFoundError, ValidationError) as e:
        logger.error(
            "create_task_failed",
            name=task_name,
            type=task_type,
            connection_id=connection_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        return error_response(e)


async def execute_collection_task(task_id: int, connection_id: int, config: dict):
    """在后台执行完整的采集任务

    此函数会在后台线程中执行，包括：
    1. 基础资源采集（集群、主机、VM信息）
    2. VM性能指标采集

    注意：此函数需要独立处理数据库会话和错误
    """
    import asyncio
    from app.core.database import async_session
    from app.services.collection import CollectionService
    from app.services.task import TaskService
    from sqlalchemy import select, func
    from app.models import VM as VMModel
    from datetime import datetime

    logger.info("collection_task_started", task_id=task_id, connection_id=connection_id)

    # 等待主事务提交
    await asyncio.sleep(0.5)

    try:
        async with async_session() as session:
            logger.info("collection_task_session_created", task_id=task_id)
            logger.info(f"collection_task_{task_id}_status_check", current_status="starting")

            task_service = TaskService(session)
            collection_service = CollectionService(session)

            try:
                # 更新任务状态为 running
                await _update_task_status(
                    session, task_id, "running", 0,
                    "开始执行采集任务..."
                )
                await task_service.add_log(task_id, "info", "任务开始执行")

                # 获取配置
                selected_vms = config.get("selectedVMs", [])

                # 步骤1: 检查是否需要采集基础资源
                result = await session.execute(
                    select(func.count()).select_from(VMModel).where(
                        VMModel.connection_id == connection_id
                    )
                )
                existing_vm_count = result.scalar() or 0

                if existing_vm_count == 0:
                    # 没有基础数据，需要先进行完整采集
                    await task_service.add_log(
                        task_id, "info",
                        "开始采集基础资源信息（集群、主机、虚拟机）..."
                    )

                    # 更新进度
                    await _update_task_status(
                        session, task_id, "running", 10,
                        "正在采集基础资源..."
                    )

                    # 执行基础资源采集
                    collection_result = await collection_service.collect_resources(connection_id)

                    await task_service.add_log(
                        task_id, "info",
                        f"基础资源采集完成：{collection_result.get('clusters', 0)} 个集群，"
                        f"{collection_result.get('hosts', 0)} 台主机，"
                        f"{collection_result.get('vms', 0)} 台虚拟机"
                    )

                    logger.info(
                        "collection_task_base_collection_completed",
                        task_id=task_id,
                        collection_result=collection_result,
                    )
                else:
                    await task_service.add_log(
                        task_id, "info",
                        f"检测到已有基础资源数据（{existing_vm_count} 台虚拟机），跳过基础采集"
                    )

                # 获取采集后的 VM 数量
                result = await session.execute(
                    select(func.count()).select_from(VMModel).where(
                        VMModel.connection_id == connection_id
                    )
                )
                vm_count = result.scalar() or 0

                # 更新进度
                await _update_task_status(
                    session, task_id, "running", 40,
                    f"基础资源采集完成，共 {vm_count} 台虚拟机",
                    {"collectedVMCount": vm_count}
                )

                # 步骤2: 采集 VM 性能指标
                if selected_vms:
                    await task_service.add_log(
                        task_id, "info",
                        f"开始收集 {len(selected_vms)} 台虚拟机的性能指标..."
                    )

                    # 更新进度
                    await _update_task_status(
                        session, task_id, "running", 40,
                        "正在采集虚拟机性能指标..."
                    )

                    metrics_result = await task_service.collect_vm_metrics(
                        task_id=task_id,
                        connection_id=connection_id,
                        selected_vm_keys=selected_vms,
                    )

                    collected = metrics_result.get("collected", 0)
                    failed = metrics_result.get("failed", 0)

                    await task_service.add_log(
                        task_id, "info",
                        f"指标采集完成：成功 {collected} 台，失败 {failed} 台"
                    )

                    logger.info(
                        "collection_task_metrics_completed",
                        task_id=task_id,
                        metrics_result=metrics_result,
                    )
                else:
                    await task_service.add_log(
                        task_id, "warn",
                        "未选择任何虚拟机进行指标采集"
                    )

                # 步骤3: 自动运行所有分析
                await task_service.add_log(
                    task_id, "info",
                    "数据采集完成，开始自动运行分析..."
                )

                # 分析结果记录
                analysis_results = {
                    "zombie": False,  # False 表示未运行或失败
                    "rightsize": False,
                    "tidal": False,
                    "health": False
                }
                analysis_errors = []

                # 导入分析服务
                from app.services.analysis import AnalysisService
                analysis_service = AnalysisService(session)

                # 3.1 僵尸VM分析
                try:
                    await task_service.add_log(task_id, "info", "开始僵尸VM检测...")
                    await _update_task_status(
                        session, task_id, "running", 55,
                        "正在进行僵尸VM检测..."
                    )

                    zombie_config = await analysis_service.get_mode("safe")
                    zombie_result = await analysis_service.run_zombie_analysis(task_id, zombie_config.get("zombie", {}))

                    if zombie_result.get("success"):
                        analysis_results["zombie"] = True
                        findings_count = len(zombie_result.get("data", []))
                        await task_service.add_log(task_id, "info", f"僵尸VM检测完成，发现 {findings_count} 台僵尸VM")
                        logger.info("zombie_analysis_success", task_id=task_id, findings_count=findings_count)
                    else:
                        error_info = zombie_result.get("error", {})
                        analysis_errors.append(f"僵尸VM检测失败: {error_info.get('message', 'Unknown error')}")
                        await task_service.add_log(task_id, "warn", f"僵尸VM检测失败: {error_info.get('message', 'Unknown error')}")

                except Exception as e:
                    error_msg = f"僵尸VM检测异常: {str(e)}"
                    analysis_errors.append(error_msg)
                    await task_service.add_log(task_id, "error", error_msg)
                    logger.error("zombie_analysis_exception", task_id=task_id, error=str(e), exc_info=True)

                # 3.2 Right Sizing分析
                try:
                    await task_service.add_log(task_id, "info", "开始资源配置优化分析...")
                    await _update_task_status(
                        session, task_id, "running", 70,
                        "正在进行资源配置优化分析..."
                    )

                    rightsize_config = await analysis_service.get_mode("safe")
                    rightsize_result = await analysis_service.run_rightsize_analysis(task_id, rightsize_config.get("rightsize", {}))

                    if rightsize_result.get("success"):
                        analysis_results["rightsize"] = True
                        findings_count = len(rightsize_result.get("data", []))
                        await task_service.add_log(task_id, "info", f"资源配置优化分析完成，涉及 {findings_count} 台虚拟机")
                        logger.info("rightsize_analysis_success", task_id=task_id, findings_count=findings_count)
                    else:
                        error_info = rightsize_result.get("error", {})
                        analysis_errors.append(f"资源配置优化分析失败: {error_info.get('message', 'Unknown error')}")
                        await task_service.add_log(task_id, "warn", f"资源配置优化分析失败: {error_info.get('message', 'Unknown error')}")

                except Exception as e:
                    error_msg = f"资源配置优化分析异常: {str(e)}"
                    analysis_errors.append(error_msg)
                    await task_service.add_log(task_id, "error", error_msg)
                    logger.error("rightsize_analysis_exception", task_id=task_id, error=str(e), exc_info=True)

                # 3.3 潮汐模式分析
                try:
                    await task_service.add_log(task_id, "info", "开始潮汐模式分析...")
                    await _update_task_status(
                        session, task_id, "running", 85,
                        "正在进行潮汐模式分析..."
                    )

                    tidal_config = await analysis_service.get_mode("safe")
                    tidal_result = await analysis_service.run_tidal_analysis(task_id, tidal_config.get("tidal", {}))

                    if tidal_result.get("success"):
                        analysis_results["tidal"] = True
                        findings_count = len(tidal_result.get("data", []))
                        await task_service.add_log(task_id, "info", f"潮汐模式分析完成，发现 {findings_count} 个潮汐模式")
                        logger.info("tidal_analysis_success", task_id=task_id, findings_count=findings_count)
                    else:
                        error_info = tidal_result.get("error", {})
                        analysis_errors.append(f"潮汐模式分析失败: {error_info.get('message', 'Unknown error')}")
                        await task_service.add_log(task_id, "warn", f"潮汐模式分析失败: {error_info.get('message', 'Unknown error')}")

                except Exception as e:
                    error_msg = f"潮汐模式分析异常: {str(e)}"
                    analysis_errors.append(error_msg)
                    await task_service.add_log(task_id, "error", error_msg)
                    logger.error("tidal_analysis_exception", task_id=task_id, error=str(e), exc_info=True)

                # 3.4 健康评分分析
                try:
                    await task_service.add_log(task_id, "info", "开始平台健康评分...")
                    await _update_task_status(
                        session, task_id, "running", 95,
                        "正在进行平台健康评分..."
                    )

                    health_config = await analysis_service.get_mode("safe")
                    health_result = await analysis_service.run_health_analysis(
                        task_id,  # task_id (primary parameter, like other analyses)
                        health_config.get("health", {})  # config
                    )

                    if health_result.get("success"):
                        analysis_results["health"] = True
                        health_score = health_result.get("data", {}).get("overallScore", 0)
                        await task_service.add_log(task_id, "info", f"平台健康评分完成，得分: {health_score}")
                        logger.info("health_analysis_success", task_id=task_id, score=health_score)
                    else:
                        error_info = health_result.get("error", {})
                        analysis_errors.append(f"平台健康评分失败: {error_info.get('message', 'Unknown error')}")
                        await task_service.add_log(task_id, "warn", f"平台健康评分失败: {error_info.get('message', 'Unknown error')}")

                except Exception as e:
                    error_msg = f"平台健康评分异常: {str(e)}"
                    analysis_errors.append(error_msg)
                    await task_service.add_log(task_id, "error", error_msg)
                    logger.error("health_analysis_exception", task_id=task_id, error=str(e), exc_info=True)

                # 步骤4: 所有分析完成，标记任务为完成
                completed_count = sum(analysis_results.values())
                total_count = len(analysis_results)
                failed_count = total_count - completed_count

                # 更新任务结果，包含分析结果
                result_data = {
                    "collectedVMCount": vm_count,
                    "analysisResults": analysis_results,
                    "analysisErrors": analysis_errors if analysis_errors else None
                }

                if failed_count > 0:
                    # 有失败的分析
                    status_message = f"部分完成：{completed_count}/{total_count} 个分析成功"
                    if analysis_errors:
                        status_message += f"，{failed_count} 个分析失败"
                    await _update_task_status(
                        session, task_id, "completed", 100,
                        status_message,
                        result_data
                    )
                else:
                    # 全部成功
                    await _update_task_status(
                        session, task_id, "completed", 100,
                        "评估任务全部完成",
                        result_data
                    )

                await task_service.add_log(
                    task_id, "info",
                    f"任务执行完成，共处理 {vm_count} 台虚拟机，{completed_count}/{total_count} 个分析完成"
                )

                logger.info(
                    "collection_task_with_analysis_completed",
                    task_id=task_id,
                    vm_count=vm_count,
                    analysis_results=analysis_results,
                    completed_count=completed_count,
                    total_count=total_count
                )

            except Exception as e:
                logger.error(
                    "collection_task_inner_failed",
                    task_id=task_id,
                    error=str(e),
                    exc_info=True
                )
                await task_service.add_log(task_id, "error", f"任务执行失败: {str(e)}")
                await _update_task_status(
                    session, task_id, "failed", 0,
                    f"任务执行失败: {str(e)}"
                )

    except Exception as e:
        logger.error(
            "collection_task_failed",
            task_id=task_id,
            error=str(e),
            exc_info=True
        )


async def execute_task_async(task_id: int, connection_id: int, config: dict):
    """在后台执行任务

    注意：此函数在后台线程中执行，需要独立处理数据库会话和错误
    """
    import asyncio
    from app.core.database import async_session
    from app.services.collection import CollectionService

    logger.info("task_execution_started", task_id=task_id, connection_id=connection_id)

    # 等待主事务提交
    await asyncio.sleep(0.5)

    try:
        async with async_session() as session:
            logger.info("task_execution_session_created", task_id=task_id)
            try:
                # 更新任务状态为 running
                logger.info("task_execution_calling_update_status_running", task_id=task_id)
                await _update_task_status(session, task_id, "running", 0, "正在采集资源...")

                # 执行采集（资源已经在 Wizard 中采集过了，这里只更新状态）
                collection_service = CollectionService(session)

                # 获取已采集的 VM 数量
                from sqlalchemy import select, func
                from app.models import VM as VMModel
                result = await session.execute(
                    select(func.count()).select_from(VMModel).where(VMModel.connection_id == connection_id)
                )
                vm_count = result.scalar() or 0

                logger.info("task_execution_vm_count", task_id=task_id, vm_count=vm_count)

                # 更新采集进度
                await _update_task_status(
                    session, task_id, "running", 30,
                    f"已完成 {vm_count} 台虚拟机的信息采集",
                    {"collectedVMCount": vm_count}
                )

                # 由于采集已经在 Wizard 中完成，这里直接标记为完成
                # 实际的分析可以由用户手动触发
                await _update_task_status(
                    session, task_id, "completed", 100,
                    "资源采集完成",
                    {
                        "collectedVMCount": vm_count,
                        "currentStep": "采集完成"
                    }
                )

                logger.info("task_execution_completed", task_id=task_id, vm_count=vm_count)

            except Exception as e:
                logger.error("task_execution_inner_failed", task_id=task_id, error=str(e), exc_info=True)
                await _update_task_status(
                    session, task_id, "failed", 0,
                    f"任务执行失败: {str(e)}"
                )

    except Exception as e:
        logger.error("task_execution_failed", task_id=task_id, error=str(e), exc_info=True)


async def _update_task_status(
    session: AsyncSession,
    task_id: int,
    status: str,
    progress: float,
    current_step: str,
    result_update: dict = None
):
    """更新任务状态"""
    from sqlalchemy import select, update
    from app.models import AssessmentTask

    # 获取当前任务
    result = await session.execute(
        select(AssessmentTask).where(AssessmentTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        logger.warning("_update_task_status_task_not_found", task_id=task_id)
        return

    logger.info("_update_task_status_before", task_id=task_id, old_status=task.status, new_status=status)

    # 更新基本状态
    task.status = status
    task.progress = progress

    # 更新 started_at
    if status == "running" and not task.started_at:
        from datetime import datetime
        task.started_at = datetime.now()

    # 更新 completed_at
    if status in ("completed", "failed", "cancelled") and not task.completed_at:
        from datetime import datetime
        task.completed_at = datetime.now()

    # 更新 result JSON
    current_result = {}
    if task.result:
        try:
            current_result = json.loads(task.result) if isinstance(task.result, str) else task.result
        except:
            pass

    if result_update:
        current_result.update(result_update)
    current_result["currentStep"] = current_step

    task.result = json.dumps(current_result)

    await session.commit()
    await session.flush()

    logger.info("_update_task_status_after", task_id=task_id, status=status, progress=progress)
    logger.info(f"task_{task_id}_status_updated", status=status, progress=progress)


@router.get("", response_model=dict)
async def list_tasks(
    status: Optional[str] = Query(None),
    limit: int = Query(100),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List all tasks (lite version, only essential fields for card display).

    This endpoint is designed for polling and returns minimal data to reduce bandwidth.
    Use GET /api/tasks/{id} to get full task details.
    """
    logger.debug("list_tasks_requested", status=status, limit=limit)

    service = TaskService(db)
    tasks = await service.list_tasks(status=status, limit=limit)

    logger.debug(
        "list_tasks_success",
        count=len(tasks),
        status_filter=status,
        task_ids=[t.id for t in tasks],
    )

    return {
        "success": True,
        "data": {
            "items": [_task_to_dict(t, lite=True) for t in tasks],  # lite模式
            "total": len(tasks),
        },
    }


@router.get("/{task_id}", response_model=dict)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get task details by ID (full version with all fields).

    This returns complete task information including:
    - Full configuration (selectedVMs, config, etc.)
    - Analysis results (zombieResult, rightsizeResult, etc.)
    - Task logs
    - All timestamps

    Use this when user clicks on a task card to view details.
    """
    logger.debug("get_task_requested", task_id=task_id)

    service = TaskService(db)

    try:
        task = await service.get_task(task_id)
        logger.debug(
            "get_task_success",
            task_id=task_id,
            name=task.name,
            status=task.status,
            progress=task.progress,
        )
        return {
            "success": True,
            "data": _task_to_dict(task),
        }
    except NotFoundError as e:
        logger.warning("get_task_not_found", task_id=task_id)
        return error_response(e)


@router.delete("/{task_id}", response_model=dict)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Delete task."""
    logger.info("delete_task_requested", task_id=task_id)

    service = TaskService(db)

    try:
        await service.delete_task(task_id)
        logger.info("delete_task_success", task_id=task_id)
        return {
            "success": True,
            "message": f"Task {task_id} deleted",
        }
    except (NotFoundError, ValidationError) as e:
        logger.error(
            "delete_task_failed",
            task_id=task_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        return error_response(e)


@router.post("/{task_id}/cancel", response_model=dict)
async def cancel_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Cancel running task."""
    logger.info("cancel_task_requested", task_id=task_id)

    service = TaskService(db)

    try:
        task = await service.cancel_task(task_id)
        # 添加日志记录
        await service.add_log(task_id, "info", "任务已被用户取消")
        logger.info(
            "cancel_task_success",
            task_id=task_id,
            previous_status=task.status,
        )
        return {
            "success": True,
            "message": f"Task {task_id} cancelled",
            "data": _task_to_dict(task),
        }
    except (NotFoundError, ValidationError) as e:
        logger.error(
            "cancel_task_failed",
            task_id=task_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        return error_response(e)


@router.post("/{task_id}/retry", response_model=dict)
async def retry_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Retry a failed task by creating a new task with the same configuration."""
    logger.info("retry_task_requested", task_id=task_id)

    service = TaskService(db)

    try:
        new_task = await service.retry_task(task_id)
        logger.info(
            "retry_task_success",
            original_task_id=task_id,
            new_task_id=new_task.id,
        )
        return {
            "success": True,
            "data": _task_to_dict(new_task),
        }
    except (NotFoundError, ValidationError) as e:
        logger.warning("retry_task_failed", task_id=task_id, error=str(e))
        return error_response(e)


@router.get("/{task_id}/logs", response_model=dict)
async def get_task_logs(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get task logs."""
    service = TaskService(db)

    try:
        logs = await service.get_task_logs(task_id)
        # 确保每条日志都有 timestamp 字段
        formatted_logs = []
        for log in logs:
            formatted_log = {
                "id": log.get("id"),
                "level": log.get("level", "info"),
                "message": log.get("message", ""),
                # 如果有 createdAt，使用它作为 timestamp
                "timestamp": log.get("createdAt") or log.get("timestamp") or "",
            }
            formatted_logs.append(formatted_log)

        return {
            "success": True,
            "data": {
                "items": formatted_logs,
                "total": len(formatted_logs),
            },
        }
    except NotFoundError as e:
        return error_response(e)


@router.get("/{task_id}/vm-snapshots", response_model=dict)
async def get_vm_snapshots(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get task VM snapshots."""
    service = TaskService(db)

    try:
        snapshots = await service.get_vm_snapshots(task_id)
        return {
            "success": True,
            "data": {
                "items": [
                    {
                        "id": s.id,
                        "vmName": s.vm_name,
                        "vmKey": s.vm_key,
                        "datacenter": s.datacenter,
                        "cpuCount": s.cpu_count,
                        "memoryGb": round(s.memory_bytes / (1024**3), 2),
                        "powerState": s.power_state,
                        "hostIp": s.host_ip,
                    }
                    for s in snapshots
                ],
                "total": len(snapshots),
            },
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "GET_SNAPSHOTS_FAILED",
                "message": str(e),
            },
        }


@router.get("/{task_id}/vms", response_model=dict)
async def get_task_vms(
    task_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    keyword: str = Query(""),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get task VMs with pagination and filtering by selected VMs."""
    from sqlalchemy import select
    from app.models import AssessmentTask, VM as VMModel

    logger.info("get_task_vms_requested", task_id=task_id, limit=limit, offset=offset, keyword=keyword)

    # 获取任务
    task_result = await db.execute(
        select(AssessmentTask).where(AssessmentTask.id == task_id)
    )
    task = task_result.scalar_one_or_none()
    if not task:
        return error_response(NotFoundError(f"Task {task_id} not found"))

    # 解析 config 获取 selectedVMs
    config = {}
    if task.config:
        try:
            config = json.loads(task.config) if isinstance(task.config, str) else task.config
        except:
            config = {}

    selected_vm_keys = config.get("selectedVMs", [])

    # 构建查询
    query = select(VMModel).where(VMModel.connection_id == task.connection_id)

    # 如果有选中的 VM，只返回选中的 VM
    if selected_vm_keys:
        # 添加 connection_id 前缀
        prefixed_keys = []
        for key in selected_vm_keys:
            if key.startswith(f"conn{task.connection_id}:"):
                prefixed_keys.append(key)
            else:
                prefixed_keys.append(f"conn{task.connection_id}:{key}")
        query = query.where(VMModel.vm_key.in_(prefixed_keys))

    # 关键字搜索
    if keyword:
        query = query.where(VMModel.name.ilike(f"%{keyword}%"))

    # 获取总数
    from sqlalchemy import func
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页
    query = query.offset(offset).limit(limit)
    vm_result = await db.execute(query)
    vms = vm_result.scalars().all()

    return {
        "success": True,
        "data": {
            "vms": [
                {
                    "id": vm.id,
                    "name": vm.name,
                    "datacenter": vm.datacenter or "",
                    "vmKey": vm.vm_key,
                    "cpuCount": vm.cpu_count or 0,
                    "memoryGb": round(vm.memory_bytes / (1024**3), 2) if vm.memory_bytes else 0,
                    "powerState": vm.power_state or "unknown",
                    "connectionState": vm.connection_state or "connected",
                    "hostIp": vm.host_ip or "",
                }
                for vm in vms
            ],
            "total": total,
        },
    }
