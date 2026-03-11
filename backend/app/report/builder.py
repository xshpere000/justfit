"""Report Data Builder - Assembles data for report generation."""

import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Connection, Cluster, Host, VM, AssessmentTask,
    TaskAnalysisJob, AnalysisFinding, TaskReport, VMMetric
)


logger = structlog.get_logger()


class ReportBuilder:
    """Builds report data from database records."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize report builder.

        Args:
            db: Database session
        """
        self.db = db

    async def build_task_report_data(
        self,
        task_id: int,
    ) -> Dict[str, Any]:
        """Build complete report data for a task.

        Args:
            task_id: Task ID

        Returns:
            Report data dict
        """
        # Get task
        task = await self._get_task(task_id)
        if not task:
            return {}

        # Get connection
        connection = await self._get_connection(task.connection_id)
        connection_name = connection.name if connection else "Unknown"
        platform = connection.platform if connection else "unknown"

        # Get resources
        clusters = await self._get_clusters(task.connection_id)
        hosts = await self._get_hosts(task.connection_id)
        vms = await self._get_vms(task.connection_id)

        # Get analysis results - use AnalysisService for consistent data structure
        from app.services.analysis import AnalysisService
        analysis_service = AnalysisService(self.db)

        # Get idle results
        idle_response = await analysis_service.get_analysis_results(task_id, "idle")
        idle_results = idle_response.get("data", []) if idle_response.get("success") else []

        # Get resource results (structured dict with rightSize, usagePattern, mismatch)
        resource_response = await analysis_service.get_analysis_results(task_id, "resource")
        resource_results = resource_response.get("data", {}) if resource_response.get("success") else {}

        # Get health results
        health_response = await analysis_service.get_analysis_results(task_id, "health")
        health_results = health_response.get("data") if health_response.get("success") else None

        # Collect VM metrics for charts
        # Combine VMs from idle, rightSize, usagePattern, and mismatch results
        vms_to_chart = []

        # Add VMs from idle results (has vmId)
        for vm in idle_results[:25]:  # Collect up to 25 VMs for potential charts
            if vm.get("vmId") or vm.get("vm_id"):
                vms_to_chart.append({
                    "vm_id": vm.get("vmId") or vm.get("vm_id"),
                    "vm_name": vm.get("vmName") or vm.get("vm_name", ""),
                })

        # Add VMs from rightSize results (need to look up by name)
        right_size = resource_results.get("rightSize", [])[:25]
        for vm in right_size:
            vm_name = vm.get("vmName") or vm.get("vm_name", "")
            if vm_name and not any(v["vm_name"] == vm_name for v in vms_to_chart):
                vms_to_chart.append({
                    "vm_name": vm_name,
                })

        # Add VMs from usagePattern results
        usage_pattern = resource_results.get("usagePattern", [])[:25]
        for vm in usage_pattern:
            vm_name = vm.get("vmName") or vm.get("vm_name", "")
            if vm_name and not any(v["vm_name"] == vm_name for v in vms_to_chart):
                vms_to_chart.append({
                    "vm_name": vm_name,
                })

        # Add VMs from mismatch results
        mismatch = resource_results.get("mismatch", [])[:25]
        for vm in mismatch:
            vm_name = vm.get("vmName") or vm.get("vm_name", "")
            if vm_name and not any(v["vm_name"] == vm_name for v in vms_to_chart):
                vms_to_chart.append({
                    "vm_name": vm_name,
                })

        # Collect metrics data for these VMs
        vm_metrics, vm_name_to_id = await self.build_vm_metrics_data(task_id, vms_to_chart, metric_days=7)

        # Build report data
        return {
            "task": {
                "id": task.id,
                "name": task.name,
                "type": task.type,
                "status": task.status,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            },
            "connection": {
                "name": connection_name,
                "platform": platform,
            },
            "summary": self._build_summary(clusters, hosts, vms),
            "resources": {
                "clusters": clusters,
                "hosts": hosts,
                "vms": vms,
            },
            "analysis": {
                "idle": idle_results,
                "resource": resource_results,
                "health": health_results,
            },
            "vm_metrics": vm_metrics,  # Time-series data for charts (vm_id -> metrics)
            "vm_name_to_id": vm_name_to_id,  # Mapping for VMs only identified by name
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _get_task(self, task_id: int) -> Optional[AssessmentTask]:
        """Get task by ID."""
        query = select(AssessmentTask).where(AssessmentTask.id == task_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_connection(
        self,
        connection_id: Optional[int],
    ) -> Optional[Connection]:
        """Get connection by ID."""
        if not connection_id:
            return None
        query = select(Connection).where(Connection.id == connection_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_clusters(self, connection_id: Optional[int]) -> List[Dict]:
        """Get clusters for connection."""
        if not connection_id:
            return []
        query = select(Cluster).where(Cluster.connection_id == connection_id)
        result = await self.db.execute(query)
        clusters = result.scalars().all()

        return [
            {
                "name": c.name,
                "datacenter": c.datacenter,
                "total_cpu": c.total_cpu,
                "total_memory_gb": round(c.total_memory / (1024**3), 2),
                "num_hosts": c.num_hosts,
                "num_vms": c.num_vms,
            }
            for c in clusters
        ]

    async def _get_hosts(self, connection_id: Optional[int]) -> List[Dict]:
        """Get hosts for connection."""
        if not connection_id:
            return []
        query = select(Host).where(Host.connection_id == connection_id)
        result = await self.db.execute(query)
        hosts = result.scalars().all()

        return [
            {
                "name": h.name,
                "datacenter": h.datacenter,
                "ip_address": h.ip_address,
                "cpu_cores": h.cpu_cores,
                "cpu_mhz": h.cpu_mhz,
                "memory_gb": round(h.memory_bytes / (1024**3), 2),
                "num_vms": h.num_vms,
                "power_state": h.power_state,
                "overall_status": h.overall_status,
            }
            for h in hosts
        ]

    async def _get_vms(self, connection_id: Optional[int]) -> List[Dict]:
        """Get VMs for connection."""
        if not connection_id:
            return []
        query = select(VM).where(VM.connection_id == connection_id)
        result = await self.db.execute(query)
        vms = result.scalars().all()

        return [
            {
                "name": v.name,
                "datacenter": v.datacenter,
                "cpu_count": v.cpu_count,
                "memory_gb": round(v.memory_bytes / (1024**3), 2),
                "power_state": v.power_state,
                "guest_os": v.guest_os,
                "ip_address": v.ip_address,
                "host_ip": v.host_ip,
                "connection_state": v.connection_state,
                "overall_status": v.overall_status,
            }
            for v in vms
        ]

    async def _get_findings(
        self,
        task_id: int,
        finding_type: str,
    ) -> List[Dict[str, Any]]:
        """Get analysis findings by type."""
        query = (
            select(AnalysisFinding)
            .where(
                AnalysisFinding.task_id == task_id,
                AnalysisFinding.job_type == finding_type,
            )
            .order_by(AnalysisFinding.confidence.desc())
        )
        result = await self.db.execute(query)
        findings = result.scalars().all()

        results = []
        for f in findings:
            item = {
                "vm_name": f.vm_name,
                "severity": f.severity,
                "confidence": f.confidence,
                "title": f.title,
                "description": f.description,
                "recommendation": f.recommendation,
            }
            # Parse details JSON if available
            if f.details:
                try:
                    import json
                    item.update(json.loads(f.details))
                except:
                    pass
            results.append(item)

        return results

    async def _get_health_results(
        self,
        task_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Get health score results for a task."""
        if not task_id:
            return None

        # Get health analysis results from database
        from app.services.analysis import AnalysisService
        service = AnalysisService(self.db)
        result = await service.get_analysis_results(task_id, "health")

        if result.get("success") and result.get("data"):
            return result.get("data")
        return None

    def _build_summary(
        self,
        clusters: List[Dict],
        hosts: List[Dict],
        vms: List[Dict],
    ) -> Dict[str, Any]:
        """Build summary statistics."""
        total_cpu = sum(c.get("total_cpu", 0) for c in clusters)
        total_memory_gb = sum(c.get("total_memory_gb", 0) for c in clusters)

        powered_on_vms = [v for v in vms if v.get("power_state") == "poweredon"]
        powered_off_vms = [v for v in vms if v.get("power_state") == "poweredoff"]

        return {
            "total_clusters": len(clusters),
            "total_hosts": len(hosts),
            "total_vms": len(vms),
            "powered_on_vms": len(powered_on_vms),
            "powered_off_vms": len(powered_off_vms),
            "total_cpu_mhz": total_cpu,
            "total_memory_gb": round(total_memory_gb, 2),
        }

    def build_idle_summary(self, idle_results: List[Dict]) -> Dict[str, Any]:
        """Build idle VM summary statistics.

        Args:
            idle_results: List of idle VM analysis results

        Returns:
            Summary dict with counts and categorization
        """
        if not idle_results:
            return {
                "total": 0,
                "by_type": {"powered_off": 0, "idle_powered_on": 0, "low_activity": 0},
                "by_risk": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "potential_savings": {"cpu_cores": 0, "memory_gb": 0},
            }

        # Count by type
        type_counts = {"powered_off": 0, "idle_powered_on": 0, "low_activity": 0}
        for item in idle_results:
            idle_type = item.get("idleType", "unknown")
            if idle_type in type_counts:
                type_counts[idle_type] += 1

        # Count by risk level
        risk_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for item in idle_results:
            risk = item.get("riskLevel", "low")
            if risk in risk_counts:
                risk_counts[risk] += 1

        # Calculate potential savings
        total_cpu = 0
        total_memory = 0
        for item in idle_results:
            total_cpu += item.get("cpuCores", 0)
            total_memory += item.get("memoryGb", 0)

        return {
            "total": len(idle_results),
            "by_type": type_counts,
            "by_risk": risk_counts,
            "potential_savings": {
                "cpu_cores": total_cpu,
                "memory_gb": round(total_memory, 2),
            },
        }

    def build_resource_summary(self, resource_results: Dict) -> Dict[str, Any]:
        """Build resource analysis summary.

        Args:
            resource_results: Resource analysis results dict

        Returns:
            Summary dict with optimization opportunities
        """
        right_size = resource_results.get("rightSize", [])
        usage_pattern = resource_results.get("usagePattern", [])
        mismatch = resource_results.get("mismatch", [])

        # Right Size summary
        right_size_summary = {
            "total": len(right_size),
            "downsize_candidates": sum(1 for r in right_size if r.get("adjustmentType", "").startswith("down")),
            "upsize_candidates": sum(1 for r in right_size if r.get("adjustmentType", "").startswith("up")),
        }

        # Calculate potential savings from Right Size
        current_cpu = sum(r.get("currentCpu", 0) for r in right_size)
        suggested_cpu = sum(r.get("suggestedCpu", 0) for r in right_size)
        current_memory = sum(r.get("currentMemory", 0) for r in right_size)
        suggested_memory = sum(r.get("suggestedMemory", 0) for r in right_size)

        right_size_summary["potential_savings"] = {
            "cpu_cores": max(0, current_cpu - suggested_cpu),
            "memory_gb": max(0, current_memory - suggested_memory),
        }

        # Usage Pattern summary
        pattern_counts = {"stable": 0, "burst": 0, "tidal": 0, "unknown": 0}
        for p in usage_pattern:
            pattern = p.get("usagePattern", "unknown")
            if pattern in pattern_counts:
                pattern_counts[pattern] += 1

        # Mismatch summary
        mismatch_summary = {
            "total": len(mismatch),
            "cpu_rich_memory_poor": sum(1 for m in mismatch if m.get("mismatchType") == "cpu_rich_memory_poor"),
            "cpu_poor_memory_rich": sum(1 for m in mismatch if m.get("mismatchType") == "cpu_poor_memory_rich"),
            "both_underutilized": sum(1 for m in mismatch if m.get("mismatchType") == "both_underutilized"),
            "both_overutilized": sum(1 for m in mismatch if m.get("mismatchType") == "both_overutilized"),
        }

        return {
            "right_size": right_size_summary,
            "usage_pattern": {"total": len(usage_pattern), "by_pattern": pattern_counts},
            "mismatch": mismatch_summary,
        }

    def build_health_summary(self, health_results: Optional[Dict]) -> Dict[str, Any]:
        """Build health score summary.

        Args:
            health_results: Health analysis results dict

        Returns:
            Summary dict with grade breakdown
        """
        if not health_results:
            return {
                "overall_score": 0,
                "grade": "no_data",
                "grade_text": "无数据",
                "sub_scores": {"overcommit": 0, "balance": 0, "hotspot": 0},
            }

        grade_map = {
            "excellent": "优秀",
            "good": "良好",
            "fair": "一般",
            "poor": "较差",
            "critical": "危急",
            "no_data": "无数据",
        }

        grade = health_results.get("grade", "no_data")

        return {
            "overall_score": health_results.get("overallScore", 0),
            "grade": grade,
            "grade_text": grade_map.get(grade, grade),
            "sub_scores": {
                "overcommit": health_results.get("overcommitScore", 0),
                "balance": health_results.get("balanceScore", 0),
                "hotspot": health_results.get("hotspotScore", 0),
            },
            "cluster_count": health_results.get("clusterCount", 0),
            "host_count": health_results.get("hostCount", 0),
            "vm_count": health_results.get("vmCount", 0),
        }

    def build_savings_estimate(
        self,
        idle_results: List[Dict],
        resource_results: Dict,
    ) -> Dict[str, Any]:
        """Build overall savings estimate.

        Args:
            idle_results: Idle VM results
            resource_results: Resource analysis results

        Returns:
            Total potential savings summary
        """
        # Idle VM savings
        idle_cpu = sum(item.get("cpuCores", 0) for item in idle_results)
        idle_memory = sum(item.get("memoryGb", 0) for item in idle_results)

        # Right Size savings
        right_size = resource_results.get("rightSize", [])
        current_cpu = sum(r.get("currentCpu", 0) for r in right_size)
        suggested_cpu = sum(r.get("suggestedCpu", 0) for r in right_size)
        current_memory = sum(r.get("currentMemory", 0) for r in right_size)
        suggested_memory = sum(r.get("suggestedMemory", 0) for r in right_size)

        rightsize_cpu_save = max(0, current_cpu - suggested_cpu)
        rightsize_memory_save = max(0, current_memory - suggested_memory)

        return {
            "total_cpu_savings": idle_cpu + rightsize_cpu_save,
            "total_memory_savings_gb": round(idle_memory + rightsize_memory_save, 2),
            "idle_vms": {
                "count": len(idle_results),
                "cpu_cores": idle_cpu,
                "memory_gb": round(idle_memory, 2),
            },
            "right_size": {
                "count": len(right_size),
                "cpu_cores": rightsize_cpu_save,
                "memory_gb": round(rightsize_memory_save, 2),
            },
        }

    async def build_vm_metrics_data(
        self,
        task_id: int,
        vm_list: List[Dict[str, Any]],
        metric_days: int = 7,
    ) -> Tuple[Dict[int, Dict[str, List[Tuple[float, float]]]], Dict[str, int]]:
        """Build VM metrics time-series data for charts.

        Args:
            task_id: Task ID
            vm_list: List of VM dicts with vm_id or vmName
            metric_days: Number of days of metrics to retrieve

        Returns:
            Tuple of (vm_metrics dict, vm_name_to_id mapping):
            - vm_metrics: Dict mapping vm_id to metrics data
            - vm_name_to_id: Dict mapping vm_name to vm_id (for cases where only vmName is available)
        """
        result = {}
        vm_name_to_id = {}

        # Collect all VM IDs and names
        vm_ids = []
        vm_names_to_lookup = []

        for vm in vm_list:
            # Try to get vm_id directly
            vm_id = vm.get("vm_id") or vm.get("vmId")
            vm_name = vm.get("vm_name") or vm.get("vmName", "")

            if vm_id:
                vm_ids.append(vm_id)
                # Also store name mapping if available
                if vm_name:
                    vm_name_to_id[vm_name] = vm_id
            elif vm_name:
                # Need to look up VM by name
                vm_names_to_lookup.append(vm_name)

        # Query VM IDs by name if needed
        if vm_names_to_lookup:
            vm_query = select(VM.id, VM.name).where(
                VM.name.in_(vm_names_to_lookup)
            )
            vm_result = await self.db.execute(vm_query)
            for row in vm_result.all():
                vm_id, vm_name = row
                vm_ids.append(vm_id)
                vm_name_to_id[vm_name] = vm_id

        if not vm_ids:
            return result, vm_name_to_id

        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=metric_days)

        # Query metrics for all VMs
        metrics_query = select(VMMetric).where(
            and_(
                VMMetric.task_id == task_id,
                VMMetric.vm_id.in_(vm_ids),
                VMMetric.timestamp >= start_time,
                VMMetric.timestamp <= end_time,
            )
        ).order_by(VMMetric.timestamp.asc())

        metrics_result = await self.db.execute(metrics_query)
        metrics = metrics_result.scalars().all()

        # Group metrics by vm_id and metric_type
        for metric in metrics:
            vm_id = metric.vm_id
            if vm_id not in result:
                result[vm_id] = {
                    "cpu": [],
                    "memory": [],
                    "disk_read": [],
                    "disk_write": [],
                    "net_rx": [],
                    "net_tx": [],
                }

            # Convert timestamp to float for chart plotting
            timestamp = metric.timestamp.timestamp()
            value = float(metric.value)

            # Store in appropriate list
            metric_type = metric.metric_type
            if metric_type in result[vm_id]:
                result[vm_id][metric_type].append((timestamp, value))

        # Also add entries for VMs looked up by name
        for vm_name, vm_id in vm_name_to_id.items():
            if vm_id not in result:
                result[vm_id] = {
                    "cpu": [],
                    "memory": [],
                    "disk_read": [],
                    "disk_write": [],
                    "net_rx": [],
                    "net_tx": [],
                }

        return result, vm_name_to_id
