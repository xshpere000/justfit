"""Report Data Builder - Assembles data for report generation."""

import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Connection, Cluster, Host, VM, AssessmentTask,
    TaskAnalysisJob, AnalysisFinding, TaskReport
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

        # Get analysis results
        zombie_results = await self._get_findings(task_id, "zombie")
        rightsize_results = await self._get_findings(task_id, "rightsize")
        tidal_results = await self._get_findings(task_id, "tidal")
        health_results = await self._get_health_results(task_id)

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
                "zombie": zombie_results,
                "rightsize": rightsize_results,
                "tidal": tidal_results,
                "health": health_results,
            },
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
