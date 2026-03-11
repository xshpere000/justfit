# JustFit 分析系统实现计划

## 文档信息

| 项目 | 说明 |
|------|------|
| 文档版本 | v2.0 |
| 创建日期 | 2026-03-08 |
| 目标版本 | v0.0.4 |
| 实施性质 | 全新实现（无历史包袱）|

---

## 一、系统架构概述

### 1.1 三大分析维度

```
┌─────────────────────────────────────────────────────────────┐
│                    JustFit 分析系统                         │
│                  Resource Optimization System               │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   闲置检测     │   │   资源分析     │   │   健康评估     │
│  (idle)       │   │  (resource)   │   │  (health)     │
├───────────────┤   ├───────────────┤   ├───────────────┤
│关机型僵尸     │   │Right Size     │   │资源超配分析   │
│开机闲置型     │   │使用模式分析   │   │负载均衡分析   │
│低效运行型     │   │资源错配检测   │   │热点风险分析   │
└───────────────┘   └───────────────┘   └───────────────┘
```

### 1.2 分析类型定义

```python
# backend/app/analyzers/types.py

from enum import Enum


class AnalysisType(Enum):
    """分析类型枚举（三大类）"""
    IDLE = "idle"           # 闲置检测
    RESOURCE = "resource"   # 资源分析
    HEALTH = "health"       # 健康评估


class IdleSubType(Enum):
    """闲置检测子类型"""
    POWERED_OFF = "powered_off"           # 关机型僵尸
    IDLE_POWERED_ON = "idle_powered_on"   # 开机闲置型
    LOW_ACTIVITY = "low_activity"         # 低效运行型


class ResourceSubType(Enum):
    """资源分析子类型"""
    RIGHT_SIZE = "right_size"             # Right Size 分析
    USAGE_PATTERN = "usage_pattern"       # 使用模式分析
    MISMATCH = "mismatch"                # 资源错配检测


class HealthSubType(Enum):
    """健康评估子类型"""
    OVERCOMMIT = "overcommit"             # 超配分析
    BALANCE = "balance"                   # 负载均衡分析
    HOTSPOT = "hotspot"                   # 热点分析


class VMStatus(Enum):
    """VM 综合状态"""
    ACTIVE = "active"                     # 正常活跃
    IDLE_ZOMBIE = "idle_zombie"           # 闲置僵尸
    OVER_PROVISIONED = "over_provisioned" # 配置过剩
    TIDAL_USAGE = "tidal_usage"           # 潮汐使用
    OPTIMIZED = "optimized"               # 已优化


class Priority(Enum):
    """优化优先级"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"
```

---

## 二、数据模型设计

### 2.1 数据库表结构

#### 2.1.1 VM表修改（关机型检测必需）

⚠️ **重要**：关机型僵尸检测需要在 VM 表中添加时间字段

```sql
-- 修改 vms 表 - 添加时间字段（已实际完成）
ALTER TABLE vms ADD COLUMN vm_create_time TIMESTAMP;
ALTER TABLE vms ADD COLUMN uptime_duration INTEGER DEFAULT 0;
ALTER TABLE vms ADD COLUMN downtime_duration INTEGER DEFAULT 0;

-- 创建索引
CREATE INDEX ix_vms_create_time ON vms(vm_create_time);
CREATE INDEX ix_vms_uptime ON vms(uptime_duration);
CREATE INDEX ix_vms_downtime ON vms(downtime_duration);

-- 完整的 vms 表结构（新增字段标记为 ✅）
CREATE TABLE vms (
    id INTEGER PRIMARY KEY,
    connection_id INTEGER,
    name VARCHAR(255),
    datacenter VARCHAR(255),
    uuid VARCHAR(100),
    vm_key VARCHAR(255) UNIQUE,
    cpu_count INTEGER DEFAULT 0,
    memory_bytes BIGINT DEFAULT 0,
    power_state VARCHAR(20) DEFAULT "",
    guest_os VARCHAR(100) DEFAULT "",
    ip_address VARCHAR(50) DEFAULT "",
    host_name VARCHAR(255) DEFAULT "",
    host_ip VARCHAR(50) DEFAULT "",
    connection_state VARCHAR(20) DEFAULT "",
    overall_status VARCHAR(20) DEFAULT "",
    vm_create_time TIMESTAMP,                  -- ✅ VM创建时间
    uptime_duration INTEGER DEFAULT 0,         -- ✅ 开机时长（秒），仅开机VM有值
    downtime_duration INTEGER DEFAULT 0,       -- ✅ 关机时长（秒），仅关机VM有值
    collected_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (connection_id) REFERENCES connections(id) ON DELETE CASCADE
);
```

#### 2.1.2 分析相关表

```sql
-- 任务分析作业表
CREATE TABLE task_analysis_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    job_type VARCHAR(20) NOT NULL,        -- idle | resource | health
    sub_type VARCHAR(50),                 -- 子类型
    status VARCHAR(20) DEFAULT 'pending', -- pending | running | completed | failed
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result_summary TEXT,                  -- JSON
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES assessment_tasks(id) ON DELETE CASCADE
);

-- 分析发现表
CREATE TABLE analysis_findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    job_type VARCHAR(20) NOT NULL,        -- idle | resource | health
    sub_type VARCHAR(50),                 -- 子类型
    vm_name VARCHAR(200),
    severity VARCHAR(20),                 -- critical | high | medium | low | info
    title VARCHAR(200),
    description TEXT,
    recommendation TEXT,
    details TEXT,                         -- JSON
    confidence FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES assessment_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES task_analysis_jobs(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX ix_jobs_task_type ON task_analysis_jobs(task_id, job_type);
CREATE INDEX ix_findings_task_type ON analysis_findings(task_id, job_type, sub_type);
CREATE INDEX ix_findings_severity ON analysis_findings(severity);
```

### 2.2 SQLAlchemy 模型

#### 2.2.1 VM 模型修改（✅ 已完成）

⚠️ **重要**：VM 模型已添加时间字段以支持关机型检测

```python
# backend/app/models/resource.py

from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, ForeignKey, DateTime, Index
from typing import TYPE_CHECKING, Optional

from app.core.database import Base


class VM(Base, TimestampMixin):
    """Virtual Machine model."""

    __tablename__ = "vms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    connection_id: Mapped[int] = mapped_column(
        ForeignKey("connections.id", ondelete="CASCADE")
    )

    # 基础字段（现有）
    name: Mapped[str] = mapped_column(String(255))
    datacenter: Mapped[str] = mapped_column(String(255), default="")
    uuid: Mapped[str] = mapped_column(String(100), default="")
    vm_key: Mapped[str] = mapped_column(String(255), unique=True)
    cpu_count: Mapped[int] = mapped_column(Integer, default=0)
    memory_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    power_state: Mapped[str] = mapped_column(String(20), default="")
    guest_os: Mapped[str] = mapped_column(String(100), default="")
    ip_address: Mapped[str] = mapped_column(String(50), default="")
    host_name: Mapped[str] = mapped_column(String(255), default="")
    host_ip: Mapped[str] = mapped_column(String(50), default="")
    connection_state: Mapped[str] = mapped_column(String(20), default="")
    overall_status: Mapped[str] = mapped_column(String(20), default="")
    collected_at: Mapped[datetime] = mapped_column(default=datetime.now)

    # ✅ 已完成：时间字段（关机型检测必需）
    vm_create_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="VM创建时间")
    uptime_duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="开机时长（秒），仅开机VM有值")
    downtime_duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="关机时长（秒），仅关机VM有值")

    connection: Mapped["Connection"] = relationship(back_populates="vms")
    metrics: Mapped[List["VMMetric"]] = relationship(
        back_populates="vm", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('ix_vms_create_time', 'vm_create_time'),
        Index('ix_vms_uptime', 'uptime_duration'),
        Index('ix_vms_downtime', 'downtime_duration'),
    )
```

#### 2.2.2 连接器基类修改（✅ 已完成）

```python
# backend/app/connectors/base.py

@dataclass
class VMInfo:
    """Virtual Machine information."""

    # 现有字段
    name: str
    datacenter: str
    uuid: str
    cpu_count: int
    memory_bytes: int
    power_state: str
    guest_os: str
    ip_address: str
    host_name: str
    host_ip: str
    connection_state: str
    overall_status: str

    # ✅ 已完成：时间字段
    vm_create_time: Optional[datetime] = None
    uptime_duration: Optional[int] = None      # 开机时长（秒），仅开机VM有值
    downtime_duration: Optional[int] = None    # 关机时长（秒），仅关机VM有值
```

#### 2.2.3 任务模型

```python
# backend/app/models/task.py

from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, Text, Float, ForeignKey, Index
from typing import Optional

from app.core.database import Base


class TaskAnalysisJob(Base):
    """任务分析作业表"""

    __tablename__ = "task_analysis_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("assessment_tasks.id", ondelete="CASCADE"))
    job_type: Mapped[str] = mapped_column(String(20))  # idle | resource | health
    sub_type: Mapped[Optional[str]] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    result_summary: Mapped[Optional[str]] = mapped_column(Text)
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AnalysisFinding(Base):
    """分析发现表"""

    __tablename__ = "analysis_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("assessment_tasks.id", ondelete="CASCADE"))
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("task_analysis_jobs.id", ondelete="CASCADE"))
    job_type: Mapped[str] = mapped_column(String(20))  # idle | resource | health
    sub_type: Mapped[Optional[str]] = mapped_column(String(50))
    vm_name: Mapped[str] = mapped_column(String(200))
    severity: Mapped[str] = mapped_column(String(20))  # critical | high | medium | low | info
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    recommendation: Mapped[Optional[str]] = mapped_column(Text)
    details: Mapped[Optional[str]] = mapped_column(Text)  # JSON
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('ix_findings_task_type', 'task_id', 'job_type', 'sub_type'),
        Index('ix_findings_severity', 'severity'),
    )
```

### 2.3 Pydantic Schema

```python
# backend/app/schemas/analysis.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class IdleDetectionResult(BaseModel):
    """闲置检测结果"""

    is_idle: bool = Field(..., description="是否为闲置VM")
    idle_type: Optional[str] = Field(None, description="闲置类型: powered_off/idle_powered_on/low_activity")
    confidence: float = Field(..., ge=0, le=100, description="置信度 0-100")
    risk_level: str = Field(..., description="风险等级: critical/high/medium/low")

    # 关机型特有字段
    days_inactive: Optional[int] = Field(None, description="未活跃天数")
    last_activity_time: Optional[datetime] = Field(None, description="最后活跃时间")

    # 开机型特有字段
    activity_score: Optional[float] = Field(None, description="活跃度分数 0-100")
    cpu_usage_p95: Optional[float] = Field(None, description="CPU P95使用率")
    memory_usage_p95: Optional[float] = Field(None, description="内存 P95使用率")
    disk_io_p95: Optional[float] = Field(None, description="磁盘 I/O P95")
    network_p95: Optional[float] = Field(None, description="网络 P95")

    # 数据质量
    data_quality: Optional[str] = Field(None, description="数据质量: high/medium/low")

    recommendation: str = Field(..., description="优化建议")


class ResourceAnalysisResult(BaseModel):
    """资源分析结果"""

    needs_optimization: bool = Field(..., description="是否需要优化")
    optimization_type: str = Field(..., description="优化类型: right_size/usage_pattern/mismatch")
    potential_savings: Optional[str] = Field(None, description="潜在节省比例")

    # Right Size 特有字段
    current_config: Optional[Dict[str, int]] = Field(None, description="当前配置 {cpu: x, memory: y}")
    recommended_config: Optional[Dict[str, int]] = Field(None, description="推荐配置")
    waste_ratio: Optional[float] = Field(None, description="资源浪费比例 0-1")

    # 使用模式特有字段
    usage_pattern: Optional[str] = Field(None, description="使用模式: tidal/stable/burst")
    volatility_level: Optional[str] = Field(None, description="波动性: very_stable/stable/moderate/high")
    tidal_details: Optional[Dict[str, Any]] = Field(None, description="潮汐模式详情")

    recommendation: str = Field(..., description="优化建议")


class VMOverallStatus(BaseModel):
    """VM 综合状态（多维度标签）"""

    vm_name: str
    vm_id: int
    cluster: str
    host_ip: str
    cpu_cores: int
    memory_gb: float

    # 各维度分析结果
    idle_detection: Optional[IdleDetectionResult] = None
    resource_analysis: Optional[ResourceAnalysisResult] = None

    # 综合判断
    overall_status: str = Field(..., description="综合状态")
    optimization_priority: str = Field(..., description="优化优先级")
    recommended_actions: List[str] = Field(default_factory=list, description="推荐操作列表")


class PlatformHealthResult(BaseModel):
    """平台健康评估结果"""

    overall_score: float = Field(..., ge=0, le=100, description="总体健康分数")
    grade: str = Field(..., description="健康等级: excellent/good/fair/poor/critical")

    # 各维度分数
    sub_scores: Dict[str, float] = Field(default_factory=dict)

    # 评估范围
    cluster_count: int
    host_count: int
    vm_count: int

    # 风险项和建议
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class AnalysisRequest(BaseModel):
    """分析请求"""
    task_id: int
    analysis_type: str  # idle | resource | health
    config: Optional[Dict[str, Any]] = None


class AnalysisResponse(BaseModel):
    """分析响应"""
    success: bool
    data: Optional[Any] = None
    error: Optional[Dict[str, str]] = None
```

---

## 三、后端实现架构

### 3.1 目录结构

```
backend/app/analyzers/
├── __init__.py
├── types.py                    # 类型定义
├── base.py                     # 分析器基类
├── idle/                       # 闲置检测模块
│   ├── __init__.py
│   ├── detector.py             # 闲置检测器（主入口）
│   ├── powered_off.py          # 关机型检测
│   └── activity_analyzer.py    # 活跃度分析
├── resource/                   # 资源分析模块
│   ├── __init__.py
│   ├── analyzer.py             # 资源分析器（主入口）
│   ├── right_size.py           # Right Size 分析
│   ├── usage_pattern.py        # 使用模式分析
│   └── mismatch.py             # 资源错配检测
└── health/                     # 健康评估模块
    ├── __init__.py
    └── analyzer.py             # 健康评估器
```

### 3.2 分析器基类

```python
# backend/app/analyzers/base.py

from abc import ABC, abstractmethod
from typing import Dict, List, Any
from app.models import VMMetric
import structlog

logger = structlog.get_logger()


class BaseAnalyzer(ABC):
    """分析器基类"""

    def __init__(
        self,
        task_id: int,
        days_threshold: int = 30,
        min_confidence: float = 60.0,
        **kwargs
    ):
        self.task_id = task_id
        self.days_threshold = days_threshold
        self.min_confidence = min_confidence
        self.config = kwargs

    @abstractmethod
    async def analyze(
        self,
        vm_metrics: Dict[int, List[VMMetric]],
        vm_data: Dict[int, Dict],
    ) -> List[Dict[str, Any]]:
        """执行分析

        Args:
            vm_metrics: VM 指标数据 {vm_id: [metrics]}
            vm_data: VM 基础信息 {vm_id: vm_info}

        Returns:
            分析结果列表
        """
        pass

    @abstractmethod
    def get_analysis_type(self) -> str:
        """返回分析类型 (idle | resource | health)"""
        pass

    def _group_metrics_by_type(self, metrics: List[VMMetric]) -> Dict[str, List[float]]:
        """按类型分组指标值"""
        from collections import defaultdict
        grouped = defaultdict(list)
        for m in metrics:
            grouped[m.metric_type].append(m.value)
        return dict(grouped)

    def _calculate_percentiles(self, values: List[float]) -> Dict[str, float]:
        """计算百分位数"""
        if not values:
            return {"min": 0, "p50": 0, "p95": 0, "p99": 0, "max": 0, "avg": 0}

        import statistics
        sorted_values = sorted(values)
        n = len(sorted_values)

        return {
            "min": sorted_values[0],
            "p50": sorted_values[int(n * 0.5)],
            "p95": sorted_values[int(n * 0.95)] if n >= 20 else sorted_values[-1],
            "p99": sorted_values[int(n * 0.99)] if n >= 100 else sorted_values[-1],
            "max": sorted_values[-1],
            "avg": statistics.mean(sorted_values),
        }
```

### 3.3 闲置检测器

```python
# backend/app/analyzers/idle/detector.py

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from app.analyzers.base import BaseAnalyzer
from app.analyzers.idle.powered_off import PoweredOffDetector
from app.analyzers.idle.activity_analyzer import ActivityAnalyzer


class IdleDetector(BaseAnalyzer):
    """闲置检测器 - 检测关机型和开机闲置型僵尸VM"""

    def __init__(self, task_id: int, days_threshold: int = 30, **kwargs):
        super().__init__(task_id, days_threshold, **kwargs)
        self.powered_off_detector = PoweredOffDetector(task_id, days_threshold)
        self.activity_analyzer = ActivityAnalyzer(task_id, days_threshold)

    async def analyze(
        self,
        vm_metrics: Dict[int, List[VMMetric]],
        vm_data: Dict[int, Dict],
    ) -> List[Dict[str, Any]]:
        """检测闲置VM

        流程：
        1. 检查电源状态
        2. 关机 → 使用 PoweredOffDetector
        3. 开机 → 使用 ActivityAnalyzer
        """
        findings = []

        for vm_id, vm_info in vm_data.items():
            metrics = vm_metrics.get(vm_id, [])
            power_state = vm_info.get("power_state", "unknown")

            if power_state == "poweredOff":
                # 关机型检测
                result = await self.powered_off_detector.detect(vm_id, vm_info)
                if result and result.get("confidence", 0) >= self.min_confidence:
                    findings.append(result)
            elif power_state == "poweredOn":
                # 开机闲置型检测
                result = await self.activity_analyzer.analyze(vm_id, metrics, vm_info)
                if result and result.get("is_idle") and result.get("confidence", 0) >= self.min_confidence:
                    findings.append(result)

        return findings

    def get_analysis_type(self) -> str:
        return "idle"
```

### 3.4 关机型检测器

```python
# backend/app/analyzers/idle/powered_off.py

from typing import Dict, Any, Optional
from datetime import datetime
from app.analyzers.types import IdleSubType


class PoweredOffDetector:
    """关机型僵尸检测器"""

    def __init__(self, task_id: int, days_threshold: int = 30):
        self.task_id = task_id
        self.days_threshold = days_threshold

    async def detect(self, vm_id: int, vm_info: Dict) -> Optional[Dict[str, Any]]:
        """检测关机型僵尸VM

        判断依据：
        - 关机天数 >= 90: 危急僵尸 (95% 置信度)
        - 关机天数 >= 30: 高疑似僵尸 (85% 置信度)
        - 关机天数 >= 14: 潜在僵尸 (70% 置信度)
        """
        current_time = datetime.utcnow()

        # 获取参考时间（最后关机时间或创建时间）
        last_shutdown_time = vm_info.get("last_shutdown_time")
        created_time = vm_info.get("created_at")
        reference_time = last_shutdown_time or created_time

        if not reference_time:
            return None

        # 计算关机天数
        days_since_shutdown = (current_time - reference_time).days

        # 判断是否为僵尸
        if days_since_shutdown >= 90:
            zombie_type = IdleSubType.POWERED_OFF.value
            confidence = 95
            risk_level = "critical"
            recommendation = f"VM已关机{days_since_shutdown}天，建议归档或删除"
        elif days_since_shutdown >= 30:
            zombie_type = IdleSubType.POWERED_OFF.value
            confidence = 85
            risk_level = "high"
            recommendation = f"VM已关机{days_since_shutdown}天，建议联系负责人确认后处理"
        elif days_since_shutdown >= 14:
            zombie_type = IdleSubType.POWERED_OFF.value
            confidence = 70
            risk_level = "medium"
            recommendation = f"VM已关机{days_since_shutdown}天，建议确认是否仍需要"
        else:
            return None

        # 特殊情况处理
        vm_name = vm_info.get("name", "")
        if self._is_template_vm(vm_name):
            return None

        if self._is_test_vm(vm_name):
            confidence = max(0, confidence - 20)

        return {
            "vmName": vm_name,
            "vmId": vm_id,
            "cluster": vm_info.get("cluster", ""),
            "hostIp": vm_info.get("host_ip", ""),
            "isIdle": True,
            "idleType": zombie_type,
            "confidence": confidence,
            "riskLevel": risk_level,
            "daysInactive": days_since_shutdown,
            "lastActivityTime": reference_time.isoformat(),
            "recommendation": recommendation,
        }

    def _is_template_vm(self, vm_name: str) -> bool:
        """判断是否为模板VM"""
        template_keywords = ["-template", "-tmpl", "_template", "_tmpl"]
        return any(kw in vm_name.lower() for kw in template_keywords)

    def _is_test_vm(self, vm_name: str) -> bool:
        """判断是否为测试VM"""
        test_keywords = ["test", "demo", "poc", "dev", "-t-"]
        return any(kw in vm_name.lower() for kw in test_keywords)
```

### 3.5 活跃度分析器

```python
# backend/app/analyzers/idle/activity_analyzer.py

from typing import Dict, List, Any
import statistics
from app.analyzers.base import BaseAnalyzer
from app.analyzers.types import IdleSubType


class ActivityAnalyzer(BaseAnalyzer):
    """活跃度分析器 - 检测开机但闲置的VM"""

    async def analyze(
        self,
        vm_id: int,
        metrics: List,
        vm_info: Dict,
    ) -> Dict[str, Any]:
        """分析VM活跃度"""
        if not metrics:
            return {
                "vmName": vm_info.get("name", ""),
                "vmId": vm_id,
                "isIdle": False,
                "confidence": 0,
                "recommendation": "无可用数据",
            }

        # 分组指标
        metrics_by_type = self._group_metrics_by_type(metrics)

        # 计算百分位数
        cpu_stats = self._calculate_percentiles(metrics_by_type.get("cpu", []))
        memory_stats = self._calculate_percentiles(metrics_by_type.get("memory", []))
        disk_stats = self._calculate_percentiles(
            metrics_by_type.get("disk_read", []) +
            metrics_by_type.get("disk_write", [])
        )
        network_stats = self._calculate_percentiles(
            metrics_by_type.get("net_rx", []) +
            metrics_by_type.get("net_tx", [])
        )

        # 计算活跃度分数
        activity_score = self._calculate_activity_score(
            cpu_stats["p95"],
            memory_stats["p95"],
            disk_stats["p95"],
            network_stats["p95"],
        )

        # 计算波动性
        volatility = self._calculate_volatility(metrics_by_type.get("cpu", []))

        # 判断是否闲置
        if activity_score < 15 and volatility < 0.3:
            idle_type = IdleSubType.IDLE_POWERED_ON.value
            confidence = min(100, 100 - activity_score + (15 if volatility < 0.2 else 0))
            risk_level = "critical" if confidence >= 90 else "high" if confidence >= 75 else "medium"
            is_idle = True
        elif activity_score < 30:
            idle_type = IdleSubType.LOW_ACTIVITY.value
            confidence = min(100, 100 - activity_score)
            risk_level = "medium"
            is_idle = True
        else:
            return {
                "vmName": vm_info.get("name", ""),
                "vmId": vm_id,
                "isIdle": False,
                "confidence": 0,
                "recommendation": "VM活跃度正常",
            }

        # 生成建议
        recommendation = self._generate_recommendation(
            idle_type,
            cpu_stats["p95"],
            memory_stats["p95"],
            confidence,
        )

        # 数据质量
        data_quality = self._assess_data_quality(metrics_by_type)

        return {
            "vmName": vm_info.get("name", ""),
            "vmId": vm_id,
            "cluster": vm_info.get("cluster", ""),
            "hostIp": vm_info.get("host_ip", ""),
            "cpuCores": vm_info.get("cpu_count", 0),
            "memoryGb": round(vm_info.get("memory_bytes", 0) / (1024**3), 2),
            "isIdle": is_idle,
            "idleType": idle_type,
            "confidence": confidence,
            "riskLevel": risk_level,
            "activityScore": activity_score,
            "cpuUsageP95": round(cpu_stats["p95"], 2),
            "memoryUsageP95": round(memory_stats["p95"], 2),
            "diskIoP95": round(disk_stats["p95"], 2),
            "networkP95": round(network_stats["p95"], 2),
            "dataQuality": data_quality,
            "recommendation": recommendation,
        }

    def _calculate_activity_score(
        self,
        cpu_p95: float,
        memory_p95: float,
        disk_p95: float,
        network_p95: float,
    ) -> float:
        """计算活跃度分数 (0-100，越高越活跃）"""
        score = 0

        # CPU (40分)
        if cpu_p95 >= 50:
            score += 40
        elif cpu_p95 >= 20:
            score += 20
        elif cpu_p95 >= 10:
            score += 10

        # 内存 (30分)
        if memory_p95 >= 40:
            score += 30
        elif memory_p95 >= 20:
            score += 15
        elif memory_p95 >= 10:
            score += 5

        # 磁盘 (15分)
        if disk_p95 >= 100:
            score += 15
        elif disk_p95 >= 50:
            score += 10
        elif disk_p95 >= 10:
            score += 5

        # 网络 (15分)
        if network_p95 >= 100:
            score += 15
        elif network_p95 >= 50:
            score += 10
        elif network_p95 >= 10:
            score += 5

        return score

    def _calculate_volatility(self, values: List[float]) -> float:
        """计算波动性（变异系数）"""
        if len(values) < 2:
            return 0.0
        mean_val = statistics.mean(values)
        if mean_val == 0:
            return 0.0
        return statistics.stdev(values) / mean_val

    def _assess_data_quality(self, metrics_by_type: Dict[str, List[float]]) -> str:
        """评估数据质量"""
        expected_samples = self.days_threshold * 24 * 12  # 5分钟间隔
        actual_samples = sum(len(v) for v in metrics_by_type.values())
        coverage = actual_samples / expected_samples if expected_samples > 0 else 0

        if coverage >= 0.8:
            return "high"
        elif coverage >= 0.5:
            return "medium"
        else:
            return "low"

    def _generate_recommendation(
        self,
        idle_type: str,
        cpu_p95: float,
        memory_p95: float,
        confidence: float,
    ) -> str:
        """生成优化建议"""
        if idle_type == IdleSubType.IDLE_POWERED_ON.value:
            if confidence >= 90:
                return f"VM完全闲置（P95 CPU {cpu_p95:.1f}%，内存 {memory_p95:.1f}%），建议关闭或删除"
            else:
                return f"VM资源使用率很低（P95 CPU {cpu_p95:.1f}%），建议评估后关闭或降配"
        else:
            return f"VM使用率较低（P95 CPU {cpu_p95:.1f}%），建议继续观察或联系负责人确认"
```

### 3.6 资源分析器

```python
# backend/app/analyzers/resource/analyzer.py

from typing import Dict, List, Any
from app.analyzers.base import BaseAnalyzer
from app.analyzers.resource.right_size import RightSizeAnalyzer
from app.analyzers.resource.usage_pattern import UsagePatternAnalyzer


class ResourceAnalyzer(BaseAnalyzer):
    """资源分析器 - 整合 Right Size 和使用模式分析"""

    def __init__(self, task_id: int, days_threshold: int = 30, **kwargs):
        super().__init__(task_id, days_threshold, **kwargs)
        self.right_size_analyzer = RightSizeAnalyzer(task_id, days_threshold)
        self.usage_pattern_analyzer = UsagePatternAnalyzer(task_id, days_threshold)

    async def analyze(
        self,
        vm_metrics: Dict[int, List[VMMetric]],
        vm_data: Dict[int, Dict],
    ) -> List[Dict[str, Any]]:
        """分析资源配置合理性"""
        findings = []

        for vm_id, vm_info in vm_data.items():
            metrics = vm_metrics.get(vm_id, [])
            if not metrics:
                continue

            # Right Size 分析
            right_size_result = await self.right_size_analyzer.analyze(vm_id, metrics, vm_info)
            if right_size_result:
                findings.append(right_size_result)

            # 使用模式分析
            pattern_result = await self.usage_pattern_analyzer.analyze(vm_id, metrics, vm_info)
            if pattern_result:
                findings.append(pattern_result)

        return findings

    def get_analysis_type(self) -> str:
        return "resource"
```

### 3.7 Right Size 分析器

```python
# backend/app/analyzers/resource/right_size.py

from typing import Dict, List
from app.analyzers.base import BaseAnalyzer
from app.analyzers.types import ResourceSubType


class RightSizeAnalyzer(BaseAnalyzer):
    """Right Size 分析器 - 分析资源配置是否合理"""

    def __init__(self, task_id: int, days_threshold: int = 7, **kwargs):
        super().__init__(task_id, days_threshold, **kwargs)
        self.cpu_buffer = kwargs.get("cpu_buffer_percent", 20) / 100
        self.memory_buffer = kwargs.get("memory_buffer_percent", 20) / 100
        self.waste_threshold = kwargs.get("waste_threshold", 0.3)

    async def analyze(
        self,
        vm_id: int,
        metrics: List,
        vm_info: Dict,
    ) -> Dict[str, Any]:
        """分析资源配置"""
        metrics_by_type = self._group_metrics_by_type(metrics)

        cpu_stats = self._calculate_percentiles(metrics_by_type.get("cpu", []))
        memory_stats = self._calculate_percentiles(metrics_by_type.get("memory", []))

        current_cpu = vm_info.get("cpu_count", 0)
        current_memory = vm_info.get("memory_bytes", 0) / (1024**3)

        # 计算推荐配置（P95 + 缓冲）
        recommended_cpu = max(1, int(cpu_stats["p95"] * current_cpu / 100 * (1 + self.cpu_buffer)))
        recommended_memory = max(1, int(memory_stats["p95"] * current_memory / 100 * (1 + self.memory_buffer)))

        # 计算浪费比例
        cpu_waste = 1 - (recommended_cpu / current_cpu) if current_cpu > 0 else 0
        memory_waste = 1 - (recommended_memory / current_memory) if current_memory > 0 else 0
        avg_waste = (cpu_waste + memory_waste) / 2

        needs_optimization = avg_waste > self.waste_threshold

        return {
            "vmName": vm_info.get("name", ""),
            "vmId": vm_id,
            "cluster": vm_info.get("cluster", ""),
            "needsOptimization": needs_optimization,
            "optimizationType": ResourceSubType.RIGHT_SIZE.value,
            "currentConfig": {"cpu": current_cpu, "memory": round(current_memory, 2)},
            "recommendedConfig": {"cpu": recommended_cpu, "memory": recommended_memory},
            "wasteRatio": round(avg_waste, 3),
            "potentialSavings": f"{round(avg_waste * 100)}%",
            "recommendation": self._generate_recommendation(
                needs_optimization,
                current_cpu,
                recommended_cpu,
                current_memory,
                recommended_memory,
            ),
        }

    def _generate_recommendation(
        self,
        needs_optimization: bool,
        current_cpu: int,
        recommended_cpu: int,
        current_memory: float,
        recommended_memory: int,
    ) -> str:
        """生成优化建议"""
        if not needs_optimization:
            return "资源配置合理，无需调整"

        return (
            f"当前配置 {current_cpu}核/{current_memory:.0f}GB 过大，"
            f"建议降配至 {recommended_cpu}核/{recommended_memory}GB"
        )
```

### 3.8 使用模式分析器

```python
# backend/app/analyzers/resource/usage_pattern.py

from typing import Dict, List
import statistics
from app.analyzers.base import BaseAnalyzer
from app.analyzers.types import ResourceSubType


class UsagePatternAnalyzer(BaseAnalyzer):
    """使用模式分析器 - 识别潮汐、稳定、突发等模式"""

    async def analyze(
        self,
        vm_id: int,
        metrics: List,
        vm_info: Dict,
    ) -> Dict[str, Any]:
        """分析使用模式"""
        metrics_by_type = self._group_metrics_by_type(metrics)
        cpu_values = metrics_by_type.get("cpu", [])

        if len(cpu_values) < 24:
            return {
                "vmName": vm_info.get("name", ""),
                "vmId": vm_id,
                "optimizationType": ResourceSubType.USAGE_PATTERN.value,
                "usagePattern": "unknown",
                "recommendation": "数据不足，无法分析使用模式",
            }

        # 计算波动性
        volatility = self._calculate_volatility(cpu_values)

        # 判断模式
        if volatility > 0.5:
            pattern = "tidal"
            recommendation = "VM呈现潮汐使用模式，建议配置自动调度策略在闲置期降低资源"
        elif volatility > 0.3:
            pattern = "burst"
            recommendation = "VM使用有较大波动，建议配置弹性伸缩策略"
        else:
            pattern = "stable"
            recommendation = "VM使用模式稳定，建议保持当前配置"

        return {
            "vmName": vm_info.get("name", ""),
            "vmId": vm_id,
            "cluster": vm_info.get("cluster", ""),
            "optimizationType": ResourceSubType.USAGE_PATTERN.value,
            "usagePattern": pattern,
            "volatilityLevel": "high" if volatility > 0.5 else "moderate" if volatility > 0.3 else "stable",
            "coefficientOfVariation": round(volatility, 3),
            "recommendation": recommendation,
        }

    def _calculate_volatility(self, values: List[float]) -> float:
        """计算波动性（变异系数）"""
        if len(values) < 2:
            return 0.0
        mean_val = statistics.mean(values)
        if mean_val == 0:
            return 0.0
        return statistics.stdev(values) / mean_val
```

### 3.9 AnalysisService

```python
# backend/app/services/analysis.py

import structlog
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.analyzers.idle.detector import IdleDetector
from app.analyzers.resource.analyzer import ResourceAnalyzer
from app.analyzers.health.analyzer import HealthAnalyzer
from app.analyzers.modes import AnalysisModes

logger = structlog.get_logger()


class AnalysisService:
    """分析服务"""

    ANALYZERS = {
        "idle": IdleDetector,
        "resource": ResourceAnalyzer,
        "health": HealthAnalyzer,
    }

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run_analysis(
        self,
        task_id: int,
        analysis_type: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """运行分析

        Args:
            task_id: 任务ID
            analysis_type: 分析类型 (idle | resource | health)
            config: 可选配置

        Returns:
            分析结果
        """
        logger.info(f"{analysis_type}_analysis_starting", task_id=task_id)

        # 获取配置
        if config is None:
            mode = AnalysisModes.get_mode("saving")
            config = mode.get(analysis_type, {})

        # 初始化分析器
        analyzer_class = self.ANALYZERS.get(analysis_type)
        if not analyzer_class:
            return {"success": False, "error": {"code": "INVALID_TYPE", "message": f"Unknown type: {analysis_type}"}}

        analyzer = analyzer_class(task_id, **config)

        # 健康评估特殊处理
        if analysis_type == "health":
            result = await analyzer.analyze(task_id, self.db)
        else:
            # 获取VM数据
            vm_metrics, vm_data = await self._get_vm_metrics_and_data(task_id)
            if not vm_metrics:
                return {"success": True, "data": []}

            findings = await analyzer.analyze(vm_metrics, vm_data)

            # 保存结果
            await self._save_findings(task_id, analysis_type, findings)
            result = {"success": True, "data": findings}

        logger.info(f"{analysis_type}_analysis_completed", task_id=task_id)
        return result

    async def _get_vm_metrics_and_data(
        self,
        task_id: int,
    ) -> tuple[Dict[int, List], Dict[int, Dict]]:
        """获取VM指标和数据"""
        # TODO: 实现数据获取逻辑
        return {}, {}

    async def _save_findings(
        self,
        task_id: int,
        analysis_type: str,
        findings: List[Dict],
    ) -> None:
        """保存分析结果"""
        # TODO: 实现结果保存逻辑
        pass
```

### 3.10 分析模式配置

```python
# backend/app/analyzers/modes.py

class AnalysisModes:
    """分析模式预设配置"""

    MODES = {
        "safe": {
            "description": "安全模式 - 保守阈值",
            "idle": {
                "days": 30,
                "cpu_threshold": 5.0,
                "memory_threshold": 10.0,
                "min_confidence": 80.0,
            },
            "resource": {
                "days": 14,
                "cpu_buffer_percent": 30.0,
                "memory_buffer_percent": 30.0,
                "waste_threshold": 0.5,
            },
            "health": {
                "overcommit_threshold": 120.0,
                "hotspot_threshold": 85.0,
                "balance_threshold": 0.5,
            },
        },
        "saving": {
            "description": "节省模式 - 平衡阈值（默认）",
            "idle": {
                "days": 14,
                "cpu_threshold": 10.0,
                "memory_threshold": 20.0,
                "min_confidence": 60.0,
            },
            "resource": {
                "days": 7,
                "cpu_buffer_percent": 20.0,
                "memory_buffer_percent": 20.0,
                "waste_threshold": 0.3,
            },
            "health": {
                "overcommit_threshold": 150.0,
                "hotspot_threshold": 90.0,
                "balance_threshold": 0.6,
            },
        },
        "aggressive": {
            "description": "激进模式 - 最大化发现问题",
            "idle": {
                "days": 7,
                "cpu_threshold": 15.0,
                "memory_threshold": 25.0,
                "min_confidence": 50.0,
            },
            "resource": {
                "days": 7,
                "cpu_buffer_percent": 10.0,
                "memory_buffer_percent": 10.0,
                "waste_threshold": 0.2,
            },
            "health": {
                "overcommit_threshold": 200.0,
                "hotspot_threshold": 95.0,
                "balance_threshold": 0.7,
            },
        },
        "custom": {
            "description": "自定义模式",
            "idle": {},
            "resource": {},
            "health": {},
        },
    }

    @classmethod
    def get_mode(cls, mode_name: str) -> Dict[str, Any]:
        return cls.MODES.get(mode_name, cls.MODES["custom"])

    @classmethod
    def list_modes(cls) -> Dict[str, Dict]:
        return cls.MODES
```

---

## 四、API 接口设计

### 4.1 路由定义

```python
# backend/app/routers/analysis.py

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List, Optional

from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    VMOverallStatus,
    PlatformHealthResult,
)
from app.services.analysis import AnalysisService
from app.core.database import get_db

router = APIRouter(prefix="/api/analysis", tags=["分析"])


@router.post("/{task_id}/run")
async def run_analysis(
    task_id: int,
    analysis_type: str,  # idle | resource | health
    config: Optional[Dict[str, Any]] = None,
    db = Depends(get_db),
) -> AnalysisResponse:
    """运行分析"""
    if analysis_type not in ["idle", "resource", "health"]:
        raise HTTPException(status_code=400, detail=f"Invalid analysis type: {analysis_type}")

    service = AnalysisService(db)
    result = await service.run_analysis(task_id, analysis_type, config)
    return result


@router.get("/{task_id}/results")
async def get_analysis_results(
    task_id: int,
    analysis_type: str,
    db = Depends(get_db),
) -> AnalysisResponse:
    """获取分析结果"""
    service = AnalysisService(db)
    # TODO: 实现结果获取逻辑
    return {"success": True, "data": []}


@router.get("/modes")
async def get_analysis_modes():
    """获取可用的分析模式"""
    from app.analyzers.modes import AnalysisModes
    return AnalysisModes.list_modes()
```

### 4.2 API 响应示例

```json
// POST /api/analysis/123/run?analysis_type=idle
{
  "success": true,
  "data": [
    {
      "vmName": "test-server-01",
      "vmId": 456,
      "cluster": "cluster1",
      "hostIp": "192.168.1.10",
      "isIdle": true,
      "idleType": "powered_off",
      "confidence": 95,
      "riskLevel": "critical",
      "daysInactive": 127,
      "lastActivityTime": "2024-11-02T10:30:00Z",
      "recommendation": "VM已关机127天，建议归档或删除"
    }
  ]
}

// POST /api/analysis/123/run?analysis_type=resource
{
  "success": true,
  "data": [
    {
      "vmName": "web-server-01",
      "vmId": 789,
      "cluster": "cluster1",
      "needsOptimization": true,
      "optimizationType": "right_size",
      "currentConfig": {"cpu": 8, "memory": 16},
      "recommendedConfig": {"cpu": 2, "memory": 4},
      "wasteRatio": 0.75,
      "potentialSavings": "75%",
      "recommendation": "当前配置 8核/16GB 过大，建议降配至 2核/4GB"
    },
    {
      "vmName": "app-server-02",
      "vmId": 790,
      "cluster": "cluster1",
      "optimizationType": "usage_pattern",
      "usagePattern": "tidal",
      "volatilityLevel": "high",
      "coefficientOfVariation": 0.65,
      "recommendation": "VM呈现潮汐使用模式，建议配置自动调度策略"
    }
  ]
}
```

---

## 五、前端实现

### 5.1 TypeScript 类型定义

```typescript
// frontend/src/types/analysis.ts

export enum AnalysisType {
  IDLE = 'idle',
  RESOURCE = 'resource',
  HEALTH = 'health',
}

export interface IdleDetectionResult {
  vmName: string;
  vmId: number;
  cluster: string;
  hostIp: string;
  cpuCores?: number;
  memoryGb?: number;
  isIdle: boolean;
  idleType?: 'powered_off' | 'idle_powered_on' | 'low_activity';
  confidence: number;
  riskLevel: 'critical' | 'high' | 'medium' | 'low';
  daysInactive?: number;
  lastActivityTime?: string;
  activityScore?: number;
  cpuUsageP95?: number;
  memoryUsageP95?: number;
  diskIoP95?: number;
  networkP95?: number;
  dataQuality?: 'high' | 'medium' | 'low';
  recommendation: string;
}

export interface ResourceAnalysisResult {
  vmName: string;
  vmId: number;
  cluster: string;
  needsOptimization: boolean;
  optimizationType: 'right_size' | 'usage_pattern' | 'mismatch';
  currentConfig?: { cpu: number; memory: number };
  recommendedConfig?: { cpu: number; memory: number };
  wasteRatio?: number;
  potentialSavings?: string;
  usagePattern?: 'tidal' | 'stable' | 'burst';
  volatilityLevel?: string;
  coefficientOfVariation?: number;
  recommendation: string;
}

export interface PlatformHealthResult {
  overallScore: number;
  grade: 'excellent' | 'good' | 'fair' | 'poor' | 'critical';
  subScores: Record<string, number>;
  clusterCount: number;
  hostCount: number;
  vmCount: number;
  findings: Array<{
    severity: string;
    category: string;
    description: string;
  }>;
  recommendations: string[];
}
```

### 5.2 API 客户端

```typescript
// frontend/src/api/analysis.ts

import axios from 'axios';
import type { AnalysisType, IdleDetectionResult, ResourceAnalysisResult } from '@/types/analysis';

const BASE_URL = '/api/analysis';

export const analysisApi = {
  // 运行分析
  async runAnalysis(
    taskId: number,
    analysisType: AnalysisType,
    config?: Record<string, unknown>
  ): Promise<{ success: boolean; data: unknown }> {
    const response = await axios.post(`${BASE_URL}/${taskId}/run`, null, {
      params: { analysis_type: analysisType },
      data: config,
    });
    return response.data;
  },

  // 获取分析结果
  async getAnalysisResults(
    taskId: number,
    analysisType: AnalysisType
  ): Promise<{ success: boolean; data: unknown }> {
    const response = await axios.get(`${BASE_URL}/${taskId}/results`, {
      params: { analysis_type: analysisType },
    });
    return response.data;
  },

  // 获取分析模式
  async getAnalysisModes(): Promise<Record<string, unknown>> {
    const response = await axios.get(`${BASE_URL}/modes`);
    return response.data;
  },
};
```

### 5.3 主页面组件

```vue
<!-- frontend/src/views/AnalysisView.vue -->

<template>
  <div class="analysis-view">
    <el-page-header @back="goBack" title="返回">
      <template #content>
        <span class="text-large font-600">
          资源优化分析 - Task #{{ taskId }}
        </span>
      </template>
    </el-page-header>

    <el-tabs v-model="activeTab" class="mt-4" @tab-change="handleTabChange">
      <!-- 闲置检测 -->
      <el-tab-pane label="闲置检测" name="idle">
        <IdleDetectionPanel :task-id="taskId" />
      </el-tab-pane>

      <!-- 资源分析 -->
      <el-tab-pane label="资源分析" name="resource">
        <ResourceAnalysisPanel :task-id="taskId" />
      </el-tab-pane>

      <!-- 健康评估 -->
      <el-tab-pane label="健康评估" name="health">
        <HealthAnalysisPanel :task-id="taskId" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import IdleDetectionPanel from '@/components/analysis/IdleDetectionPanel.vue';
import ResourceAnalysisPanel from '@/components/analysis/ResourceAnalysisPanel.vue';
import HealthAnalysisPanel from '@/components/analysis/HealthAnalysisPanel.vue';

const route = useRoute();
const router = useRouter();
const taskId = ref(Number(route.params.taskId));
const activeTab = ref('idle');

const goBack = () => {
  router.back();
};

const handleTabChange = (tabName: string) => {
  console.log('切换到:', tabName);
};
</script>
```

### 5.4 闲置检测面板

```vue
<!-- frontend/src/components/analysis/IdleDetectionPanel.vue -->

<template>
  <div class="idle-detection-panel">
    <el-card class="mb-4">
      <template #header>
        <div class="card-header">
          <span>闲置检测设置</span>
          <el-button type="primary" @click="runAnalysis" :loading="loading">
            开始分析
          </el-button>
        </div>
      </template>

      <el-form :model="config" label-width="150px">
        <el-form-item label="分析模式">
          <el-select v-model="mode">
            <el-option label="节省模式（推荐）" value="saving" />
            <el-option label="安全模式" value="safe" />
            <el-option label="激进模式" value="aggressive" />
          </el-select>
        </el-form-item>

        <el-form-item label="分析天数">
          <el-input-number v-model="config.days" :min="7" :max="90" />
        </el-form-item>

        <el-form-item label="最小置信度">
          <el-slider v-model="config.min_confidence" :min="0" :max="100" />
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 分析结果 -->
    <el-card v-if="results.length > 0">
      <template #header>
        <span>分析结果 ({{ results.length }} 台闲置VM)</span>
      </template>

      <el-table :data="results" stripe>
        <el-table-column prop="vmName" label="VM名称" width="200" />
        <el-table-column prop="cluster" label="集群" width="150" />
        <el-table-column prop="idleType" label="类型" width="150">
          <template #default="{ row }">
            <el-tag v-if="row.idleType === 'powered_off'" type="danger">关机型</el-tag>
            <el-tag v-else-if="row.idleType === 'idle_powered_on'" type="warning">开机闲置</el-tag>
            <el-tag v-else type="info">低效运行</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="confidence" label="置信度" width="100">
          <template #default="{ row }">
            {{ row.confidence }}%
          </template>
        </el-table-column>
        <el-table-column prop="riskLevel" label="风险等级" width="120">
          <template #default="{ row }">
            <el-tag :type="getRiskTagType(row.riskLevel)">
              {{ row.riskLevel }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="daysInactive" label="未活跃天数" width="120">
          <template #default="{ row }">
            {{ row.daysInactive || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="recommendation" label="建议" min-width="300" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetails(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { analysisApi } from '@/api/analysis';
import type { IdleDetectionResult } from '@/types/analysis';
import { ElMessage } from 'element-plus';

const props = defineProps<{
  taskId: number;
}>();

const loading = ref(false);
const mode = ref('saving');
const config = ref({
  days: 14,
  min_confidence: 60,
});
const results = ref<IdleDetectionResult[]>([]);

const runAnalysis = async () => {
  loading.value = true;
  try {
    const response = await analysisApi.runAnalysis(
      props.taskId,
      'idle',
      { ...config.value, mode: mode.value }
    );

    if (response.success) {
      results.value = response.data as IdleDetectionResult[];
      ElMessage.success(`分析完成，发现 ${results.value.length} 台闲置VM`);
    }
  } catch (error) {
    ElMessage.error('分析失败');
  } finally {
    loading.value = false;
  }
};

const getRiskTagType = (level: string) => {
  const map: Record<string, string> = {
    critical: 'danger',
    high: 'warning',
    medium: 'info',
    low: 'info',
  };
  return map[level] || '';
};

const viewDetails = (row: IdleDetectionResult) => {
  // 打开详情对话框
  console.log('查看详情:', row);
};
</script>
```

---

## 六、实施步骤

### 阶段0：数据采集准备（✅ 已完成）

⚠️ **重要**：关机型僵尸检测需要额外的VM时间字段，已完成数据采集修改

```
任务清单:
✅ 数据库表结构修改
  - ✅ 添加 vms.vm_create_time 字段 (TIMESTAMP)
  - ✅ 添加 vms.uptime_duration 字段 (INTEGER 秒)
  - ✅ 添加 vms.downtime_duration 字段 (INTEGER 秒)
  - ✅ 创建相关索引

✅ 更新 SQLAlchemy 模型
  - ✅ backend/app/models/resource.py 中的 VM 类
  - ✅ 添加三个时间字段

✅ 更新连接器基类
  - ✅ backend/app/connectors/base.py 中的 VMInfo
  - ✅ 添加三个时间字段

✅ 更新 vCenter 连接器
  - ✅ backend/app/connectors/vcenter.py 的 get_vms() 方法
  - ✅ 采集 vm.config.createDate
  - ✅ 采集 vm.summary.quickStats.uptimeSeconds
  - ✅ 计算 downtime_duration

✅ 更新 UIS 连接器
  - ✅ backend/app/connectors/uis.py
  - ✅ 采集 createTime, uptime, lastOffTime

✅ 更新数据采集服务
  - ✅ backend/app/services/collection.py
  - ✅ 确保新字段正确保存

✅ 编写单元测试
  - ✅ 测试字段采集
  - ✅ 测试数据保存

验收标准:
✅ 数据库表结构更新成功
✅ vCenter 连接器能采集时间字段
✅ UIS 连接器能采集时间字段
✅ 时间字段正确保存到数据库
✅ 所有测试通过
```

**数据采集实现（已完成）**：

```python
# vCenter 连接器实现
async def get_vms(self) -> List[VMInfo]:
    """Get all virtual machines."""

    vms = []
    for vm in vm_view.view:
        # ✅ 采集时间信息
        create_time = vm.config.createDate if vm.config else None
        uptime_seconds = None
        downtime_seconds = None

        if vm.summary and vm.summary.quickStats:
            uptime_seconds = vm.summary.quickStats.uptimeSeconds

        # 计算关机时长
        if power_state_str and power_state_str.lower() in ["poweredoff", "powered off"]:
            boot_time = vm.runtime.bootTime if vm.runtime else None
            if boot_time is None:
                downtime_seconds = 2592000  # 30天默认值
            else:
                now = datetime.now(timezone.utc)
                if boot_time.tzinfo is None:
                    boot_time = boot_time.replace(tzinfo=timezone.utc)
                duration = now - boot_time
                downtime_seconds = int(duration.total_seconds())

        vms.append(VMInfo(
            # 现有字段...
            name=vm.name,
            uuid=vm.config.uuid,
            cpu_count=vm.config.hardware.numCPU,
            # ...

            # ✅ 新增字段
            vm_create_time=create_time,
            uptime_duration=uptime_seconds,
            downtime_duration=downtime_seconds,
        ))

    return vms
```

**相关文档**：
- 详细的数据依赖分析：`docs/DATA_DEPENDENCIES_ANALYSIS.md`

---

### 阶段1：基础架构（2天）

```
任务清单:
□ 创建类型定义文件
  - backend/app/analyzers/types.py
  - frontend/src/types/analysis.ts

□ 创建数据库表
  - 编写 SQLAlchemy 模型
  - 创建表结构

□ 创建分析器基类
  - backend/app/analyzers/base.py

□ 编写单元测试
  - 测试类型定义
  - 测试基类功能

验收标准:
✓ 类型定义完整
✓ 数据库表创建成功
✓ 基类接口清晰
```

### 阶段2：闲置检测模块（3天）

```
任务清单:
□ 创建 idle/ 目录结构

□ 实现 PoweredOffDetector
  - 关机型检测逻辑
  - 天数计算
  - 特殊VM处理（模板、测试）

□ 实现 ActivityAnalyzer
  - 活跃度评分
  - 百分位数计算
  - 波动性分析

□ 实现 IdleDetector
  - 整合两个子检测器
  - 统一输出格式

□ 编写单元测试
  - 测试关机型检测
  - 测试活跃度分析
  - 测试边界情况

验收标准:
✓ 所有单元测试通过
✓ 检测逻辑准确
✓ 输出格式符合规范
```

### 阶段3：资源分析模块（3天）

```
任务清单:
□ 创建 resource/ 目录结构

□ 实现 RightSizeAnalyzer
  - 推荐配置计算
  - 浪费比例计算
  - 优化建议生成

□ 实现 UsagePatternAnalyzer
  - 波动性计算
  - 模式识别（潮汐/稳定/突发）

□ 实现 ResourceAnalyzer
  - 整合两个子分析器
  - 统一输出格式

□ 编写单元测试
  - 测试 Right Size
  - 测试模式识别

验收标准:
✓ 所有单元测试通过
✓ 配置推荐合理
✓ 模式识别准确
```

### 阶段4：健康评估模块（2天）

```
任务清单:
□ 创建 health/ 目录结构

□ 实现 HealthAnalyzer
  - 超配分析
  - 负载均衡分析
  - VM密度分析（基于已有数据）
  - 综合评分

□ 编写单元测试

验收标准:
✓ 单元测试通过
✓ 评分逻辑正确
```

### 阶段5：服务层和API（2天）

```
任务清单:
□ 实现 AnalysisService
  - 分析调度逻辑
  - 数据获取
  - 结果保存

□ 实现 API 路由
  - /api/analysis/{task_id}/run
  - /api/analysis/{task_id}/results
  - /api/analysis/modes

□ 集成测试
  - 端到端测试
  - API 响应验证

验收标准:
✓ API 正常工作
✓ 集成测试通过
```

### 阶段6：前端实现（3天）

```
任务清单:
□ 实现 TypeScript 类型
□ 实现 API 客户端

□ 实现分析页面
  - AnalysisView.vue
  - IdleDetectionPanel.vue
  - ResourceAnalysisPanel.vue
  - HealthAnalysisPanel.vue

□ 实现 VM 状态展示组件
  - VMStatusTags.vue
  - VMCard.vue

□ 编写前端测试

验收标准:
✓ UI 功能完整
✓ 数据展示正确
✓ 无控制台错误
```

### 阶段7：联调测试（2天）

```
任务清单:
□ 完整流程测试
  - 创建任务
  - 数据采集
  - 运行分析
  - 查看结果

□ 性能测试
  - 大数据量测试
  - 并发测试

□ Bug 修复

验收标准:
✓ 所有功能正常
✓ 性能满足要求
```

### 阶段8：文档和发布（1天）

```
任务清单:
□ 更新 API 文档
□ 更新用户手册
□ 代码审查
□ 发布

验收标准:
✓ 文档完整准确
✓ 代码审查通过
```

---

## 七、总时间估算

| 阶段 | 内容 | 预计时长 |
|------|------|----------|
| 0 | 数据采集准备⚠️ | 1天（必须优先）|
| 1 | 基础架构 | 2天 |
| 2 | 闲置检测模块 | 3天 |
| 3 | 资源分析模块 | 3天 |
| 4 | 健康评估模块 | 2天 |
| 5 | 服务层和API | 2天 |
| 6 | 前端实现 | 3天 |
| 7 | 联调测试 | 2天 |
| 8 | 文档和发布 | 1天 |
| **总计** | | **19天 (约4周)** |

⚠️ **注意**：阶段0（数据采集准备）必须在阶段1之前完成，否则关机型僵尸检查功能无法实现。

---

## 八、成功标准

### 技术标准

- ✅ 所有单元测试通过率 ≥ 95%
- ✅ API 响应时间 < 2秒
- ✅ 前端无 TypeScript 错误
- ✅ 代码符合规范

### 功能标准

- ✅ 三大分析类型功能完整
- ✅ 检测结果准确率高
- ✅ 优化建议具体可行
- ✅ 用户体验良好

---

## 附录

### A. 数据依赖说明

⚠️ **重要**：本重构计划依赖于 VM 时间字段的采集，详细信息请参考：

**📄 数据依赖分析文档**：`docs/DATA_DEPENDENCIES_ANALYSIS.md`

该文档包含：
- 当前 VM 数据模型的完整分析
- 各分析功能的数据需求
- 数据缺失字段汇总（含优先级）
- 数据采集实施建议
- vCenter API 参考

**关键数据依赖（✅ 已完成）**：

| 数据字段 | 用途 | 优先级 | 当前状态 |
|----------|------|--------|----------|
| `vm_create_time` | VM 年龄计算、关机型检测（备用）| 🔴 P0 | ✅ 已完成 |
| `uptime_duration` | 开机时长显示 | 🔴 P0 | ✅ 已完成 |
| `downtime_duration` | 关机型僵尸检测 | 🔴 P0 | ✅ 已完成 |
| 性能指标时间戳 | 时间序列分析 | 🟡 P1 | ✅ 已有 |

**实施顺序**：
1. ✅ **已完成**：VM 时间字段采集（阶段0）
2. ⏸️ 待开始：关机型僵尸检测功能实现

**⚠️ 注意**：VM密度分析基于已有数据（主机VM数量、CPU核心数），无需额外数据采集。

### B. 术语对照

| 中文 | 英文 | 代码值 |
|------|------|--------|
| 闲置检测 | Idle Detection | idle |
| 资源分析 | Resource Analysis | resource |
| 健康评估 | Health Assessment | health |
| 关机型僵尸 | Powered Off Zombie | powered_off |
| 开机闲置型 | Idle Powered On | idle_powered_on |
| 低效运行型 | Low Activity | low_activity |
| Right Size | Right Size | right_size |
| 使用模式分析 | Usage Pattern | usage_pattern |
| 资源错配 | Resource Mismatch | mismatch |
| 潮汐模式 | Tidal Pattern | tidal |
| 稳定模式 | Stable Pattern | stable |
| 突发模式 | Burst Pattern | burst |

---

**文档结束**
