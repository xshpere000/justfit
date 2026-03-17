"""Task Service - Assessment task management."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import structlog

from app.models import (
    AssessmentTask, TaskVMSnapshot, TaskAnalysisJob,
    VMMetric, Connection
)
from app.repositories.base import BaseRepository
from app.repositories.connection import ConnectionRepository
from app.core.errors import NotFoundError, ValidationError, AppError


logger = structlog.get_logger()


class TaskService:
    """Service for managing assessment tasks."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize task service.

        Args:
            session: Database session
        """
        self.session = session
        self.task_repo = BaseRepository(AssessmentTask, session)
        self.connection_repo = ConnectionRepository(session)

    async def create_task(
        self,
        name: str,
        task_type: str,
        connection_id: int,
        config: Optional[Dict] = None,
    ) -> AssessmentTask:
        """Create a new assessment task.

        Args:
            name: Task name
            task_type: Task type (collection or analysis)
            connection_id: Connection ID
            config: Task configuration

        Returns:
            Created task

        Raises:
            ValidationError: If validation fails
        """
        # Validate task type
        if task_type not in ("collection", "analysis"):
            raise ValidationError(f"Invalid task type: {task_type}")

        # Validate connection exists
        connection = await self.connection_repo.get_by_id(connection_id)
        if not connection:
            raise NotFoundError(f"Connection {connection_id} not found")

        # Create task
        import json
        task = await self.task_repo.create(
            name=name,
            type=task_type,
            connection_id=connection_id,
            config=json.dumps(config) if config else None,
            status="pending",
            progress=0.0,
        )

        logger.info(
            "task_created",
            task_id=task.id,
            name=name,
            type=task_type,
            connection_id=connection_id,
        )

        return task

    async def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[AssessmentTask]:
        """List tasks with optional filtering.

        Args:
            status: Filter by status
            limit: Max results

        Returns:
            List of tasks
        """
        query = select(AssessmentTask).order_by(AssessmentTask.created_at.desc())

        if status:
            query = query.where(AssessmentTask.status == status)

        query = query.limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_task(self, task_id: int) -> AssessmentTask:
        """Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task

        Raises:
            NotFoundError: If task not found
        """
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise NotFoundError(f"Task {task_id} not found")
        return task

    async def update_task_progress(
        self,
        task_id: int,
        progress: float,
        status: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update task progress.

        Args:
            task_id: Task ID
            progress: Progress value (0-100)
            status: New status
            error: Error message if failed
        """
        updates = {"progress": progress}
        if status:
            updates["status"] = status
        if error:
            updates["error"] = error

        if status == "running":
            updates["started_at"] = datetime.now()
        elif status in ("completed", "failed", "cancelled"):
            updates["completed_at"] = datetime.now()

        await self.session.execute(
            update(AssessmentTask).where(AssessmentTask.id == task_id).values(**updates)
        )
        await self.session.flush()

        logger.debug("task_progress_updated", task_id=task_id, progress=progress)

    async def cancel_task(self, task_id: int) -> AssessmentTask:
        """Cancel a task.

        Args:
            task_id: Task ID

        Returns:
            Updated task

        Raises:
            NotFoundError: If task not found
        """
        task = await self.get_task(task_id)

        if task.status not in ("pending", "running"):
            raise ValidationError(f"Cannot cancel task with status: {task.status}")

        await self.update_task_progress(task_id, progress=task.progress, status="cancelled")

        logger.info("task_cancelled", task_id=task_id)

        return task

    async def delete_task(self, task_id: int) -> None:
        """Delete a task.

        Args:
            task_id: Task ID

        Raises:
            NotFoundError: If task not found
        """
        task = await self.get_task(task_id)

        # Don't allow deleting running tasks
        if task.status == "running":
            raise ValidationError("Cannot delete running task")

        await self.task_repo.delete(task_id)

        logger.info("task_deleted", task_id=task_id)

    async def add_vm_snapshot(
        self,
        task_id: int,
        vm_name: str,
        vm_key: str,
        datacenter: str,
        cpu_count: int,
        memory_bytes: int,
        power_state: str,
        host_ip: str,
    ) -> TaskVMSnapshot:
        """Add VM snapshot to task.

        Args:
            task_id: Task ID
            vm_name: VM name
            vm_key: VM unique key
            datacenter: Datacenter name
            cpu_count: CPU count
            memory_bytes: Memory in bytes
            power_state: Power state
            host_ip: Host IP address

        Returns:
            Created snapshot
        """
        snapshot = TaskVMSnapshot(
            task_id=task_id,
            vm_name=vm_name,
            vm_key=vm_key,
            datacenter=datacenter,
            cpu_count=cpu_count,
            memory_bytes=memory_bytes,
            power_state=power_state,
            host_ip=host_ip,
        )
        self.session.add(snapshot)
        await self.session.flush()
        await self.session.refresh(snapshot)

        return snapshot

    async def add_log(
        self,
        task_id: int,
        level: str,
        message: str,
    ) -> TaskLog:
        """Add log entry to task.

        Args:
            task_id: Task ID
            level: Log level (debug, info, warn, error)
            message: Log message

        Returns:
            Created log entry
        """
        from app.models import TaskLog

        log = TaskLog(
            task_id=task_id,
            level=level,
            message=message,
            created_at=datetime.now(),
        )
        self.session.add(log)
        await self.session.flush()

        return log

    async def get_vm_snapshots(
        self,
        task_id: int,
    ) -> List[TaskVMSnapshot]:
        """Get VM snapshots for task.

        Args:
            task_id: Task ID

        Returns:
            List of VM snapshots
        """
        from sqlalchemy import select
        from app.models import TaskVMSnapshot

        result = await self.session.execute(
            select(TaskVMSnapshot).where(TaskVMSnapshot.task_id == task_id)
        )
        return list(result.scalars().all())

    async def save_metric(
        self,
        task_id: int,
        vm_id: int,
        metric_type: str,
        value: float,
        timestamp: datetime,
    ) -> VMMetric:
        """Save VM metric.

        Args:
            task_id: Task ID
            vm_id: VM ID
            metric_type: Metric type (cpu, memory, disk_read, etc.)
            value: Metric value
            timestamp: Metric timestamp

        Returns:
            Created metric
        """
        metric = VMMetric(
            task_id=task_id,
            vm_id=vm_id,
            metric_type=metric_type,
            value=value,
            timestamp=timestamp,
        )
        self.session.add(metric)
        await self.session.flush()
        await self.session.refresh(metric)

        return metric

    async def collect_vm_metrics(
        self,
        task_id: int,
        connection_id: int,
        selected_vm_keys: List[str],
        metric_days: int = 30,
    ) -> Dict[str, int]:
        """Collect VM metrics for analysis.

        Args:
            task_id: Task ID
            connection_id: Connection ID
            selected_vm_keys: List of VM keys to collect metrics for
            metric_days: Number of days of metrics to collect (1-90)

        Returns:
            Dictionary with collection stats
        """
        from app.services.connection import ConnectionService
        from app.models import VM as VMModel
        from sqlalchemy import select

        conn_service = ConnectionService(self.session)
        connector = await conn_service.get_connector(connection_id)

        # Get selected VMs from database
        # Add connection_id prefix to vm_keys if not already present
        prefixed_keys = []
        for key in selected_vm_keys:
            if key.startswith(f"conn{connection_id}:"):
                prefixed_keys.append(key)
            else:
                prefixed_keys.append(f"conn{connection_id}:{key}")

        vm_query = (
            select(VMModel)
            .where(
                VMModel.connection_id == connection_id,
                VMModel.vm_key.in_(prefixed_keys)
            )
        )
        result = await self.session.execute(vm_query)
        vms = result.scalars().all()

        if not vms:
            logger.warning("collect_vm_metrics_no_vms", task_id=task_id, connection_id=connection_id)
            return {"total": 0, "collected": 0, "failed": 0}

        collected = 0
        failed = 0
        now = datetime.now()

        # For each VM, collect metrics
        for vm in vms:
            try:
                # Get metrics from vCenter (realtime data)
                from datetime import timedelta
                end_time = now
                start_time = now - timedelta(days=metric_days)  # Get metrics for specified days

                metrics = await connector.get_vm_metrics(
                    datacenter=vm.datacenter or "",
                    vm_name=vm.name,
                    vm_uuid=vm.uuid or "",
                    start_time=start_time,
                    end_time=end_time,
                    cpu_count=vm.cpu_count or 1,
                    total_memory_bytes=vm.memory_bytes or 0,
                )

                # Save metrics
                await self._save_vm_metrics(task_id, vm.id, metrics, now)
                collected += 1

            except Exception as e:
                logger.error("collect_vm_metrics_failed", vm_id=vm.id, vm_name=vm.name, error=str(e))
                failed += 1

        logger.info(
            "collect_vm_metrics_completed",
            task_id=task_id,
            total=len(vms),
            collected=collected,
            failed=failed,
        )

        return {"total": len(vms), "collected": collected, "failed": failed}

    async def _save_vm_metrics(
        self,
        task_id: int,
        vm_id: int,
        metrics: Any,
        timestamp: datetime,
    ) -> None:
        """Save VM metrics to database.

        如果 metrics.hourly_series 存在，则保存按小时聚合的时间序列数据；
        否则保存单个聚合值。

        Args:
            task_id: Task ID
            vm_id: VM ID
            metrics: VMMetrics object
            timestamp: Timestamp for metrics
        """
        from datetime import timedelta, datetime as dt

        # 检查是否有按小时聚合的时间序列数据
        hourly_series = getattr(metrics, 'hourly_series', None)

        if hourly_series and isinstance(hourly_series, list):
            # 保存每个小时的聚合数据
            saved_count = 0
            for data_point in hourly_series:
                try:
                    # data_point 格式：(hour_timestamp_ms, cpu_avg, cpu_min, cpu_max, memory_avg, memory_min, memory_max,
                    #                  disk_read_avg, disk_write_avg, net_rx_avg, net_tx_avg)
                    hour_timestamp_ms = data_point[0]
                    cpu_avg = data_point[1]
                    memory_avg = data_point[4]
                    disk_read_avg = data_point[7]
                    disk_write_avg = data_point[8]
                    net_rx_avg = data_point[9]
                    net_tx_avg = data_point[10]

                    # 将毫秒时间戳转换为 datetime
                    point_timestamp = dt.fromtimestamp(hour_timestamp_ms / 1000)

                    # 保存该小时的平均值，暂只保存平均值，后续可扩展 min/max）
                    # 注意：hourly_series 中的单位已经是标准单位：cpu=MHz, memory=bytes, disk/net=bytes/s
                    await self.save_metric(task_id, vm_id, "cpu", float(cpu_avg), point_timestamp)
                    await self.save_metric(task_id, vm_id, "memory", float(memory_avg), point_timestamp)  # 已经是 bytes
                    await self.save_metric(task_id, vm_id, "disk_read", float(disk_read_avg), point_timestamp)
                    await self.save_metric(task_id, vm_id, "disk_write", float(disk_write_avg), point_timestamp)
                    await self.save_metric(task_id, vm_id, "net_rx", float(net_rx_avg), point_timestamp)
                    await self.save_metric(task_id, vm_id, "net_tx", float(net_tx_avg), point_timestamp)
                    saved_count += 1

                except Exception as e:
                    logger.warning("failed_to_save_hourly_metric_point", vm_id=vm_id, error=str(e))

            logger.info(
                "saved_hourly_metrics",
                task_id=task_id,
                vm_id=vm_id,
                hours_count=saved_count,
            )
        else:
            # 没有时间序列数据，保存单个聚合值
            metric_types = [
                ("cpu", metrics.cpu_mhz if hasattr(metrics, 'cpu_mhz') else 0),
                ("memory", metrics.memory_bytes if hasattr(metrics, 'memory_bytes') else 0),
                ("disk_read", metrics.disk_read_bytes_per_sec if hasattr(metrics, 'disk_read_bytes_per_sec') else 0),
                ("disk_write", metrics.disk_write_bytes_per_sec if hasattr(metrics, 'disk_write_bytes_per_sec') else 0),
                ("net_rx", metrics.net_rx_bytes_per_sec if hasattr(metrics, 'net_rx_bytes_per_sec') else 0),
                ("net_tx", metrics.net_tx_bytes_per_sec if hasattr(metrics, 'net_tx_bytes_per_sec') else 0),
            ]

            for metric_type, value in metric_types:
                await self.save_metric(task_id, vm_id, metric_type, float(value), timestamp)

    async def get_task_logs(self, task_id: int) -> List[dict]:
        """Get task logs.

        Args:
            task_id: Task ID

        Returns:
            List of log entries
        """
        from sqlalchemy import select
        from app.models import TaskLog

        result = await self.session.execute(
            select(TaskLog)
            .where(TaskLog.task_id == task_id)
            .order_by(TaskLog.created_at.asc())
        )
        logs = result.scalars().all()

        return [
            {
                "id": log.id,
                "level": log.level,
                "message": log.message,
                "createdAt": (log.created_at.isoformat() + "Z") if log.created_at else None,
            }
            for log in logs
        ]

    async def retry_task(self, task_id: int) -> AssessmentTask:
        """Retry a failed task by creating a new task with the same configuration.

        Args:
            task_id: Original task ID

        Returns:
            New task
        """
        from sqlalchemy import select

        # Get original task
        result = await self.session.execute(
            select(AssessmentTask).where(AssessmentTask.id == task_id)
        )
        original_task = result.scalar_one_or_none()

        if not original_task:
            raise NotFoundError(f"Task {task_id} not found")

        # Create new task with same configuration
        new_task = AssessmentTask(
            name=f"{original_task.name} (重试)",
            type=original_task.type,
            connection_id=original_task.connection_id,
            config=original_task.config,
            status="pending",
            progress=0,
        )
        self.session.add(new_task)
        await self.session.commit()
        await self.session.refresh(new_task)

        logger.info(
            "task_retried",
            original_task_id=task_id,
            new_task_id=new_task.id,
        )

        return new_task
