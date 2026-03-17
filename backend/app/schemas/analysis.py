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
    recommended_cpu: int = Field(..., alias="recommendedCpu")
    current_memory_gb: float = Field(..., alias="currentMemoryGb")
    recommended_memory_gb: float = Field(..., alias="recommendedMemoryGb")
    cpu_p95: float = Field(..., alias="cpuP95")
    cpu_avg: float = Field(..., alias="cpuAvg")
    memory_p95: float = Field(..., alias="memoryP95")
    memory_avg: float = Field(..., alias="memoryAvg")
    adjustment_type: str = Field(..., alias="adjustmentType")
    waste_ratio: float = Field(..., alias="wasteRatio")
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


# ============ Usage Pattern Analysis Schemas ============

class TidalDetails(BaseSchema):
    """Tidal pattern details."""

    pattern_type: str = Field(..., alias="patternType")
    day_avg: float = Field(..., alias="dayAvg")
    night_avg: float = Field(..., alias="nightAvg")
    hourly_avg: Dict[str, float] = Field(default_factory=dict, alias="hourlyAvg")


class UsagePatternResult(BaseSchema):
    """Usage pattern analysis result."""

    vm_name: str = Field(..., alias="vmName")
    datacenter: str
    cluster: str
    host_ip: str = Field(..., alias="hostIp")
    optimization_type: str = Field(default="usage_pattern", alias="optimizationType")
    usage_pattern: str = Field(..., alias="usagePattern")
    volatility_level: str = Field(..., alias="volatilityLevel")
    coefficient_of_variation: float = Field(..., alias="coefficientOfVariation")
    peak_valley_ratio: float = Field(..., alias="peakValleyRatio")
    tidal_details: Optional[TidalDetails] = Field(default=None, alias="tidalDetails")
    recommendation: str
    details: Dict[str, Any] = Field(default_factory=dict)


# ============ Resource Mismatch Analysis Schemas ============

class MismatchResult(BaseSchema):
    """Resource mismatch analysis result."""

    vm_name: str = Field(..., alias="vmName")
    datacenter: str
    cluster: str
    host_ip: str = Field(..., alias="hostIp")
    has_mismatch: bool = Field(..., alias="hasMismatch")
    mismatch_type: Optional[str] = Field(default=None, alias="mismatchType")
    cpu_utilization: float = Field(..., alias="cpuUtilization")
    memory_utilization: float = Field(..., alias="memoryUtilization")
    current_cpu: int = Field(..., alias="currentCpu")
    current_memory: float = Field(..., alias="currentMemory")
    recommendation: str
    details: Dict[str, Any] = Field(default_factory=dict)


# ============ Resource Analysis Combined Schemas ============

class ResourceAnalysisSummary(BaseSchema):
    """Resource analysis summary."""

    right_size_count: int = Field(..., alias="rightSizeCount")
    usage_pattern_count: int = Field(..., alias="usagePatternCount")
    mismatch_count: int = Field(..., alias="mismatchCount")
    total_vms_analyzed: int = Field(..., alias="totalVmsAnalyzed")


class ResourceAnalysisResult(BaseSchema):
    """Combined resource analysis result."""

    right_size: List[RightSizeResult] = Field(default_factory=list, alias="rightSize")
    usage_pattern: List[UsagePatternResult] = Field(default_factory=list, alias="usagePattern")
    mismatch: List[MismatchResult] = Field(default_factory=list)
    summary: ResourceAnalysisSummary


# ============ Analysis Mode Schemas ============

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


class MismatchConfig(BaseSchema):
    """Resource mismatch analysis configuration (within resource)."""

    cpu_low_threshold: float = Field(default=30.0, alias="cpuLowThreshold")
    cpu_high_threshold: float = Field(default=70.0, alias="cpuHighThreshold")
    memory_low_threshold: float = Field(default=30.0, alias="memoryLowThreshold")
    memory_high_threshold: float = Field(default=70.0, alias="memoryHighThreshold")


class ResourceConfig(BaseSchema):
    """Resource analysis configuration (contains rightsize, usage_pattern, mismatch)."""

    rightsize: RightSizeModeConfig = Field(default_factory=RightSizeModeConfig)
    usage_pattern: UsagePatternConfig = Field(default_factory=UsagePatternConfig, alias="usagePattern")
    mismatch: MismatchConfig = Field(default_factory=MismatchConfig)


class HealthConfig(BaseSchema):
    """Health analysis configuration."""

    overcommit_threshold: float = Field(default=1.5, alias="overcommitThreshold")
    hotspot_threshold: float = Field(default=7.0, alias="hotspotThreshold")
    balance_threshold: float = Field(default=0.6, alias="balanceThreshold")


class AnalysisModeConfig(BaseSchema):
    """Analysis mode configuration.

    Matches the structure defined in app/analyzers/modes.py:
    - idle: Idle detection config
    - resource: Resource analysis config (contains rightsize, usage_pattern, mismatch)
    - health: Health score config
    """

    description: str
    idle: IdleConfig = Field(default_factory=IdleConfig)
    resource: ResourceConfig = Field(default_factory=ResourceConfig)
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


class UsagePatternAnalysisResponse(BaseSchema):
    """Usage pattern analysis results response."""

    success: bool
    data: List[UsagePatternResult] = Field(default_factory=list)
    message: Optional[str] = None
    error: Optional[Dict[str, Any]] = None


class MismatchAnalysisResponse(BaseSchema):
    """Resource mismatch analysis results response."""

    success: bool
    data: List[MismatchResult] = Field(default_factory=list)
    message: Optional[str] = None
    error: Optional[Dict[str, Any]] = None


class ResourceAnalysisResponse(BaseSchema):
    """Combined resource analysis results response."""

    success: bool
    data: Optional[ResourceAnalysisResult] = None
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

    analysis_type: str = Field(..., pattern="^(idle|resource|health)$")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    task_id: Optional[int] = Field(default=None, alias="taskId")
