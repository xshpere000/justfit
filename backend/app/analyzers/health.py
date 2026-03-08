"""Health Score Analyzer - Platform health assessment."""

import structlog
from typing import List, Dict, Any

from app.models import Connection


logger = structlog.get_logger()


class HealthAnalyzer:
    """Analyzer for platform health scoring."""

    def __init__(
        self,
        overcommit_threshold: float = 150.0,
        hotspot_threshold: float = 90.0,
        balance_threshold: float = 0.6,
    ) -> None:
        """Initialize health analyzer.

        Args:
            overcommit_threshold: Overcommit ratio threshold (default 150%)
            hotspot_threshold: Hotspot usage threshold (default 90%)
            balance_threshold: Balance threshold (default 0.6)
        """
        self.overcommit_threshold = overcommit_threshold
        self.hotspot_threshold = hotspot_threshold
        self.balance_threshold = balance_threshold

    async def analyze(
        self,
        task_id: int,
        db,
    ) -> Dict[str, Any]:
        """Analyze platform health.

        Args:
            task_id: Task ID (primary parameter, consistent with other analyzers)
            db: Database session

        Returns:
            Health score result
        """
        # Get resource data
        from sqlalchemy import select, func
        from app.models import Cluster, Host, VM, AssessmentTask

        # Get task to retrieve connection_id
        task_result = await db.execute(
            select(AssessmentTask).where(AssessmentTask.id == task_id)
        )
        task = task_result.scalar_one_or_none()

        if not task:
            return {
                "success": False,
                "error": "Task not found",
            }

        connection_id = task.connection_id

        # Get cluster/host/VM data
        clusters_result = await db.execute(
            select(Cluster).where(Cluster.connection_id == connection_id)
        )
        clusters = clusters_result.scalars().all()

        hosts_result = await db.execute(
            select(Host).where(Host.connection_id == connection_id)
        )
        hosts = hosts_result.scalars().all()

        vms_result = await db.execute(
            select(VM).where(VM.connection_id == connection_id)
        )
        vms = vms_result.scalars().all()

        if not clusters and not hosts:
            return self._empty_result()

        # Calculate scores
        balance_score = self._calculate_balance_score(clusters, hosts, vms)
        overcommit_score = self._calculate_overcommit_score(clusters, vms)
        hotspot_score = self._calculate_hotspot_score(hosts, vms)

        # Overall score
        overall_score = (
            balance_score * 0.4 +
            overcommit_score * 0.3 +
            hotspot_score * 0.3
        )

        # Determine grade
        if overall_score >= 90:
            grade = "excellent"
        elif overall_score >= 75:
            grade = "good"
        elif overall_score >= 60:
            grade = "fair"
        elif overall_score >= 40:
            grade = "poor"
        else:
            grade = "critical"

        # Generate findings
        findings = self._generate_findings(
            balance_score, overcommit_score, hotspot_score
        )

        return {
            "success": True,
            "data": {
                "overallScore": round(overall_score, 2),
                "grade": grade,
                "balanceScore": round(balance_score, 2),
                "overcommitScore": round(overcommit_score, 2),
                "hotspotScore": round(hotspot_score, 2),
                "clusterCount": len(clusters),
                "hostCount": len(hosts),
                "vmCount": len(vms),
                "findings": findings,
            },
        }

    def _empty_result(self) -> Dict:
        """Return empty result."""
        return {
            "success": True,
            "data": {
                "overallScore": 0,
                "grade": "no_data",
                "balanceScore": 0,
                "overcommitScore": 0,
                "hotspotScore": 0,
                "clusterCount": 0,
                "hostCount": 0,
                "vmCount": 0,
                "findings": [],
            },
        }

    def _calculate_balance_score(self, clusters, hosts, vms) -> float:
        """Calculate resource balance score."""
        if not hosts:
            return 0

        # Calculate VM distribution across hosts
        host_vm_counts = [h.num_vms for h in hosts if h.num_vms is not None]

        if not host_vm_counts:
            return 100

        # Calculate coefficient of variation
        avg_vms = sum(host_vm_counts) / len(host_vm_counts)
        variance = sum((count - avg_vms) ** 2 for count in host_vm_counts) / len(host_vm_counts)
        cv = (variance ** 0.5 / avg_vms) if avg_vms > 0 else 0

        # Convert to score (lower CV = better balance)
        if cv < 0.3:
            return 100
        elif cv < 0.5:
            return 80
        elif cv < 0.8:
            return 60
        else:
            return 40

    def _calculate_overcommit_score(self, clusters, vms) -> float:
        """Calculate overcommit risk score."""
        if not clusters:
            return 0

        total_cluster_cpu = sum(c.total_cpu for c in clusters)
        total_cluster_memory = sum(c.total_memory for c in clusters)

        total_vm_cpu = sum(v.cpu_count for v in vms)
        total_vm_memory = sum(v.memory_bytes for v in vms)

        if total_cluster_cpu == 0 or total_cluster_memory == 0:
            return 50

        # Calculate overcommit ratio
        cpu_overcommit = (total_vm_cpu / total_cluster_cpu) * 100 if total_cluster_cpu > 0 else 0
        memory_overcommit = (total_vm_memory / total_cluster_memory) * 100 if total_cluster_memory > 0 else 0

        # Score based on ideal ranges (2-4x for CPU, 1.5-2.5x for Memory)
        cpu_score = self._range_score(cpu_overcommit, 200, 400)
        memory_score = self._range_score(memory_overcommit, 150, 250)

        return (cpu_score + memory_score) / 2

    def _calculate_hotspot_score(self, hosts, vms) -> float:
        """Calculate hotspot concentration score."""
        if not hosts or not vms:
            return 0

        # Calculate load per host
        host_loads = []
        for host in hosts:
            host_cpu_load = sum(
                vm.cpu_count for vm in vms
                if vm.host_ip == host.ip_address and vm.power_state == "poweredon"
            )
            host_memory_load = sum(
                vm.memory_bytes for vm in vms
                if vm.host_ip == host.ip_address and vm.power_state == "poweredon"
            ) / (1024**3)  # Convert to GB

            # Normalize load (CPU + memory/8192)
            load = host_cpu_load + host_memory_load / 8192
            host_loads.append(load)

        if not host_loads:
            return 100

        # Calculate Gini coefficient (0 = perfectly equal, 1 = maximum inequality)
        sorted_loads = sorted(host_loads)
        n = len(sorted_loads)
        gini_sum = sum((i + 1) * load for i, load in enumerate(sorted_loads))
        total_load = sum(sorted_loads)
        gini = (2 * gini_sum) / (n * total_load) - 1 if n > 0 and total_load > 0 else 0

        # Convert to score (lower Gini = better distribution = higher score)
        # Gini 0-0.3 → 100, 0.3-0.5 → 80, 0.5-0.7 → 60, >0.7 → 40
        if gini < 0.3:
            return 100
        elif gini < 0.5:
            return 80
        elif gini < 0.7:
            return 60
        else:
            return 40

    def _range_score(self, value: float, ideal_min: float, ideal_max: float) -> float:
        """Calculate score based on range."""
        if ideal_min <= value <= ideal_max:
            return 100
        elif value < ideal_min:
            return max(0, 100 - (ideal_min - value) / ideal_min * 50)
        else:
            return max(0, 100 - (value - ideal_max) / (ideal_max * 2) * 50)

    def _generate_findings(
        self,
        balance_score: float,
        overcommit_score: float,
        hotspot_score: float,
    ) -> List[Dict]:
        """Generate health findings."""
        findings = []

        if balance_score < 70:
            findings.append({
                "type": "balance",
                "severity": "medium" if balance_score >= 50 else "high",
                "title": "VM 分布不均衡",
                "description": f"虚拟机在主机上的分布变异系数较高 (平衡度: {balance_score:.0f}/100)",
            })

        if overcommit_score < 70:
            findings.append({
                "type": "overcommit",
                "severity": "high" if overcommit_score < 50 else "medium",
                "title": "资源超配风险",
                "description": f"当前超配比例可能过高 (超配分: {overcommit_score:.0f}/100)",
            })

        if hotspot_score < 70:
            findings.append({
                "type": "hotspot",
                "severity": "medium" if hotspot_score >= 50 else "high",
                "title": "负载集中度过高",
                "description": f"部分主机负载过高，考虑迁移 VM (负载均衡度: {hotspot_score:.0f}/100)",
            })

        return findings
