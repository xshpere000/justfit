"""Resource Analyzer - Right Size, Usage Pattern, and Mismatch Detection."""

import structlog
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from app.models import VMMetric


logger = structlog.get_logger()


class UsagePatternAnalyzer:
    """Usage pattern analyzer - detects stable, tidal, or burst patterns."""

    def __init__(
        self,
        cv_threshold: float = 0.4,
        peak_valley_ratio_threshold: float = 2.5,
        min_samples: int = 24,
    ) -> None:
        """Initialize usage pattern analyzer.

        Args:
            cv_threshold: Coefficient of variation threshold (default 0.4)
            peak_valley_ratio_threshold: Peak/valley ratio threshold (default 2.5)
            min_samples: Minimum samples required for analysis (default 24)
        """
        self.cv_threshold = cv_threshold
        self.peak_valley_ratio_threshold = peak_valley_ratio_threshold
        self.min_samples = min_samples

    def _convert_cpu_to_percentage(
        self,
        cpu_metrics: List[VMMetric],
        cpu_count: int,
        host_cpu_mhz: int,
    ) -> List[float]:
        """将 CPU 指标从存储值（MHz）转换为百分比。

        vCenter/UIS 存储：percentage / 100 * cpu_count * host_cpu_mhz
        还原百分比：stored_value / cpu_count / host_cpu_mhz * 100

        Args:
            cpu_metrics: CPU 指标列表（存储的 MHz 值）
            cpu_count: CPU 核心数
            host_cpu_mhz: 主机 CPU 单核频率 (MHz)

        Returns:
            转换后的 CPU 百分比列表
        """
        if not cpu_metrics:
            return []

        # 使用 host_cpu_mhz，如果为 0 则使用估算值
        effective_host_mhz = host_cpu_mhz if host_cpu_mhz > 0 else 2600
        effective_cpu_count = cpu_count if cpu_count > 0 else 1

        if effective_host_mhz == 0:
            return [m.value for m in cpu_metrics]

        result = []
        for metric in cpu_metrics:
            # 还原百分比：stored_value / cpu_count / host_cpu_mhz * 100
            percentage = (metric.value / effective_cpu_count / effective_host_mhz) * 100
            result.append(round(percentage, 2))

        return result

    async def analyze(
        self,
        task_id: int,
        vm_metrics: Dict[int, List[VMMetric]],
        vm_data: Dict[int, Dict],
    ) -> List[Dict]:
        """Analyze VMs for usage patterns.

        Args:
            task_id: Task ID
            vm_metrics: Dict mapping vm_id to list of metrics
            vm_data: Dict mapping vm_id to VM info

        Returns:
            List of usage pattern findings
        """
        findings = []

        for vm_id, metrics in vm_metrics.items():
            if not metrics:
                continue

            vm_info = vm_data.get(vm_id, {})
            result = await self._analyze_vm(vm_id, metrics, vm_info)

            # Include all results, not just significant ones
            findings.append(result)

        logger.info(
            "usage_pattern_analysis_completed",
            task_id=task_id,
            total_vms=len(vm_metrics),
            findings_count=len(findings),
        )

        return findings

    async def _analyze_vm(
        self,
        vm_id: int,
        metrics: List[VMMetric],
        vm_info: Dict,
    ) -> Dict[str, Any]:
        """Analyze single VM for usage pattern.

        Args:
            vm_id: VM ID
            metrics: List of metrics
            vm_info: VM info (必须包含 cpu_count, host_cpu_mhz)

        Returns:
            Usage pattern analysis result
        """
        vm_name = vm_info.get("name", f"VM-{vm_id}")
        cluster = vm_info.get("cluster", "")
        host_ip = vm_info.get("host_ip", "")

        # 获取 CPU 配置信息（用于百分比转换）
        cpu_count = vm_info.get("cpu_count", 0)
        host_cpu_mhz = vm_info.get("host_cpu_mhz", 0)

        # 提取 CPU 指标并转换为百分比
        cpu_metrics = [m for m in metrics if m.metric_type == "cpu"]
        cpu_values_pct = self._convert_cpu_to_percentage(cpu_metrics, cpu_count, host_cpu_mhz)

        if len(cpu_values_pct) < self.min_samples:
            return {
                "vmName": vm_name,
                "datacenter": cluster,
                "cluster": cluster,
                "hostIp": host_ip,
                "optimizationType": "usage_pattern",
                "usagePattern": "unknown",
                "volatilityLevel": "unknown",
                "coefficientOfVariation": 0.0,
                "peakValleyRatio": 0.0,
                "recommendation": f"数据不足（需要至少 {self.min_samples} 个样本），无法分析使用模式",
                "details": {
                    "samplesCount": len(cpu_values_pct),
                    "minSamplesRequired": self.min_samples,
                },
            }

        # Calculate statistics (使用百分比)
        mean_cpu = statistics.mean(cpu_values_pct)
        cv = 0.0

        if mean_cpu > 0 and len(cpu_values_pct) > 1:
            std_cpu = statistics.stdev(cpu_values_pct)
            cv = std_cpu / mean_cpu

        # Calculate peak/valley ratio (使用百分比)
        max_cpu = max(cpu_values_pct)
        min_cpu = min(cpu_values_pct)

        # 计算峰谷比：需要注意防止除零和过大的比值
        # 当 min_cpu 很小时（接近 0），峰谷比会失去意义，需要限制
        if min_cpu < 0.5:  # 如果最小值小于 0.5%，使用 0.5 作为基准
            peak_valley_ratio = max_cpu / 0.5
        else:
            peak_valley_ratio = max_cpu / min_cpu

        # 限制峰谷比最大值为 100，避免异常值
        peak_valley_ratio = min(peak_valley_ratio, 100.0)

        # Determine pattern
        pattern, volatility_level, recommendation = self._classify_pattern(
            cv, peak_valley_ratio
        )

        # Tidal details (if applicable) - 需要传入转换参数
        tidal_details = None
        if pattern == "tidal":
            tidal_details = self._analyze_tidal_details(metrics, cpu_count, host_cpu_mhz)

        return {
            "vmName": vm_name,
            "datacenter": cluster,
            "cluster": cluster,
            "hostIp": host_ip,
            "optimizationType": "usage_pattern",
            "usagePattern": pattern,
            "volatilityLevel": volatility_level,
            "coefficientOfVariation": round(cv, 3),
            "peakValleyRatio": round(peak_valley_ratio, 3),
            "tidalDetails": tidal_details,
            "recommendation": recommendation,
            "details": {
                "samplesCount": len(cpu_values_pct),
                "meanCpu": round(mean_cpu, 2),
                "maxCpu": round(max_cpu, 2),
                "minCpu": round(min_cpu, 2),
            },
        }

    def _classify_pattern(
        self, cv: float, peak_valley_ratio: float
    ) -> tuple[str, str, str]:
        """Classify usage pattern based on CV and peak/valley ratio using configured thresholds.

        Returns:
            Tuple of (pattern, volatility_level, recommendation)
        """
        # Use configured thresholds
        cv_threshold = self.cv_threshold
        ratio_threshold = self.peak_valley_ratio_threshold

        if cv > cv_threshold * 1.25 and peak_valley_ratio > ratio_threshold * 1.2:
            return (
                "tidal",
                "high",
                "VM呈现潮汐使用模式，建议配置自动调度策略在闲置期降低资源或关闭VM",
            )
        elif cv > cv_threshold * 0.75:
            return (
                "burst",
                "moderate",
                "VM使用有较大波动，建议配置弹性伸缩策略",
            )
        else:
            return (
                "stable",
                "low",
                "VM使用模式稳定，建议保持当前配置",
            )

    def _analyze_tidal_details(
        self,
        metrics: List[VMMetric],
        cpu_count: int,
        host_cpu_mhz: int,
    ) -> Dict[str, Any]:
        """Analyze tidal pattern details.

        Args:
            metrics: List of metrics
            cpu_count: CPU 核心数（用于百分比转换）
            host_cpu_mhz: 主机 CPU 频率（用于百分比转换）

        Returns:
            Tidal pattern details
        """
        cpu_metrics = [m for m in metrics if m.metric_type == "cpu"]

        if not cpu_metrics:
            return {}

        # 先转换为百分比
        cpu_values_pct = self._convert_cpu_to_percentage(cpu_metrics, cpu_count, host_cpu_mhz)

        # Group by hour (使用本地时间，而非 UTC)
        hourly_avg: Dict[int, List[float]] = {}
        for i, m in enumerate(cpu_metrics):
            # 转换为本地时间（假设服务器在中国 UTC+8）
            # 如果 timestamp 是 naive datetime（无时区信息），假设是 UTC
            timestamp = m.timestamp
            if timestamp.tzinfo is None:
                # 假设是 UTC 时间，转换为北京时间 (UTC+8)
                local_hour = (timestamp.hour + 8) % 24
            else:
                # 有时区信息，转换为本地时间
                from datetime import timezone
                utc_ts = timestamp.astimezone(timezone.utc)
                local_ts = utc_ts.astimezone(timezone(timedelta(hours=8)))
                local_hour = local_ts.hour

            if i < len(cpu_values_pct):
                if local_hour not in hourly_avg:
                    hourly_avg[local_hour] = []
                hourly_avg[local_hour].append(cpu_values_pct[i])

        hourly_avg = {h: statistics.mean(v) for h, v in hourly_avg.items()}

        # Day hours: 9:00-18:00 (本地时间)
        day_hours = list(range(9, 18))
        # Night hours: 22:00-6:00 (本地时间)
        night_hours = list(range(0, 6)) + list(range(22, 24))

        day_avg = statistics.mean([hourly_avg.get(h, 0) for h in day_hours])
        night_avg = statistics.mean([hourly_avg.get(h, 0) for h in night_hours])

        if day_avg > night_avg * 2:
            pattern_type = "day_active"
        elif night_avg > day_avg * 2:
            pattern_type = "night_active"
        else:
            pattern_type = "uniform"

        return {
            "patternType": pattern_type,
            "dayAvg": round(day_avg, 2),
            "nightAvg": round(night_avg, 2),
            "hourlyAvg": {str(h): round(v, 2) for h, v in sorted(hourly_avg.items())},
        }


class MismatchDetector:
    """Resource mismatch detector - detects CPU/memory configuration mismatches."""

    def __init__(
        self,
        cpu_low_threshold: float = 30.0,
        cpu_high_threshold: float = 70.0,
        memory_low_threshold: float = 30.0,
        memory_high_threshold: float = 70.0,
    ) -> None:
        """Initialize mismatch detector.

        Args:
            cpu_low_threshold: CPU low utilization threshold % (default 30%)
            cpu_high_threshold: CPU high utilization threshold % (default 70%)
            memory_low_threshold: Memory low utilization threshold % (default 30%)
            memory_high_threshold: Memory high utilization threshold % (default 70%)
        """
        self.cpu_low_threshold = cpu_low_threshold
        self.cpu_high_threshold = cpu_high_threshold
        self.memory_low_threshold = memory_low_threshold
        self.memory_high_threshold = memory_high_threshold

    async def analyze(
        self,
        task_id: int,
        vm_metrics: Dict[int, List[VMMetric]],
        vm_data: Dict[int, Dict],
    ) -> List[Dict]:
        """Analyze VMs for resource mismatches.

        Args:
            task_id: Task ID
            vm_metrics: Dict mapping vm_id to list of metrics
            vm_data: Dict mapping vm_id to VM info

        Returns:
            List of mismatch findings (only VMs with mismatches)
        """
        findings = []

        for vm_id, metrics in vm_metrics.items():
            if not metrics:
                continue

            vm_info = vm_data.get(vm_id, {})
            result = await self._analyze_vm(vm_id, metrics, vm_info)

            # Only include VMs with mismatches
            if result["hasMismatch"]:
                findings.append(result)

        logger.info(
            "mismatch_analysis_completed",
            task_id=task_id,
            total_vms=len(vm_metrics),
            mismatch_count=len(findings),
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
        """Analyze single VM for resource mismatch.

        Args:
            vm_id: VM ID
            metrics: List of metrics
            vm_info: VM info

        Returns:
            Mismatch analysis result
        """
        vm_name = vm_info.get("name", f"VM-{vm_id}")
        cluster = vm_info.get("cluster", "")
        host_ip = vm_info.get("host_ip", "")

        # Get current configuration
        current_cpu = vm_info.get("cpu_count", 0)
        current_memory_gb = vm_info.get("memory_bytes", 0) / (1024**3)

        # 获取转换所需的参数
        host_cpu_mhz = vm_info.get("host_cpu_mhz", 0)

        # 提取 CPU 和内存指标并转换为百分比
        cpu_metrics = [m for m in metrics if m.metric_type == "cpu"]
        memory_metrics = [m for m in metrics if m.metric_type == "memory"]

        cpu_values_pct = self._convert_cpu_to_percentage(cpu_metrics, current_cpu, host_cpu_mhz)
        memory_values_pct = self._convert_memory_to_percentage(memory_metrics, vm_info.get("memory_bytes", 0))

        # Calculate P95 utilization（使用百分比）
        cpu_p95 = self._percentile(cpu_values_pct, 95) if cpu_values_pct else 0
        memory_p95 = self._percentile(memory_values_pct, 95) if memory_values_pct else 0

        # Determine mismatch type
        mismatch_type = None
        recommendation = "资源配置比例合理"

        if cpu_p95 < self.cpu_low_threshold and memory_p95 > self.memory_high_threshold:
            mismatch_type = "cpu_rich_memory_poor"
            recommendation = "内存使用率较高但CPU使用率低，可能存在内存瓶颈，建议增加内存或降低CPU"
        elif cpu_p95 > self.cpu_high_threshold and memory_p95 < self.memory_low_threshold:
            mismatch_type = "cpu_poor_memory_rich"
            recommendation = "CPU使用率较高但内存使用率低，可能存在CPU瓶颈，建议增加CPU或降低内存"
        elif cpu_p95 < self.cpu_low_threshold and memory_p95 < self.memory_low_threshold:
            mismatch_type = "both_underutilized"
            recommendation = "CPU和内存使用率都较低，建议整体降配以节省资源"
        elif cpu_p95 > self.cpu_high_threshold and memory_p95 > self.memory_high_threshold:
            mismatch_type = "both_overutilized"
            recommendation = "CPU和内存使用率都较高，建议整体扩容以提升性能"

        return {
            "vmName": vm_name,
            "datacenter": cluster,
            "cluster": cluster,
            "hostIp": host_ip,
            "hasMismatch": mismatch_type is not None,
            "mismatchType": mismatch_type,
            "cpuUtilization": round(cpu_p95, 2),
            "memoryUtilization": round(memory_p95, 2),
            "currentCpu": current_cpu,
            "currentMemory": round(current_memory_gb, 2),
            "recommendation": recommendation,
            "details": {
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


class ResourceAnalyzer:
    """Main resource analyzer - combines right-size, usage pattern, and mismatch detection."""

    def __init__(
        self,
        mode: str = "saving",
        right_size_config: Optional[Dict[str, Any]] = None,
        usage_pattern_config: Optional[Dict[str, Any]] = None,
        mismatch_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize resource analyzer.

        Args:
            mode: Analysis mode (safe, saving, aggressive, custom)
            right_size_config: Optional Right Size configuration override
            usage_pattern_config: Optional Usage Pattern configuration override
            mismatch_config: Optional Mismatch configuration override
        """
        self.mode = mode

        # Import right size analyzer (already implemented)
        from app.analyzers.rightsize import RightSizeAnalyzer

        # Get mode-based configurations
        from app.analyzers.modes import AnalysisModes

        mode_config = AnalysisModes.get_mode(mode)
        rightsize_mode_config = mode_config.get("rightsize", {})

        # Initialize sub-analyzers
        self.right_size_analyzer = RightSizeAnalyzer(
            days_threshold=right_size_config.get("days", rightsize_mode_config.get("days", 7))
            if right_size_config
            else rightsize_mode_config.get("days", 7),
            cpu_buffer_percent=right_size_config.get("cpu_buffer_percent", rightsize_mode_config.get("cpu_buffer_percent", 20.0))
            if right_size_config
            else rightsize_mode_config.get("cpu_buffer_percent", 20.0),
            memory_buffer_percent=right_size_config.get("memory_buffer_percent", rightsize_mode_config.get("memory_buffer_percent", 20.0))
            if right_size_config
            else rightsize_mode_config.get("memory_buffer_percent", 20.0),
            min_confidence=right_size_config.get("min_confidence", rightsize_mode_config.get("min_confidence", 60.0))
            if right_size_config
            else rightsize_mode_config.get("min_confidence", 60.0),
        )

        self.usage_pattern_analyzer = UsagePatternAnalyzer(
            cv_threshold=usage_pattern_config.get("cv_threshold", 0.4)
            if usage_pattern_config
            else 0.4,
            peak_valley_ratio_threshold=usage_pattern_config.get("peak_valley_ratio", 2.5)
            if usage_pattern_config
            else 2.5,
        )

        self.mismatch_detector = MismatchDetector(
            cpu_low_threshold=mismatch_config.get("cpu_low_threshold", 30.0)
            if mismatch_config
            else 30.0,
            cpu_high_threshold=mismatch_config.get("cpu_high_threshold", 70.0)
            if mismatch_config
            else 70.0,
            memory_low_threshold=mismatch_config.get("memory_low_threshold", 30.0)
            if mismatch_config
            else 30.0,
            memory_high_threshold=mismatch_config.get("memory_high_threshold", 70.0)
            if mismatch_config
            else 70.0,
        )

    async def analyze(
        self,
        task_id: int,
        vm_metrics: Dict[int, List[VMMetric]],
        vm_data: Dict[int, Dict],
    ) -> Dict[str, Any]:
        """Run all resource analysis types.

        Args:
            task_id: Task ID
            vm_metrics: Dict mapping vm_id to list of metrics
            vm_data: Dict mapping vm_id to VM info

        Returns:
            Combined analysis results with rightSize, usagePattern, and mismatch
        """
        # Run all analyzers in parallel
        import asyncio

        right_size_results, usage_pattern_results, mismatch_results = await asyncio.gather(
            self.right_size_analyzer.analyze(task_id, vm_metrics, vm_data),
            self.usage_pattern_analyzer.analyze(task_id, vm_metrics, vm_data),
            self.mismatch_detector.analyze(task_id, vm_metrics, vm_data),
        )

        return {
            "rightSize": right_size_results,
            "usagePattern": usage_pattern_results,
            "mismatch": mismatch_results,
            "summary": {
                "rightSizeCount": len(right_size_results),
                "usagePatternCount": len(usage_pattern_results),
                "mismatchCount": len(mismatch_results),
                "totalVmsAnalyzed": len(vm_metrics),
            },
        }
