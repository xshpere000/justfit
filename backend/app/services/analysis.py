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
from app.analyzers.rightsize import RightSizeAnalyzer
from app.analyzers.health import HealthAnalyzer
from app.analyzers.resource_analyzer import ResourceAnalyzer
from app.analyzers.idle_detector import IdleDetector
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
                created_at=datetime.utcnow(),
            )
            self.db.add(log)
            await self.db.flush()
            # 立即提交日志，避免长事务阻塞
            await self.db.commit()
        except Exception as e:
            logger.warning("failed_to_add_task_log", task_id=task_id, error=str(e))
            # 发生错误时回滚，防止会话处于无效状态
            try:
                await self.db.rollback()
            except Exception:
                pass

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

    @staticmethod
    def merge_mode_config(
        base_mode: str,
        custom_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge custom configuration with base mode configuration.

        Args:
            base_mode: Base mode name (safe, saving, aggressive)
            custom_config: User's custom configuration

        Returns:
            Merged configuration dict
        """
        base = AnalysisModes.get_mode(base_mode).copy()

        def deep_merge(base_dict: Dict, custom_dict: Dict) -> Dict:
            """Recursively merge custom dict into base dict."""
            result = base_dict.copy()
            for key, value in custom_dict.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result

        return deep_merge(base, custom_config)

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
            # 有已运行的 job，强制重置并创建新 job
            logger.warning("health_analysis_resetting_stale_job", task_id=task_id, job_id=job.get("id"))
            await self._add_log(task_id, "warn", "检测到未完成的健康评分，将重新开始...")

            # 强制标记旧 job 为失败
            from sqlalchemy import select, update
            stmt = (
                update(TaskAnalysisJob)
                .where(TaskAnalysisJob.id == job["id"])
                .values(status="failed", error="Superseded by new analysis")
            )
            await self.db.execute(stmt)
            await self.db.commit()

            # 创建新 job
            job = await self._get_or_create_job(task_id, "health")
            if not job.get("is_new", False):
                logger.error("health_analysis_failed_to_create_job", task_id=task_id)
                return {"success": False, "error": {"code": "JOB_CREATE_FAILED", "message": "Failed to create analysis job"}}

        connection_id = task.connection_id
        logger.info("health_analysis_starting", task_id=task_id, connection_id=connection_id)
        await self._add_log(task_id, "info", "开始执行健康评分分析...")

        # Get configuration
        if config is None:
            config = AnalysisModes.get_mode("saving")["health"]

        logger.debug("health_analysis_config", task_id=task_id, connection_id=connection_id, config=config)
        await self._add_log(task_id, "info", f"分析配置：超配阈值{config.get('overcommit_threshold', 1.5)}，热点阈值{config.get('hotspot_threshold', 7.0)}")

        # Initialize analyzer (thresholds are ratios, not percentages)
        analyzer = HealthAnalyzer(
            overcommit_threshold=config.get("overcommit_threshold", 1.5),
            hotspot_threshold=config.get("hotspot_threshold", 7.0),
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

    async def run_resource_analysis(
        self,
        task_id: int,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run resource analysis (Resource Optimization + Tidal Detection).

        Args:
            task_id: Task ID
            config: Optional configuration override with keys:
                    - rightsize: dict for right size config
                    - usage_pattern: dict for tidal detection config

        Returns:
            Resource analysis results with resourceOptimization and tidal
        """
        logger.info("resource_analysis_starting", task_id=task_id)
        await self._add_log(task_id, "info", "开始执行资源分析...")

        # Get task
        task = await self._get_task(task_id)
        if not task:
            logger.warning("resource_analysis_task_not_found", task_id=task_id)
            await self._add_log(task_id, "error", "任务不存在，无法执行分析")
            return {"success": False, "error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}}

        # Get or create analysis job
        job = await self._get_or_create_job(task_id, "resource")
        if not job.get("is_new", False):
            logger.warning("resource_analysis_resetting_stale_job", task_id=task_id, job_id=job.get("id"))
            await self._add_log(task_id, "warn", "检测到未完成的资源分析，将重新开始...")

            from sqlalchemy import select, update
            stmt = (
                update(TaskAnalysisJob)
                .where(TaskAnalysisJob.id == job["id"])
                .values(status="failed", error="Superseded by new analysis")
            )
            await self.db.execute(stmt)
            await self.db.commit()

            job = await self._get_or_create_job(task_id, "resource")
            if not job.get("is_new", False):
                logger.error("resource_analysis_failed_to_create_job", task_id=task_id)
                return {"success": False, "error": {"code": "JOB_CREATE_FAILED", "message": "Failed to create analysis job"}}

        # Get configuration
        mode = "saving"
        if config is None:
            mode_config = AnalysisModes.get_mode(mode)
            config = {
                "rightsize": mode_config.get("resource", {}).get("rightsize", {}),
                "usage_pattern": mode_config.get("resource", {}).get("usage_pattern", {
                    "cv_threshold": 0.4,
                    "peak_valley_ratio": 2.5,
                }),
            }

        rightsize_config = config.get("rightsize", {})
        usage_pattern_config = config.get("usage_pattern", {})

        logger.debug("resource_analysis_config", task_id=task_id, config=config)
        await self._add_log(task_id, "info", "分析配置：资源优化（含错配检测）、潮汐检测")

        # Initialize analyzer
        analyzer = ResourceAnalyzer(
            mode=mode,
            right_size_config=rightsize_config,
            usage_pattern_config=usage_pattern_config,
        )

        # Get VM metrics and data
        vm_metrics, vm_data = await self._get_vm_metrics_and_data(task_id)

        if not vm_metrics:
            logger.info("resource_analysis_no_metrics", task_id=task_id)
            await self._add_log(task_id, "warn", "没有可用的VM指标数据，无法执行分析")
            return {
                "success": True,
                "data": {
                    "resourceOptimization": [],
                    "tidal": [],
                    "summary": {
                        "resourceOptimizationCount": 0,
                        "tidalCount": 0,
                        "totalVmsAnalyzed": 0,
                    },
                },
            }

        logger.info("resource_analysis_analyzing", task_id=task_id, vm_count=len(vm_metrics))
        await self._add_log(task_id, "info", f"正在分析 {len(vm_metrics)} 台虚拟机的资源配置和潮汐模式...")

        # Run analysis
        result = await analyzer.analyze(task_id, vm_metrics, vm_data)

        # Save findings
        await self._save_findings(task_id, job["id"], "rightsize", result.get("resourceOptimization", []))
        await self._save_findings(task_id, job["id"], "tidal", result.get("tidal", []))

        summary = result.get("summary", {})
        logger.info(
            "resource_analysis_completed",
            task_id=task_id,
            resource_optimization_count=summary.get("resourceOptimizationCount", 0),
            tidal_count=summary.get("tidalCount", 0),
        )
        await self._add_log(
            task_id, "info",
            f"资源分析完成：资源优化 {summary.get('resourceOptimizationCount', 0)} 台，"
            f"潮汐检测 {summary.get('tidalCount', 0)} 台"
        )

        return {"success": True, "data": result}

    async def get_analysis_results(
        self,
        task_id: int,
        analysis_type: str,
    ) -> Dict[str, Any]:
        """Get analysis results from database.

        Args:
            task_id: Task ID
            analysis_type: Analysis type (idle, resource, health)

        Returns:
            Analysis results
        """
        from sqlalchemy import select
        import json

        # Health score is special - it's a single platform-level result
        if analysis_type == "health":
            query = (
                select(AnalysisFinding)
                .where(
                    AnalysisFinding.task_id == task_id,
                    AnalysisFinding.job_type == "health",
                )
                .order_by(AnalysisFinding.confidence.desc())
            )
            result = await self.db.execute(query)
            findings = result.scalars().all()

            if findings:
                health_finding = findings[0]  # Should only be one
                if health_finding.details:
                    try:
                        health_data = json.loads(health_finding.details)
                        logger.info(
                            "health_score_data_loaded",
                            task_id=task_id,
                            has_overcommit_score="overcommitScore" in health_data,
                            has_balance_score="balanceScore" in health_data,
                            has_hotspot_score="hotspotScore" in health_data,
                            has_sub_scores="subScores" in health_data,
                            has_overcommit_results="overcommitResults" in health_data,
                            has_balance_results="balanceResults" in health_data,
                            has_hotspot_hosts="hotspotHosts" in health_data,
                        )
                        return {"success": True, "data": health_data}
                    except json.JSONDecodeError as e:
                        logger.error("health_score_json_parse_error", task_id=task_id, error=str(e))
                        return {"success": False, "error": {"code": "JSON_PARSE_ERROR", "message": f"Failed to parse health score data: {str(e)}"}}
                    except Exception as e:
                        logger.error("health_score_data_error", task_id=task_id, error=str(e))
                        return {"success": False, "error": {"code": "DATA_ERROR", "message": f"Health score data error: {str(e)}"}}
            logger.warning("health_score_no_details", task_id=task_id)
            return {"success": False, "error": {"code": "NO_DATA", "message": "Health score data not found"}}

        # Resource analysis returns structured data with two sub-types
        if analysis_type == "resource":
            sub_types = ["rightsize", "tidal"]
            resource_data: Dict[str, Any] = {"resourceOptimization": [], "tidal": []}

            for sub_type in sub_types:
                query = (
                    select(AnalysisFinding)
                    .where(
                        AnalysisFinding.task_id == task_id,
                        AnalysisFinding.job_type == sub_type,
                    )
                    .order_by(AnalysisFinding.confidence.desc())
                )
                result = await self.db.execute(query)
                findings = result.scalars().all()

                data = []
                for finding in findings:
                    item = {
                        "vmName": finding.vm_name,
                        "cluster": "",
                        "confidence": finding.confidence,
                        "severity": finding.severity,
                        "title": finding.title,
                        "description": finding.description,
                        "reason": finding.recommendation,
                    }
                    if finding.details:
                        try:
                            item.update(json.loads(finding.details))
                        except Exception:
                            pass
                    data.append(item)

                if sub_type == "rightsize":
                    resource_data["resourceOptimization"] = data
                elif sub_type == "tidal":
                    resource_data["tidal"] = data

            return {"success": True, "data": resource_data}

        # For idle analysis, return as list
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
                try:
                    item.update(json.loads(finding.details))
                except Exception:
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
        from app.models import Host

        # Get all VMs for this task
        vm_query = (
            select(VM)
            .where(VM.connection_id == select(AssessmentTask.connection_id).where(AssessmentTask.id == task_id).scalar_subquery())
        )
        vm_result = await self.db.execute(vm_query)
        vms = vm_result.scalars().all()

        # Get all Hosts for this connection (to get host_cpu_mhz for percentage conversion)
        connection_id = select(AssessmentTask.connection_id).where(AssessmentTask.id == task_id).scalar_subquery()
        host_query = (
            select(Host)
            .where(Host.connection_id == connection_id)
        )
        host_result = await self.db.execute(host_query)
        hosts = host_result.scalars().all()

        # Build host mappings (支持通过 IP 或 name 关联)
        # vCenter 存储 host_name，UIS 可能存储 host_ip
        host_cpu_by_ip = {host.ip_address: host.cpu_mhz for host in hosts if host.ip_address}
        host_cpu_by_name = {host.name: host.cpu_mhz for host in hosts if host.name}
        host_cluster_by_ip = {host.ip_address: host.cluster_name for host in hosts if host.ip_address}
        host_cluster_by_name = {host.name: host.cluster_name for host in hosts if host.name}

        # Build vm_data dict
        vm_data = {}
        for vm in vms:
            # 优先通过 host_name 匹配（vCenter），其次通过 host_ip 匹配（UIS）
            host_cpu_mhz = host_cpu_by_name.get(vm.host_name, 0)
            if host_cpu_mhz == 0:
                host_cpu_mhz = host_cpu_by_ip.get(vm.host_ip, 0)

            cluster_name = host_cluster_by_name.get(vm.host_name, "")
            if not cluster_name:
                cluster_name = host_cluster_by_ip.get(vm.host_ip, "")

            vm_data[vm.id] = {
                "name": vm.name,
                "cluster": cluster_name,
                "cpu_count": vm.cpu_count,
                "memory_bytes": vm.memory_bytes,
                "host_ip": vm.host_ip,
                "host_name": vm.host_name,
                "host_cpu_mhz": host_cpu_mhz,
                "power_state": vm.power_state,
                # 闲置检测所需字段
                "downtime_duration": vm.downtime_duration,
                "vm_create_time": vm.vm_create_time,
                "uptime_duration": vm.uptime_duration,
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
        """Save analysis findings to database.

        批量提交以避免 SQLite 长事务锁定问题。
        """
        import json

        if not findings:
            # 没有结果时也要更新 job 状态
            job_query = (
                select(TaskAnalysisJob)
                .where(TaskAnalysisJob.id == job_id)
            )
            job_result = await self.db.execute(job_query)
            job = job_result.scalar_one_or_none()
            if job:
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                job.result_summary = json.dumps({"count": 0})
            await self.db.commit()
            return

        # 分批保存 findings，避免长事务
        batch_size = 50  # 每批最多 50 条记录
        total_saved = 0

        for i in range(0, len(findings), batch_size):
            batch = findings[i:i + batch_size]

            for finding in batch:
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
                    if job_type == "idle":
                        idle_type = finding.get("idleType", "unknown")
                        idle_type_map = {
                            "powered_off": "长期关机",
                            "idle_powered_on": "开机闲置",
                            "low_activity": "低活跃度",
                        }
                        idle_text = idle_type_map.get(idle_type, idle_type)
                        title = f"闲置VM: {vm_name} ({idle_text})"
                    elif job_type == "rightsize":
                        title = f"资源优化: {vm_name}"
                    elif job_type == "tidal":
                        granularity = finding.get("tidalGranularity", "daily")
                        granularity_map = {"daily": "日粒度", "weekly": "周粒度", "monthly": "月粒度"}
                        title = f"潮汐检测: {vm_name} ({granularity_map.get(granularity, granularity)})"

                description = finding.get("description", "")
                recommendation = finding.get("reason", finding.get("recommendation", ""))

                # Build details JSON（保留 cluster 和 hostIp 等字段以便读取时恢复）
                details = {k: v for k, v in finding.items()
                          if k not in ["vmName", "confidence", "severity",
                                      "title", "description", "recommendation", "reason"]}

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
                    confidence=finding.get("confidence", 0.0),
                )
                self.db.add(db_finding)
                total_saved += 1

            # 每批提交一次
            await self.db.commit()

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
            job.result_summary = json.dumps({"count": total_saved})

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

        # Store full health data in details (preserve complete structure)
        details = health_data  # Use the complete health_data from analyzer

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

    async def run_idle_analysis(
        self,
        task_id: int,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run idle detection analysis.

        Args:
            task_id: Task ID
            config: Optional configuration override

        Returns:
            Analysis results
        """
        logger.info("idle_analysis_starting", task_id=task_id)
        await self._add_log(task_id, "info", "开始执行闲置检测分析...")

        # Get task
        task = await self._get_task(task_id)
        if not task:
            logger.warning("idle_analysis_task_not_found", task_id=task_id)
            await self._add_log(task_id, "error", "任务不存在，无法执行分析")
            return {"success": False, "error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}}

        # Get or create analysis job
        job = await self._get_or_create_job(task_id, "idle")
        if not job.get("is_new", False):
            # 有已运行的 job，强制重置并创建新 job
            logger.warning("idle_analysis_resetting_stale_job", task_id=task_id, job_id=job.get("id"))
            await self._add_log(task_id, "warn", "检测到未完成的闲置检测，将重新开始...")

            # 强制标记旧 job 为失败
            from sqlalchemy import select, update
            stmt = (
                update(TaskAnalysisJob)
                .where(TaskAnalysisJob.id == job["id"])
                .values(status="failed", error="Superseded by new analysis")
            )
            await self.db.execute(stmt)
            await self.db.commit()

            # 创建新 job
            job = await self._get_or_create_job(task_id, "idle")
            if not job.get("is_new", False):
                logger.error("idle_analysis_failed_to_create_job", task_id=task_id)
                return {"success": False, "error": {"code": "JOB_CREATE_FAILED", "message": "Failed to create analysis job"}}

        # Get configuration
        if config is None:
            config = AnalysisModes.get_mode("saving").get("idle", {
                "days": 14,
                "cpu_threshold": 10.0,
                "memory_threshold": 20.0,
                "min_confidence": 60.0,
            })

        logger.debug("idle_analysis_config", task_id=task_id, config=config)
        await self._add_log(task_id, "info", f"分析配置：{config.get('days', 14)}天数据，最小置信度{config.get('min_confidence', 60)}%")

        # Initialize analyzer
        analyzer = IdleDetector(
            days_threshold=config.get("days", 14),
            cpu_threshold=config.get("cpu_threshold", 10.0),
            memory_threshold=config.get("memory_threshold", 20.0),
            min_confidence=config.get("min_confidence", 60.0),
        )

        # Get VM metrics and data
        vm_metrics, vm_data = await self._get_vm_metrics_and_data(task_id)

        if not vm_metrics and not vm_data:
            logger.info("idle_analysis_no_data", task_id=task_id)
            await self._add_log(task_id, "warn", "没有可用的VM数据，无法执行分析")
            return {"success": True, "data": []}

        logger.info("idle_analysis_analyzing", task_id=task_id, vm_count=len(vm_data))
        await self._add_log(task_id, "info", f"正在分析 {len(vm_data)} 台虚拟机...")

        # Run analysis
        findings = await analyzer.analyze(task_id, vm_metrics, vm_data)

        # Save findings
        await self._save_findings(task_id, job["id"], "idle", findings)

        logger.info(
            "idle_analysis_completed",
            task_id=task_id,
            findings_count=len(findings),
        )
        await self._add_log(task_id, "info", f"闲置检测完成，发现 {len(findings)} 台闲置VM")

        return {"success": True, "data": findings}

    async def calculate_host_freeability(
        self,
        task_id: int,
        enabled_optimizations: List[str],
    ) -> Dict[str, Any]:
        """计算启用指定优化后可释放的物理主机。

        Args:
            task_id: Task ID
            enabled_optimizations: 启用的优化项列表，如 ["resource", "idle"]

        Returns:
            包含当前资源总量、节省量、可释放主机列表的 dict
        """
        import json

        task = await self._get_task(task_id)
        if not task:
            return {"success": False, "error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}}

        connection_id = task.connection_id

        # 查询所有主机
        host_query = select(Host).where(Host.connection_id == connection_id)
        host_result = await self.db.execute(host_query)
        hosts = host_result.scalars().all()

        # 查询所有 VM（用于统计总量）
        vm_query = select(VM).where(VM.connection_id == connection_id)
        vm_result = await self.db.execute(vm_query)
        vms = vm_result.scalars().all()

        # 当前平台总量
        total_cpu_cores = sum(h.cpu_cores for h in hosts)
        total_memory_gb = round(sum(h.memory_bytes for h in hosts) / (1024 ** 3), 2)
        total_hosts = len(hosts)
        total_vms = len(vms)

        # 各优化项的节省量
        freed_cpu_from_resource = 0
        freed_memory_from_resource = 0.0
        freed_cpu_from_idle = 0
        freed_memory_from_idle = 0.0

        if "resource" in enabled_optimizations:
            # 从 rightsize findings 计算节省
            rs_query = (
                select(AnalysisFinding)
                .where(
                    AnalysisFinding.task_id == task_id,
                    AnalysisFinding.job_type == "rightsize",
                )
            )
            rs_result = await self.db.execute(rs_query)
            rs_findings = rs_result.scalars().all()

            for finding in rs_findings:
                if finding.details:
                    try:
                        d = json.loads(finding.details)
                        current_cpu = d.get("currentCpu", 0)
                        recommended_cpu = d.get("recommendedCpu", 0)
                        current_mem = d.get("currentMemoryGb", 0.0)
                        recommended_mem = d.get("recommendedMemoryGb", 0.0)
                        freed_cpu_from_resource += max(0, current_cpu - recommended_cpu)
                        freed_memory_from_resource += max(0.0, current_mem - recommended_mem)
                    except Exception:
                        pass

        if "idle" in enabled_optimizations:
            # 从 idle findings 计算节省（闲置 VM 的完整资源）
            idle_query = (
                select(AnalysisFinding)
                .where(
                    AnalysisFinding.task_id == task_id,
                    AnalysisFinding.job_type == "idle",
                )
            )
            idle_result = await self.db.execute(idle_query)
            idle_findings = idle_result.scalars().all()

            for finding in idle_findings:
                if finding.details:
                    try:
                        d = json.loads(finding.details)
                        freed_cpu_from_idle += d.get("cpuCores", 0)
                        freed_memory_from_idle += d.get("memoryGb", 0.0)
                    except Exception:
                        pass

        total_freed_cpu = freed_cpu_from_resource + freed_cpu_from_idle
        total_freed_memory = round(freed_memory_from_resource + freed_memory_from_idle, 2)

        # 计算可释放主机（按配置从低到高排序，贪心匹配）
        # 主机排序：按 cpu_cores * cpu_mhz + memory_bytes 综合算力从低到高
        sorted_hosts = sorted(
            hosts,
            key=lambda h: (h.cpu_cores, h.memory_bytes)
        )

        # 建立主机→VM 映射（按主机 IP 和 name 关联）
        host_vm_count: Dict[str, int] = {}
        host_vm_cpu: Dict[str, int] = {}
        host_vm_mem: Dict[str, float] = {}

        for vm in vms:
            key = vm.host_name or vm.host_ip or ""
            if not key:
                continue
            host_vm_count[key] = host_vm_count.get(key, 0) + 1
            host_vm_cpu[key] = host_vm_cpu.get(key, 0) + vm.cpu_count
            host_vm_mem[key] = host_vm_mem.get(key, 0.0) + vm.memory_bytes / (1024 ** 3)

        remaining_cpu = total_freed_cpu
        remaining_mem = total_freed_memory
        freeable_hosts = []

        for host in sorted_hosts:
            host_key = host.name or host.ip_address or ""
            vm_count = host_vm_count.get(host_key, 0)
            if vm_count == 0:
                continue  # 无 VM 的主机跳过

            vm_cpu_needed = host_vm_cpu.get(host_key, 0)
            vm_mem_needed = host_vm_mem.get(host_key, 0.0)

            if remaining_cpu >= vm_cpu_needed and remaining_mem >= vm_mem_needed:
                freeable_hosts.append({
                    "hostName": host.name,
                    "hostIp": host.ip_address,
                    "cpuCores": host.cpu_cores,
                    "memoryGb": round(host.memory_bytes / (1024 ** 3), 2),
                    "currentVmCount": vm_count,
                    "reason": (
                        f"该主机上 {vm_count} 台 VM 共需 {vm_cpu_needed} 核 CPU / "
                        f"{vm_mem_needed:.1f} GB 内存，"
                        f"优化后可节省资源足以迁移这些 VM，主机可下线"
                    ),
                })
                remaining_cpu -= vm_cpu_needed
                remaining_mem -= vm_mem_needed

        freed_cpu_pct = round(total_freed_cpu / total_cpu_cores * 100, 1) if total_cpu_cores > 0 else 0.0
        freed_mem_pct = round(total_freed_memory / total_memory_gb * 100, 1) if total_memory_gb > 0 else 0.0

        return {
            "success": True,
            "data": {
                "current": {
                    "totalCpuCores": total_cpu_cores,
                    "totalMemoryGb": total_memory_gb,
                    "totalHosts": total_hosts,
                    "totalVms": total_vms,
                },
                "optimized": {
                    "freedCpuCores": total_freed_cpu,
                    "freedMemoryGb": total_freed_memory,
                    "freedCpuPercent": freed_cpu_pct,
                    "freedMemoryPercent": freed_mem_pct,
                },
                "freeableHosts": freeable_hosts,
                "breakdown": {
                    "resourceOptimization": {
                        "cpuCores": freed_cpu_from_resource,
                        "memoryGb": round(freed_memory_from_resource, 2),
                    },
                    "idleDetection": {
                        "cpuCores": freed_cpu_from_idle,
                        "memoryGb": round(freed_memory_from_idle, 2),
                    },
                },
            },
        }
