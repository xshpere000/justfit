"""Report Data Builder - Assembles data for report generation."""

import structlog
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, or_
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

        # Get resource results (structured dict with resourceOptimization and tidal)
        resource_response = await analysis_service.get_analysis_results(task_id, "resource")
        resource_results = resource_response.get("data", {}) if resource_response.get("success") else {}

        # Get health results
        health_response = await analysis_service.get_analysis_results(task_id, "health")
        health_results = health_response.get("data") if health_response.get("success") else None

        # Get host freeability summary (综合优化建议 + 可释放主机)
        # 根据已有分析结果决定启用哪些优化项
        enabled_opts = []
        if idle_results:
            enabled_opts.append("idle")
        if resource_results.get("resourceOptimization"):
            enabled_opts.append("resource")
        freeability_response = await analysis_service.calculate_host_freeability(task_id, enabled_opts)
        freeability_data = freeability_response.get("data") if freeability_response.get("success") else None

        # Collect VM metrics for charts
        # Combine VMs from idle and resource optimization results
        vms_to_chart = []

        # Add VMs from idle results (has vmId)
        for vm in idle_results[:25]:  # Collect up to 25 VMs for potential charts
            if vm.get("vmId"):
                vms_to_chart.append({
                    "vm_id": vm.get("vmId"),
                    "vm_name": vm.get("vmName", ""),
                })

        # Add VMs from resourceOptimization results
        resource_optimization = resource_results.get("resourceOptimization", [])[:25]
        for vm in resource_optimization:
            vm_name = vm.get("vmName", "")
            if vm_name and not any(v["vm_name"] == vm_name for v in vms_to_chart):
                vms_to_chart.append({
                    "vm_name": vm_name,
                })

        # Add VMs from tidal results
        tidal = resource_results.get("tidal", [])[:25]
        for vm in tidal:
            vm_name = vm.get("vmName", "")
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
                # freeability_data 包含 current/optimized/freeableHosts/recommendation/breakdown
                # 单位说明：cpuCores=核, memoryGb=GB, storageGb=GB, diskGb=GB, loadPercent=%
                "freeability": freeability_data,
            },
            "vm_metrics": vm_metrics,  # Time-series data for charts (vm_id -> metrics)
            "vm_name_to_id": vm_name_to_id,  # Mapping for VMs only identified by name
            "generated_at": datetime.now().isoformat(),
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
                "total_storage_gb": round(c.total_storage / (1024**3), 2),
                "used_storage_gb": round(c.used_storage / (1024**3), 2),
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
                "disk_usage_gb": round(v.disk_usage_bytes / (1024**3), 2),
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

    def _build_summary(
        self,
        clusters: List[Dict],
        hosts: List[Dict],
        vms: List[Dict],
    ) -> Dict[str, Any]:
        """Build summary statistics."""
        total_cpu = sum(c.get("total_cpu", 0) for c in clusters)
        total_memory_gb = sum(c.get("total_memory_gb", 0) for c in clusters)
        total_storage_gb = sum(c.get("total_storage_gb", 0) for c in clusters)
        used_storage_gb = sum(c.get("used_storage_gb", 0) for c in clusters)

        powered_on_vms = [v for v in vms if (v.get("power_state") or "").lower().replace(" ", "").replace("_", "") in ("poweredon", "on", "running")]
        powered_off_vms = [v for v in vms if (v.get("power_state") or "").lower().replace(" ", "").replace("_", "") in ("poweredoff", "off", "shutdown", "suspended")]

        return {
            "total_clusters": len(clusters),
            "total_hosts": len(hosts),
            "total_vms": len(vms),
            "powered_on_vms": len(powered_on_vms),
            "powered_off_vms": len(powered_off_vms),
            "total_cpu_mhz": total_cpu,
            "total_memory_gb": round(total_memory_gb, 2),
            "total_storage_gb": round(total_storage_gb, 2),
            "used_storage_gb": round(used_storage_gb, 2),
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
                "potential_savings": {"cpu_cores": 0, "memory_gb": 0, "disk_gb": 0},
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

        # Calculate potential savings (关机 VM 已不占 CPU/内存，仅占磁盘)
        total_cpu = 0
        total_memory = 0
        total_disk = 0
        for item in idle_results:
            idle_type = item.get("idleType", "")
            if idle_type == "powered_off":
                # 关机 VM 只释放磁盘
                total_disk += item.get("diskUsageGb", 0)
            else:
                # 开机闲置 VM 释放 CPU + 内存 + 磁盘
                total_cpu += item.get("cpuCores", 0)
                total_memory += item.get("memoryGb", 0)
                total_disk += item.get("diskUsageGb", 0)

        return {
            "total": len(idle_results),
            "by_type": type_counts,
            "by_risk": risk_counts,
            "potential_savings": {
                "cpu_cores": total_cpu,
                "memory_gb": round(total_memory, 2),
                "disk_gb": round(total_disk, 2),
            },
        }

    def build_resource_summary(self, resource_results: Dict) -> Dict[str, Any]:
        """Build resource analysis summary."""
        resource_optimization = resource_results.get("resourceOptimization", [])
        tidal = resource_results.get("tidal", [])

        # Resource optimization summary
        current_cpu = sum(r.get("currentCpu", 0) for r in resource_optimization)
        suggested_cpu = sum(r.get("recommendedCpu", 0) for r in resource_optimization)
        current_memory = sum(r.get("currentMemoryGb", 0) for r in resource_optimization)
        suggested_memory = sum(r.get("recommendedMemoryGb", 0) for r in resource_optimization)

        mismatch_type_counts = {}
        for r in resource_optimization:
            mt = r.get("mismatchType", "balanced")
            mismatch_type_counts[mt] = mismatch_type_counts.get(mt, 0) + 1

        resource_summary = {
            "total": len(resource_optimization),
            "downsize_candidates": sum(1 for r in resource_optimization if (r.get("cpuAdjustmentType", "") or "").startswith("down") or (r.get("memAdjustmentType", "") or "").startswith("down")),
            "upsize_candidates": sum(1 for r in resource_optimization if (r.get("cpuAdjustmentType", "") or "").startswith("up") or (r.get("memAdjustmentType", "") or "").startswith("up")),
            "mismatch_types": mismatch_type_counts,
            "potential_savings": {
                "cpu_cores": max(0, current_cpu - suggested_cpu),
                "memory_gb": max(0, current_memory - suggested_memory),
            },
        }

        # Tidal summary
        granularity_counts = {"daily": 0, "weekly": 0, "monthly": 0}
        for t in tidal:
            g = t.get("tidalGranularity", "daily")
            if g in granularity_counts:
                granularity_counts[g] += 1

        tidal_summary = {
            "total": len(tidal),
            "by_granularity": granularity_counts,
        }

        return {
            "resource_optimization": resource_summary,
            "tidal": tidal_summary,
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
        # Idle VM savings (关机 VM 已不占 CPU/内存，仅占磁盘)
        idle_vm_ids = {item.get("vmId") for item in idle_results if item.get("vmId") is not None}
        idle_cpu = 0
        idle_memory = 0.0
        idle_disk = 0.0
        for item in idle_results:
            idle_type = item.get("idleType", "")
            if idle_type == "powered_off":
                idle_disk += item.get("diskUsageGb", 0)
            else:
                idle_cpu += item.get("cpuCores", 0)
                idle_memory += item.get("memoryGb", 0)
                idle_disk += item.get("diskUsageGb", 0)

        # Right Size savings（排除已在 idle 列表中的 VM，避免重复计算）
        resource_optimization = resource_results.get("resourceOptimization", [])
        rs_deduped = [r for r in resource_optimization if r.get("vmId") not in idle_vm_ids]
        current_cpu = sum(r.get("currentCpu", 0) for r in rs_deduped)
        suggested_cpu = sum(r.get("recommendedCpu", 0) for r in rs_deduped)
        current_memory = sum(r.get("currentMemoryGb", 0) for r in rs_deduped)
        suggested_memory = sum(r.get("recommendedMemoryGb", 0) for r in rs_deduped)

        rightsize_cpu_save = max(0, current_cpu - suggested_cpu)
        rightsize_memory_save = max(0, current_memory - suggested_memory)

        return {
            "total_cpu_savings": idle_cpu + rightsize_cpu_save,
            "total_memory_savings_gb": round(idle_memory + rightsize_memory_save, 2),
            "total_disk_savings_gb": round(idle_disk, 2),
            "idle_vms": {
                "count": len(idle_results),
                "cpu_cores": idle_cpu,
                "memory_gb": round(idle_memory, 2),
                "disk_gb": round(idle_disk, 2),
            },
            "right_size": {
                "count": len(rs_deduped),
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
            vm_id = vm.get("vm_id")
            vm_name = vm.get("vm_name", "")

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

        # Query VM info to get cpu_count, memory_bytes, host_name, host_ip for unit conversion
        vm_info_query = select(VM.id, VM.cpu_count, VM.memory_bytes, VM.host_name, VM.host_ip).where(
            VM.id.in_(vm_ids)
        )
        vm_info_result = await self.db.execute(vm_info_query)
        vm_info_map: Dict[int, Dict] = {}
        host_names_to_lookup = set()
        host_ips_to_lookup = set()
        for row in vm_info_result.all():
            vid, cpu_count, memory_bytes, host_name, host_ip = row
            vm_info_map[vid] = {
                "cpu_count": cpu_count or 0,
                "memory_bytes": memory_bytes or 0,
                "host_name": host_name or "",
                "host_ip": host_ip or "",
            }
            if host_name:
                host_names_to_lookup.add(host_name)
            if host_ip:
                host_ips_to_lookup.add(host_ip)

        # Query Host cpu_mhz for percentage conversion (CPU stored as MHz)
        host_cpu_by_name: Dict[str, int] = {}
        host_cpu_by_ip: Dict[str, int] = {}
        if host_names_to_lookup or host_ips_to_lookup:
            host_query = select(Host.name, Host.ip_address, Host.cpu_mhz).where(
                or_(
                    Host.name.in_(host_names_to_lookup),
                    Host.ip_address.in_(host_ips_to_lookup),
                )
            )
            host_result = await self.db.execute(host_query)
            for row in host_result.all():
                hname, hip, cpu_mhz = row
                if hname:
                    host_cpu_by_name[hname] = cpu_mhz or 0
                if hip:
                    host_cpu_by_ip[hip] = cpu_mhz or 0

        def _get_host_cpu_mhz(vm_id: int) -> int:
            info = vm_info_map.get(vm_id, {})
            mhz = host_cpu_by_name.get(info.get("host_name", ""), 0)
            if mhz == 0:
                mhz = host_cpu_by_ip.get(info.get("host_ip", ""), 0)
            return mhz if mhz > 0 else 2600  # fallback to 2600 MHz

        def _cpu_to_pct(vm_id: int, value_mhz: float) -> float:
            info = vm_info_map.get(vm_id, {})
            cpu_count = max(1, info.get("cpu_count", 1))
            host_mhz = _get_host_cpu_mhz(vm_id)
            pct = value_mhz / (cpu_count * host_mhz) * 100
            return min(100.0, round(pct, 2))

        def _mem_to_pct(vm_id: int, value_bytes: float) -> float:
            info = vm_info_map.get(vm_id, {})
            total = max(1, info.get("memory_bytes", 1))
            pct = value_bytes / total * 100
            return min(100.0, round(pct, 2))

        # Calculate time range
        end_time = datetime.now()
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

        # Group metrics by vm_id and metric_type, converting CPU/memory to percentages
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

            metric_type = metric.metric_type
            if metric_type == "cpu":
                # Convert MHz → percentage
                result[vm_id]["cpu"].append((timestamp, _cpu_to_pct(vm_id, value)))
            elif metric_type == "memory":
                # Convert bytes → percentage
                result[vm_id]["memory"].append((timestamp, _mem_to_pct(vm_id, value)))
            elif metric_type in result[vm_id]:
                if value >= 0:  # vCenter 用 -1 表示无效采样，过滤掉
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
