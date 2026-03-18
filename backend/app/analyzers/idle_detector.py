"""Idle Detector - Detects idle and powered off VMs."""

import structlog
import statistics
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Union
from enum import Enum
from dataclasses import dataclass

from app.models import VMMetric


@dataclass
class MetricValue:
    """简单的指标值容器，用于存储转换后的百分比。"""
    task_id: int
    vm_id: int
    metric_type: str
    value: float
    timestamp: datetime


# 支持两种指标类型的类型别名
MetricType = Union[VMMetric, MetricValue]


logger = structlog.get_logger()


class IdleSubType(str, Enum):
    """Idle detection sub-types."""

    POWERED_OFF = "powered_off"
    IDLE_POWERED_ON = "idle_powered_on"
    LOW_ACTIVITY = "low_activity"


class IdleDetector:
    """Analyzer for detecting idle and powered off VMs."""

    # 关机天数阈值
    CRITICAL_ZOMBIE_DAYS = 90
    HIGH_ZOMBIE_DAYS = 30
    MEDIUM_ZOMBIE_DAYS = 14

    # 新VM观察期（天）
    NEW_VM_OBSERVATION_DAYS = 7

    # 模板VM关键词
    TEMPLATE_KEYWORDS = ["-template", "-tmpl", "_template", "_tmpl"]

    # 测试VM关键词
    TEST_KEYWORDS = ["test", "demo", "poc", "dev", "-t-"]

    def __init__(
        self,
        days_threshold: int = 14,
        cpu_threshold: float = 10.0,
        memory_threshold: float = 20.0,
        min_confidence: float = 60.0,
    ) -> None:
        """Initialize idle detector.

        Args:
            days_threshold: Days to consider for analysis (default 14)
            cpu_threshold: CPU usage threshold % (default 10%)
            memory_threshold: Memory usage threshold % (default 20%)
            min_confidence: Minimum confidence score (0-100)
        """
        self.days_threshold = days_threshold
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.min_confidence = min_confidence

    async def analyze(
        self,
        task_id: int,
        vm_metrics: Dict[int, List[VMMetric]],
        vm_data: Dict[int, Dict],
    ) -> List[Dict]:
        """Analyze VMs for idle status.

        Args:
            task_id: Task ID
            vm_metrics: Dict mapping vm_id to list of metrics
            vm_data: Dict mapping vm_id to VM info

        Returns:
            List of idle VM findings
        """
        findings = []
        powered_off_count = 0
        no_downtime_data_count = 0

        for vm_id, vm_info in vm_data.items():
            vm_name = vm_info.get("name", "")
            power_state = vm_info.get("power_state", "")
            downtime_duration = vm_info.get("downtime_duration")
            vm_create_time = vm_info.get("vm_create_time")

            # 调试日志：记录每个VM的状态
            logger.debug(
                "vm_analysis_check",
                task_id=task_id,
                vm_id=vm_id,
                vm_name=vm_name,
                power_state=power_state,
                downtime_duration=downtime_duration,
                vm_create_time=str(vm_create_time) if vm_create_time else None,
            )

            # 首先检测关机型僵尸
            if self._is_powered_off(vm_info):
                powered_off_count += 1
                result = await self._detect_powered_off_zombie(vm_id, vm_info)
                if result and result["confidence"] >= self.min_confidence:
                    findings.append(result)
                else:
                    # 记录为什么没有检测到
                    if downtime_duration is None and vm_create_time is None:
                        no_downtime_data_count += 1
                        logger.debug(
                            "powered_off_vm_no_data",
                            task_id=task_id,
                            vm_id=vm_id,
                            vm_name=vm_name,
                            reason="downtime_duration and vm_create_time are both None",
                        )
                    elif result is None:
                        logger.debug(
                            "powered_off_vm_not_detected",
                            task_id=task_id,
                            vm_id=vm_id,
                            vm_name=vm_name,
                            downtime_duration=downtime_duration,
                            reason=f"Below detection threshold ({min(self.MEDIUM_ZOMBIE_DAYS, self.days_threshold)} days)",
                        )
                    else:
                        logger.debug(
                            "powered_off_vm_low_confidence",
                            task_id=task_id,
                            vm_id=vm_id,
                            vm_name=vm_name,
                            confidence=result.get("confidence"),
                            min_confidence=self.min_confidence,
                        )
                continue

            # 开机VM检测闲置
            metrics = vm_metrics.get(vm_id, [])
            if metrics:
                result = await self._detect_idle_powered_on(vm_id, metrics, vm_info)
                if result and result["confidence"] >= self.min_confidence:
                    findings.append(result)

        logger.info(
            "idle_detection_completed",
            task_id=task_id,
            total_vms=len(vm_data),
            powered_off_count=powered_off_count,
            no_downtime_data_count=no_downtime_data_count,
            idle_count=len(findings),
        )

        return findings

    def _is_powered_off(self, vm_info: Dict) -> bool:
        """Check if VM is powered off.

        支持多种 power_state 格式：
        - vCenter: "poweredOff", "powered on"
        - UIS: "off", "on"
        - 其他变体
        """
        power_state = vm_info.get("power_state", "").lower().replace(" ", "").replace("_", "")
        # 支持多种关机状态表示
        return power_state in ["poweredoff", "off", "shutdown", "suspended"]

    async def _detect_powered_off_zombie(
        self, vm_id: int, vm_info: Dict
    ) -> Optional[Dict[str, Any]]:
        """Detect powered off zombie VM.

        Args:
            vm_id: VM ID
            vm_info: VM info dict

        Returns:
            Detection result or None
        """
        vm_name = vm_info.get("name", "")

        # 排除模板VM
        if self._is_template_vm(vm_name):
            return None

        # 获取时间信息
        downtime_duration = vm_info.get("downtime_duration")
        vm_create_time = vm_info.get("vm_create_time")

        # 计算关机天数
        days_inactive = None
        reference_time = None

        if downtime_duration is not None and downtime_duration > 0:
            # 直接使用 downtime_duration（秒）
            days_inactive = downtime_duration / 86400
            reference_time = vm_create_time
        elif vm_create_time:
            # 备用方案：使用 VM 创建时间
            current_time = datetime.now(timezone.utc)
            if vm_create_time.tzinfo is None:
                vm_create_time = vm_create_time.replace(tzinfo=timezone.utc)
            days_inactive = (current_time - vm_create_time).days
            reference_time = vm_create_time

            # 新创建VM给予观察期
            if days_inactive < self.NEW_VM_OBSERVATION_DAYS:
                return None
        else:
            return None  # 无时间信息，无法判断

        if days_inactive is None:
            return None

        # 判断僵尸级别（最低门槛取 days_threshold 和 MEDIUM_ZOMBIE_DAYS 的较小值）
        effective_medium_days = min(self.MEDIUM_ZOMBIE_DAYS, self.days_threshold)
        if days_inactive >= self.CRITICAL_ZOMBIE_DAYS:
            confidence = 95
            risk_level = "critical"
            recommendation = f"VM已关机≥{days_inactive:.0f}天，建议归档或删除"
        elif days_inactive >= self.HIGH_ZOMBIE_DAYS:
            confidence = 85
            risk_level = "high"
            recommendation = f"VM已关机≥{days_inactive:.0f}天，建议联系负责人确认后处理"
        elif days_inactive >= effective_medium_days:
            confidence = 70
            risk_level = "medium"
            recommendation = f"VM已关机≥{days_inactive:.0f}天，建议确认是否仍需要"
        else:
            return None  # 关机时间较短

        # 测试VM降低置信度
        if self._is_test_vm(vm_name):
            confidence = max(0, confidence - 20)
            risk_level = self._get_risk_level(confidence)

        return {
            "vmName": vm_name,
            "vmId": vm_id,
            "cluster": vm_info.get("cluster", ""),
            "hostIp": vm_info.get("host_ip", ""),
            "cpuCores": vm_info.get("cpu_count", 0),
            "memoryGb": round(vm_info.get("memory_bytes", 0) / (1024**3), 2),
            "diskUsageGb": round(vm_info.get("disk_usage_bytes", 0) / (1024**3), 2),
            "isIdle": True,
            "idleType": IdleSubType.POWERED_OFF.value,
            "confidence": confidence,
            "riskLevel": risk_level,
            "daysInactive": int(days_inactive),
            "lastActivityTime": reference_time.isoformat() if reference_time else None,
            "downtimeDuration": int(days_inactive * 86400) if days_inactive else None,
            "recommendation": recommendation,
            "details": {
                "powerState": vm_info.get("power_state", ""),
                "daysAnalyzed": self.days_threshold,
            },
        }

    async def _detect_idle_powered_on(
        self, vm_id: int, metrics: List[VMMetric], vm_info: Dict
    ) -> Optional[Dict[str, Any]]:
        """Detect idle powered on VM.

        数据库中存储的是绝对值（CPU 为 MHz，内存为 bytes），需要转换为百分比后再判断。

        Args:
            vm_id: VM ID
            metrics: List of VM metrics
            vm_info: VM info dict (必须包含 cpu_count, memory_bytes, host_cpu_mhz)

        Returns:
            Detection result or None
        """
        if not metrics:
            return None

        vm_name = vm_info.get("name", "")

        # 获取 VM 配置信息（用于百分比转换）
        cpu_count = vm_info.get("cpu_count", 0)
        memory_bytes = vm_info.get("memory_bytes", 0)
        host_cpu_mhz = vm_info.get("host_cpu_mhz", 0)

        # 分组指标
        metrics_by_type = self._group_metrics_by_type(metrics)

        # 将绝对值转换为百分比
        cpu_metrics_pct = self._convert_cpu_to_percentage(
            metrics_by_type.get("cpu", []), cpu_count, host_cpu_mhz
        )
        memory_metrics_pct = self._convert_memory_to_percentage(
            metrics_by_type.get("memory", []), memory_bytes
        )

        # 计算百分位数（使用转换后的百分比）
        cpu_stats = self._calculate_percentiles(cpu_metrics_pct)
        memory_stats = self._calculate_percentiles(memory_metrics_pct)
        disk_stats = self._calculate_percentiles(
            metrics_by_type.get("disk_read", []) + metrics_by_type.get("disk_write", [])
        )
        network_stats = self._calculate_percentiles(
            metrics_by_type.get("net_rx", []) + metrics_by_type.get("net_tx", [])
        )

        # 计算活跃度分数（使用百分比）
        activity_score = self._calculate_activity_score(
            cpu_stats["p95"],
            memory_stats["p95"],
            disk_stats["p95"],
            network_stats["p95"],
        )

        # 计算波动性（使用百分比）
        cpu_values_pct = [m.value for m in cpu_metrics_pct]
        volatility = self._calculate_volatility(cpu_values_pct)

        # 判断是否闲置
        if activity_score >= 30:
            return None  # 正常VM

        # 确定闲置类型和置信度
        if activity_score < 15:
            if volatility < 0.3:
                confidence = min(100, 100 - activity_score + 15)
            else:
                confidence = min(100, 100 - activity_score)
            idle_type = IdleSubType.IDLE_POWERED_ON.value
        else:  # 15 <= activity_score < 30
            confidence = min(100, 100 - activity_score)
            idle_type = IdleSubType.LOW_ACTIVITY.value

        risk_level = self._get_risk_level(confidence)
        data_quality = self._assess_data_quality(metrics_by_type)

        # 生成建议（使用百分比）
        recommendation = self._generate_recommendation(
            idle_type, cpu_stats["p95"], memory_stats["p95"], activity_score
        )

        uptime_duration = vm_info.get("uptime_duration")
        days_inactive = self.days_threshold  # 分析窗口内持续低活跃

        return {
            "vmName": vm_name,
            "vmId": vm_id,
            "cluster": vm_info.get("cluster", ""),
            "hostIp": vm_info.get("host_ip", ""),
            "cpuCores": vm_info.get("cpu_count", 0),
            "memoryGb": round(vm_info.get("memory_bytes", 0) / (1024**3), 2),
            "diskUsageGb": round(vm_info.get("disk_usage_bytes", 0) / (1024**3), 2),
            "uptimeDuration": uptime_duration,
            "daysInactive": days_inactive,
            "lastActivityTime": None,
            "isIdle": True,
            "idleType": idle_type,
            "confidence": confidence,
            "riskLevel": risk_level,
            "activityScore": activity_score,
            "cpuUsageP95": round(cpu_stats["p95"], 2),  # 百分比
            "memoryUsageP95": round(memory_stats["p95"], 2),  # 百分比
            "diskIoP95": round(disk_stats["p95"], 2),
            "networkP95": round(network_stats["p95"], 2),
            "dataQuality": data_quality,
            "recommendation": recommendation,
            "details": {
                "powerState": vm_info.get("power_state", ""),
                "volatility": round(volatility, 3),
                "daysAnalyzed": self.days_threshold,
                "cpuSamples": len(cpu_metrics_pct),
                "memorySamples": len(memory_metrics_pct),
            },
        }

    def _convert_cpu_to_percentage(
        self,
        cpu_metrics: List[VMMetric],
        cpu_count: int,
        host_cpu_mhz: int,
    ) -> List[MetricValue]:
        """将 CPU 指标从存储值转换为百分比。

        vCenter/UIS 存储：percentage / 100 * cpu_count * host_cpu_mhz
        还原百分比：stored_value / cpu_count / host_cpu_mhz * 100

        Args:
            cpu_metrics: CPU 指标列表（存储的 MHz 值）
            cpu_count: CPU 核心数
            host_cpu_mhz: 主机 CPU 单核频率 (MHz)

        Returns:
            转换后的 CPU 指标列表（值为百分比）
        """
        if not cpu_metrics:
            return []

        # 使用 host_cpu_mhz，如果为 0 则使用估算值
        effective_host_mhz = host_cpu_mhz if host_cpu_mhz > 0 else 2600
        effective_cpu_count = cpu_count if cpu_count > 0 else 1

        if effective_host_mhz == 0:
            return [MetricValue(
                task_id=m.task_id,
                vm_id=m.vm_id,
                metric_type=m.metric_type,
                value=m.value,
                timestamp=m.timestamp,
            ) for m in cpu_metrics]

        result = []
        for metric in cpu_metrics:
            # 还原百分比：stored_value / cpu_count / host_cpu_mhz * 100
            percentage = (metric.value / effective_cpu_count / effective_host_mhz) * 100
            result.append(MetricValue(
                task_id=metric.task_id,
                vm_id=metric.vm_id,
                metric_type=metric.metric_type,
                value=round(percentage, 2),
                timestamp=metric.timestamp,
            ))

        return result

    def _convert_memory_to_percentage(
        self,
        memory_metrics: List[VMMetric],
        memory_bytes: int,
    ) -> List[MetricValue]:
        """将内存指标从存储单位转换为百分比。

        数据库存储：bytes（绝对值）
        还原百分比：metric.value / memory_bytes * 100

        Args:
            memory_metrics: 内存指标列表（数据库存储为 bytes）
            memory_bytes: VM 总内存（bytes）

        Returns:
            转换后的内存指标列表（值为百分比）
        """
        if not memory_metrics or memory_bytes == 0:
            return [MetricValue(
                task_id=m.task_id,
                vm_id=m.vm_id,
                metric_type=m.metric_type,
                value=m.value,
                timestamp=m.timestamp,
            ) for m in memory_metrics] if memory_metrics else []

        result = []
        for metric in memory_metrics:
            # 将 bytes 存储值转换为百分比
            percentage = (metric.value / memory_bytes) * 100
            result.append(MetricValue(
                task_id=metric.task_id,
                vm_id=metric.vm_id,
                metric_type=metric.metric_type,
                value=round(percentage, 2),
                timestamp=metric.timestamp,
            ))

        return result

    def _calculate_activity_score(
        self,
        cpu_p95: float,
        memory_p95: float,
        disk_p95: float,
        network_p95: float,
    ) -> int:
        """Calculate activity score (0-100, higher is more active) using configured thresholds.

        Args:
            cpu_p95: CPU usage P95 percentile
            memory_p95: Memory usage P95 percentile
            disk_p95: Disk I/O P95 value
            network_p95: Network P95 value

        Returns:
            Activity score 0-100
        """
        score = 0

        # CPU (40分) - 使用配置的 cpu_threshold
        cpu_threshold = self.cpu_threshold
        if cpu_p95 >= cpu_threshold * 5:
            score += 40
        elif cpu_p95 >= cpu_threshold * 2:
            score += 20
        elif cpu_p95 >= cpu_threshold:
            score += 10

        # 内存 (30分) - 使用配置的 memory_threshold
        memory_threshold = self.memory_threshold
        if memory_p95 >= memory_threshold * 2:
            score += 30
        elif memory_p95 >= memory_threshold * 1.5:
            score += 15
        elif memory_p95 >= memory_threshold:
            score += 5

        # 磁盘 I/O (15分) - 保持固定阈值
        if disk_p95 >= 100:
            score += 15
        elif disk_p95 >= 50:
            score += 10
        elif disk_p95 >= 10:
            score += 5

        # 网络 (15分) - 保持固定阈值
        if network_p95 >= 100:
            score += 15
        elif network_p95 >= 50:
            score += 10
        elif network_p95 >= 10:
            score += 5

        return score

    def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate volatility (coefficient of variation).

        Args:
            values: List of numeric values

        Returns:
            Coefficient of variation (std/mean)
        """
        if len(values) < 2:
            return 0.0
        mean_val = statistics.mean(values)
        if mean_val == 0:
            return 0.0
        return statistics.stdev(values) / mean_val

    def _calculate_percentiles(self, metrics: List[MetricType]) -> Dict[str, float]:
        """Calculate percentile statistics for metrics.

        Args:
            metrics: List of VMMetric or MetricValue objects

        Returns:
            Dict with p50, p95, p99, min, max, avg
        """
        if not metrics:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "min": 0.0, "max": 0.0, "avg": 0.0}

        values = sorted([m.value for m in metrics])
        n = len(values)

        return {
            "p50": values[int(n * 0.5)] if n > 1 else values[0],
            "p95": values[min(int(n * 0.95), n - 1)],
            "p99": values[min(int(n * 0.99), n - 1)],
            "min": values[0],
            "max": values[-1],
            "avg": sum(values) / n,
        }

    def _group_metrics_by_type(self, metrics: List[MetricType]) -> Dict[str, List[MetricType]]:
        """Group metrics by type.

        Args:
            metrics: List of VMMetric objects

        Returns:
            Dict mapping metric_type to list of metrics
        """
        grouped: Dict[str, List[VMMetric]] = {}
        for metric in metrics:
            metric_type = metric.metric_type
            if metric_type not in grouped:
                grouped[metric_type] = []
            grouped[metric_type].append(metric)
        return grouped

    def _assess_data_quality(self, metrics_by_type: Dict[str, List[VMMetric]]) -> str:
        """Assess data quality based on sample count and coverage.

        Args:
            metrics_by_type: Grouped metrics

        Returns:
            Data quality level: 'high', 'medium', 'low'
        """
        total_samples = sum(len(v) for v in metrics_by_type.values())

        # 根据实际点数推断粒度：若总点数 ≤ days_threshold * 类型数 * 2，认为是天级数据
        metric_type_count = len([v for v in metrics_by_type.values() if v])
        if metric_type_count == 0:
            return "low"
        avg_samples_per_type = total_samples / metric_type_count
        if avg_samples_per_type <= self.days_threshold * 2:
            # 天级粒度：每天1个点
            expected_samples = self.days_threshold * metric_type_count
        else:
            # 20秒粒度：每小时180个点
            expected_samples = self.days_threshold * 24 * 180

        if expected_samples <= 0:
            return "low"

        coverage = total_samples / expected_samples

        if coverage >= 0.8:
            return "high"
        elif coverage >= 0.5:
            return "medium"
        else:
            return "low"

    def _get_risk_level(self, confidence: float) -> str:
        """Get risk level based on confidence score.

        Args:
            confidence: Confidence score 0-100

        Returns:
            Risk level: 'critical', 'high', 'medium', 'low'
        """
        if confidence >= 90:
            return "critical"
        elif confidence >= 75:
            return "high"
        elif confidence >= 50:
            return "medium"
        else:
            return "low"

    def _is_template_vm(self, vm_name: str) -> bool:
        """Check if VM is a template.

        Args:
            vm_name: VM name

        Returns:
            True if VM is a template
        """
        vm_name_lower = vm_name.lower()
        return any(kw in vm_name_lower for kw in self.TEMPLATE_KEYWORDS)

    def _is_test_vm(self, vm_name: str) -> bool:
        """Check if VM is a test VM.

        Args:
            vm_name: VM name

        Returns:
            True if VM is a test VM
        """
        vm_name_lower = vm_name.lower()
        return any(kw in vm_name_lower for kw in self.TEST_KEYWORDS)

    def _generate_recommendation(
        self, idle_type: str, cpu_p95: float, memory_p95: float, activity_score: int
    ) -> str:
        """Generate recommendation based on idle type and metrics.

        Args:
            idle_type: Type of idle detection
            cpu_p95: CPU usage P95
            memory_p95: Memory usage P95
            activity_score: Activity score

        Returns:
            Recommendation text
        """
        if idle_type == IdleSubType.IDLE_POWERED_ON.value:
            return f"VM完全闲置（P95 CPU {cpu_p95:.1f}%，内存 {memory_p95:.1f}%），建议关闭或降配"
        elif idle_type == IdleSubType.LOW_ACTIVITY.value:
            return f"VM低活跃（活动分{activity_score}），建议观察或降配"
        else:
            return "VM使用率较低，建议评估是否需要保留"
