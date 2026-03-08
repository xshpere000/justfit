"""Zombie VM Analyzer - Detects unused/underutilized VMs."""

import structlog
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from app.models import VMMetric


logger = structlog.get_logger()


class ZombieAnalyzer:
    """Analyzer for detecting zombie (unused/underutilized) VMs."""

    def __init__(
        self,
        days_threshold: int = 30,
        cpu_threshold: float = 10.0,
        memory_threshold: float = 20.0,
        disk_io_threshold: float = 5.0,
        network_threshold: float = 5.0,
        min_confidence: float = 70.0,
    ) -> None:
        """Initialize zombie analyzer.

        Args:
            days_threshold: Days to consider for analysis (default 30)
            cpu_threshold: CPU usage threshold % (default 10%)
            memory_threshold: Memory usage threshold % (default 20%)
            disk_io_threshold: Disk I/O threshold % (default 5%)
            network_threshold: Network traffic threshold % (default 5%)
            min_confidence: Minimum confidence score (0-100)
        """
        self.days_threshold = days_threshold
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_io_threshold = disk_io_threshold
        self.network_threshold = network_threshold
        self.min_confidence = min_confidence

    async def analyze(
        self,
        task_id: int,
        vm_metrics: Dict[int, List[VMMetric]],
        vm_data: Dict[int, Dict],
    ) -> List[Dict]:
        """Analyze VMs for zombie status.

        Args:
            task_id: Task ID
            vm_metrics: Dict mapping vm_id to list of metrics
            vm_data: Dict mapping vm_id to VM info

        Returns:
            List of zombie VM findings
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
            "zombie_analysis_completed",
            task_id=task_id,
            total_vms=len(vm_metrics),
            zombie_count=len(findings),
        )

        return findings

    async def _analyze_vm(
        self,
        vm_id: int,
        metrics: List[VMMetric],
        vm_info: Dict,
    ) -> Dict[str, Any]:
        """Analyze single VM.

        Args:
            vm_id: VM ID
            metrics: List of metrics
            vm_info: VM info

        Returns:
            Zombie analysis result
        """
        vm_name = vm_info.get("name", f"VM-{vm_id}")
        host_ip = vm_info.get("host_ip", "")
        cluster = vm_info.get("cluster", "")

        # Calculate averages
        cpu_avg = self._avg_metric(metrics, "cpu") or 0
        memory_avg = self._avg_metric(metrics, "memory") or 0
        disk_io_avg = (self._avg_metric(metrics, "disk_read") or 0) + (self._avg_metric(metrics, "disk_write") or 0)
        network_avg = (self._avg_metric(metrics, "net_rx") or 0) + (self._avg_metric(metrics, "net_tx") or 0)

        # Calculate sample counts
        cpu_samples = self._count_samples(metrics, "cpu")
        memory_samples = self._count_samples(metrics, "memory")
        total_samples = cpu_samples + memory_samples

        # Calculate confidence score
        confidence = 0

        # CPU score (max 40)
        if cpu_avg < 5:
            confidence += 40
        elif cpu_avg < 10:
            confidence += 30
        elif cpu_avg < 20:
            confidence += 10

        # Memory score (max 30)
        if memory_avg < 10:
            confidence += 30
        elif memory_avg < 20:
            confidence += 20
        elif memory_avg < 30:
            confidence += 10

        # Disk I/O score (max 15)
        if disk_io_avg < 10:
            confidence += 15
        elif disk_io_avg < 50:
            confidence += 5

        # Network score (max 15)
        if network_avg < 10:
            confidence += 15
        elif network_avg < 50:
            confidence += 5

        # Low usage days bonus (max 10)
        if total_samples > 0:
            low_usage_ratio = total_samples / (self.days_threshold * 288)  # Assuming 5-min intervals
            if low_usage_ratio > 0.8:
                confidence += 10
            elif low_usage_ratio > 0.5:
                confidence += 5

        # Normalize to 0-100
        confidence = min(100, confidence)

        # Determine severity
        if confidence >= 90:
            severity = "critical"
        elif confidence >= 75:
            severity = "high"
        elif confidence >= 50:
            severity = "medium"
        else:
            severity = "low"

        # Generate recommendation
        recommendation = self._generate_recommendation(
            cpu_avg, memory_avg, confidence
        )

        return {
            "vmName": vm_name,
            "datacenter": cluster,  # 前端期望 datacenter 字段
            "cluster": cluster,  # 保留 cluster 以兼容
            "hostIp": host_ip,
            "cpuCores": vm_info.get("cpu_count", 0),
            "memoryGb": round(vm_info.get("memory_bytes", 0) / (1024**3), 2),
            "cpuUsage": round(cpu_avg, 2),
            "memoryUsage": round(memory_avg, 2),
            "diskIoUsage": round(disk_io_avg, 2),
            "networkUsage": round(network_avg, 2),
            "confidence": confidence,
            "severity": severity,
            "recommendation": recommendation,
            "details": {
                "daysAnalyzed": self.days_threshold,
                "cpuSamples": cpu_samples,
                "memorySamples": memory_samples,
                "totalSamples": total_samples,
            },
        }

    def _avg_metric(self, metrics: List[VMMetric], metric_type: str) -> Optional[float]:
        """Calculate average value for metric type."""
        values = [
            m.value
            for m in metrics
            if m.metric_type == metric_type
        ]
        return sum(values) / len(values) if values else None

    def _count_samples(self, metrics: List[VMMetric], metric_type: str) -> int:
        """Count samples for metric type."""
        return len([m for m in metrics if m.metric_type == metric_type])

    def _generate_recommendation(self, cpu_avg: float, memory_avg: float, confidence: float) -> str:
        """Generate recommendation based on usage patterns."""
        if confidence >= 90:
            return "VM 长期闲置（CPU < 5%，内存 < 10%），建议迁移或关机以节省资源"
        elif confidence >= 75:
            return "VM 使用率极低（CPU < 10%，内存 < 20%），建议评估是否需要保留"
        elif confidence >= 50:
            return "VM 使用率较低，建议调查业务需求后考虑迁移"
        else:
            return "VM 使用率一般，建议继续观察"
