"""Tidal Pattern Analyzer - Detects cyclical usage patterns."""

import structlog
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from app.models import VMMetric


logger = structlog.get_logger()


class TidalAnalyzer:
    """Analyzer for detecting tidal (cyclical) usage patterns."""

    def __init__(
        self,
        days_threshold: int = 30,
        peak_threshold: float = 80.0,
        valley_threshold: float = 30.0,
        min_stability: float = 70.0,
    ) -> None:
        """Initialize tidal analyzer.

        Args:
            days_threshold: Days to analyze (default 30)
            peak_threshold: Peak usage threshold % (default 80)
            valley_threshold: Valley usage threshold % (default 30)
            min_stability: Minimum stability score (0-100)
        """
        self.days_threshold = days_threshold
        self.peak_threshold = peak_threshold
        self.valley_threshold = valley_threshold
        self.min_stability = min_stability

    async def analyze(
        self,
        task_id: int,
        vm_metrics: Dict[int, List[VMMetric]],
        vm_data: Dict[int, Dict],
    ) -> List[Dict]:
        """Analyze VMs for tidal patterns.

        Args:
            task_id: Task ID
            vm_metrics: Dict mapping vm_id to list of metrics
            vm_data: Dict mapping vm_id to VM info

        Returns:
            List of tidal pattern findings
        """
        findings = []

        for vm_id, metrics in vm_metrics.items():
            if not metrics:
                continue

            vm_info = vm_data.get(vm_id, {})
            result = await self._analyze_vm(vm_id, metrics, vm_info)

            if result["stabilityScore"] >= self.min_stability:
                findings.append(result)

        logger.info(
            "tidal_analysis_completed",
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
        """Analyze single VM for tidal patterns.

        Args:
            vm_id: VM ID
            metrics: List of metrics
            vm_info: VM info

        Returns:
            Tidal pattern analysis result
        """
        vm_name = vm_info.get("name", f"VM-{vm_id}")
        cluster = vm_info.get("cluster", "")

        # Combine CPU and memory for analysis
        cpu_metrics = [m.value for m in metrics if m.metric_type == "cpu"]
        memory_metrics = [m.value for m in metrics if m.metric_type == "memory"]

        # Detect daily pattern
        daily_result = self._detect_daily_pattern(metrics)
        weekly_result = self._detect_weekly_pattern(metrics)

        # Choose best pattern
        if daily_result["stability"] > weekly_result["stability"]:
            pattern = daily_result
            pattern_type = "daily"
        else:
            pattern = weekly_result
            pattern_type = weekly_result.get("patternType", "none")

        # Extract peak hours
        peak_hours = pattern.get("peakHours", [])
        peak_days = pattern.get("peakDays", [])

        # Calculate stability score
        stability_score = pattern["stability"]

        # Calculate potential savings
        if stability_score >= 80:
            estimated_saving = "50-70%"
        elif stability_score >= 60:
            estimated_saving = "30-50%"
        else:
            estimated_saving = "10-30%"

        # Generate recommendation
        recommendation = self._generate_recommendation(
            pattern_type, stability_score, estimated_saving
        )

        return {
            "vmName": vm_name,
            "datacenter": cluster,  # 前端期望 datacenter 字段
            "cluster": cluster,  # 保留 cluster 以兼容
            "cpuCores": vm_info.get("cpu_count", 0),
            "memoryGb": round(vm_info.get("memory_bytes", 0) / (1024**3), 2),
            "pattern": pattern_type,  # 前端期望 pattern 字段
            "patternType": pattern_type,  # 保留 patternType 以兼容
            "stability": round(stability_score, 2),  # 前端期望 stability 字段
            "stabilityScore": round(stability_score, 2),  # 保留 stabilityScore 以兼容
            "peakHours": peak_hours,
            "peakDays": peak_days,
            "recommendation": recommendation,
            "estimatedSaving": estimated_saving,
            "details": {
                "daysAnalyzed": self.days_threshold,
                "coefficientOfVariation": round(pattern.get("cv", 0), 2),
            },
        }

    def _detect_daily_pattern(self, metrics: List[VMMetric]) -> Dict:
        """Detect daily (hourly) usage pattern."""
        # Group by hour (0-23)
        hourly_usage = {}  # hour -> [usage values]

        for metric in metrics:
            if metric.metric_type == "cpu":
                hour = metric.timestamp.hour
                if hour not in hourly_usage:
                    hourly_usage[hour] = []
                hourly_usage[hour].append(metric.value)

        # Calculate statistics for each hour
        hour_stats = {}
        for hour, values in hourly_usage.items():
            if values:
                avg = sum(values) / len(values)
                hour_stats[hour] = avg

        # Calculate coefficient of variation
        if len(hour_stats) > 0:
            avg_usage = sum(hour_stats.values()) / len(hour_stats)
            variance = sum((v - avg_usage) ** 2 for v in hour_stats.values()) / len(hour_stats)
            cv = (variance ** 0.5 / avg_usage * 100) if avg_usage > 0 else 0

            # Stability is inverse of CV (lower CV = more stable)
            stability = max(0, 100 - cv * 2)
        else:
            stability = 0
            cv = 0

        # Find peak hours (top 25%)
        sorted_hours = sorted(hour_stats.items(), key=lambda x: x[1], reverse=True)
        peak_count = max(1, len(sorted_hours) // 4)
        peak_hours = [h for h, _ in sorted_hours[:peak_count]]

        return {
            "stability": stability,
            "cv": cv,
            "peakHours": peak_hours,
            "patternType": "daily" if stability >= 20 else "none",
        }

    def _detect_weekly_pattern(self, metrics: List[VMMetric]) -> Dict:
        """Detect weekly (day-of-week) usage pattern."""
        # Group by day of week (0=Monday, 6=Sunday)
        daily_usage = {}  # day -> [usage values]

        for metric in metrics:
            if metric.metric_type == "cpu":
                day = metric.timestamp.weekday()
                if day not in daily_usage:
                    daily_usage[day] = []
                daily_usage[day].append(metric.value)

        # Calculate statistics for each day
        day_stats = {}
        for day, values in daily_usage.items():
            if values:
                avg = sum(values) / len(values)
                day_stats[day] = avg

        # Calculate coefficient of variation
        if len(day_stats) > 0:
            avg_usage = sum(day_stats.values()) / len(day_stats)
            variance = sum((v - avg_usage) ** 2 for v in day_stats.values()) / len(day_stats)
            cv = (variance ** 0.5 / avg_usage * 100) if avg_usage > 0 else 0

            # Stability is inverse of CV (lower CV = more stable)
            stability = max(0, 100 - cv * 2.5)
        else:
            stability = 0
            cv = 0

        # Find peak days (top 25%)
        sorted_days = sorted(day_stats.items(), key=lambda x: x[1], reverse=True)
        peak_count = max(1, len(sorted_days) // 4)
        peak_days = [d for d, _ in sorted_days[:peak_count]]

        return {
            "stability": stability,
            "cv": cv,
            "peakDays": peak_days,
            "patternType": "weekly" if stability >= 15 else "none",
        }

    def _generate_recommendation(
        self,
        pattern_type: str,
        stability: float,
        estimated_saving: str,
    ) -> str:
        """Generate tidal pattern recommendation."""
        if pattern_type == "daily":
            return f"检测到明显的日周期模式（稳定性: {stability:.0f}%），可通过潮汐调度节省 {estimated_saving} 资源成本"
        elif pattern_type == "weekly":
            return f"检测到周周期模式（稳定性: {stability:.0f}%），可通过调整资源分配节省 {estimated_saving} 成本"
        else:
            return "未检测到明显的周期性使用模式，建议继续监控"
