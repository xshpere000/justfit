"""Analysis Service - Orchestrates analysis engines."""

import structlog
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    VMMetric, VM, TaskAnalysisJob, AnalysisFinding,
    AssessmentTask, Cluster, Host, TaskLog
)
from app.analyzers.zombie import ZombieAnalyzer
from app.analyzers.rightsize import RightSizeAnalyzer
from app.analyzers.tidal import TidalAnalyzer
from app.analyzers.health import HealthAnalyzer
from app.analyzers.modes import AnalysisModes


logger = structlog.get_logger()


class AnalysisService:
    """Service for orchestrating analysis operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize analysis service.

        Args:
            db: Database session
        """
        self.db = db

    async def _add_log(self, task_id: int, level: str, message: str) -> None:
        """Add log entry for task.

        Args:
            task_id: Task ID
            level: Log level (debug, info, warn, error)
            message: Log message
        """
        try:
            log = TaskLog(
                task_id=task_id,
                level=level,
                message=message,
            )
            self.db.add(log)
            await self.db.flush()
        except Exception as e:
            logger.warning("failed_to_add_task_log", task_id=task_id, error=str(e))

    async def get_modes(self) -> Dict[str, Dict]:
        """Get all available analysis modes.

        Returns:
            Dict of mode configurations
        """
        return AnalysisModes.list_modes()

    async def get_mode(self, mode_name: str) -> Dict[str, Any]:
        """Get specific analysis mode configuration.

        Args:
            mode_name: Mode name (safe, saving, aggressive, custom)

        Returns:
            Mode configuration
        """
        return AnalysisModes.get_mode(mode_name)

    async def update_custom_mode(
        self,
        analysis_type: str,
        config: Dict[str, Any],
        task_id: Optional[int] = None,
    ) -> None:
        """Update custom mode configuration.

        Args:
            analysis_type: Analysis type (zombie, rightsize, tidal, health)
            config: New configuration
            task_id: Optional task ID for logging
        """
        AnalysisModes.update_custom_mode(analysis_type, config)
        if task_id:
            type_names = {
                "zombie": "僵尸VM检测",
                "rightsize": "Right Size分析",
                "tidal": "潮汐模式检测",
                "health": "健康评分"
            }
            type_name = type_names.get(analysis_type, analysis_type)
            await self._add_log(task_id, "info", f"{type_name}配置已更新")

    async def run_zombie_analysis(
        self,
        task_id: int,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run zombie VM analysis.

        Args:
            task_id: Task ID
            config: Optional configuration override

        Returns:
            Analysis results
        """
        logger.info("zombie_analysis_starting", task_id=task_id)
        await self._add_log(task_id, "info", "开始执行僵尸VM分析...")

        # Get task
        task = await self._get_task(task_id)
        if not task:
            logger.warning("zombie_analysis_task_not_found", task_id=task_id)
            await self._add_log(task_id, "error", "任务不存在，无法执行分析")
            return {"success": False, "error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}}

        # Get or create analysis job
        job = await self._get_or_create_job(task_id, "zombie")
        if not job.get("is_new", False):
            logger.warning("zombie_analysis_already_running", task_id=task_id)
            await self._add_log(task_id, "warn", "僵尸VM分析已在运行中")
            return {"success": False, "error": {"code": "ALREADY_RUNNING", "message": "Analysis already running"}}

        # Get configuration
        if config is None:
            config = AnalysisModes.get_mode("saving")["zombie"]

        logger.debug("zombie_analysis_config", task_id=task_id, config=config)
        await self._add_log(task_id, "info", f"分析配置：{config.get('days', 14)}天数据，CPU阈值{config.get('cpu_threshold', 10)}%")

        # Initialize analyzer
        analyzer = ZombieAnalyzer(
            days_threshold=config.get("days", 14),
            cpu_threshold=config.get("cpu_threshold", 10.0),
            memory_threshold=config.get("memory_threshold", 20.0),
            disk_io_threshold=config.get("disk_io_threshold", 5.0),
            network_threshold=config.get("network_threshold", 5.0),
            min_confidence=config.get("min_confidence", 60.0),
        )

        # Get VM metrics and data
        vm_metrics, vm_data = await self._get_vm_metrics_and_data(task_id)

        if not vm_metrics:
            logger.info("zombie_analysis_no_metrics", task_id=task_id)
            await self._add_log(task_id, "warn", "没有可用的VM指标数据，无法执行分析")
            return {"success": True, "data": []}

        logger.info("zombie_analysis_analyzing", task_id=task_id, vm_count=len(vm_metrics))
        await self._add_log(task_id, "info", f"正在分析 {len(vm_metrics)} 台虚拟机...")

        # Run analysis
        findings = await analyzer.analyze(task_id, vm_metrics, vm_data)

        # Save findings
        await self._save_findings(task_id, job["id"], "zombie", findings)

        logger.info(
            "zombie_analysis_completed",
            task_id=task_id,
            findings_count=len(findings),
        )
        await self._add_log(task_id, "info", f"僵尸VM分析完成，发现 {len(findings)} 台可能闲置的VM")

        return {"success": True, "data": findings}

    async def run_rightsize_analysis(
        self,
        task_id: int,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run right-size analysis.

        Args:
            task_id: Task ID
            config: Optional configuration override

        Returns:
            Analysis results
        """
        logger.info("rightsize_analysis_starting", task_id=task_id)
        await self._add_log(task_id, "info", "开始执行Right Size分析...")

        # Get task
        task = await self._get_task(task_id)
        if not task:
            logger.warning("rightsize_analysis_task_not_found", task_id=task_id)
            await self._add_log(task_id, "error", "任务不存在，无法执行分析")
            return {"success": False, "error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}}

        # Get or create analysis job
        job = await self._get_or_create_job(task_id, "rightsize")
        if not job.get("is_new", False):
            logger.warning("rightsize_analysis_already_running", task_id=task_id)
            await self._add_log(task_id, "warn", "Right Size分析已在运行中")
            return {"success": False, "error": {"code": "ALREADY_RUNNING", "message": "Analysis already running"}}

        # Get configuration
        if config is None:
            config = AnalysisModes.get_mode("saving")["rightsize"]

        logger.debug("rightsize_analysis_config", task_id=task_id, config=config)
        await self._add_log(task_id, "info", f"分析配置：{config.get('days', 7)}天数据，缓冲比例{config.get('cpu_buffer_percent', 20)}%")

        # Initialize analyzer
        analyzer = RightSizeAnalyzer(
            days_threshold=config.get("days", 7),
            cpu_buffer_percent=config.get("cpu_buffer_percent", 20.0),
            memory_buffer_percent=config.get("memory_buffer_percent", 20.0),
            high_usage_threshold=config.get("high_usage_threshold", 90.0),
            low_usage_threshold=config.get("low_usage_threshold", 30.0),
            min_confidence=config.get("min_confidence", 60.0),
        )

        # Get VM metrics and data
        vm_metrics, vm_data = await self._get_vm_metrics_and_data(task_id)

        if not vm_metrics:
            logger.info("rightsize_analysis_no_metrics", task_id=task_id)
            await self._add_log(task_id, "warn", "没有可用的VM指标数据，无法执行分析")
            return {"success": True, "data": []}

        logger.info("rightsize_analysis_analyzing", task_id=task_id, vm_count=len(vm_metrics))
        await self._add_log(task_id, "info", f"正在分析 {len(vm_metrics)} 台虚拟机的资源配置...")

        # Run analysis
        findings = await analyzer.analyze(task_id, vm_metrics, vm_data)

        # Save findings
        await self._save_findings(task_id, job["id"], "rightsize", findings)

        logger.info(
            "rightsize_analysis_completed",
            task_id=task_id,
            findings_count=len(findings),
        )
        await self._add_log(task_id, "info", f"Right Size分析完成，发现 {len(findings)} 台VM需要调整配置")

        return {"success": True, "data": findings}

    async def run_tidal_analysis(
        self,
        task_id: int,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run tidal pattern analysis.

        Args:
            task_id: Task ID
            config: Optional configuration override

        Returns:
            Analysis results
        """
        logger.info("tidal_analysis_starting", task_id=task_id)
        await self._add_log(task_id, "info", "开始执行潮汐模式检测...")

        # Get task
        task = await self._get_task(task_id)
        if not task:
            logger.warning("tidal_analysis_task_not_found", task_id=task_id)
            await self._add_log(task_id, "error", "任务不存在，无法执行分析")
            return {"success": False, "error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}}

        # Get or create analysis job
        job = await self._get_or_create_job(task_id, "tidal")
        if not job.get("is_new", False):
            logger.warning("tidal_analysis_already_running", task_id=task_id)
            await self._add_log(task_id, "warn", "潮汐模式检测已在运行中")
            return {"success": False, "error": {"code": "ALREADY_RUNNING", "message": "Analysis already running"}}

        # Get configuration
        if config is None:
            config = AnalysisModes.get_mode("saving")["tidal"]

        logger.debug("tidal_analysis_config", task_id=task_id, config=config)
        await self._add_log(task_id, "info", f"分析配置：{config.get('days', 14)}天数据，稳定性阈值{config.get('min_stability', 50)}%")

        # Initialize analyzer
        analyzer = TidalAnalyzer(
            days_threshold=config.get("days", 14),
            peak_threshold=config.get("peak_threshold", 75.0),
            valley_threshold=config.get("valley_threshold", 35.0),
            min_stability=config.get("min_stability", 50.0),
        )

        # Get VM metrics and data
        vm_metrics, vm_data = await self._get_vm_metrics_and_data(task_id)

        if not vm_metrics:
            logger.info("tidal_analysis_no_metrics", task_id=task_id)
            await self._add_log(task_id, "warn", "没有可用的VM指标数据，无法执行分析")
            return {"success": True, "data": []}

        logger.info("tidal_analysis_analyzing", task_id=task_id, vm_count=len(vm_metrics))
        await self._add_log(task_id, "info", f"正在分析 {len(vm_metrics)} 台虚拟机的使用模式...")

        # Run analysis
        findings = await analyzer.analyze(task_id, vm_metrics, vm_data)

        # Save findings
        await self._save_findings(task_id, job["id"], "tidal", findings)

        logger.info(
            "tidal_analysis_completed",
            task_id=task_id,
            findings_count=len(findings),
        )
        await self._add_log(task_id, "info", f"潮汐模式检测完成，发现 {len(findings)} 台VM具有周期性使用模式")

        return {"success": True, "data": findings}

    async def run_health_analysis(
        self,
        task_id: int,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run health score analysis.

        Args:
            task_id: Task ID (primary parameter, like other analyses)
            config: Optional configuration override

        Returns:
            Analysis results
        """
        # Get task
        task = await self._get_task(task_id)
        if not task:
            logger.warning("health_analysis_task_not_found", task_id=task_id)
            await self._add_log(task_id, "error", "任务不存在，无法执行分析")
            return {"success": False, "error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}}

        # Get or create analysis job
        job = await self._get_or_create_job(task_id, "health")
        if not job.get("is_new", False):
            logger.warning("health_analysis_already_running", task_id=task_id)
            await self._add_log(task_id, "warn", "健康评分分析已在运行中")
            return {"success": False, "error": {"code": "ALREADY_RUNNING", "message": "Analysis already running"}}

        connection_id = task.connection_id
        logger.info("health_analysis_starting", task_id=task_id, connection_id=connection_id)
        await self._add_log(task_id, "info", "开始执行健康评分分析...")

        # Get configuration
        if config is None:
            config = AnalysisModes.get_mode("saving")["health"]

        logger.debug("health_analysis_config", task_id=task_id, connection_id=connection_id, config=config)
        await self._add_log(task_id, "info", f"分析配置：超配阈值{config.get('overcommit_threshold', 150)}%，热点阈值{config.get('hotspot_threshold', 90)}%")

        # Initialize analyzer
        analyzer = HealthAnalyzer(
            overcommit_threshold=config.get("overcommit_threshold", 150.0),
            hotspot_threshold=config.get("hotspot_threshold", 90.0),
            balance_threshold=config.get("balance_threshold", 0.6),
        )

        # Run analysis
        result = await analyzer.analyze(task_id, self.db)

        if result.get("success"):
            health_data = result.get("data", {})
            health_score = health_data.get("overallScore")
            grade = health_data.get("grade", "unknown")

            # Save health score as a special finding (platform-level, not per-VM)
            await self._save_health_score(task_id, job["id"], health_data)

            logger.info(
                "health_analysis_completed",
                task_id=task_id,
                connection_id=connection_id,
                health_score=health_score,
            )
            grade_map = {"excellent": "优秀", "good": "良好", "fair": "一般", "poor": "较差", "critical": "危急"}
            grade_text = grade_map.get(grade, grade)
            await self._add_log(task_id, "info", f"健康评分完成：得分 {health_score:.0f}，等级 {grade_text}")
        else:
            logger.error("health_analysis_failed", task_id=task_id, connection_id=connection_id)
            await self._add_log(task_id, "error", "健康评分分析失败")

        return result

    async def get_analysis_results(
        self,
        task_id: int,
        analysis_type: str,
    ) -> Dict[str, Any]:
        """Get analysis results from database.

        Args:
            task_id: Task ID
            analysis_type: Analysis type (zombie, rightsize, tidal, health)

        Returns:
            Analysis results
        """
        # Query findings
        from sqlalchemy import select

        query = (
            select(AnalysisFinding)
            .where(
                AnalysisFinding.task_id == task_id,
                AnalysisFinding.job_type == analysis_type,
            )
            .order_by(AnalysisFinding.confidence.desc())
        )

        result = await self.db.execute(query)
        findings = result.scalars().all()

        # Health score is special - it's a single platform-level result
        if analysis_type == "health" and findings:
            # Return the health score data directly from details
            health_finding = findings[0]  # Should only be one
            if health_finding.details:
                import json
                try:
                    health_data = json.loads(health_finding.details)
                    return {"success": True, "data": health_data}
                except json.JSONDecodeError as e:
                    logger.error("health_score_json_parse_error", task_id=task_id, error=str(e))
                    return {"success": False, "error": {"code": "JSON_PARSE_ERROR", "message": f"Failed to parse health score data: {str(e)}"}}
                except Exception as e:
                    logger.error("health_score_data_error", task_id=task_id, error=str(e))
                    return {"success": False, "error": {"code": "DATA_ERROR", "message": f"Health score data error: {str(e)}"}}
            # Fallback: no data found
            logger.warning("health_score_no_details", task_id=task_id)
            return {"success": False, "error": {"code": "NO_DATA", "message": "Health score data not found"}}
        # No findings found
        logger.warning("health_score_no_findings", task_id=task_id, analysis_type=analysis_type)
        return {"success": False, "error": {"code": "NO_DATA", "message": f"No {analysis_type} analysis found for task {task_id}"}}

        # For other analyses (zombie, rightsize, tidal), return as list
        data = []
        for finding in findings:
            item = {
                "vmName": finding.vm_name,
                "cluster": "",
                "confidence": finding.confidence,
                "severity": finding.severity,
                "title": finding.title,
                "description": finding.description,
                "recommendation": finding.recommendation,
            }
            if finding.details:
                import json
                try:
                    item.update(json.loads(finding.details))
                except:
                    pass
            data.append(item)

        return {"success": True, "data": data}

    async def _get_task(self, task_id: int) -> Optional[AssessmentTask]:
        """Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task or None
        """
        query = select(AssessmentTask).where(AssessmentTask.id == task_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_or_create_job(
        self,
        task_id: int,
        job_type: str,
    ) -> Dict[str, Any]:
        """Get or create analysis job.

        Args:
            task_id: Task ID
            job_type: Job type

        Returns:
            Job info dict with 'is_new' flag indicating if job was just created
        """
        # Try to get existing job
        query = (
            select(TaskAnalysisJob)
            .where(
                TaskAnalysisJob.task_id == task_id,
                TaskAnalysisJob.job_type == job_type,
            )
            .order_by(TaskAnalysisJob.id.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        job = result.scalar_one_or_none()

        if job:
            # 检查 job 状态
            if job.status == "running":
                # 检查是否超时（超过 2 分钟）或有 completed_at 但状态仍是 running
                timeout_threshold = datetime.utcnow() - timedelta(minutes=2)
                if job.completed_at or (job.started_at and job.started_at < timeout_threshold):
                    # Job 已完成或超时，标记为失败并创建新 job
                    job.status = "failed"
                    job.error = "Job stale or completed" if job.completed_at else "Job timeout"
                    await self.db.commit()
                else:
                    # Job 确实正在运行
                    return {
                        "id": job.id,
                        "status": "running",
                        "is_new": False,
                    }
            # Job 已完成或失败，创建新的 job

            # Job 已完成或失败，创建新的 job
            job = TaskAnalysisJob(
                task_id=task_id,
                job_type=job_type,
                status="running",
                started_at=datetime.utcnow(),
            )
            self.db.add(job)
            await self.db.commit()
            await self.db.refresh(job)

            return {
                "id": job.id,
                "status": "running",
                "is_new": True,
            }

        # No existing job, create new one
        job = TaskAnalysisJob(
            task_id=task_id,
            job_type=job_type,
            status="running",
            started_at=datetime.utcnow(),
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        return {
            "id": job.id,
            "status": "running",
            "is_new": True,
        }

    async def _get_vm_metrics_and_data(
        self,
        task_id: int,
    ) -> tuple[Dict[int, List[VMMetric]], Dict[int, Dict]]:
        """Get VM metrics and data for analysis.

        Args:
            task_id: Task ID

        Returns:
            Tuple of (vm_metrics dict, vm_data dict)
        """
        # Get all VMs for this task
        vm_query = (
            select(VM)
            .where(VM.connection_id == select(AssessmentTask.connection_id).where(AssessmentTask.id == task_id).scalar_subquery())
        )
        vm_result = await self.db.execute(vm_query)
        vms = vm_result.scalars().all()

        # Build vm_data dict
        vm_data = {}
        for vm in vms:
            vm_data[vm.id] = {
                "name": vm.name,
                "cluster": "",
                "cpu_count": vm.cpu_count,
                "memory_bytes": vm.memory_bytes,
                "host_ip": vm.host_ip,
                "power_state": vm.power_state,
            }

        # Get metrics
        metrics_query = (
            select(VMMetric)
            .where(VMMetric.task_id == task_id)
        )
        metrics_result = await self.db.execute(metrics_query)
        metrics = metrics_result.scalars().all()

        # Group by VM
        vm_metrics: Dict[int, List[VMMetric]] = {}
        for metric in metrics:
            if metric.vm_id not in vm_metrics:
                vm_metrics[metric.vm_id] = []
            vm_metrics[metric.vm_id].append(metric)

        return vm_metrics, vm_data

    async def _save_findings(
        self,
        task_id: int,
        job_id: int,
        job_type: str,
        findings: List[Dict],
    ) -> None:
        """Save analysis findings to database."""
        import json

        for finding in findings:
            # Extract basic fields
            vm_name = finding.get("vmName", "")
            cluster = finding.get("cluster", "")

            # Determine severity
            if "severity" in finding:
                severity = finding["severity"]
            elif "confidence" in finding:
                conf = finding["confidence"]
                if conf >= 90:
                    severity = "critical"
                elif conf >= 75:
                    severity = "high"
                elif conf >= 50:
                    severity = "medium"
                else:
                    severity = "low"
            else:
                severity = "info"

            # Create title and description
            title = finding.get("title", "")
            if not title:
                if job_type == "zombie":
                    title = f"僵尸 VM: {vm_name}"
                elif job_type == "rightsize":
                    title = f"Right Size: {vm_name}"
                elif job_type == "tidal":
                    title = f"潮汐模式: {vm_name}"

            description = finding.get("description", "")
            recommendation = finding.get("recommendation", "")

            # Build details JSON
            details = {k: v for k, v in finding.items()
                      if k not in ["vmName", "cluster", "confidence", "severity",
                                  "title", "description", "recommendation"]}

            db_finding = AnalysisFinding(
                task_id=task_id,
                job_id=job_id,
                job_type=job_type,
                vm_name=vm_name,
                severity=severity,
                title=title,
                description=description,
                recommendation=recommendation,
                details=json.dumps(details) if details else None,
                confidence=findings[0].get("confidence", 0.0) if findings else 0.0,
            )
            self.db.add(db_finding)

        # Update job status
        job_query = (
            select(TaskAnalysisJob)
            .where(TaskAnalysisJob.id == job_id)
        )
        job_result = await self.db.execute(job_query)
        job = job_result.scalar_one_or_none()
        if job:
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.result_summary = json.dumps({"count": len(findings)})

        await self.db.commit()

    async def _save_health_score(
        self,
        task_id: int,
        job_id: int,
        health_data: Dict[str, Any],
    ) -> None:
        """Save health score analysis results to database.

        Health score is different from other analyses - it's a single platform-level result,
        not per-VM findings. We store it as a special finding with vm_name=None.
        """
        import json
        from datetime import datetime

        overall_score = health_data.get("overallScore", 0)
        grade = health_data.get("grade", "unknown")

        # Map grade to severity
        grade_severity_map = {
            "excellent": "low",  # Excellent is good, low severity
            "good": "low",
            "fair": "medium",
            "poor": "high",
            "critical": "critical",
            "no_data": "info",
        }
        severity = grade_severity_map.get(grade, "info")

        # Create title and description
        grade_text_map = {
            "excellent": "优秀",
            "good": "良好",
            "fair": "一般",
            "poor": "较差",
            "critical": "危急",
            "no_data": "无数据",
        }
        grade_text = grade_text_map.get(grade, grade)

        title = f"平台健康评分: {grade_text} ({overall_score:.0f}分)"

        # Build detailed description
        balance_score = health_data.get("balanceScore", 0)
        overcommit_score = health_data.get("overcommitScore", 0)
        hotspot_score = health_data.get("hotspotScore", 0)
        cluster_count = health_data.get("clusterCount", 0)
        host_count = health_data.get("hostCount", 0)
        vm_count = health_data.get("vmCount", 0)

        description = (
            f"平台健康评分 {overall_score:.0f} 分，等级 {grade_text}。\n"
            f"负载均衡度: {balance_score:.0f}，"
            f"资源超配: {overcommit_score:.0f}，"
            f"负载分布: {hotspot_score:.0f}。\n"
            f"评估范围: {cluster_count} 个集群，{host_count} 台主机，{vm_count} 台虚拟机。"
        )

        # Extract findings if available
        health_findings = health_data.get("findings", [])
        recommendations = []
        for finding in health_findings:
            if finding.get("severity") in ["high", "critical"]:
                recommendations.append(finding.get("description", ""))

        recommendation = "\n".join(recommendations) if recommendations else "平台运行状况良好，暂无优化建议。"

        # Store full health data in details
        details = {
            "overallScore": overall_score,
            "grade": grade,
            "balanceScore": balance_score,
            "overcommitScore": overcommit_score,
            "hotspotScore": hotspot_score,
            "clusterCount": cluster_count,
            "hostCount": host_count,
            "vmCount": vm_count,
            "findings": health_findings,
        }

        # Create database record
        db_finding = AnalysisFinding(
            task_id=task_id,
            job_id=job_id,
            job_type="health",
            vm_name="",  # Platform-level, not specific to a VM (empty string, not None)
            severity=severity,
            title=title,
            description=description,
            recommendation=recommendation,
            details=json.dumps(details),
            confidence=overall_score,  # Use score as confidence
        )
        self.db.add(db_finding)

        # Update job status
        job_query = select(TaskAnalysisJob).where(TaskAnalysisJob.id == job_id)
        job_result = await self.db.execute(job_query)
        job = job_result.scalar_one_or_none()
        if job:
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.result_summary = json.dumps({
                "overallScore": overall_score,
                "grade": grade,
                "clusterCount": cluster_count,
                "hostCount": host_count,
                "vmCount": vm_count,
            })

        await self.db.commit()
