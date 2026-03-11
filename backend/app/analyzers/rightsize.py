"""Right Size Analyzer - VM resource sizing recommendations."""

import structlog
from datetime import datetime
from typing import List, Dict, Any

from app.models import VMMetric


logger = structlog.get_logger()


# Standard CPU configurations
CPU_STANDARDS = [1, 2, 4, 8, 12, 16, 24, 32, 48, 64]

# Standard memory configurations (in GB)
MEMORY_STANDARDS = [0.5, 1, 2, 4, 8, 16, 32, 64, 128, 256]


class RightSizeAnalyzer:
    """Analyzer for VM right-sizing recommendations."""

    def __init__(
        self,
        days_threshold: int = 14,
        cpu_buffer_percent: float = 20.0,
        memory_buffer_percent: float = 20.0,
        high_usage_threshold: float = 85.0,
        low_usage_threshold: float = 30.0,
        min_confidence: float = 60.0,
    ) -> None:
        """Initialize right-size analyzer.

        Args:
            days_threshold: Days to analyze (default 14)
            cpu_buffer_percent: CPU buffer percentage (default 20%)
            memory_buffer_percent: Memory buffer percentage (default 20%)
            high_usage_threshold: High usage threshold % (default 85%)
            low_usage_threshold: Low usage threshold % (default 30%)
            min_confidence: Minimum confidence (default 60)
        """
        self.days_threshold = days_threshold
        self.cpu_buffer = 1.0 + cpu_buffer_percent / 100
        self.memory_buffer = 1.0 + memory_buffer_percent / 100
        self.high_threshold = high_usage_threshold
        self.low_threshold = low_usage_threshold
        self.min_confidence = min_confidence

    async def analyze(
        self,
        task_id: int,
        vm_metrics: Dict[int, List[VMMetric]],
        vm_data: Dict[int, Dict],
    ) -> List[Dict]:
        """Analyze VMs for right-sizing recommendations.

        Args:
            task_id: Task ID
            vm_metrics: Dict mapping vm_id to list of metrics
            vm_data: Dict mapping vm_id to VM info

        Returns:
            List of right-size findings
        """
        findings = []

        for vm_id, metrics in vm_metrics.items():
            if not metrics:
                continue

            vm_info = vm_data.get(vm_id, {})
            result = await self._analyze_vm(vm_id, metrics, vm_info)

            if result["confidence"] >= self.min_confidence:
                findings.append(result)

        logger.info(
            "rightsize_analysis_completed",
            task_id=task_id,
            total_vms=len(vm_metrics),
            findings_count=len(findings),
        )

        return findings

    def _convert_cpu_to_percentage(
        self,
        cpu_metrics: List[VMMetric],
        cpu_count: int,
        host_cpu_mhz: int,
    ) -> List[float]:
        """将 CPU 指标从存储值转换为百分比。

        存储：percentage / 100 * cpu_count * host_cpu_mhz
        还原：stored_value / cpu_count / host_cpu_mhz * 100
        """
        if not cpu_metrics:
            return []

        effective_host_mhz = host_cpu_mhz if host_cpu_mhz > 0 else 2600
        effective_cpu_count = cpu_count if cpu_count > 0 else 1

        if effective_host_mhz == 0:
            return [m.value for m in cpu_metrics]

        result = []
        for metric in cpu_metrics:
            percentage = (metric.value / effective_cpu_count / effective_host_mhz) * 100
            result.append(round(percentage, 2))

        return result

    def _convert_memory_to_percentage(
        self,
        memory_metrics: List[VMMetric],
        memory_bytes: int,
    ) -> List[float]:
        """将内存指标从存储值（bytes）转换为百分比。

        数据库存储：实际使用的内存字节数 (bytes)
        转换公式：(metric.value / memory_bytes) * 100
        """
        if not memory_metrics or memory_bytes == 0:
            return [m.value for m in memory_metrics] if memory_metrics else []

        result = []
        for metric in memory_metrics:
            percentage = (metric.value / memory_bytes) * 100
            result.append(round(percentage, 2))

        return result

    async def _analyze_vm(
        self,
        vm_id: int,
        metrics: List[VMMetric],
        vm_info: Dict,
    ) -> Dict[str, Any]:
        """Analyze single VM for right-sizing.

        Args:
            vm_id: VM ID
            metrics: List of metrics
            vm_info: VM info

        Returns:
            Right-size analysis result
        """
        vm_name = vm_info.get("name", f"VM-{vm_id}")
        host_ip = vm_info.get("host_ip", "")
        cluster = vm_info.get("cluster", "")

        # Get current configuration
        current_cpu = vm_info.get("cpu_count", 0)
        current_memory_bytes = vm_info.get("memory_bytes", 0)
        current_memory_gb = current_memory_bytes / (1024**3) if current_memory_bytes > 0 else 0

        # 获取转换所需的参数
        host_cpu_mhz = vm_info.get("host_cpu_mhz", 0)

        # 提取 CPU 和内存指标并转换为百分比
        cpu_metrics = [m for m in metrics if m.metric_type == "cpu"]
        memory_metrics = [m for m in metrics if m.metric_type == "memory"]

        cpu_values_pct = self._convert_cpu_to_percentage(cpu_metrics, current_cpu, host_cpu_mhz)
        memory_values_pct = self._convert_memory_to_percentage(memory_metrics, current_memory_bytes)

        # Calculate statistics（使用百分比）
        cpu_p95 = self._percentile(cpu_values_pct, 95) if cpu_values_pct else 0
        cpu_max = max(cpu_values_pct) if cpu_values_pct else 0
        cpu_avg = sum(cpu_values_pct) / len(cpu_values_pct) if cpu_values_pct else 0

        memory_p95 = self._percentile(memory_values_pct, 95) if memory_values_pct else 0
        memory_max = max(memory_values_pct) if memory_values_pct else 0
        memory_avg = sum(memory_values_pct) / len(memory_values_pct) if memory_values_pct else 0

        # Calculate recommended configuration
        # CPU: convert percentage to actual cores
        if current_cpu > 0:
            suggested_cpu = self._normalize_cpu(current_cpu * cpu_p95 / 100 * self.cpu_buffer)
        else:
            suggested_cpu = 0
        # Memory: value is already in bytes for the total, so calculate percentage
        if current_memory_gb > 0:
            # memory_p95 is percentage, convert to GB
            suggested_memory_gb = self._normalize_memory(current_memory_gb * memory_p95 / 100 * self.memory_buffer)
        else:
            suggested_memory_gb = 0

        # Determine adjustment type
        cpu_diff = suggested_cpu - current_cpu
        memory_diff = suggested_memory_gb - current_memory_gb

        if cpu_diff < -2 or memory_diff < -1:
            adjustment_type = "down_significant"
        elif cpu_diff < -1 or memory_diff < -0.5:
            adjustment_type = "down"
        elif cpu_diff > 2 or memory_diff > 2:
            adjustment_type = "up_significant"
        elif cpu_diff > 1 or memory_diff > 1:
            adjustment_type = "up"
        else:
            adjustment_type = "none"

        # Calculate risk level (使用 CPU 使用率的变异系数)
        cpu_stddev = self._stddev(cpu_values_pct) if cpu_values_pct else 0
        risk = self._calculate_risk(cpu_stddev, cpu_avg)

        # Calculate confidence
        # 数据存储是按小时聚合的，每小时1个数据点
        total_samples = len(cpu_values_pct) + len(memory_values_pct)
        expected_samples = self.days_threshold * 24  # 每小时1个数据点
        confidence = min(100, (total_samples / expected_samples) * 100) if expected_samples > 0 else 0

        # Generate recommendation
        recommendation = self._generate_recommendation(
            adjustment_type, risk, suggested_cpu, suggested_memory_gb
        )

        # 计算预计节省百分比（综合考虑 CPU 和内存）
        if adjustment_type in ("down", "down_significant"):
            cpu_saving = (1 - (suggested_cpu / current_cpu if current_cpu > 0 else 1)) * 100
            memory_saving = (1 - (suggested_memory_gb / current_memory_gb if current_memory_gb > 0 else 1)) * 100
            # 取平均值作为总体节省
            saving_percent = round((cpu_saving + memory_saving) / 2, 1)
            estimated_saving = f"{saving_percent}%"
        else:
            estimated_saving = "0%"

        return {
            "vmName": vm_name,
            "datacenter": cluster,  # 前端期望 datacenter 字段
            "cluster": cluster,  # 保留 cluster 以兼容
            "hostIp": host_ip,
            # 前端期望的字段
            "currentCpu": current_cpu,
            "recommendedCpu": suggested_cpu,  # 前端期望 recommendedCpu
            "suggestedCpu": suggested_cpu,  # 保留 suggestedCpu 以兼容
            "currentMemoryMb": round(current_memory_gb * 1024, 2),  # 前端期望 MB 单位
            "currentMemory": round(current_memory_gb, 2),  # 保留 GB 单位
            "recommendedMemoryMb": round(suggested_memory_gb * 1024, 2),  # 前端期望 MB 单位
            "suggestedMemory": round(suggested_memory_gb, 2),  # 保留 GB 单位
            "cpuP95": round(cpu_p95, 2),
            "cpuMax": round(cpu_max, 2),
            "cpuAvg": round(cpu_avg, 2),
            "memoryP95": round(memory_p95, 2),
            "memoryMax": round(memory_max, 2),
            "memoryAvg": round(memory_avg, 2),
            "adjustmentType": adjustment_type,
            "riskLevel": risk,
            "confidence": round(confidence, 2),
            "estimatedSaving": estimated_saving,  # 前端期望此字段
            "recommendation": recommendation,
            "details": {
                "daysAnalyzed": self.days_threshold,
                "cpuSamples": len(cpu_values_pct),
                "memorySamples": len(memory_values_pct),
            },
        }

    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]

    def _stddev(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if not values:
            return 0.0
        avg = sum(values) / len(values)
        variance = sum((x - avg) ** 2 for x in values) / len(values)
        return variance ** 0.5

    def _normalize_cpu(self, value: float) -> int:
        """Normalize CPU to standard configuration."""
        for standard in CPU_STANDARDS:
            if value <= standard:
                return standard
        return CPU_STANDARDS[-1]

    def _normalize_memory(self, value_gb: float) -> float:
        """Normalize memory to standard configuration."""
        for standard in MEMORY_STANDARDS:
            if value_gb <= standard:
                return standard
        return MEMORY_STANDARDS[-1]

    def _calculate_risk(self, stddev: float, mean: float) -> str:
        """Calculate risk level based on variability using coefficient of variation.

        CV = stddev / mean，表示数据的相对波动性
        """
        if mean == 0:
            return "low"

        cv = stddev / mean if mean > 0 else 0
        if cv > 0.4:
            return "high"
        elif cv > 0.2:
            return "medium"
        else:
            return "low"

    def _generate_recommendation(
        self,
        adjustment_type: str,
        risk: str,
        suggested_cpu: int,
        suggested_memory_gb: float,
    ) -> str:
        """Generate right-sizing recommendation."""
        if adjustment_type == "down_significant":
            return f"建议大幅缩容至 {suggested_cpu} vCPU / {suggested_memory_gb}GB RAM"
        elif adjustment_type == "down":
            return f"建议缩容至 {suggested_cpu} vCPU / {suggested_memory_gb}GB RAM"
        elif adjustment_type == "up_significant":
            return f"需要大幅扩容至 {suggested_cpu} vCPU / {suggested_memory_gb}GB RAM"
        elif adjustment_type == "up":
            return f"建议扩容至 {suggested_cpu} vCPU / {suggested_memory_gb}GB RAM"
        else:
            return "当前配置合理，无需调整"
