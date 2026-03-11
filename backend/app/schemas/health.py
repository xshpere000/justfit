"""Health Assessment Schemas."""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional


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


class OvercommitAnalysis(BaseSchema):
    """Resource overcommit analysis result."""

    cluster_name: str = Field(..., alias="clusterName")
    physical_cpu_cores: float = Field(..., alias="physicalCpuCores")
    physical_memory_gb: float = Field(..., alias="physicalMemoryGb")
    allocated_cpu: int = Field(..., alias="allocatedCpu")
    allocated_memory_gb: float = Field(..., alias="allocatedMemoryGb")
    cpu_overcommit: float = Field(..., alias="cpuOvercommit")
    memory_overcommit: float = Field(..., alias="memoryOvercommit")
    cpu_risk: str = Field(..., alias="cpuRisk")
    memory_risk: str = Field(..., alias="memoryRisk")


class BalanceAnalysis(BaseSchema):
    """Load balance analysis result."""

    cluster_name: str = Field(..., alias="clusterName")
    host_count: int = Field(..., alias="hostCount")
    vm_counts: List[int] = Field(..., alias="vmCounts")
    mean_vm_count: float = Field(..., alias="meanVmCount")
    std_dev: float = Field(..., alias="stdDev")
    coefficient_of_variation: float = Field(..., alias="coefficientOfVariation")
    balance_level: str = Field(..., alias="balanceLevel")
    balance_score: float = Field(..., alias="balanceScore")


class HotspotAnalysis(BaseSchema):
    """Hotspot risk analysis result."""

    host_name: str = Field(..., alias="hostName")
    ip_address: str = Field(..., alias="ipAddress")
    vm_count: int = Field(..., alias="vmCount")
    cpu_cores: int = Field(..., alias="cpuCores")
    memory_gb: float = Field(..., alias="memoryGb")
    vm_density: float = Field(..., alias="vmDensity")
    risk_level: str = Field(..., alias="riskLevel")
    recommendation: str


class HealthFinding(BaseSchema):
    """Health finding."""

    severity: str
    category: str
    cluster: Optional[str] = None
    host: Optional[str] = None
    description: str
    details: Dict[str, Any] = Field(default_factory=dict)


class PlatformHealthResult(BaseSchema):
    """Platform health assessment result."""

    overall_score: float = Field(..., alias="overallScore", ge=0, le=100)
    grade: str = Field(..., pattern="^(excellent|good|fair|poor|critical|no_data)$")

    sub_scores: Dict[str, float] = Field(default_factory=dict, alias="subScores")

    cluster_count: int = Field(..., alias="clusterCount")
    host_count: int = Field(..., alias="hostCount")
    vm_count: int = Field(..., alias="vmCount")

    # Detailed analysis results
    overcommit_results: List[OvercommitAnalysis] = Field(
        default_factory=list, alias="overcommitResults"
    )
    balance_results: List[BalanceAnalysis] = Field(
        default_factory=list, alias="balanceResults"
    )
    hotspot_hosts: List[HotspotAnalysis] = Field(
        default_factory=list, alias="hotspotHosts"
    )

    # Aggregated scores
    overcommit_score: float = Field(..., alias="overcommitScore")
    balance_score: float = Field(..., alias="balanceScore")
    hotspot_score: float = Field(..., alias="hotspotScore")

    # Overall metrics
    avg_vm_density: float = Field(..., alias="avgVmDensity")

    findings: List[HealthFinding] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class HealthAnalysisRequest(BaseSchema):
    """Health analysis request."""

    overcommit_threshold: float = Field(default=150.0, alias="overcommitThreshold")
    hotspot_threshold: float = Field(default=10.0, alias="hotspotThreshold")
    balance_threshold: float = Field(default=0.6, alias="balanceThreshold")


class HealthAnalysisResponse(BaseSchema):
    """Health analysis response."""

    success: bool
    data: Optional[PlatformHealthResult] = None
    message: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
