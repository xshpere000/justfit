"""Metric Model - VM Performance Metrics.

数据单位规范（与 connectors/base.py 的 VMMetrics 保持一致）:
    - cpu: MHz (兆赫兹)
    - memory: bytes (字节)
    - disk_read: bytes/s (字节/秒)
    - disk_write: bytes/s (字节/秒)
    - net_rx: bytes/s (字节/秒)
    - net_tx: bytes/s (字节/秒)

注意: 此模型存储的是时间序列数据（每小时一个点），不是聚合平均值。
"""

from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Index
from typing import TYPE_CHECKING

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.task import AssessmentTask
    from app.models.resource import VM


class VMMetric(Base):
    """虚拟机性能指标 - 时序数据存储.

    每个 VM 每小时每种指标类型一条记录。

    Attributes:
        id: 主键
        task_id: 关联的评估任务 ID
        vm_id: 关联的虚拟机 ID
        metric_type: 指标类型
        value: 指标值（单位见下文）
        timestamp: 时间戳（整点）

    metric_type 与 value 单位对照:
        metric_type    | value 单位      | 说明
        ---------------|----------------|------------------
        cpu            | MHz            | 实际使用频率
        memory         | bytes          | 实际使用内存
        disk_read      | bytes/s        | 磁盘读取速率
        disk_write     | bytes/s        | 磁盘写入速率
        net_rx         | bytes/s        | 网络接收速率
        net_tx         | bytes/s        | 网络发送速率
    """

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
    # 指标类型: cpu|memory|disk_read|disk_write|net_rx|net_tx
    # 注意: 网络指标使用 net_rx/net_tx (而非 net_received/net_transmitted) 以保持简洁
    metric_type: Mapped[str] = mapped_column(String(20))
    # value 单位取决于 metric_type，见上表
    value: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime)

    vm: Mapped["VM"] = relationship(back_populates="metrics")
    task: Mapped["AssessmentTask"] = relationship(back_populates="metrics")

    __table_args__ = (
        Index("ix_metrics_task_vm_type", "task_id", "vm_id", "metric_type"),
    )
