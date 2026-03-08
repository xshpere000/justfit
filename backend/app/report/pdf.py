"""PDF Report Generator - Creates PDF reports using reportlab."""

import structlog
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, PageBreak, KeepTogether
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


logger = structlog.get_logger()


class PDFReportGenerator:
    """Generates PDF reports using reportlab."""

    def __init__(self, font_path: str | None = None) -> None:
        """Initialize PDF report generator.

        Args:
            font_path: Path to Chinese font file (e.g., simhei.ttf)
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for PDF report generation")

        self.font_path = font_path
        self._setup_fonts()

    def _setup_fonts(self) -> None:
        """Setup fonts for Chinese support."""
        # Try to register Chinese font
        if self.font_path and Path(self.font_path).exists():
            try:
                pdfmetrics.registerFont(TTFont('SimHei', self.font_path))
                self.font_name = 'SimHei'
            except:
                self.font_name = 'Helvetica'
        else:
            # Try default font locations
            default_paths = [
                '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/System/Library/Fonts/PingFang.ttc',  # macOS
            ]
            for path in default_paths:
                try:
                    pdfmetrics.registerFont(TTFont('SimHei', path))
                    self.font_name = 'SimHei'
                    return
                except:
                    continue
            self.font_name = 'Helvetica'

    def generate(
        self,
        data: Dict[str, Any],
        output_path: str,
    ) -> str:
        """Generate PDF report.

        Args:
            data: Report data from ReportBuilder
            output_path: Output file path

        Returns:
            Generated file path
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )

        # Build story
        story = []
        styles = self._get_styles()

        # Title page
        story.extend(self._build_title(data, styles))
        story.append(Spacer(1*cm, 1*cm))

        # Summary
        story.extend(self._build_summary(data, styles))
        story.append(Spacer(1*cm, 1*cm))

        # Resources
        story.extend(self._build_resources(data, styles))
        story.append(PageBreak())

        # Analysis results
        story.extend(self._build_analysis(data, styles))

        # Build PDF
        doc.build(story)

        logger.info("pdf_report_generated", path=str(output_path))
        return str(output_path)

    def _get_styles(self) -> dict:
        """Get paragraph styles."""
        styles = getSampleStyleSheet()

        # Custom styles
        styles.add(ParagraphStyle(
            name='CNTitle',
            parent=styles['Heading1'],
            fontName=self.font_name,
            fontSize=24,
            textColor=colors.HexColor('#1a73e8'),
            spaceAfter=0.5*cm,
        ))

        styles.add(ParagraphStyle(
            name='CNHeading',
            parent=styles['Heading2'],
            fontName=self.font_name,
            fontSize=16,
            textColor=colors.HexColor('#333333'),
            spaceAfter=0.3*cm,
        ))

        styles.add(ParagraphStyle(
            name='CNBody',
            parent=styles['BodyText'],
            fontName=self.font_name,
            fontSize=10,
            leading=14,
        ))

        styles.add(ParagraphStyle(
            name='CNTableHeader',
            parent=styles['Normal'],
            fontName=self.font_name,
            fontSize=10,
            textColor=colors.white,
            backColor=colors.HexColor('#1a73e8'),
        ))

        return styles

    def _build_title(self, data: Dict[str, Any], styles: dict) -> List:
        """Build title section."""
        story = []

        # Main title
        title = Paragraph("云平台资源评估报告", styles['CNTitle'])
        story.append(title)

        # Task info
        task = data.get("task", {})
        connection = data.get("connection", {})

        info_data = [
            ["任务名称", task.get("name", "")],
            ["平台", connection.get("platform", "").upper()],
            ["状态", task.get("status", "")],
            ["生成时间", data.get("generated_at", "")[:19]],
        ]

        info_table = Table(info_data, colWidths=[5*cm, 10*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ]))

        story.append(info_table)

        return story

    def _build_summary(self, data: Dict[str, Any], styles: dict) -> List:
        """Build summary section."""
        story = []

        # Heading
        heading = Paragraph("资源统计", styles['CNHeading'])
        story.append(heading)

        # Summary data
        summary = data.get("summary", {})

        summary_data = [
            ["指标", "数值"],
            ["集群数量", str(summary.get("total_clusters", 0))],
            ["主机数量", str(summary.get("total_hosts", 0))],
            ["虚拟机数量", str(summary.get("total_vms", 0))],
            ["开机 VM", str(summary.get("powered_on_vms", 0))],
            ["关机 VM", str(summary.get("powered_off_vms", 0))],
            ["总 CPU (MHz)", str(summary.get("total_cpu_mhz", 0))],
            ["总内存 (GB)", str(summary.get("total_memory_gb", 0))],
        ]

        summary_table = Table(summary_data, colWidths=[8*cm, 7*cm])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f0f0f0')),
        ]))

        story.append(summary_table)

        return story

    def _build_resources(self, data: Dict[str, Any], styles: dict) -> List:
        """Build resources section."""
        story = []

        resources = data.get("resources", {})

        # Clusters
        clusters = resources.get("clusters", [])
        if clusters:
            heading = Paragraph("集群列表", styles['CNHeading'])
            story.append(heading)

            cluster_data = [["名称", "数据中心", "CPU (MHz)", "内存 (GB)", "主机数", "VM数"]]
            for c in clusters[:10]:  # Limit to 10
                cluster_data.append([
                    c.get("name", ""),
                    c.get("datacenter", ""),
                    str(c.get("total_cpu", 0)),
                    str(c.get("total_memory_gb", 0)),
                    str(c.get("num_hosts", 0)),
                    str(c.get("num_vms", 0)),
                ])

            cluster_table = Table(cluster_data, colWidths=[3*cm, 2.5*cm, 2*cm, 2*cm, 1.5*cm, 1*cm])
            cluster_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ]))
            story.append(cluster_table)
            story.append(Spacer(0.5*cm, 0.5*cm))

        # Hosts summary
        hosts = resources.get("hosts", [])
        if hosts:
            heading = Paragraph("主机列表", styles['CNHeading'])
            story.append(heading)

            host_data = [["名称", "IP地址", "CPU核数", "内存 (GB)", "VM数"]]
            for h in hosts[:10]:
                host_data.append([
                    h.get("name", ""),
                    h.get("ip_address", ""),
                    str(h.get("cpu_cores", 0)),
                    str(h.get("memory_gb", 0)),
                    str(h.get("num_vms", 0)),
                ])

            host_table = Table(host_data, colWidths=[3*cm, 2.5*cm, 1.5*cm, 2*cm, 1*cm])
            host_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ]))
            story.append(host_table)

        return story

    def _build_analysis(self, data: Dict[str, Any], styles: dict) -> List:
        """Build analysis results section."""
        story = []
        analysis = data.get("analysis", {})

        # Zombie VMs
        zombie = analysis.get("zombie", [])
        heading = Paragraph(f"僵尸 VM 分析 ({len(zombie)} 个)", styles['CNHeading'])
        story.append(heading)

        if zombie:
            zombie_data = [["VM名称", "集群", "CPU使用率", "内存使用率", "置信度", "建议"]]
            for z in zombie[:10]:
                zombie_data.append([
                    z.get("vm_name", ""),
                    z.get("cluster", ""),
                    f"{z.get('cpu_usage', 0):.1f}%",
                    f"{z.get('memory_usage', 0):.1f}%",
                    f"{z.get('confidence', 0):.0f}",
                    z.get("recommendation", "")[:30],
                ])

            zombie_table = Table(zombie_data, colWidths=[3*cm, 2*cm, 1.5*cm, 1.5*cm, 1*cm, 3*cm])
            zombie_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d32f2f')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ]))
            story.append(zombie_table)
        else:
            story.append(Paragraph("未发现僵尸 VM", styles['CNBody']))

        story.append(Spacer(0.5*cm, 0.5*cm))

        # Right Size
        rightsize = analysis.get("rightsize", [])
        heading = Paragraph(f"Right Size 分析 ({len(rightsize)} 个)", styles['CNHeading'])
        story.append(heading)

        if rightsize:
            rightsize_data = [["VM名称", "当前CPU", "建议CPU", "当前内存", "建议内存", "风险", "建议"]]
            for r in rightsize[:10]:
                rightsize_data.append([
                    r.get("vm_name", ""),
                    str(r.get("current_cpu", 0)),
                    str(r.get("suggested_cpu", 0)),
                    f"{r.get('current_memory', 0):.0f}",
                    f"{r.get('suggested_memory', 0):.0f}",
                    r.get("risk_level", ""),
                    r.get("recommendation", "")[:20],
                ])

            rightsize_table = Table(rightsize_data, colWidths=[2.5*cm, 1*cm, 1*cm, 1.5*cm, 1.5*cm, 1*cm, 3*cm])
            rightsize_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f57c00')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ]))
            story.append(rightsize_table)
        else:
            story.append(Paragraph("无 Right Size 建议", styles['CNBody']))

        story.append(Spacer(0.5*cm, 0.5*cm))

        # Health Score
        health = analysis.get("health", {})
        if health:
            heading = Paragraph("平台健康评分", styles['CNHeading'])
            story.append(heading)

            health_data = [
                ["指标", "评分"],
                ["整体评分", f"{health.get('overallScore', 0):.1f}"],
                ["等级", health.get('grade', 'N/A')],
                ["资源均衡度", f"{health.get('balanceScore', 0):.1f}"],
                ["超配风险", f"{health.get('overcommitScore', 0):.1f}"],
                ["热点集中度", f"{health.get('hotspotScore', 0):.1f}"],
            ]

            health_table = Table(health_data, colWidths=[8*cm, 7*cm])
            health_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#388e3c')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ]))
            story.append(health_table)

            # Findings
            findings = health.get("findings", [])
            if findings:
                story.append(Spacer(0.5*cm, 0.5*cm))
                for f in findings:
                    finding_text = f"• {f.get('title', '')}: {f.get('description', '')}"
                    story.append(Paragraph(finding_text, styles['CNBody']))

        return story
