"""Metric Repository."""

from datetime import datetime
from typing import List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import VMMetric
from .base import BaseRepository


class MetricRepository(BaseRepository[VMMetric]):
    """Repository for VMMetric model."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize metric repository."""
        super().__init__(VMMetric, session)

    async def get_metrics_by_vm(
        self,
        task_id: int,
        vm_id: int,
        start_time: datetime,
        end_time: datetime,
    ) -> List[VMMetric]:
        """Get metrics for VM within time range.

        Args:
            task_id: Task ID
            vm_id: VM ID
            start_time: Start time
            end_time: End time

        Returns:
            List of metrics
        """
        result = await self.session.execute(
            select(VMMetric)
            .where(
                and_(
                    VMMetric.task_id == task_id,
                    VMMetric.vm_id == vm_id,
                    VMMetric.timestamp >= start_time,
                    VMMetric.timestamp <= end_time,
                )
            )
            .order_by(VMMetric.timestamp.asc())
        )
        return list(result.scalars().all())

    async def get_metrics_by_type(
        self,
        task_id: int,
        vm_id: int,
        metric_type: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[VMMetric]:
        """Get metrics of specific type.

        Args:
            task_id: Task ID
            vm_id: VM ID
            metric_type: Metric type
            start_time: Start time
            end_time: End time

        Returns:
            List of metrics
        """
        result = await self.session.execute(
            select(VMMetric)
            .where(
                and_(
                    VMMetric.task_id == task_id,
                    VMMetric.vm_id == vm_id,
                    VMMetric.metric_type == metric_type,
                    VMMetric.timestamp >= start_time,
                    VMMetric.timestamp <= end_time,
                )
            )
            .order_by(VMMetric.timestamp.asc())
        )
        return list(result.scalars().all())

    async def delete_by_task(self, task_id: int) -> int:
        """Delete all metrics for a task.

        Args:
            task_id: Task ID

        Returns:
            Number of deleted records
        """
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(VMMetric).where(VMMetric.task_id == task_id)
        )
        await self.session.flush()
        return result.rowcount

    async def count_metrics(self, task_id: int, vm_id: int) -> dict:
        """Count metrics by type for VM.

        Args:
            task_id: Task ID
            vm_id: VM ID

        Returns:
            Dictionary with counts per metric type
        """
        result = await self.session.execute(
            select(VMMetric.metric_type)
            .where(
                and_(
                    VMMetric.task_id == task_id,
                    VMMetric.vm_id == vm_id,
                )
            )
            .distinct()
        )
        types = [row[0] for row in result.all()]

        counts = {}
        for metric_type in types:
            count_result = await self.session.execute(
                select(VMMetric)
                .where(
                    and_(
                        VMMetric.task_id == task_id,
                        VMMetric.vm_id == vm_id,
                        VMMetric.metric_type == metric_type,
                    )
                )
            )
            counts[metric_type] = len(count_result.scalars().all())

        return counts
