"""Excel Report Generator - Creates Excel reports using openpyxl."""

import structlog
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


logger = structlog.get_logger()


# Column definitions for each sheet
COLUMNS = {
    "clusters": [
        ("name", "名称"),
        ("datacenter", "数据中心"),
        ("total_cpu", "CPU (MHz)"),
        ("total_memory_gb", "内存 (GB)"),
        ("num_hosts", "主机数"),
        ("num_vms", "虚拟机数"),
    ],
    "hosts": [
        ("name", "名称"),
        ("datacenter", "数据中心"),
        ("ip_address", "IP地址"),
        ("cpu_cores", "CPU核数"),
        ("cpu_mhz", "频率 (MHz)"),
        ("memory_gb", "内存 (GB)"),
        ("num_vms", "虚拟机数"),
        ("power_state", "电源状态"),
        ("overall_status", "状态"),
    ],
    "vms": [
        ("name", "名称"),
        ("datacenter", "数据中心"),
        ("cpu_count", "CPU"),
        ("memory_gb", "内存 (GB)"),
        ("power_state", "电源状态"),
        ("guest_os", "操作系统"),
        ("ip_address", "IP地址"),
        ("host_ip", "主机IP"),
        ("connection_state", "连接状态"),
        ("overall_status", "状态"),
    ],
    "zombie": [
        ("vm_name", "虚拟机名称"),
        ("cluster", "集群"),
        ("host_ip", "主机IP"),
        ("cpu_cores", "CPU核数"),
        ("memory_gb", "内存 (GB)"),
        ("cpu_usage", "CPU使用率 (%)"),
        ("memory_usage", "内存使用率 (%)"),
        ("confidence", "置信度"),
        ("recommendation", "建议"),
    ],
    "rightsize": [
        ("vm_name", "虚拟机名称"),
        ("cluster", "集群"),
        ("current_cpu", "当前CPU"),
        ("suggested_cpu", "建议CPU"),
        ("current_memory", "当前内存 (GB)"),
        ("suggested_memory", "建议内存 (GB)"),
        ("adjustment_type", "调整类型"),
        ("risk_level", "风险等级"),
        ("confidence", "置信度"),
        ("recommendation", "建议"),
    ],
    "tidal": [
        ("vm_name", "虚拟机名称"),
        ("cluster", "集群"),
        ("pattern_type", "模式类型"),
        ("stability_score", "稳定性评分"),
        ("peak_hours", "高峰时段"),
        ("peak_days", "高峰日期"),
        ("recommendation", "建议"),
    ],
    "health": [
        ("metric", "指标"),
        ("score", "评分"),
        ("description", "描述"),
    ],
}


class ExcelReportGenerator:
    """Generates Excel reports using openpyxl."""

    def __init__(self) -> None:
        """Initialize Excel report generator."""
        if not OPENPYXL_AVAILABLE:
            raise ImportError("openpyxl is required for Excel report generation")

    def generate(
        self,
        data: Dict[str, Any],
        output_path: str,
    ) -> str:
        """Generate Excel report.

        Args:
            data: Report data from ReportBuilder
            output_path: Output file path

        Returns:
            Generated file path
        """
        wb = Workbook()
        wb.remove(wb.active)  # Remove default sheet

        # Create sheets in specific order
        self._create_summary_sheet(wb, data)
        self._create_clusters_sheet(wb, data)
        self._create_hosts_sheet(wb, data)
        self._create_vms_sheet(wb, data)
        self._create_zombie_sheet(wb, data)
        self._create_rightsize_sheet(wb, data)
        self._create_tidal_sheet(wb, data)
        self._create_health_sheet(wb, data)

        # Save workbook
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        wb.save(output_path)

        logger.info("excel_report_generated", path=str(output_path))
        return str(output_path)

    def _create_summary_sheet(self, wb: Workbook, data: Dict[str, Any]) -> None:
        """Create summary sheet."""
        ws = wb.create_sheet("概览", 0)

        # Title
        ws["A1"] = "资源评估报告"
        ws["A1"].font = Font(size=16, bold=True)
        ws.merge_cells("A1:B1")

        # Task info
        row = 3
        task = data.get("task", {})
        ws[f"A{row}"] = "任务名称"
        ws[f"B{row}"] = task.get("name", "")
        row += 1
        ws[f"A{row}"] = "平台"
        ws[f"B{row}"] = data.get("connection", {}).get("platform", "")
        row += 1
        ws[f"A{row}"] = "生成时间"
        ws[f"B{row}"] = data.get("generated_at", "")

        # Summary stats
        row += 2
        ws[f"A{row}"] = "资源统计"
        ws[f"A{row}"].font = Font(bold=True)
        row += 1

        summary = data.get("summary", {})
        stats = [
            ("集群数量", summary.get("total_clusters", 0)),
            ("主机数量", summary.get("total_hosts", 0)),
            ("虚拟机数量", summary.get("total_vms", 0)),
            ("开机VM", summary.get("powered_on_vms", 0)),
            ("关机VM", summary.get("powered_off_vms", 0)),
            ("总CPU (MHz)", summary.get("total_cpu_mhz", 0)),
            ("总内存 (GB)", summary.get("total_memory_gb", 0)),
        ]

        for label, value in stats:
            ws[f"A{row}"] = label
            ws[f"B{row}"] = value
            row += 1

        self._auto_fit_columns(ws)

    def _create_clusters_sheet(self, wb: Workbook, data: Dict[str, Any]) -> None:
        """Create clusters sheet."""
        ws = wb.create_sheet("集群")
        resources = data.get("resources", {})
        clusters = resources.get("clusters", [])

        self._write_table(ws, clusters, COLUMNS["clusters"])

    def _create_hosts_sheet(self, wb: Workbook, data: Dict[str, Any]) -> None:
        """Create hosts sheet."""
        ws = wb.create_sheet("主机")
        resources = data.get("resources", {})
        hosts = resources.get("hosts", [])

        self._write_table(ws, hosts, COLUMNS["hosts"])

    def _create_vms_sheet(self, wb: Workbook, data: Dict[str, Any]) -> None:
        """Create VMs sheet."""
        ws = wb.create_sheet("虚拟机")
        resources = data.get("resources", {})
        vms = resources.get("vms", [])

        self._write_table(ws, vms, COLUMNS["vms"])

    def _create_zombie_sheet(self, wb: Workbook, data: Dict[str, Any]) -> None:
        """Create zombie VM sheet."""
        ws = wb.create_sheet("僵尸VM")
        analysis = data.get("analysis", {})
        zombie = analysis.get("zombie", [])

        self._write_table(ws, zombie, COLUMNS["zombie"])

    def _create_rightsize_sheet(self, wb: Workbook, data: Dict[str, Any]) -> None:
        """Create right-size sheet."""
        ws = wb.create_sheet("Right Size")
        analysis = data.get("analysis", {})
        rightsize = analysis.get("rightsize", [])

        self._write_table(ws, rightsize, COLUMNS["rightsize"])

    def _create_tidal_sheet(self, wb: Workbook, data: Dict[str, Any]) -> None:
        """Create tidal pattern sheet."""
        ws = wb.create_sheet("潮汐模式")
        analysis = data.get("analysis", {})
        tidal = analysis.get("tidal", [])

        self._write_table(ws, tidal, COLUMNS["tidal"])

    def _create_health_sheet(self, wb: Workbook, data: Dict[str, Any]) -> None:
        """Create health score sheet."""
        ws = wb.create_sheet("健康评分")
        analysis = data.get("analysis", {})
        health = analysis.get("health", {})

        if not health:
            ws["A1"] = "无健康评分数据"
            return

        # Overall score
        row = 1
        ws[f"A{row}"] = "整体评分"
        ws[f"A{row}"].font = Font(bold=True)
        row += 1
        ws[f"A{row}"] = "总分"
        ws[f"B{row}"] = health.get("overallScore", 0)
        row += 1
        ws[f"A{row}"] = "等级"
        ws[f"B{row}"] = health.get("grade", "N/A")
        row += 1

        # Dimension scores
        row += 1
        ws[f"A{row}"] = "维度评分"
        ws[f"A{row}"].font = Font(bold=True)
        row += 1

        dimensions = [
            ("资源均衡度", health.get("balanceScore", 0)),
            ("超配风险", health.get("overcommitScore", 0)),
            ("热点集中度", health.get("hotspotScore", 0)),
        ]

        for label, score in dimensions:
            ws[f"A{row}"] = label
            ws[f"B{row}"] = score
            row += 1

        # Findings
        findings = health.get("findings", [])
        if findings:
            row += 1
            ws[f"A{row}"] = "发现的问题"
            ws[f"A{row}"].font = Font(bold=True)
            row += 1

            for finding in findings:
                ws[f"A{row}"] = finding.get("title", "")
                ws[f"B{row}"] = finding.get("description", "")
                row += 1

        self._auto_fit_columns(ws)

    def _write_table(
        self,
        ws,
        data: List[Dict[str, Any]],
        columns: List[tuple],
    ) -> None:
        """Write data table to worksheet.

        Args:
            ws: Worksheet object
            data: List of data dicts
            columns: List of (field, header) tuples
        """
        if not data:
            ws["A1"] = "无数据"
            return

        # Header style
        header_font = Font(bold=True)
        header_fill = PatternFill(start_color="CCE5FF", end_color="CCE5FF", fill_type="solid")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin'),
        )

        # Write headers
        for col_idx, (_, header) in enumerate(columns, 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border
            cell.alignment = Alignment(horizontal='center')

        # Write data
        for row_idx, item in enumerate(data, 2):
            for col_idx, (field, _) in enumerate(columns, 1):
                value = item.get(field, "")
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.value = value
                cell.border = border

        self._auto_fit_columns(ws)

    def _auto_fit_columns(self, ws) -> None:
        """Auto-fit column widths."""
        for column in ws.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)

            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass

            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
