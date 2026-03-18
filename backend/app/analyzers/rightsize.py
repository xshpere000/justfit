"""Right Size Analyzer - VM resource sizing recommendations."""

import structlog
from typing import List, Dict, Any

from app.models import VMMetric


logger = structlog.get_logger()


# Standard CPU configurations
CPU_STANDARDS = [1, 2, 4, 8, 12, 16, 24, 32, 48, 64]

# Standard memory configurations (in GB)
MEMORY_STANDARDS = [0.5, 1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256]


class RightSizeAnalyzer:
    """Analyzer for VM right-sizing recommendations."""

    def __init__(
        self,
        days_threshold: int = 14,
        cpu_buffer_percent: float = 20.0,
        memory_buffer_percent: float = 20.0,
        min_confidence: float = 60.0,
    ) -> None:
        """Initialize right-size analyzer.

        Args:
            days_threshold: Days to analyze (default 14)
            cpu_buffer_percent: CPU buffer percentage (default 20%)
            memory_buffer_percent: Memory buffer percentage (default 20%)
            min_confidence: Minimum confidence (default 60)
        """
        self.days_threshold = days_threshold
        self.cpu_buffer = 1.0 + cpu_buffer_percent / 100
        self.memory_buffer = 1.0 + memory_buffer_percent / 100
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
        """Analyze single VM for right-sizing with integrated mismatch detection.

        Args:
            vm_id: VM ID
            metrics: List of metrics
            vm_info: VM info

        Returns:
            Right-size analysis result including mismatch type and reason
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
        cpu_p90 = self._percentile(cpu_values_pct, 90) if cpu_values_pct else 0
        cpu_max = max(cpu_values_pct) if cpu_values_pct else 0
        cpu_avg = sum(cpu_values_pct) / len(cpu_values_pct) if cpu_values_pct else 0

        memory_p95 = self._percentile(memory_values_pct, 95) if memory_values_pct else 0
        memory_max = max(memory_values_pct) if memory_values_pct else 0
        memory_avg = sum(memory_values_pct) / len(memory_values_pct) if memory_values_pct else 0

        # 推荐配置算法：P95+max 双重保障
        # 推荐使用率 = max(P95, P90) * buffer，同时设置峰值保护下限 = max * 0.8
        if current_cpu > 0:
            base_cpu_pct = max(cpu_p95, cpu_p90) * self.cpu_buffer
            peak_floor_pct = cpu_max * 0.8
            effective_cpu_pct = max(base_cpu_pct, peak_floor_pct)
            recommended_cpu = self._normalize_cpu(current_cpu * effective_cpu_pct / 100)
            recommended_cpu = max(1, recommended_cpu)  # 最少1核
        else:
            recommended_cpu = 0

        if current_memory_gb > 0:
            base_mem_pct = memory_p95 * self.memory_buffer
            peak_floor_pct = memory_max * 0.8
            effective_mem_pct = max(base_mem_pct, peak_floor_pct)
            recommended_memory_gb = self._normalize_memory(current_memory_gb * effective_mem_pct / 100)
            recommended_memory_gb = max(0.5, recommended_memory_gb)  # 最少 0.5GB
        else:
            recommended_memory_gb = 0

        # 错配类型判断（基于 P95 使用率）
        mismatch_type = self._determine_mismatch_type(cpu_p95, memory_p95)

        # 分别计算 CPU 和内存的浪费比例（缩减为正，扩容为负）
        if current_cpu > 0 and current_memory_gb > 0:
            cpu_waste_ratio = round((current_cpu - recommended_cpu) / current_cpu * 100, 1)
            mem_waste_ratio = round((current_memory_gb - recommended_memory_gb) / current_memory_gb * 100, 1)
        else:
            cpu_waste_ratio = 0.0
            mem_waste_ratio = 0.0

        # 分别判断 CPU 和内存的调整方向
        cpu_adjustment_type = self._determine_single_adjustment_type(current_cpu, recommended_cpu)
        mem_adjustment_type = self._determine_single_adjustment_type(current_memory_gb, recommended_memory_gb)

        # Calculate risk level (使用 CPU 使用率的变异系数)
        cpu_stddev = self._stddev(cpu_values_pct) if cpu_values_pct else 0
        risk = self._calculate_risk(cpu_stddev, cpu_avg)

        # Calculate confidence（基于采样点数，同时考虑数据质量）
        total_samples = len(cpu_values_pct) + len(memory_values_pct)
        # 根据实际点数推断数据粒度：若 CPU 点数 ≤ days_threshold*2，认为是天级数据
        cpu_sample_count = len(cpu_values_pct)
        if cpu_sample_count > 0 and cpu_sample_count <= self.days_threshold * 2:
            # 天级粒度：期望 = days_threshold × 2（CPU + 内存各1天1个）
            expected_samples = self.days_threshold * 2
        else:
            # 小时级粒度：期望 = days_threshold × 24 × 2
            expected_samples = self.days_threshold * 24 * 2
        base_confidence = min(100, (total_samples / expected_samples) * 100) if expected_samples > 0 else 0

        # 数据质量修正：方差过高降低置信度
        if cpu_values_pct:
            cv = cpu_stddev / cpu_avg if cpu_avg > 0 else 0
            quality_factor = max(0.7, 1.0 - cv * 0.3)
            confidence = base_confidence * quality_factor
        else:
            confidence = base_confidence

        # 生成有说服力的判断依据（含具体数据）
        reason = self._build_reason(
            current_cpu, recommended_cpu,
            current_memory_gb, recommended_memory_gb,
            cpu_p95, cpu_p90, cpu_max, cpu_avg,
            memory_p95, memory_max, memory_avg,
            cpu_adjustment_type, mem_adjustment_type, mismatch_type, risk,
        )

        return {
            "vmName": vm_name,
            "vmId": vm_id,
            "cluster": cluster,
            "hostIp": host_ip,
            "currentCpu": current_cpu,
            "recommendedCpu": recommended_cpu,
            "currentMemoryGb": round(current_memory_gb, 2),
            "recommendedMemoryGb": round(recommended_memory_gb, 2),
            "cpuP95": round(cpu_p95, 2),
            "cpuP90": round(cpu_p90, 2),
            "cpuMax": round(cpu_max, 2),
            "cpuAvg": round(cpu_avg, 2),
            "memoryP95": round(memory_p95, 2),
            "memoryMax": round(memory_max, 2),
            "memoryAvg": round(memory_avg, 2),
            "mismatchType": mismatch_type,
            "cpuAdjustmentType": cpu_adjustment_type,
            "memAdjustmentType": mem_adjustment_type,
            "cpuWasteRatio": cpu_waste_ratio,
            "memWasteRatio": mem_waste_ratio,
            "riskLevel": risk,
            "confidence": round(confidence, 2),
            "reason": reason,
        }

    def _determine_single_adjustment_type(self, current: float, recommended: float) -> str:
        """按比例判断单个维度（CPU 或内存）的调整方向。"""
        if current <= 0:
            return "none"
        ratio = recommended / current
        if ratio <= 0.5:
            return "down_significant"
        elif ratio <= 0.75:
            return "down"
        elif ratio >= 1.5:
            return "up_significant"
        elif ratio >= 1.25:
            return "up"
        else:
            return "none"

    def _determine_mismatch_type(self, cpu_p95: float, memory_p95: float) -> str:
        """判断 CPU/内存配比错配类型。

        基于 P95 使用率，阈值：低=30%，高=70%
        """
        cpu_low = cpu_p95 < 30.0
        cpu_high = cpu_p95 > 70.0
        mem_low = memory_p95 < 30.0
        mem_high = memory_p95 > 70.0

        if cpu_low and mem_high:
            return "cpu_rich_memory_poor"
        elif cpu_high and mem_low:
            return "cpu_poor_memory_rich"
        elif cpu_low and mem_low:
            return "both_underutilized"
        elif cpu_high and mem_high:
            return "both_overutilized"
        else:
            return "balanced"

    def _build_reason(
        self,
        current_cpu: int,
        recommended_cpu: int,
        current_memory_gb: float,
        recommended_memory_gb: float,
        cpu_p95: float,
        cpu_p90: float,
        cpu_max: float,
        cpu_avg: float,
        memory_p95: float,
        memory_max: float,
        memory_avg: float,
        cpu_adjustment_type: str,
        mem_adjustment_type: str,
        mismatch_type: str,
        risk: str,
    ) -> str:
        """生成有说服力的判断依据，包含具体数据和结论。"""
        parts = []

        # CPU 数据描述
        parts.append(
            f"CPU：P95={cpu_p95:.1f}%、P90={cpu_p90:.1f}%、峰值={cpu_max:.1f}%、均值={cpu_avg:.1f}%"
            f"（当前 {current_cpu} 核 → 推荐 {recommended_cpu} 核）"
        )

        # 内存数据描述
        parts.append(
            f"内存：P95={memory_p95:.1f}%、峰值={memory_max:.1f}%、均值={memory_avg:.1f}%"
            f"（当前 {current_memory_gb:.1f} GB → 推荐 {recommended_memory_gb:.1f} GB）"
        )

        # 错配类型结论
        mismatch_desc = {
            "cpu_rich_memory_poor": f"CPU 长期低使用率（P95={cpu_p95:.1f}%）但内存已接近瓶颈（P95={memory_p95:.1f}%），典型 CPU 富余/内存紧张错配",
            "cpu_poor_memory_rich": f"CPU 持续高负载（P95={cpu_p95:.1f}%）但内存利用率低（P95={memory_p95:.1f}%），典型 CPU 不足/内存浪费错配",
            "both_underutilized": f"CPU（P95={cpu_p95:.1f}%）和内存（P95={memory_p95:.1f}%）利用率均偏低，整体配置过剩",
            "both_overutilized": f"CPU（P95={cpu_p95:.1f}%）和内存（P95={memory_p95:.1f}%）利用率均偏高，存在性能瓶颈风险",
            "balanced": f"CPU（P95={cpu_p95:.1f}%）和内存（P95={memory_p95:.1f}%）配比基本合理",
        }
        parts.append(mismatch_desc.get(mismatch_type, ""))

        # 调整方向结论
        adj_label = {
            "down_significant": "大幅缩容",
            "down": "缩容",
            "up_significant": "大幅扩容",
            "up": "扩容",
            "none": "合理",
        }
        cpu_label = adj_label.get(cpu_adjustment_type, "合理")
        mem_label = adj_label.get(mem_adjustment_type, "合理")
        conclusion = f"CPU建议{cpu_label}至 {recommended_cpu} vCPU，内存建议{mem_label}至 {recommended_memory_gb:.1f} GB"
        if risk == "high" and (cpu_adjustment_type != "none" or mem_adjustment_type != "none"):
            conclusion += "（注意：负载波动较大，建议谨慎操作）"
        parts.append(conclusion)

        return "；".join(p for p in parts if p)

    def _percentile(self, values: List[float], percentile: int) -> float:
        if not values:
            return 0.0
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n == 1:
            return sorted_values[0]
        # 线性插值：更精确的百分位计算
        rank = (percentile / 100) * (n - 1)
        lower = int(rank)
        upper = min(lower + 1, n - 1)
        frac = rank - lower
        return sorted_values[lower] + frac * (sorted_values[upper] - sorted_values[lower])

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

        cv = stddev / mean
        if cv > 0.4:
            return "high"
        elif cv > 0.2:
            return "medium"
        else:
            return "low"


