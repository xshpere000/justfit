"""Analysis Schemas."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any


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


# ============ Zombie VM Analysis Schemas ============

class ZombieVMResult(BaseSchema):
    """Zombie VM analysis result."""

    vm_name: str = Field(..., alias="vmName")
    cluster: str
    host_ip: str = Field(..., alias="hostIp")
    cpu_cores: int = Field(..., alias="cpuCores")
    memory_gb: float = Field(..., alias="memoryGb")
    cpu_usage: float = Field(..., alias="cpuUsage")
    memory_usage: float = Field(..., alias="memoryUsage")
    disk_io_usage: float = Field(..., alias="diskIoUsage")
    network_usage: float = Field(..., alias="networkUsage")
    confidence: float
    severity: str
    recommendation: str
    details: Dict[str, Any] = Field(default_factory=dict)


# ============ Right Size Analysis Schemas ============

class RightSizeResult(BaseSchema):
    """Right size analysis result."""

    vm_name: str = Field(..., alias="vmName")
    cluster: str
    host_ip: str = Field(..., alias="hostIp")
    current_cpu: int = Field(..., alias="currentCpu")
    suggested_cpu: int = Field(..., alias="suggestedCpu")
    current_memory: float = Field(..., alias="currentMemory")
    suggested_memory: float = Field(..., alias="suggestedMemory")
    cpu_p95: float = Field(..., alias="cpuP95")
    cpu_max: float = Field(..., alias="cpuMax")
    cpu_avg: float = Field(..., alias="cpuAvg")
    memory_p95: float = Field(..., alias="memoryP95")
    memory_max: float = Field(..., alias="memoryMax")
    memory_avg: float = Field(..., alias="memoryAvg")
    adjustment_type: str = Field(..., alias="adjustmentType")
    risk_level: str = Field(..., alias="riskLevel")
    confidence: float
    recommendation: str
    details: Dict[str, Any] = Field(default_factory=dict)


# ============ Tidal Pattern Analysis Schemas ============

class TidalResult(BaseSchema):
    """Tidal pattern analysis result."""

    vm_name: str = Field(..., alias="vmName")
    cluster: str
    cpu_cores: int = Field(..., alias="cpuCores")
    memory_gb: float = Field(..., alias="memoryGb")
    pattern_type: str = Field(..., alias="patternType")
    stability_score: float = Field(..., alias="stabilityScore")
    peak_hours: List[int] = Field(..., alias="peakHours")
    peak_days: List[int] = Field(..., alias="peakDays")
    recommendation: str
    estimated_saving: str = Field(..., alias="estimatedSaving")
    details: Dict[str, Any] = Field(default_factory=dict)


# ============ Health Score Analysis Schemas ============

class HealthFinding(BaseSchema):
    """Health finding."""

    type: str
    severity: str
    title: str
    description: str


class HealthScoreResult(BaseSchema):
    """Health score analysis result."""

    overall_score: float = Field(..., alias="overallScore")
    grade: str
    balance_score: float = Field(..., alias="balanceScore")
    overcommit_score: float = Field(..., alias="overcommitScore")
    hotspot_score: float = Field(..., alias="hotspotScore")
    cluster_count: int = Field(..., alias="clusterCount")
    host_count: int = Field(..., alias="hostCount")
    vm_count: int = Field(..., alias="vmCount")
    findings: List[HealthFinding] = Field(default_factory=list)


# ============ Analysis Mode Schemas ============

class ZombieConfig(BaseSchema):
    """Zombie analysis configuration."""

    days: int = Field(default=14)
    cpu_threshold: float = Field(default=10.0, alias="cpuThreshold")
    memory_threshold: float = Field(default=20.0, alias="memoryThreshold")
    disk_io_threshold: float = Field(default=5.0, alias="diskIoThreshold")
    network_threshold: float = Field(default=5.0, alias="networkThreshold")
    min_confidence: float = Field(default=60.0, alias="minConfidence")


class RightSizeConfig(BaseSchema):
    """Right size analysis configuration."""

    days: int = Field(default=7)
    cpu_buffer_percent: float = Field(default=20.0, alias="cpuBufferPercent")
    memory_buffer_percent: float = Field(default=20.0, alias="memoryBufferPercent")
    high_usage_threshold: float = Field(default=90.0, alias="highUsageThreshold")
    low_usage_threshold: float = Field(default=30.0, alias="lowUsageThreshold")
    min_confidence: float = Field(default=60.0, alias="minConfidence")


class TidalConfig(BaseSchema):
    """Tidal analysis configuration."""

    days: int = Field(default=14)
    peak_threshold: float = Field(default=75.0, alias="peakThreshold")
    valley_threshold: float = Field(default=35.0, alias="valleyThreshold")
    min_stability: float = Field(default=50.0, alias="minStability")


class HealthConfig(BaseSchema):
    """Health analysis configuration."""

    overcommit_threshold: float = Field(default=150.0, alias="overcommitThreshold")
    hotspot_threshold: float = Field(default=90.0, alias="hotspotThreshold")
    balance_threshold: float = Field(default=0.6, alias="balanceThreshold")


class AnalysisModeConfig(BaseSchema):
    """Analysis mode configuration."""

    description: str
    zombie: ZombieConfig = Field(default_factory=ZombieConfig)
    rightsize: RightSizeConfig = Field(default_factory=RightSizeConfig)
    tidal: TidalConfig = Field(default_factory=TidalConfig)
    health: HealthConfig = Field(default_factory=HealthConfig)


# ============ Analysis Request/Response Schemas ============

class AnalysisRequest(BaseSchema):
    """Analysis execution request."""

    mode: Optional[str] = Field(default="saving", pattern="^(safe|saving|aggressive|custom)$")
    config: Optional[Dict[str, Any]] = None
    task_id: Optional[int] = Field(default=None, alias="taskId")  # 用于记录日志


class AnalysisResponse(BaseSchema):
    """Analysis execution response."""

    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    error: Optional[Dict[str, Any]] = None


class ZombieAnalysisResponse(BaseSchema):
    """Zombie analysis results response."""

    success: bool
    data: List[ZombieVMResult] = Field(default_factory=list)
    message: Optional[str] = None
    error: Optional[Dict[str, Any]] = None


class RightSizeAnalysisResponse(BaseSchema):
    """Right size analysis results response."""

    success: bool
    data: List[RightSizeResult] = Field(default_factory=list)
    message: Optional[str] = None
    error: Optional[Dict[str, Any]] = None


class TidalAnalysisResponse(BaseSchema):
    """Tidal analysis results response."""

    success: bool
    data: List[TidalResult] = Field(default_factory=list)
    message: Optional[str] = None
    error: Optional[Dict[str, Any]] = None


class HealthAnalysisResponse(BaseSchema):
    """Health analysis results response."""

    success: bool
    data: Optional[HealthScoreResult] = None
    message: Optional[str] = None
    error: Optional[Dict[str, Any]] = None


# ============ Mode Management Schemas ============

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


class CustomModeUpdateRequest(BaseSchema):
    """Custom mode update request."""

    analysis_type: str = Field(..., pattern="^(zombie|rightsize|tidal|health)$")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)  # 使 config 可选，默认为空字典
    task_id: Optional[int] = Field(default=None, alias="taskId")  # 用于记录日志
