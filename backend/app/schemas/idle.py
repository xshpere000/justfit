"""Idle Detection Schemas."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class BaseSchema(BaseModel):
    """Base schema with camelCase alias."""

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


class IdleDetectionResult(BaseSchema):
    """Idle detection result."""

    # 通用字段
    vm_name: str = Field(..., alias="vmName")
    vm_id: int = Field(..., alias="vmId")
    cluster: str
    host_ip: str = Field(..., alias="hostIp")

    # 闲置判断
    is_idle: bool = Field(..., alias="isIdle")
    idle_type: Optional[str] = Field(None, alias="idleType")  # 'powered_off' | 'idle_powered_on' | 'low_activity'
    confidence: float = Field(..., ge=0, le=100)
    risk_level: str = Field(..., pattern="^(critical|high|medium|low)$", alias="riskLevel")

    # 关机型特有字段
    days_inactive: Optional[int] = Field(None, alias="daysInactive")
    last_activity_time: Optional[datetime] = Field(None, alias="lastActivityTime")
    downtime_duration: Optional[int] = Field(
        None, description="关机时长（秒）", alias="downtimeDuration"
    )

    # 开机型特有字段
    cpu_cores: Optional[int] = Field(None, alias="cpuCores")
    memory_gb: Optional[float] = Field(None, alias="memoryGb")
    uptime_duration: Optional[int] = Field(
        None, description="开机时长（秒）", alias="uptimeDuration"
    )
    activity_score: Optional[int] = Field(None, ge=0, le=100, alias="activityScore")
    cpu_usage_p95: Optional[float] = Field(None, ge=0, le=100, alias="cpuUsageP95")
    memory_usage_p95: Optional[float] = Field(None, ge=0, le=100, alias="memoryUsageP95")
    disk_io_p95: Optional[float] = Field(None, ge=0, alias="diskIoP95")
    network_p95: Optional[float] = Field(None, ge=0, alias="networkP95")
    data_quality: Optional[str] = Field(
        None, pattern="^(high|medium|low)$", alias="dataQuality"
    )

    recommendation: str
    details: Dict[str, Any] = Field(default_factory=dict)


class IdleAnalysisRequest(BaseSchema):
    """Idle analysis request."""

    days: int = Field(default=14, ge=7, le=90, description="分析天数")
    cpu_threshold: float = Field(default=10.0, ge=0, le=100, alias="cpuThreshold")
    memory_threshold: float = Field(default=20.0, ge=0, le=100, alias="memoryThreshold")
    min_confidence: float = Field(default=60.0, ge=0, le=100, alias="minConfidence")


class IdleAnalysisResponse(BaseSchema):
    """Idle analysis results response."""

    success: bool
    data: List[IdleDetectionResult] = Field(default_factory=list)
    message: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
