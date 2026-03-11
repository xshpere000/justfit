"""Health Score Analyzer - Platform health assessment.

Implements health assessment based on:
- Resource overcommit analysis
- Load balance analysis
- VM density (hotspot) analysis

Reference: docs/SPEC_HEALTH_ASSESSMENT.md
"""

import structlog
import statistics
from typing import List, Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Cluster, Host, VM, AssessmentTask


logger = structlog.get_logger()


class HealthAnalyzer:
    """Analyzer for platform health scoring."""

    def __init__(
        self,
        overcommit_threshold: float = 1.5,
        hotspot_threshold: float = 7.0,
        balance_threshold: float = 0.6,
    ) -> None:
        """Initialize health analyzer.

        Args:
            overcommit_threshold: Overcommit ratio threshold (default 1.5 = 150%)
            hotspot_threshold: VM density threshold (default 7.0 VMs per CPU core)
            balance_threshold: Balance CV threshold (default 0.6)
        """
        self.overcommit_threshold = overcommit_threshold
        self.hotspot_threshold = hotspot_threshold
        self.balance_threshold = balance_threshold

        # CPU frequency assumption for MHz to cores conversion
        self.cpu_mhz_per_core = 3000

    async def analyze(
        self,
        task_id: int,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Analyze platform health.

        Args:
            task_id: Task ID (primary parameter, consistent with other analyzers)
            db: Database session

        Returns:
            Health score result with success/data structure
        """
        # Get task to retrieve connection_id
        task_result = await db.execute(
            select(AssessmentTask).where(AssessmentTask.id == task_id)
        )
        task = task_result.scalar_one_or_none()

        if not task:
            return {
                "success": False,
                "error": {
                    "code": "TASK_NOT_FOUND",
                    "message": f"Task {task_id} not found",
                },
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

        # Build cluster data structure with associated VMs
        cluster_data = self._build_cluster_data(clusters, vms)

        # Run three analyses
        overcommit_results, overcommit_score = await self._analyze_overcommit(
            cluster_data
        )
        balance_results, balance_score = await self._analyze_balance(
            cluster_data, hosts
        )
        hotspot_hosts, hotspot_score, avg_vm_density = await self._analyze_hotspot(
            hosts
        )

        # Calculate overall score
        # Weights: overcommit 40%, balance 30%, hotspot 30%
        overall_score = (
            overcommit_score * 0.4 +
            balance_score * 0.3 +
            hotspot_score * 0.3
        )

        # Determine grade
        grade = self._determine_grade(overall_score)

        # Generate findings and recommendations
        findings = self._generate_findings(
            overcommit_results,
            balance_results,
            hotspot_hosts,
            overcommit_score,
            balance_score,
            hotspot_score,
        )

        recommendations = self._generate_recommendations(
            overcommit_results,
            balance_results,
            hotspot_hosts,
        )

        result = {
            "success": True,
            "data": {
                "overallScore": round(overall_score, 2),
                "grade": grade,
                "subScores": {
                    "overcommit": round(overcommit_score, 2),
                    "balance": round(balance_score, 2),
                    "hotspot": round(hotspot_score, 2),
                },
                "clusterCount": len(clusters),
                "hostCount": len(hosts),
                "vmCount": len(vms),
                "overcommitResults": overcommit_results,
                "balanceResults": balance_results,
                "hotspotHosts": hotspot_hosts,
                "overcommitScore": round(overcommit_score, 2),
                "balanceScore": round(balance_score, 2),
                "hotspotScore": round(hotspot_score, 2),
                "avgVmDensity": round(avg_vm_density, 2),
                "findings": findings,
                "recommendations": recommendations,
            },
        }

        logger.info(
            "health_analysis_completed",
            task_id=task_id,
            overall_score=round(overall_score, 2),
            grade=grade,
        )

        return result

    def _build_cluster_data(
        self, clusters: List[Cluster], vms: List[VM]
    ) -> Dict[str, Dict[str, Any]]:
        """Build cluster data structure with associated VMs.

        Args:
            clusters: List of Cluster objects
            vms: List of VM objects

        Returns:
            Dict mapping cluster_key to cluster data with VMs
        """
        cluster_map = {}

        for cluster in clusters:
            cluster_key = f"{cluster.datacenter}:{cluster.name}"
            cluster_map[cluster_key] = {
                "cluster": cluster,
                "vms": [],
            }

        for vm in vms:
            # Find cluster by matching datacenter and cluster info
            vm_cluster_key = f"{vm.datacenter}:{vm.datacenter}"  # VM's cluster
            if vm_cluster_key in cluster_map:
                cluster_map[vm_cluster_key]["vms"].append(vm)
            else:
                # Try direct match
                for cluster_key, cluster_info in cluster_map.items():
                    if cluster_info["cluster"].name in vm.host_name or vm.datacenter in cluster_key:
                        cluster_info["vms"].append(vm)
                        break

        return cluster_map

    async def _analyze_overcommit(
        self, cluster_data: Dict[str, Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], float]:
        """Analyze resource overcommit.

        Overcommit = Allocated Resources / Physical Resources

        Risk levels:
        - <= 1.0: Low (no overcommit)
        - 1.0 - 1.2: Medium (light overcommit)
        - 1.2 - 1.5: High (moderate overcommit)
        - 1.5 - 2.0: Critical (high overcommit)
        - > 2.0: Severe (severe overcommit)

        Args:
            cluster_data: Cluster data with VMs

        Returns:
            Tuple of (results list, overall score)
        """
        results = []
        total_physical_cpu_cores = 0
        total_physical_memory_gb = 0
        total_allocated_cpu = 0
        total_allocated_memory_gb = 0

        for cluster_key, data in cluster_data.items():
            cluster = data["cluster"]
            vms = data["vms"]

            # Physical resources
            physical_cpu_mhz = cluster.total_cpu
            physical_memory_bytes = cluster.total_memory

            # Convert to usable units
            physical_cpu_cores = physical_cpu_mhz / self.cpu_mhz_per_core
            physical_memory_gb = physical_memory_bytes / (1024**3)

            # Allocated resources (sum of VM configs)
            allocated_cpu = sum(vm.cpu_count for vm in vms)
            allocated_memory_bytes = sum(vm.memory_bytes for vm in vms)
            allocated_memory_gb = allocated_memory_bytes / (1024**3)

            # Calculate overcommit ratios
            cpu_overcommit = (
                allocated_cpu / physical_cpu_cores
                if physical_cpu_cores > 0 else 0
            )
            memory_overcommit = (
                allocated_memory_gb / physical_memory_gb
                if physical_memory_gb > 0 else 0
            )

            # Assess risk
            cpu_risk = self._assess_overcommit_risk(cpu_overcommit)
            memory_risk = self._assess_overcommit_risk(memory_overcommit)

            results.append({
                "clusterName": cluster.name,
                "physicalCpuCores": round(physical_cpu_cores, 1),
                "physicalMemoryGb": round(physical_memory_gb, 2),
                "allocatedCpu": allocated_cpu,
                "allocatedMemoryGb": round(allocated_memory_gb, 2),
                "cpuOvercommit": round(cpu_overcommit, 2),
                "memoryOvercommit": round(memory_overcommit, 2),
                "cpuRisk": cpu_risk,
                "memoryRisk": memory_risk,
            })

            total_physical_cpu_cores += physical_cpu_cores
            total_physical_memory_gb += physical_memory_gb
            total_allocated_cpu += allocated_cpu
            total_allocated_memory_gb += allocated_memory_gb

        # Calculate overall overcommit
        overall_cpu_overcommit = (
            total_allocated_cpu / total_physical_cpu_cores
            if total_physical_cpu_cores > 0 else 0
        )
        overall_memory_overcommit = (
            total_allocated_memory_gb / total_physical_memory_gb
            if total_physical_memory_gb > 0 else 0
        )

        # Calculate score
        score = self._calculate_overcommit_score(
            overall_cpu_overcommit, overall_memory_overcommit
        )

        return results, score

    def _assess_overcommit_risk(self, overcommit: float) -> str:
        """Assess overcommit risk level.

        Args:
            overcommit: Overcommit ratio

        Returns:
            Risk level string
        """
        if overcommit > 2.0:
            return "severe"
        elif overcommit > 1.5:
            return "critical"
        elif overcommit > 1.2:
            return "high"
        elif overcommit > 1.0:
            return "medium"
        else:
            return "low"

    def _calculate_overcommit_score(
        self, cpu_overcommit: float, memory_overcommit: float
    ) -> float:
        """Calculate overcommit score (0-100) using configured threshold.

        Args:
            cpu_overcommit: CPU overcommit ratio
            memory_overcommit: Memory overcommit ratio

        Returns:
            Score from 0-100
        """
        avg_overcommit = (cpu_overcommit + memory_overcommit) / 2
        threshold = self.overcommit_threshold

        if avg_overcommit <= 1.0:
            return 100  # No overcommit
        elif avg_overcommit <= min(1.2, threshold):
            return 85  # Light overcommit
        elif avg_overcommit <= min(1.5, threshold):
            return 65  # Moderate overcommit
        elif avg_overcommit <= min(2.0, threshold * 1.5):
            return 40  # High overcommit
        else:
            return 20  # Severe overcommit

    async def _analyze_balance(
        self, cluster_data: Dict[str, Dict[str, Any]], hosts: List[Host]
    ) -> tuple[List[Dict[str, Any]], float]:
        """Analyze load balance across hosts in each cluster.

        Uses Coefficient of Variation (CV) to measure distribution:
        - CV < 0.2: Excellent
        - CV < 0.4: Good
        - CV < 0.6: Fair
        - CV >= 0.6: Poor

        Args:
            cluster_data: Cluster data
            hosts: List of hosts

        Returns:
            Tuple of (results list, overall score)
        """
        results = []

        # Group hosts by cluster
        for cluster_key, data in cluster_data.items():
            cluster = data["cluster"]

            # Get hosts for this cluster
            cluster_hosts = [
                h for h in hosts
                if h.datacenter == cluster.datacenter
            ]

            if not cluster_hosts:
                continue

            # Get VM counts for each host
            host_vm_counts = [h.num_vms for h in cluster_hosts]

            if not host_vm_counts or all(c == 0 for c in host_vm_counts):
                # No VMs, consider balanced
                results.append({
                    "clusterName": cluster.name,
                    "hostCount": len(cluster_hosts),
                    "vmCounts": host_vm_counts,
                    "meanVmCount": 0.0,
                    "stdDev": 0.0,
                    "coefficientOfVariation": 0.0,
                    "balanceLevel": "excellent",
                    "balanceScore": 100.0,
                })
                continue

            # Calculate statistics
            mean_vm = statistics.mean(host_vm_counts)

            if len(host_vm_counts) > 1:
                std_vm = statistics.stdev(host_vm_counts)
            else:
                std_vm = 0.0

            # Coefficient of variation
            cv = std_vm / mean_vm if mean_vm > 0 else 0

            # Determine balance level and score
            balance_level, balance_score = self._assess_balance_level(cv)

            results.append({
                "clusterName": cluster.name,
                "hostCount": len(cluster_hosts),
                "vmCounts": host_vm_counts,
                "meanVmCount": round(mean_vm, 2),
                "stdDev": round(std_vm, 2),
                "coefficientOfVariation": round(cv, 3),
                "balanceLevel": balance_level,
                "balanceScore": balance_score,
            })

        # Calculate overall balance score
        if results:
            overall_score = statistics.mean([r["balanceScore"] for r in results])
        else:
            overall_score = 100.0

        return results, overall_score

    def _assess_balance_level(self, cv: float) -> tuple[str, float]:
        """Assess balance level from coefficient of variation using configured threshold.

        Args:
            cv: Coefficient of variation

        Returns:
            Tuple of (level, score)

        Assessment based on balance_threshold (default 0.6):
        - CV < threshold * 0.33: Excellent
        - CV < threshold * 0.66: Good
        - CV < threshold: Fair
        - CV >= threshold: Poor
        """
        threshold = self.balance_threshold

        if cv < threshold * 0.33:
            return "excellent", 100
        elif cv < threshold * 0.66:
            return "good", 80
        elif cv < threshold:
            return "fair", 60
        else:
            return "poor", 40

    async def _analyze_hotspot(
        self, hosts: List[Host]
    ) -> tuple[List[Dict[str, Any]], float, float]:
        """Analyze VM density to detect hotspots using configured threshold.

        VM Density = VM Count / CPU Cores

        Risk levels based on hotspot_threshold:
        - < threshold * 0.4: Low
        - threshold * 0.4 - threshold * 0.7: Medium
        - threshold * 0.7 - threshold: High
        - threshold - threshold * 1.4: Critical
        - >= threshold * 1.4: Severe

        Args:
            hosts: List of hosts

        Returns:
            Tuple of (hotspot hosts list, score, avg density)
        """
        hotspot_hosts = []
        vm_densities = []
        threshold = self.hotspot_threshold

        for host in hosts:
            if host.cpu_cores == 0:
                continue

            # VM density (VMs per CPU core)
            vm_density = host.num_vms / host.cpu_cores
            vm_densities.append(vm_density)

            # Assess risk using configured threshold
            risk_level = self._assess_hotspot_risk(vm_density)

            # Include high/critical/severe in results
            if risk_level in ["high", "critical", "severe"]:
                hotspot_hosts.append({
                    "hostName": host.name,
                    "ipAddress": host.ip_address,
                    "vmCount": host.num_vms,
                    "cpuCores": host.cpu_cores,
                    "memoryGb": round(host.memory_bytes / (1024**3), 2),
                    "vmDensity": round(vm_density, 2),
                    "riskLevel": risk_level,
                    "recommendation": self._get_hotspot_recommendation(
                        host.name, vm_density, risk_level
                    ),
                })

        # Calculate average density and score using threshold
        if vm_densities:
            avg_density = statistics.mean(vm_densities)
            # Score decreases as density increases beyond threshold * 0.4
            base_density = threshold * 0.4
            hotspot_score = max(0, 100 - max(0, avg_density - base_density) * (100 / (threshold * 1.5)))
        else:
            avg_density = 0.0
            hotspot_score = 100.0

        return hotspot_hosts, hotspot_score, avg_density

    def _assess_hotspot_risk(self, vm_density: float) -> str:
        """Assess hotspot risk level from VM density using configured threshold.

        Args:
            vm_density: VMs per CPU core

        Returns:
            Risk level string

        Risk levels based on hotspot_threshold:
        - < threshold * 0.4: Low
        - threshold * 0.4 - threshold * 0.7: Medium
        - threshold * 0.7 - threshold: High
        - threshold - threshold * 1.4: Critical
        - >= threshold * 1.4: Severe
        """
        threshold = self.hotspot_threshold

        if vm_density >= threshold * 1.4:
            return "severe"
        elif vm_density >= threshold:
            return "critical"
        elif vm_density >= threshold * 0.7:
            return "high"
        elif vm_density >= threshold * 0.4:
            return "medium"
        else:
            return "low"

    def _get_hotspot_recommendation(
        self, host_name: str, vm_density: float, risk_level: str
    ) -> str:
        """Generate hotspot recommendation.

        Args:
            host_name: Host name
            vm_density: VM density
            risk_level: Risk level

        Returns:
            Recommendation string
        """
        if risk_level == "severe":
            return (f"{host_name} 主机严重过载（VM密度 {vm_density:.1f}），"
                    f"建议迁移 {int(vm_density - 3)} 台虚拟机")
        elif risk_level == "critical":
            return (f"{host_name} 主机高负载（VM密度 {vm_density:.1f}），"
                    f"建议迁移 {max(1, int(vm_density - 5))} 台虚拟机")
        elif risk_level == "high":
            return f"{host_name} 主机负载较高（VM密度 {vm_density:.1f}），建议关注并准备迁移"
        else:
            return f"{host_name} 主机负载适中"

    def _determine_grade(self, overall_score: float) -> str:
        """Determine health grade from overall score.

        Args:
            overall_score: Overall health score

        Returns:
            Grade string
        """
        if overall_score >= 90:
            return "excellent"
        elif overall_score >= 75:
            return "good"
        elif overall_score >= 60:
            return "fair"
        elif overall_score >= 40:
            return "poor"
        else:
            return "critical"

    def _generate_findings(
        self,
        overcommit_results: List[Dict[str, Any]],
        balance_results: List[Dict[str, Any]],
        hotspot_hosts: List[Dict[str, Any]],
        overcommit_score: float,
        balance_score: float,
        hotspot_score: float,
    ) -> List[Dict[str, Any]]:
        """Generate health findings.

        Args:
            overcommit_results: Overcommit analysis results
            balance_results: Balance analysis results
            hotspot_hosts: Hotspot hosts
            overcommit_score: Overcommit score
            balance_score: Balance score
            hotspot_score: Hotspot score

        Returns:
            List of findings
        """
        findings = []

        # Overcommit findings
        for result in overcommit_results:
            if result["cpuRisk"] in ["high", "critical", "severe"]:
                findings.append({
                    "severity": result["cpuRisk"],
                    "category": "overcommit",
                    "cluster": result["clusterName"],
                    "description": (
                        f"{result['clusterName']} CPU超配比例 {result['cpuOvercommit']}，"
                        f"风险等级: {result['cpuRisk']}"
                    ),
                    "details": {
                        "cpuOvercommit": result["cpuOvercommit"],
                        "memoryOvercommit": result["memoryOvercommit"],
                    },
                })

        # Balance findings
        for result in balance_results:
            if result["balanceLevel"] in ["fair", "poor"]:
                severity = "high" if result["balanceLevel"] == "poor" else "medium"
                findings.append({
                    "severity": severity,
                    "category": "balance",
                    "cluster": result["clusterName"],
                    "description": (
                        f"{result['clusterName']} 负载分布{result['balanceLevel']}，"
                        f"变异系数 {result['coefficientOfVariation']}"
                    ),
                    "details": {
                        "coefficientOfVariation": result["coefficientOfVariation"],
                        "balanceLevel": result["balanceLevel"],
                    },
                })

        # Hotspot findings
        for host in hotspot_hosts:
            findings.append({
                "severity": host["riskLevel"],
                "category": "hotspot",
                "host": host["hostName"],
                "description": (
                    f"{host['hostName']} VM密度过高（{host['vmDensity']}），"
                    f"风险等级: {host['riskLevel']}"
                ),
                "details": {
                    "vmDensity": host["vmDensity"],
                    "vmCount": host["vmCount"],
                    "cpuCores": host["cpuCores"],
                },
            })

        return findings

    def _generate_recommendations(
        self,
        overcommit_results: List[Dict[str, Any]],
        balance_results: List[Dict[str, Any]],
        hotspot_hosts: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate recommendations.

        Args:
            overcommit_results: Overcommit analysis results
            balance_results: Balance analysis results
            hotspot_hosts: Hotspot hosts

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Overcommit recommendations
        high_overcommit = [
            r for r in overcommit_results
            if r["cpuRisk"] in ["high", "critical", "severe"] or
               r["memoryRisk"] in ["high", "critical", "severe"]
        ]
        if high_overcommit:
            cluster_names = ", ".join([r["clusterName"] for r in high_overcommit])
            recommendations.append(
                f"以下集群资源超配比例较高，建议评估是否需要扩容或迁移VM：{cluster_names}"
            )

        # Balance recommendations
        poor_balance = [
            r for r in balance_results
            if r["balanceLevel"] == "poor"
        ]
        if poor_balance:
            cluster_names = ", ".join([r["clusterName"] for r in poor_balance])
            recommendations.append(
                f"以下集群负载分布不均，建议通过DRS或vMotion重新平衡：{cluster_names}"
            )

        # Hotspot recommendations
        critical_hotspots = [
            h for h in hotspot_hosts
            if h["riskLevel"] in ["critical", "severe"]
        ]
        if critical_hotspots:
            host_names = ", ".join([h["hostName"] for h in critical_hotspots])
            recommendations.append(
                f"以下主机VM密度过高，强烈建议迁移VM：{host_names}"
            )

        return recommendations

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result when no data available.

        Returns:
            Empty result dict
        """
        return {
            "success": True,
            "data": {
                "overallScore": 0.0,
                "grade": "no_data",
                "subScores": {
                    "overcommit": 0.0,
                    "balance": 0.0,
                    "hotspot": 0.0,
                },
                "clusterCount": 0,
                "hostCount": 0,
                "vmCount": 0,
                "overcommitResults": [],
                "balanceResults": [],
                "hotspotHosts": [],
                "overcommitScore": 0.0,
                "balanceScore": 0.0,
                "hotspotScore": 0.0,
                "avgVmDensity": 0.0,
                "findings": [],
                "recommendations": [],
            },
        }
