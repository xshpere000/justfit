"""Analysis Schemas - 仅保留实际被路由层引用的类型定义."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any


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


# ============ Analysis Mode Config Schemas ============

class IdleConfig(BaseSchema):
    """Idle detection analysis configuration."""

    days: int = Field(default=14)
    cpu_threshold: float = Field(default=10.0, alias="cpuThreshold")
    memory_threshold: float = Field(default=20.0, alias="memoryThreshold")
    min_confidence: float = Field(default=60.0, alias="minConfidence")


class RightSizeModeConfig(BaseSchema):
    """Right size analysis configuration (within resource)."""

    days: int = Field(default=7)
    cpu_buffer_percent: float = Field(default=20.0, alias="cpuBufferPercent")
    memory_buffer_percent: float = Field(default=20.0, alias="memoryBufferPercent")
    high_usage_threshold: float = Field(default=90.0, alias="highUsageThreshold")
    low_usage_threshold: float = Field(default=30.0, alias="lowUsageThreshold")
    min_confidence: float = Field(default=60.0, alias="minConfidence")


class UsagePatternConfig(BaseSchema):
    """Usage pattern analysis configuration (within resource)."""

    cv_threshold: float = Field(default=0.4, alias="cvThreshold")
    peak_valley_ratio: float = Field(default=2.5, alias="peakValleyRatio")


class ResourceConfig(BaseSchema):
    """Resource analysis configuration."""

    rightsize: RightSizeModeConfig = Field(default_factory=RightSizeModeConfig)
    usage_pattern: UsagePatternConfig = Field(default_factory=UsagePatternConfig, alias="usagePattern")


class HealthConfig(BaseSchema):
    """Health analysis configuration."""

    overcommit_threshold: float = Field(default=1.5, alias="overcommitThreshold")
    hotspot_threshold: float = Field(default=7.0, alias="hotspotThreshold")
    balance_threshold: float = Field(default=0.6, alias="balanceThreshold")


class AnalysisModeConfig(BaseSchema):
    """Analysis mode configuration."""

    description: str
    idle: IdleConfig = Field(default_factory=IdleConfig)
    resource: ResourceConfig = Field(default_factory=ResourceConfig)
    health: HealthConfig = Field(default_factory=HealthConfig)


# ============ Request / Response Schemas ============

class AnalysisRequest(BaseSchema):
    """Analysis execution request."""

    mode: Optional[str] = Field(default="saving", pattern="^(safe|saving|aggressive|custom)$")
    config: Optional[Dict[str, Any]] = None
    task_id: Optional[int] = Field(default=None, alias="taskId")


class ModesResponse(BaseSchema):
    """All analysis modes response."""

    success: bool
    data: Dict[str, AnalysisModeConfig]
    message: Optional[str] = None


class ModeResponse(BaseSchema):
    """Single mode response."""

    success: bool
    data: AnalysisModeConfig
    message: Optional[str] = None
