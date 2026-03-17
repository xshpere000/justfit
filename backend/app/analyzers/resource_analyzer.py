"""Resource Analyzer - Tidal Detection and combined resource analysis orchestration."""

import structlog
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from app.models import VMMetric


logger = structlog.get_logger()


class TidalDetector:
    """潮汐检测器 - 只输出具有潮汐特征的 VM，支持周/月粒度分析（基于天级数据）。"""

    def __init__(
        self,
        cv_threshold: float = 0.4,
        peak_valley_ratio_threshold: float = 2.5,
        min_samples: int = 24,
    ) -> None:
        self.cv_threshold = cv_threshold
        self.peak_valley_ratio_threshold = peak_valley_ratio_threshold
        self.min_samples = min_samples

    def _convert_cpu_to_percentage(
        self,
        cpu_metrics: List[VMMetric],
        cpu_count: int,
        host_cpu_mhz: int,
    ) -> List[float]:
        """将 CPU 指标从存储值（MHz）转换为百分比。"""
        if not cpu_metrics:
            return []

        effective_host_mhz = host_cpu_mhz if host_cpu_mhz > 0 else 2600
        effective_cpu_count = cpu_count if cpu_count > 0 else 1

        result = []
        for metric in cpu_metrics:
            percentage = (metric.value / effective_cpu_count / effective_host_mhz) * 100
            result.append(round(percentage, 2))

        return result

    async def analyze(
        self,
        task_id: int,
        vm_metrics: Dict[int, List[VMMetric]],
        vm_data: Dict[int, Dict],
    ) -> List[Dict]:
        """分析所有VM，输出具有潮汐特征的VM列表。天级数据支持周/月粒度。"""
        results = []
        for vm_id, metrics in vm_metrics.items():
            if not metrics:
                continue
            vm_info = vm_data.get(vm_id, {})
            result = await self._analyze_vm(vm_id, metrics, vm_info)
            if result is not None:
                results.append(result)

        logger.info(
            "tidal_analysis_completed",
            task_id=task_id,
            total_vms=len(vm_metrics),
            tidal_count=len(results),
        )
        return results

    async def _analyze_vm(
        self,
        vm_id: int,
        metrics: List[VMMetric],
        vm_info: Dict,
    ) -> Optional[Dict[str, Any]]:
        """分析单台 VM，若非潮汐返回 None。"""
        vm_name = vm_info.get("name", f"VM-{vm_id}")
        cluster = vm_info.get("cluster", "")
        host_ip = vm_info.get("host_ip", "")
        cpu_count = vm_info.get("cpu_count", 0)
        host_cpu_mhz = vm_info.get("host_cpu_mhz", 0)

        cpu_metrics = [m for m in metrics if m.metric_type == "cpu"]
        cpu_values_pct = self._convert_cpu_to_percentage(cpu_metrics, cpu_count, host_cpu_mhz)

        # 天级数据：周粒度分析需要覆盖完整一周（至少7个点）
        effective_min_samples = 7
        if len(cpu_values_pct) < effective_min_samples:
            return None

        mean_cpu = statistics.mean(cpu_values_pct)
        cv = 0.0
        if mean_cpu > 0 and len(cpu_values_pct) > 1:
            std_cpu = statistics.stdev(cpu_values_pct)
            cv = std_cpu / mean_cpu

        max_cpu = max(cpu_values_pct)
        min_cpu = min(cpu_values_pct)

        if min_cpu < 0.5:
            peak_valley_ratio = max_cpu / 0.5
        else:
            peak_valley_ratio = max_cpu / min_cpu
        peak_valley_ratio = min(peak_valley_ratio, 100.0)

        # 判断是否为潮汐：CV 和峰谷比都超过阈值
        is_tidal = (
            cv > self.cv_threshold * 1.25
            and peak_valley_ratio > self.peak_valley_ratio_threshold * 1.2
        )

        if not is_tidal:
            return None

        # 分析潮汐粒度（日/周/月）
        tidal_details, granularity, recommended_off_hours = self._analyze_tidal_granularity(
            cpu_metrics, cpu_values_pct
        )

        reason = self._build_reason(
            cv, peak_valley_ratio, mean_cpu, max_cpu, min_cpu,
            granularity, tidal_details, recommended_off_hours,
            len(cpu_values_pct),
        )

        return {
            "vmName": vm_name,
            "cluster": cluster,
            "hostIp": host_ip,
            "usagePattern": "tidal",
            "volatilityLevel": "high" if cv > self.cv_threshold * 1.5 else "moderate",
            "coefficientOfVariation": round(cv, 3),
            "peakValleyRatio": round(peak_valley_ratio, 3),
            "tidalGranularity": granularity,
            "tidalDetails": tidal_details,
            "recommendedOffHours": recommended_off_hours,
            "reason": reason,
        }

    def _analyze_tidal_granularity(
        self,
        cpu_metrics: List[VMMetric],
        cpu_values_pct: List[float],
    ) -> tuple[Dict[str, Any], str, Dict[str, str]]:
        """分析潮汐的时间粒度（周/月），返回 (details, granularity, recommended_off_hours)。

        天级数据不支持日粒度（无小时分布），只支持周粒度（≥7天）和月粒度（≥30天）。
        """
        if not cpu_metrics or not cpu_values_pct:
            return {}, "weekly", {"type": "weekly", "description": "暂无法确定"}

        weekday_avg: Dict[int, List[float]] = {}  # 0=周一 ~ 6=周日
        monthly_avg: Dict[int, List[float]] = {}  # 1~31 日

        for i, m in enumerate(cpu_metrics):
            if i >= len(cpu_values_pct):
                break
            ts = m.timestamp
            if ts.tzinfo is None:
                local_weekday = ts.weekday()
                local_day = ts.day
            else:
                from datetime import timezone
                local_ts = ts.astimezone(timezone(timedelta(hours=8)))
                local_weekday = local_ts.weekday()
                local_day = local_ts.day

            val = cpu_values_pct[i]
            weekday_avg.setdefault(local_weekday, []).append(val)
            monthly_avg.setdefault(local_day, []).append(val)

        weekday_means = {d: statistics.mean(v) for d, v in weekday_avg.items()}
        monthly_means = {d: statistics.mean(v) for d, v in monthly_avg.items()}

        # 周粒度：工作日 vs 周末（需要至少7天覆盖完整一周）
        workday_list = [weekday_means.get(d, 0) for d in range(5)]
        weekend_list = [weekday_means.get(d, 0) for d in range(5, 7)]
        workday_val = statistics.mean(workday_list) if workday_list else 0
        weekend_val = statistics.mean(weekend_list) if weekend_list else 0

        # 月粒度：需要至少30天数据
        monthly_cv = 0.0
        if len(monthly_means) >= 14:
            all_monthly = list(monthly_means.values())
            monthly_cv = statistics.stdev(all_monthly) / statistics.mean(all_monthly) if statistics.mean(all_monthly) > 0 else 0

        # 周粒度优先（需至少覆盖5种星期几 且 有周末数据）
        weekly_ratio = workday_val / weekend_val if weekend_val > 0.5 else workday_val / 0.5
        has_weekly_data = len(weekday_means) >= 5 and len([d for d in range(5, 7) if d in weekday_means]) > 0

        if has_weekly_data and weekly_ratio >= 2.0:
            granularity = "weekly"
            overall = statistics.mean(list(weekday_means.values()))
            low_days = [d for d, v in weekday_means.items() if v < overall * 0.5]
            day_names = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
            if low_days:
                off_desc = "、".join(day_names[d] for d in sorted(low_days))
            else:
                off_desc = "周六、周日"
            recommended_off_hours = {"type": "weekly", "description": off_desc}
            tidal_details = {
                "patternType": "weekday_active",
                "workdayAvg": round(workday_val, 2),
                "weekendAvg": round(weekend_val, 2),
                "weekdayAvg": {str(d): round(v, 2) for d, v in sorted(weekday_means.items())},
            }
        elif monthly_cv >= 0.4 and len(monthly_means) >= 14:
            granularity = "monthly"
            overall = statistics.mean(list(monthly_means.values()))
            low_dates = sorted([d for d, v in monthly_means.items() if v < overall * 0.5])

            # 月初/月中/月末均值
            early_month = [monthly_means.get(d, 0) for d in range(1, 8)]
            mid_month = [monthly_means.get(d, 0) for d in range(8, 23)]
            late_month = [monthly_means.get(d, 0) for d in range(23, 32)]
            early_val = statistics.mean(early_month) if early_month else 0
            mid_val = statistics.mean(mid_month) if mid_month else 0
            late_val = statistics.mean(late_month) if late_month else 0

            if low_dates:
                if len(low_dates) >= 3:
                    off_desc = f"每月 {low_dates[0]}~{low_dates[-1]} 日"
                else:
                    off_desc = "每月 " + "、".join(f"{d} 日" for d in low_dates)
            else:
                peak_date = max(monthly_means, key=lambda k: monthly_means[k])
                if peak_date <= 10:
                    off_desc = "每月 15~25 日（月中低谷）"
                elif peak_date >= 20:
                    off_desc = "每月 5~15 日（月中低谷）"
                else:
                    off_desc = "每月月初或月末"
            recommended_off_hours = {"type": "monthly", "description": off_desc}
            tidal_details = {
                "patternType": "monthly_peak",
                "earlyMonthAvg": round(early_val, 2),
                "midMonthAvg": round(mid_val, 2),
                "lateMonthAvg": round(late_val, 2),
                "monthlyAvg": {str(d): round(v, 2) for d, v in sorted(monthly_means.items())},
            }
        else:
            # 数据不足以判断明确粒度，不携带具体均值字段，避免输出误导性的 0.0
            granularity = "weekly"
            recommended_off_hours = {"type": "weekly", "description": "周末（数据不足，建议补充采集）"}
            tidal_details = {
                "patternType": "insufficient_data",
            }

        return tidal_details, granularity, recommended_off_hours

    def _build_reason(
        self,
        cv: float,
        peak_valley_ratio: float,
        mean_cpu: float,
        max_cpu: float,
        min_cpu: float,
        granularity: str,
        tidal_details: Dict[str, Any],
        recommended_off_hours: Dict[str, str],
        sample_count: int,
    ) -> str:
        """生成潮汐检测的判断依据。"""
        parts = []

        parts.append(
            f"基于 {sample_count} 个采样点分析：变异系数 CV={cv:.2f}（阈值 {self.cv_threshold * 1.25:.2f}），"
            f"峰谷比={peak_valley_ratio:.1f}（阈值 {self.peak_valley_ratio_threshold * 1.2:.1f}），"
            f"CPU 均值={mean_cpu:.1f}%、峰值={max_cpu:.1f}%、谷值={min_cpu:.1f}%"
        )

        if granularity == "weekly":
            if tidal_details.get("patternType") == "insufficient_data":
                parts.append("使用规律有明显波动，数据不足以确定具体粒度，建议补充采集后重新分析")
            else:
                workday = tidal_details.get("workdayAvg", 0)
                weekend = tidal_details.get("weekendAvg", 0)
                parts.append(
                    f"呈现周粒度潮汐：工作日均值 {workday:.1f}%，周末均值 {weekend:.1f}%，"
                    f"落差 {workday - weekend:.1f}%"
                )
        elif granularity == "monthly":
            early = tidal_details.get("earlyMonthAvg", 0)
            mid = tidal_details.get("midMonthAvg", 0)
            late = tidal_details.get("lateMonthAvg", 0)
            parts.append(
                f"呈现月粒度潮汐：月初均值 {early:.1f}%、月中 {mid:.1f}%、月末 {late:.1f}%"
            )
        else:
            parts.append("使用规律有明显波动，建议结合业务场景进行评估")

        off_desc = recommended_off_hours.get("description", "")
        parts.append(f"推荐在 {off_desc} 关机或降低资源配置以节省成本")

        return "；".join(parts)


class ResourceAnalyzer:
    """主资源分析器 - 组合 RightSizeAnalyzer（含 mismatch）和 TidalDetector 并行执行。"""

    def __init__(
        self,
        mode: str = "saving",
        right_size_config: Optional[Dict[str, Any]] = None,
        usage_pattern_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.mode = mode

        from app.analyzers.rightsize import RightSizeAnalyzer
        from app.analyzers.modes import AnalysisModes

        mode_config = AnalysisModes.get_mode(mode)
        rightsize_mode_config = mode_config.get("resource", {}).get("rightsize", {})

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

        self.tidal_detector = TidalDetector(
            cv_threshold=usage_pattern_config.get("cv_threshold", 0.4)
            if usage_pattern_config
            else 0.4,
            peak_valley_ratio_threshold=usage_pattern_config.get("peak_valley_ratio", 2.5)
            if usage_pattern_config
            else 2.5,
        )

    async def analyze(
        self,
        task_id: int,
        vm_metrics: Dict[int, List[VMMetric]],
        vm_data: Dict[int, Dict],
    ) -> Dict[str, Any]:
        """并行执行资源优化和潮汐检测分析。"""
        import asyncio

        resource_optimization_results, tidal_results = await asyncio.gather(
            self.right_size_analyzer.analyze(task_id, vm_metrics, vm_data),
            self.tidal_detector.analyze(task_id, vm_metrics, vm_data),
        )

        return {
            "resourceOptimization": resource_optimization_results,
            "tidal": tidal_results,
            "summary": {
                "resourceOptimizationCount": len(resource_optimization_results),
                "tidalCount": len(tidal_results),
                "totalVmsAnalyzed": len(vm_metrics),
            },
        }
