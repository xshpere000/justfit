"""PDF Report Generator - Creates professional technical reports.

This module generates comprehensive PDF reports with:
- Cover page with logo and health score gauge
- Table of contents
- Detailed analysis sections with charts
- Headers and footers
- Technical field explanations
"""

import structlog
import sys
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass


def _get_assets_dir() -> Path:
    """Get assets directory path, handles both dev and PyInstaller frozen exe."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / 'app' / 'report' / 'assets'
    return Path(__file__).parent / 'assets'

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, PageBreak, KeepTogether, Image, Flowable,
        Indenter
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
    from reportlab.platypus.frames import Frame
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.graphics.shapes import Drawing, Line
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    # Define dummy class for type checking
    class _DummyColors:
        class HexColor:
            def __init__(self, x, *args, **kwargs):
                pass
    colors = _DummyColors()

# Import charts module (only if reportlab is available)
if REPORTLAB_AVAILABLE:
    from app.report.charts import PDFCharts
    # Use colors from charts module for consistency
    from app.report.charts import COLORS as CHART_COLORS, GRADE_COLORS as CHART_GRADE_COLORS
else:
    PDFCharts = None
    CHART_COLORS = {}
    CHART_GRADE_COLORS = {}


logger = structlog.get_logger()


@dataclass
class ReportSection:
    """Report section for table of contents."""
    title: str
    subsections: List[str] = None
    page_number: int = 0

    def __post_init__(self):
        if self.subsections is None:
            self.subsections = []


class PDFReportGenerator:
    """Generates professional PDF reports with charts and visualizations."""

    # Color scheme - defined as class variables, evaluated at class definition time
    # Only use these if reportlab is available
    if REPORTLAB_AVAILABLE:
        COLOR_PRIMARY = colors.HexColor("#1E3A8A")
        COLOR_SUCCESS = colors.HexColor("#10B981")
        COLOR_WARNING = colors.HexColor("#F59E0B")
        COLOR_DANGER = colors.HexColor("#EF4444")
        COLOR_INFO = colors.HexColor("#3B82F6")
        COLOR_GRAY = colors.HexColor("#6B7280")
        COLOR_BG_LIGHT = colors.HexColor("#F9FAFB")
        COLOR_BORDER = colors.HexColor("#E5E7EB")
        COLOR_TEXT_DARK = colors.HexColor("#111827")
        COLOR_TEXT_SECONDARY = colors.HexColor("#6B7280")

        # ============================================================
        # 统一图表色系 (Chart Color Palette)
        # 用于所有图表，保持视觉一致性
        # ============================================================
        # 主色系 - 按优先级排序
        CHART_COLOR_1 = colors.HexColor("#3B82F6")  # 蓝色 - 主要数据
        CHART_COLOR_2 = colors.HexColor("#10B981")  # 绿色 - 正面/健康
        CHART_COLOR_3 = colors.HexColor("#F59E0B")  # 橙色 - 警告/注意
        CHART_COLOR_4 = colors.HexColor("#EF4444")  # 红色 - 危险/问题
        CHART_COLOR_5 = colors.HexColor("#8B5CF6")  # 紫色 - 辅助数据
        CHART_COLOR_6 = colors.HexColor("#EC4899")  # 粉色 - 辅助数据

        # 图表色系列表（按顺序使用）
        CHART_COLORS = [
            CHART_COLOR_1,  # 蓝
            CHART_COLOR_2,  # 绿
            CHART_COLOR_3,  # 橙
            CHART_COLOR_4,  # 红
            CHART_COLOR_5,  # 紫
            CHART_COLOR_6,  # 粉
        ]
    else:
        COLOR_PRIMARY = None
        COLOR_SUCCESS = None
        COLOR_WARNING = None
        COLOR_DANGER = None
        COLOR_INFO = None
        COLOR_GRAY = None
        COLOR_BG_LIGHT = None
        COLOR_BORDER = None
        COLOR_TEXT_DARK = None
        COLOR_TEXT_SECONDARY = None
        CHART_COLOR_1 = None
        CHART_COLOR_2 = None
        CHART_COLOR_3 = None
        CHART_COLOR_4 = None
        CHART_COLOR_5 = None
        CHART_COLOR_6 = None
        CHART_COLORS = []

    # Grade text mapping
    GRADE_TEXT_MAP = {
        "excellent": "优秀",
        "good": "良好",
        "fair": "一般",
        "poor": "较差",
        "critical": "危急",
        "no_data": "无数据",
    }

    def __init__(self, font_path: Optional[str] = None, logo_path: Optional[str] = None) -> None:
        """Initialize PDF report generator.

        Args:
            font_path: Path to Chinese font file (e.g., simhei.ttf)
            logo_path: Path to logo image file
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for PDF report generation")

        self.font_path = font_path
        self.logo_path = logo_path or self._find_logo()
        self._setup_fonts()
        self._init_charts()

        # Report metadata
        self.report_title = ""
        self.sections: List[ReportSection] = []
        self.current_page = 0

    def _find_logo(self) -> Optional[str]:
        """Find logo file in default locations."""
        possible_paths = [
            _get_assets_dir() / "logo.png",
            Path(__file__).parent.parent.parent / "frontend" / "src" / "assets" / "images" / "logo.png",
        ]
        for path in possible_paths:
            if path.exists():
                return str(path)
        return None

    def _setup_fonts(self) -> None:
        """Setup fonts for Chinese support."""
        # Try to register Chinese font
        if self.font_path and Path(self.font_path).exists():
            try:
                pdfmetrics.registerFont(TTFont('CNFont', self.font_path))
                pdfmetrics.registerFont(TTFont('CNFont-Bold', self.font_path))
                self.font_name = 'CNFont'
                self.font_bold = 'CNFont-Bold'
                return
            except Exception:
                pass

        # Try default font locations - check bundled font first
        assets_dir = _get_assets_dir()
        default_paths = [
            str(assets_dir / "simhei.ttf"),
            str(assets_dir / "SourceHanSansCN-Regular.otf"),
            str(assets_dir / "wqy-microhei.ttc"),
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/System/Library/Fonts/PingFang.ttc',
        ]
        for path in default_paths:
            try:
                pdfmetrics.registerFont(TTFont('CNFont', path))
                pdfmetrics.registerFont(TTFont('CNFont-Bold', path))
                self.font_name = 'CNFont'
                self.font_bold = 'CNFont-Bold'
                logger.info("font_registered", font=path)
                return
            except Exception:
                continue

        # Fallback to default fonts
        logger.warning("chinese_font_not_found", using="Helvetica")
        self.font_name = 'Helvetica'
        self.font_bold = 'Helvetica-Bold'

    def _init_charts(self) -> None:
        """Initialize chart drawer."""
        try:
            self.charts = PDFCharts(font_name=self.font_name)
        except Exception as e:
            logger.warning("failed_to_init_charts", error=str(e))
            self.charts = None

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

        self.report_title = f"云平台资源评估报告 - {data.get('connection', {}).get('name', 'Unknown')}"
        self.sections = []
        self.current_page = 0

        # Create PDF document with custom template
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=1.8*cm,
            leftMargin=1.8*cm,
            topMargin=2.5*cm,
            bottomMargin=2*cm,
        )

        # Build story
        story = []
        styles = self._get_styles()

        # 1. Cover page
        story.extend(self._build_cover_page(data, styles))
        story.append(PageBreak())

        # 2. Define sections first (before building TOC)
        # Section 1: Assessment Summary
        self.sections.append(ReportSection(
            "1. 评估概要",
            subsections=["1.1 评估范围", "1.2 关键发现"]
        ))

        # Section 2: Health Score
        health_data = data.get("analysis", {}).get("health")
        if health_data:
            self.sections.append(ReportSection(
                "2. 平台健康评分",
                subsections=["2.1 整体评分", "2.2 维度评分", "2.3 详细发现", "2.4 优化建议"]
            ))

        # Section 3: Idle VM Analysis
        idle_data = data.get("analysis", {}).get("idle", [])
        if idle_data:
            self.sections.append(ReportSection(
                "3. 闲置VM分析",
                subsections=["3.1 统计摘要", "3.2 检测方法", "3.3 闲置VM详情", "3.4 闲置VM资源趋势"]
            ))

        # Section 4: Resource Optimization
        resource_data = data.get("analysis", {}).get("resource", {})
        if resource_data:
            self.sections.append(ReportSection(
                "4. 资源配置优化",
                subsections=["4.1 优化摘要", "4.2 优化方法", "4.3 优化建议详情", "4.4 优化建议VM资源趋势"]
            ))

        # Section 5: Usage Pattern
        usage_pattern = resource_data.get("usagePattern", []) if resource_data else []
        if usage_pattern:
            self.sections.append(ReportSection(
                "5. 使用模式分析",
                subsections=["5.1 模式分布", "5.2 模式说明", "5.3 详细列表", "5.4 特殊模式VM资源趋势"]
            ))

        # Section 6: Mismatch Analysis
        mismatch = resource_data.get("mismatch", []) if resource_data else []
        if mismatch:
            self.sections.append(ReportSection(
                "6. 配置错配分析",
                subsections=["6.1 错配类型分布", "6.2 错配说明", "6.3 错配详情", "6.4 错配VM资源趋势"]
            ))

        # Section 7: Resource Inventory
        inventory_subsections = []
        resources = data.get("resources", {})
        if resources.get("clusters"):
            inventory_subsections.append("7.1 集群列表")
        if resources.get("hosts"):
            inventory_subsections.append("7.2 主机列表")
        if resources.get("vms"):
            inventory_subsections.append("7.3 虚拟机列表")
        self.sections.append(ReportSection(
            "7. 资源清单",
            subsections=inventory_subsections
        ))

        # 3. Table of Contents (now sections are defined)
        story.extend(self._build_toc(styles))
        story.append(PageBreak())

        # 4. Assessment Summary
        story.extend(self._build_assessment_summary(data, styles))
        story.append(PageBreak())

        # 5. Health Score
        if health_data:
            story.extend(self._build_health_section(data, styles))
            story.append(PageBreak())

        # 6. Idle VM Analysis
        if idle_data:
            story.extend(self._build_idle_section(data, styles))
            story.append(PageBreak())

        # 7. Resource Optimization
        if resource_data:
            story.extend(self._build_resource_section(data, styles))
            story.append(PageBreak())

        # 8. Usage Pattern
        if usage_pattern:
            story.extend(self._build_usage_pattern_section(data, styles))
            story.append(PageBreak())

        # 9. Mismatch Analysis
        if mismatch:
            story.extend(self._build_mismatch_section(data, styles))
            story.append(PageBreak())

        # 10. Resource Inventory
        story.extend(self._build_inventory_section(data, styles))

        # Build PDF with page numbers
        doc.build(
            story,
            onFirstPage=self._on_page_header_footer,
            onLaterPages=self._on_page_header_footer,
        )

        logger.info("pdf_report_generated", path=str(output_path))
        return str(output_path)

    def _get_styles(self) -> dict:
        """Get paragraph styles."""
        styles = getSampleStyleSheet()

        # Helper function to add or update style
        def add_or_update_style(name, **kwargs):
            if name in styles:
                # Update existing style
                style = styles[name]
                for key, value in kwargs.items():
                    setattr(style, key, value)
            else:
                # Add new style
                styles.add(ParagraphStyle(name=name, **kwargs))

        # Custom styles
        add_or_update_style(
            'TitleMain',
            fontName=self.font_bold,
            fontSize=28,
            textColor=self.COLOR_PRIMARY,
            spaceAfter=1*cm,  # Increased spacing after title
            alignment=TA_CENTER,
        )

        add_or_update_style(
            'Subtitle',
            fontName=self.font_name,
            fontSize=14,
            textColor=self.COLOR_GRAY,
            spaceAfter=0.3*cm,
            alignment=TA_CENTER,
        )

        add_or_update_style(
            'SectionTitle',
            fontName=self.font_bold,
            fontSize=18,
            textColor=self.COLOR_PRIMARY,
            spaceBefore=0.8*cm,
            spaceAfter=0.5*cm,
        )

        add_or_update_style(
            'SubsectionTitle',
            fontName=self.font_bold,
            fontSize=14,
            textColor=self.COLOR_PRIMARY,
            spaceBefore=0.5*cm,
            spaceAfter=0.3*cm,
        )

        add_or_update_style(
            'BodyText',
            fontName=self.font_name,
            fontSize=10,
            leading=14,
            spaceAfter=0.2*cm,
        )

        add_or_update_style(
            'Explanation',
            fontName=self.font_name,
            fontSize=9,
            leading=12,
            textColor=self.COLOR_GRAY,
            spaceAfter=0.3*cm,
        )

        add_or_update_style(
            'Term',
            fontName=self.font_bold,
            fontSize=9,
            leading=12,
            textColor=self.COLOR_INFO,
        )

        add_or_update_style(
            'TermDef',
            fontName=self.font_name,
            fontSize=9,
            leading=12,
            textColor=self.COLOR_GRAY,
        )

        # 表格单元格样式 - 用于支持自动换行
        add_or_update_style(
            'TableCell',
            parent=styles['Normal'],
            fontName=self.font_name,
            fontSize=9,
            leading=12,
            alignment=TA_LEFT,
        )

        add_or_update_style(
            'TableCellSmall',
            parent=styles['Normal'],
            fontName=self.font_name,
            fontSize=8,
            leading=11,
            alignment=TA_LEFT,
        )

        add_or_update_style(
            'TableCellHeader',
            parent=styles['Normal'],
            fontName=self.font_bold,
            fontSize=9,
            leading=12,
            alignment=TA_LEFT,  # 居左对齐
            textColor=colors.white,  # 白色文字，配合蓝色表头背景
        )

        return styles

    def _table_cell(self, text: str, style: str = 'TableCell') -> Paragraph:
        """
        将文字包装为 Paragraph 对象，用于表格单元格自动换行。

        Args:
            text: 单元格文字内容
            style: 样式名称 ('TableCell', 'TableCellSmall', 'TableCellHeader')

        Returns:
            Paragraph 对象，支持自动换行
        """
        return Paragraph(str(text), self._get_styles()[style])

    def _on_page_header_footer(
        self,
        canvas: Canvas,
        doc: SimpleDocTemplate,
    ) -> None:
        """Draw header and footer on each page."""
        # Page dimensions
        width, height = A4

        # Save state
        canvas.saveState()

        # Header - line at top
        canvas.setStrokeColor(self.COLOR_BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(1.8*cm, height - 1.8*cm, width - 1.8*cm, height - 1.8*cm)

        # Header - report title
        canvas.setFont(self.font_name, 9)
        canvas.setFillColor(self.COLOR_GRAY)
        title = self.report_title[:50] + "..." if len(self.report_title) > 50 else self.report_title
        canvas.drawString(1.8*cm, height - 1.5*cm, title)

        # Header - date
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        canvas.drawRightString(width - 1.8*cm, height - 1.5*cm, date_str)

        # Footer - line at bottom
        canvas.setStrokeColor(self.COLOR_BORDER)
        canvas.line(1.8*cm, 2*cm, width - 1.8*cm, 2*cm)

        # Footer - page number
        canvas.setFont(self.font_name, 9)
        canvas.setFillColor(self.COLOR_GRAY)
        page_num = canvas.getPageNumber()
        canvas.drawCentredString(width / 2, 1.5*cm, f"第 {page_num} 页")

        # Footer - product name
        canvas.drawString(1.8*cm, 1.5*cm, "云平台资源评估工具")

        canvas.restoreState()

    def _build_cover_page(self, data: Dict, styles: dict) -> List:
        """Build cover page."""
        story = []

        # Logo
        if self.logo_path and Path(self.logo_path).exists():
            try:
                logo = Image(self.logo_path, width=4*cm, height=4*cm)
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1*cm, 0.8*cm))  # Reduced to fit on one page
            except Exception as e:
                logger.warning("failed_to_add_logo", error=str(e))

        # Main title
        title = Paragraph("云平台资源评估报告", styles['TitleMain'])
        story.append(title)

        # Subtitle
        connection = data.get("connection", {})
        task = data.get("task", {})
        subtitle = f"{connection.get('name', 'Unknown')} · {connection.get('platform', '').upper()} 平台"
        story.append(Paragraph(subtitle, styles['Subtitle']))

        story.append(Spacer(1*cm, 1*cm))  # Moderate spacing

        # Health Score Card
        health_data = data.get("analysis", {}).get("health")
        if health_data:
            story.extend(self._build_health_score_card(health_data, styles))
        else:
            # No health data placeholder
            no_data = Paragraph("暂无健康评分数据", styles['BodyText'])
            no_data.alignment = TA_CENTER
            story.append(no_data)

        story.append(Spacer(1*cm, 1*cm))  # Moderate spacing

        # Key Metrics Grid
        story.extend(self._build_key_metrics(data, styles))

        story.append(Spacer(1*cm, 0.8*cm))  # Reduced spacing

        # Footer info
        generated_at = (data.get("generated_at") or "")[:10]
        footer = Paragraph(f"报告生成时间: {generated_at}", styles['Subtitle'])
        story.append(footer)

        # Add blank space to push content to center
        story.append(Spacer(1*cm, 1.5*cm))  # Reduced bottom spacing

        return story

    def _build_health_score_card(self, health: Dict, styles: dict) -> List:
        """Build health score card with gauge chart."""
        story = []

        score = health.get("overallScore", 0)
        grade = health.get("grade", "no_data")
        grade_text = self.GRADE_TEXT_MAP.get(grade, grade)

        # Get grade color
        grade_color = CHART_GRADE_COLORS.get(grade, self.COLOR_GRAY)

        # Gauge chart
        if self.charts:
            gauge = self.charts.draw_gauge_chart(
                score=score,
                title="",
                max_score=100,
                width=10*cm,
                height=6*cm,
            )
            gauge.hAlign = 'CENTER'
            story.append(gauge)
            # Add spacing after the chart
            story.append(Spacer(0, 0.5*cm))

        # Score and grade - centered in a table with closer spacing
        score_style = ParagraphStyle(
            'HealthScore',
            parent=styles['BodyText'],
            fontName=self.font_bold,
            fontSize=12,
            alignment=TA_CENTER,
        )
        grade_style = ParagraphStyle(
            'HealthGrade',
            parent=styles['BodyText'],
            fontName=self.font_name,
            fontSize=12,
            alignment=TA_CENTER,
        )

        score_para = Paragraph(f"健康评分: {score:.1f}", score_style)
        grade_para = Paragraph(f"等级: {grade_text}", grade_style)

        # Combine horizontally using table with narrower columns for closer spacing
        score_table = Table([[score_para, grade_para]], colWidths=[5*cm, 5*cm])
        score_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        score_table.hAlign = 'CENTER'
        story.append(score_table)

        # Spacing before sub scores
        story.append(Spacer(0, 0.5*cm))

        # Sub scores - centered
        sub_scores = [
            ("负载均衡度", health.get("balanceScore", 0)),
            ("资源超配", health.get("overcommitScore", 0)),
            ("负载分布", health.get("hotspotScore", 0)),
        ]

        sub_data = []
        for label, value in sub_scores:
            sub_data.append(f"{label}: {value:.1f}")

        sub_text = " | ".join(sub_data)
        # Create centered style for sub scores
        sub_score_style = ParagraphStyle(
            'SubScore',
            parent=styles['Explanation'],
            alignment=TA_CENTER,
        )
        story.append(Paragraph(sub_text, sub_score_style))

        return story

    def _build_key_metrics(self, data: Dict, styles: dict) -> List:
        """Build key metrics grid."""
        story = []

        summary = data.get("summary", {})

        # Define metrics
        metrics = [
            ("集群数量", str(summary.get("total_clusters", 0))),
            ("主机数量", str(summary.get("total_hosts", 0))),
            ("虚拟机总数", str(summary.get("total_vms", 0))),
            ("开机VM", str(summary.get("powered_on_vms", 0))),
            ("总CPU (MHz)", f"{summary.get('total_cpu_mhz', 0):,.0f}"),
            ("总内存 (GB)", f"{summary.get('total_memory_gb', 0):,.1f}"),
        ]

        # Create cell style for metrics
        cell_style = ParagraphStyle(
            'MetricCell',
            parent=styles['Normal'],
            fontName=self.font_name,
            fontSize=10,
            alignment=TA_CENTER,
            leading=14,
        )

        # Create 2x3 grid
        for i in range(0, len(metrics), 3):
            row_data = []
            for j in range(3):
                if i + j < len(metrics):
                    label, value = metrics[i + j]
                    # Use Paragraph to parse HTML tags
                    cell_content = Paragraph(f"<b>{label}</b><br/>{value}", cell_style)
                    row_data.append(cell_content)
                else:
                    row_data.append("")

            table = Table([row_data], colWidths=[5*cm, 5*cm, 5*cm])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGNMENT', (0, 0), (-1, -1), 'CENTRE'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, self.COLOR_BORDER),
                ('BOX', (0, 0), (-1, -1), 0.5, self.COLOR_BORDER),
                ('BACKGROUND', (0, 0), (-1, -1), self.COLOR_BG_LIGHT),
            ]))
            story.append(table)
            story.append(Spacer(0.3*cm, 0.3*cm))

        return story

    def _build_toc(self, styles: dict) -> List:
        """Build table of contents in Word-style list format."""
        story = []

        # Title
        title = Paragraph("目　录", styles['SectionTitle'])
        story.append(title)

        story.append(Spacer(0.8*cm, 0.8*cm))

        # Add a horizontal line under title
        line = Drawing(15*cm, 0.5*cm)
        line.add(Line(0, 0.25*cm, 15*cm, 0.25*cm, strokeColor=self.COLOR_PRIMARY, strokeWidth=2))
        line.hAlign = 'CENTER'
        story.append(line)

        story.append(Spacer(0.5*cm, 0.5*cm))

        # Define TOC styles - use leftIndent to shift all content right
        toc_level1_style = ParagraphStyle(
            'TOCLevel1',
            parent=styles['Normal'],
            fontName=self.font_bold,
            fontSize=12,
            leftIndent=3*cm,  # Shift level 1 right by 3cm
            spaceAfter=0.3*cm,
            textColor=self.COLOR_TEXT_DARK,
        )

        toc_level2_style = ParagraphStyle(
            'TOCLevel2',
            parent=styles['Normal'],
            fontName=self.font_name,
            fontSize=11,
            leftIndent=4*cm,  # Shift level 2 right by 4cm (1cm more than level 1)
            spaceAfter=0.15*cm,
            textColor=self.COLOR_TEXT_SECONDARY,
        )

        # Build TOC entries
        for section in self.sections:
            # Level 1: Section title
            section_entry = Paragraph(f"{section.title}", toc_level1_style)
            story.append(section_entry)

            # Level 2: Sub-sections
            for subsection in section.subsections:
                subsection_entry = Paragraph(subsection, toc_level2_style)
                story.append(subsection_entry)

        # Add some space at the end
        story.append(Spacer(1*cm, 1*cm))

        return story

    def _build_assessment_summary(self, data: Dict, styles: dict) -> List:
        """Build assessment summary section."""
        story = []

        title = Paragraph("1. 评估概要", styles['SectionTitle'])
        story.append(title)

        # Assessment scope
        story.append(Paragraph("<b>1.1 评估范围</b>", styles['SubsectionTitle']))

        summary = data.get("summary", {})
        scope_text = (
            f"本次评估对 <b>{summary.get('total_clusters', 0)} 个集群</b>、"
            f"<b>{summary.get('total_hosts', 0)} 台主机</b>、"
            f"<b>{summary.get('total_vms', 0)} 台虚拟机</b> 进行了全面的资源分析和健康状况评估。"
        )
        story.append(Paragraph(scope_text, styles['BodyText']))

        story.append(Spacer(0.5*cm, 0.5*cm))

        # Resource overview chart - horizontal bar chart with统一色系
        if self.charts:
            resource_data = [
                ("集群数量", summary.get("total_clusters", 0)),
                ("主机数量", summary.get("total_hosts", 0)),
                ("虚拟机数量", summary.get("total_vms", 0)),
            ]
            # 使用统一图表色系 (蓝/绿/橙)
            bar_chart = self.charts.draw_horizontal_bar_chart(
                data=resource_data,
                title="资源分布总览",
                colors_list=self.CHART_COLORS[:3],  # 前3种颜色
                width=14*cm,
                height=6*cm,
            )
            bar_chart.hAlign = 'CENTER'
            story.append(bar_chart)

        story.append(Spacer(0.5*cm, 0.5*cm))

        # Key findings
        story.append(Paragraph("<b>1.2 关键发现</b>", styles['SubsectionTitle']))

        findings = []

        # Health finding
        health = data.get("analysis", {}).get("health")
        if health:
            grade = health.get("grade", "no_data")
            grade_text = self.GRADE_TEXT_MAP.get(grade, grade)
            findings.append(f"> 平台健康评分: <b>{health.get('overallScore', 0):.1f}</b> 分，等级为 <b>{grade_text}</b>")

        # Idle VM finding
        idle = data.get("analysis", {}).get("idle", [])
        if idle:
            findings.append(f"> 发现 <b>{len(idle)}</b> 台闲置虚拟机，可能造成资源浪费")

        # Right Size finding
        resource = data.get("analysis", {}).get("resource", {})
        right_size = resource.get("rightSize", [])
        if right_size:
            downsize = sum(1 for r in right_size if r.get("adjustmentType", "").startswith("down"))
            findings.append(f"> 有 <b>{downsize}</b> 台虚拟机存在资源配置过高的现象")

        if findings:
            for finding in findings:
                story.append(Paragraph(finding, styles['BodyText']))
        else:
            story.append(Paragraph("暂无关键发现", styles['BodyText']))

        return story

    def _build_health_section(self, data: Dict, styles: dict) -> List:
        """Build health score section."""
        story = []

        title = Paragraph("2. 平台健康评分", styles['SectionTitle'])
        story.append(title)

        health = data.get("analysis", {}).get("health", {})
        if not health:
            story.append(Paragraph("无健康评分数据", styles['BodyText']))
            return story

        # Overall score with gauge
        story.append(Paragraph("<b>2.1 整体评分</b>", styles['SubsectionTitle']))

        # Reduced spacing after subsection title
        story.append(Spacer(0, 0.2*cm))

        if self.charts:
            gauge = self.charts.draw_gauge_chart(
                score=health.get("overallScore", 0),
                title="平台健康评分",
                width=12*cm,
                height=6*cm,
            )
            gauge.hAlign = 'CENTER'
            story.append(gauge)

        # Spacing after gauge before description
        story.append(Spacer(0, 0.5*cm))

        # Score explanation
        grade = health.get("grade", "no_data")
        grade_desc = self._get_grade_description(grade)
        story.append(Paragraph(grade_desc, styles['BodyText']))

        story.append(Spacer(0.5*cm, 0.5*cm))

        # Sub-dimensions radar chart
        story.append(Paragraph("<b>2.2 维度评分</b>", styles['SubsectionTitle']))

        if self.charts:
            sub_scores = [
                health.get("overcommitScore", 0),
                health.get("balanceScore", 0),
                health.get("hotspotScore", 0),
            ]
            labels = ["资源超配", "负载均衡", "负载分布"]
            radar = self.charts.draw_radar_chart(
                scores=sub_scores,
                labels=labels,
                title="三维健康度",
                width=12*cm,
                height=10*cm,
            )
            radar.hAlign = 'CENTER'
            story.append(radar)

        story.append(Spacer(0.5*cm, 0.5*cm))

        # Dimension explanations
        story.extend(self._build_term_explanations([
            ("资源超配评分", "评估虚拟化平台的资源超配情况，超配过高可能导致性能风险。"),
            ("负载均衡度", "评估集群内VM分布的均衡程度，不均衡可能导致热点问题。"),
            ("负载分布", "评估主机间负载的分布情况，识别潜在的负载集中风险。"),
        ], styles))

        # Detailed findings
        findings = health.get("findings", [])
        if findings:
            story.append(Paragraph("<b>2.3 详细发现</b>", styles['SubsectionTitle']))

            for i, finding in enumerate(findings[:10], 1):
                severity = finding.get("severity", "info")
                severity_text = self._translate_severity(severity)
                desc = finding.get("description", "")
                story.append(Paragraph(f"{i}. [{severity_text}] {desc}", styles['BodyText']))

        # Recommendations
        recommendations = health.get("recommendations", [])
        if recommendations:
            story.append(Paragraph("<b>2.4 优化建议</b>", styles['SubsectionTitle']))
            for rec in recommendations[:5]:
                story.append(Paragraph(f"> {rec}", styles['BodyText']))

        return story

    def _build_idle_section(self, data: Dict, styles: dict) -> List:
        """Build idle VM analysis section."""
        story = []

        title = Paragraph("3. 闲置VM分析", styles['SectionTitle'])
        story.append(title)

        idle = data.get("analysis", {}).get("idle", [])
        if not idle:
            story.append(Paragraph("未发现闲置虚拟机", styles['BodyText']))
            return story

        # Summary statistics
        from app.report.builder import ReportBuilder
        builder = ReportBuilder(None)
        summary = builder.build_idle_summary(idle)

        story.append(Paragraph("<b>3.1 统计摘要</b>", styles['SubsectionTitle']))

        summary_text = (
            f"共发现 <b>{summary['total']}</b> 台闲置虚拟机，"
            f"其中关机型 <b>{summary['by_type']['powered_off']}</b> 台，"
            f"开机闲置型 <b>{summary['by_type']['idle_powered_on']}</b> 台，"
            f"低活跃度型 <b>{summary['by_type']['low_activity']}</b> 台。"
        )
        story.append(Paragraph(summary_text, styles['BodyText']))

        story.append(Spacer(0.5*cm, 0.5*cm))

        # Pie chart by type
        if self.charts:
            type_data = [
                summary['by_type']['powered_off'],
                summary['by_type']['idle_powered_on'],
                summary['by_type']['low_activity'],
            ]
            type_labels = ["关机型", "开机闲置", "低活跃度"]
            # 使用统一图表色系 (3种颜色)
            pie = self.charts.draw_pie_chart(
                data=type_data,
                labels=type_labels,
                title="闲置类型分布",
                colors_list=self.CHART_COLORS[:3],
                width=12*cm,
                height=8*cm,
            )
            pie.hAlign = 'CENTER'
            story.append(pie)

        story.append(Spacer(0.5*cm, 0.5*cm))

        # Savings estimate
        savings = summary['potential_savings']
        savings_text = (
            f"<b>潜在节省:</b> 如果处理这些闲置VM，可释放 "
            f"<b>{savings['cpu_cores']}</b> 个CPU核心和 <b>{savings['memory_gb']:.1f} GB</b> 内存。"
        )
        story.append(Paragraph(savings_text, styles['BodyText']))

        story.append(Spacer(0.5*cm, 0.5*cm))

        # Detection method explanation
        story.append(Paragraph("<b>3.2 检测方法</b>", styles['SubsectionTitle']))
        story.extend(self._build_term_explanations([
            ("关机型闲置", "虚拟机处于关机状态超过14天，且无开机迹象。"),
            ("开机闲置型", "虚拟机处于开机状态，但CPU和内存使用率均低于阈值（CPU<10%，内存<20%）。"),
            ("低活跃度型", "虚拟机有一定活动，但整体活跃度很低，活动分数低于30分。"),
            ("置信度", "分析结果的可信程度，范围0-100，数值越高表示结果越可靠。"),
        ], styles))

        story.append(Spacer(0.5*cm, 0.5*cm))

        # Detailed list
        story.append(Paragraph("<b>3.3 闲置VM详情</b>", styles['SubsectionTitle']))

        # Table header
        table_data = [
            [
                self._table_cell("VM名称", 'TableCellHeader'),
                self._table_cell("集群", 'TableCellHeader'),
                self._table_cell("类型", 'TableCellHeader'),
                self._table_cell("风险等级", 'TableCellHeader'),
                self._table_cell("置信度", 'TableCellHeader'),
                self._table_cell("天数", 'TableCellHeader'),
                self._table_cell("建议", 'TableCellHeader'),
            ],
        ]

        for item in idle[:20]:  # Limit to 20 items
            idle_type = item.get("idleType", "unknown")
            type_map = {
                "powered_off": "关机",
                "idle_powered_on": "开机闲置",
                "low_activity": "低活跃",
            }
            type_text = type_map.get(idle_type, idle_type)

            risk_map = {
                "critical": "危急",
                "high": "高",
                "medium": "中",
                "low": "低",
            }
            risk_text = risk_map.get(item.get("riskLevel", "low"), "低")

            rec = item.get("recommendation", "")  # 不再截断，让 Paragraph 自动换行

            table_data.append([
                self._table_cell(item.get("vmName", "")),
                self._table_cell(item.get("cluster", "")),
                self._table_cell(type_text),
                self._table_cell(risk_text),
                self._table_cell(f"{item.get('confidence', 0):.0f}%", 'TableCellSmall'),
                self._table_cell(f"{item.get('daysInactive', 0)} 天", 'TableCellSmall'),
                self._table_cell(rec),
            ])

        table = Table(table_data, colWidths=[4.5*cm, 3*cm, 1.5*cm, 1.2*cm, 1.2*cm, 1.5*cm, 4.4*cm])  # 总宽度 17.3cm
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # 居左对齐
            ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_BORDER),
            ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), self.font_bold),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0.2*cm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0.2*cm),
        ]))
        story.append(table)

        if len(idle) > 20:
            story.append(Spacer(0.3*cm, 0.3*cm))
            story.append(Paragraph(f"<i>... 还有 {len(idle) - 20} 台闲置VM未显示</i>", styles['Explanation']))

        # VM 资源分析图表
        story.extend(self._build_vm_resource_charts(data, idle[:25], styles, "3.4 闲置VM资源趋势"))

        return story

    def _build_resource_section(self, data: Dict, styles: dict) -> List:
        """Build resource optimization section."""
        story = []

        title = Paragraph("4. 资源配置优化 (Right Size)", styles['SectionTitle'])
        story.append(title)

        resource = data.get("analysis", {}).get("resource", {})
        right_size = resource.get("rightSize", [])

        if not right_size:
            story.append(Paragraph("未发现需要优化资源配置的虚拟机", styles['BodyText']))
            return story

        # Summary
        from app.report.builder import ReportBuilder
        builder = ReportBuilder(None)
        summary = builder.build_resource_summary(resource)
        rs_summary = summary["right_size"]

        story.append(Paragraph("<b>4.1 优化摘要</b>", styles['SubsectionTitle']))

        summary_text = (
            f"共有 <b>{rs_summary['total']}</b> 台虚拟机的资源配置需要优化，"
            f"其中 <b>{rs_summary['downsize_candidates']}</b> 台可缩容，"
            f"<b>{rs_summary['upsize_candidates']}</b> 台需扩容。"
        )
        story.append(Paragraph(summary_text, styles['BodyText']))

        # Savings
        savings = rs_summary['potential_savings']
        if savings['cpu_cores'] > 0 or savings['memory_gb'] > 0:
            savings_text = (
                f"<b>预计节省:</b> CPU核心 <b>{savings['cpu_cores']:.0f}</b> 个，"
                f"内存 <b>{savings['memory_gb']:.1f}</b> GB。"
            )
            story.append(Paragraph(savings_text, styles['BodyText']))

        story.append(Spacer(0.5*cm, 0.5*cm))

        # Comparison chart (first 10 VMs)
        if self.charts and len(right_size) > 0:
            sample = right_size[:10]
            current_cpu = [r.get("currentCpu", 0) for r in sample]
            suggested_cpu = [r.get("recommendedCpu", 0) for r in sample]
            labels = [r.get("vmName", "")[:10] for r in sample]

            comparison = self.charts.draw_comparison_chart(
                current=current_cpu,
                suggested=suggested_cpu,
                labels=labels,
                title="CPU配置对比 (前10台)",
                width=14*cm,
                height=6*cm,
            )
            comparison.hAlign = 'CENTER'
            story.append(comparison)

        story.append(Spacer(0.5*cm, 0.5*cm))

        # Method explanation
        story.append(Paragraph("<b>4.2 优化方法</b>", styles['SubsectionTitle']))
        story.extend(self._build_term_explanations([
            ("P95值", "第95百分位数值，表示95%的时间内的资源使用率都低于此值，用于确定推荐配置。"),
            ("缓冲比例", "在P95值基础上增加的缓冲空间，默认20%，用于应对突发负载。"),
            ("缩容", "当前配置高于建议配置，降低配置可节省资源。"),
            ("扩容", "当前配置低于建议配置，增加配置可避免性能瓶颈。"),
        ], styles))

        story.append(Spacer(0.5*cm, 0.5*cm))

        # Detailed list
        story.append(Paragraph("<b>4.3 优化建议详情</b>", styles['SubsectionTitle']))

        table_data = [
            [
                self._table_cell("VM名称", 'TableCellHeader'),
                self._table_cell("当前CPU", 'TableCellHeader'),
                self._table_cell("建议CPU", 'TableCellHeader'),
                self._table_cell("当前内存", 'TableCellHeader'),
                self._table_cell("建议内存", 'TableCellHeader'),
                self._table_cell("CPU P95", 'TableCellHeader'),
                self._table_cell("内存P95", 'TableCellHeader'),
                self._table_cell("调整类型", 'TableCellHeader'),
            ],
        ]

        for item in right_size[:20]:
            adj_type = item.get("adjustmentType", "none")
            type_map = {
                "down_significant": "大幅缩容",
                "down": "缩容",
                "up_significant": "大幅扩容",
                "up": "扩容",
                "none": "无需调整",
            }
            type_text = type_map.get(adj_type, adj_type)

            table_data.append([
                self._table_cell(item.get("vmName", "")),
                self._table_cell(str(item.get("currentCpu", 0)), 'TableCellSmall'),
                self._table_cell(str(item.get("recommendedCpu", 0)), 'TableCellSmall'),
                self._table_cell(f"{item.get('currentMemoryGb', 0):.1f}", 'TableCellSmall'),
                self._table_cell(f"{item.get('recommendedMemoryGb', 0):.1f}", 'TableCellSmall'),
                self._table_cell(f"{item.get('cpuP95', 0):.1f}%", 'TableCellSmall'),
                self._table_cell(f"{item.get('memoryP95', 0):.1f}%", 'TableCellSmall'),
                self._table_cell(type_text),
            ])

        table = Table(table_data, colWidths=[4*cm, 1.5*cm, 1.5*cm, 1.8*cm, 1.8*cm, 1.5*cm, 1.5*cm, 3.7*cm])  # 总宽度 17.3cm
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # 居左对齐
            ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_BORDER),
            ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), self.font_bold),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(table)

        if len(right_size) > 20:
            story.append(Spacer(0.3*cm, 0.3*cm))
            story.append(Paragraph(f"<i>... 还有 {len(right_size) - 20} 台VM未显示</i>", styles['Explanation']))

        # VM 资源分析图表
        story.extend(self._build_vm_resource_charts(data, right_size[:25], styles, "4.4 优化建议VM资源趋势"))

        return story

    def _build_usage_pattern_section(self, data: Dict, styles: dict) -> List:
        """Build usage pattern section."""
        story = []

        title = Paragraph("5. 使用模式分析", styles['SectionTitle'])
        story.append(title)

        resource = data.get("analysis", {}).get("resource", {})
        patterns = resource.get("usagePattern", [])

        if not patterns:
            story.append(Paragraph("未发现特殊使用模式的虚拟机", styles['BodyText']))
            return story

        # Summary
        from app.report.builder import ReportBuilder
        builder = ReportBuilder(None)
        summary = builder.build_resource_summary(resource)
        pattern_summary = summary["usage_pattern"]

        story.append(Paragraph("<b>5.1 模式分布</b>", styles['SubsectionTitle']))

        summary_text = (
            f"共识别 <b>{pattern_summary['total']}</b> 台具有特殊使用模式的虚拟机。"
        )
        story.append(Paragraph(summary_text, styles['BodyText']))

        story.append(Spacer(0.5*cm, 0.5*cm))

        # Pie chart
        if self.charts:
            pattern_data = [
                pattern_summary['by_pattern']['stable'],
                pattern_summary['by_pattern']['burst'],
                pattern_summary['by_pattern']['tidal'],
            ]
            pattern_labels = ["稳定", "突发", "潮汐"]
            # 使用统一图表色系 (3种颜色)
            pie = self.charts.draw_pie_chart(
                data=pattern_data,
                labels=pattern_labels,
                title="使用模式分布",
                colors_list=self.CHART_COLORS[:3],
                width=12*cm,
                height=8*cm,
            )
            pie.hAlign = 'CENTER'
            story.append(pie)

        story.append(Spacer(0.5*cm, 0.5*cm))

        # Pattern explanation
        story.append(Paragraph("<b>5.2 模式说明</b>", styles['SubsectionTitle']))
        story.extend(self._build_term_explanations([
            ("稳定模式", "资源使用率相对平稳，波动性较低，适合固定配置。"),
            ("突发模式", "资源使用率在短时间内急剧上升，可能需要自动扩缩容。"),
            ("潮汐模式", "资源使用呈现明显的周期性规律（如白天高、夜间低），适合调度优化。"),
            ("变异系数", "衡量数据波动程度的指标，值越大表示波动越剧烈。"),
        ], styles))

        story.append(Spacer(0.5*cm, 0.5*cm))

        # Detailed list
        story.append(Paragraph("<b>5.3 详细列表</b>", styles['SubsectionTitle']))

        table_data = [
            [
                self._table_cell("VM名称", 'TableCellHeader'),
                self._table_cell("模式", 'TableCellHeader'),
                self._table_cell("波动性", 'TableCellHeader'),
                self._table_cell("峰谷比", 'TableCellHeader'),
                self._table_cell("建议", 'TableCellHeader'),
            ],
        ]

        for item in patterns[:15]:
            pattern = item.get("usagePattern", "unknown")
            pattern_map = {"stable": "稳定", "burst": "突发", "tidal": "潮汐", "unknown": "未知"}
            pattern_text = pattern_map.get(pattern, pattern)

            volatility = item.get("volatilityLevel", "unknown")
            vol_map = {"high": "高", "moderate": "中", "low": "低"}
            vol_text = vol_map.get(volatility, volatility)

            rec = item.get("recommendation", "")  # 不再截断，让 Paragraph 自动换行

            table_data.append([
                self._table_cell(item.get("vmName", "")),
                self._table_cell(pattern_text),
                self._table_cell(vol_text),
                self._table_cell(f"{item.get('peakValleyRatio', 0):.1f}", 'TableCellSmall'),
                self._table_cell(rec),
            ])

        table = Table(table_data, colWidths=[5*cm, 2*cm, 1.5*cm, 1.8*cm, 7*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # 居左对齐
            ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_BORDER),
            ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), self.font_bold),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(table)

        if len(patterns) > 15:
            story.append(Spacer(0.3*cm, 0.3*cm))
            story.append(Paragraph(f"<i>... 还有 {len(patterns) - 15} 台VM未显示</i>", styles['Explanation']))

        # VM 资源分析图表
        story.extend(self._build_vm_resource_charts(data, patterns[:25], styles, "5.4 特殊模式VM资源趋势"))

        return story

    def _build_mismatch_section(self, data: Dict, styles: dict) -> List:
        """Build configuration mismatch section."""
        story = []

        title = Paragraph("6. 配置错配分析", styles['SectionTitle'])
        story.append(title)

        resource = data.get("analysis", {}).get("resource", {})
        mismatch = resource.get("mismatch", [])

        if not mismatch:
            story.append(Paragraph("未发现资源配置错配的虚拟机", styles['BodyText']))
            return story

        # Summary
        from app.report.builder import ReportBuilder
        builder = ReportBuilder(None)
        summary = builder.build_resource_summary(resource)
        mm_summary = summary["mismatch"]

        story.append(Paragraph("<b>6.1 错配类型分布</b>", styles['SubsectionTitle']))

        summary_text = (
            f"共发现 <b>{mm_summary['total']}</b> 台虚拟机存在资源配置错配问题。"
        )
        story.append(Paragraph(summary_text, styles['BodyText']))

        story.append(Spacer(0.5*cm, 0.5*cm))

        # Horizontal bar chart - 使用统一色系
        if self.charts:
            bar_data = [
                ("CPU富裕/内存紧张", mm_summary['cpu_rich_memory_poor']),
                ("CPU紧张/内存富裕", mm_summary['cpu_poor_memory_rich']),
                ("双重过剩", mm_summary['both_underutilized']),
                ("双重紧张", mm_summary['both_overutilized']),
            ]
            # 使用统一图表色系 (蓝/绿/橙/红)
            bar_chart = self.charts.draw_horizontal_bar_chart(
                data=bar_data,
                title="错配类型分布",
                colors_list=self.CHART_COLORS[:4],  # 前4种颜色
                width=14*cm,
                height=6*cm,
            )
            bar_chart.hAlign = 'CENTER'
            story.append(bar_chart)

        story.append(Spacer(0.5*cm, 0.5*cm))

        # Explanation
        story.append(Paragraph("<b>6.2 错配说明</b>", styles['SubsectionTitle']))
        story.extend(self._build_term_explanations([
            ("CPU富裕/内存紧张", "CPU使用率低但内存使用率高，建议降低CPU配置或增加内存。"),
            ("CPU紧张/内存富裕", "CPU使用率高但内存使用率低，建议增加CPU配置或降低内存。"),
            ("双重过剩", "CPU和内存使用率都偏低，资源被过度分配。"),
            ("双重紧张", "CPU和内存使用率都偏高，资源不足可能影响性能。"),
        ], styles))

        story.append(Spacer(0.5*cm, 0.5*cm))

        # Detailed list
        story.append(Paragraph("<b>6.3 错配详情</b>", styles['SubsectionTitle']))

        table_data = [
            [
                self._table_cell("VM名称", 'TableCellHeader'),
                self._table_cell("错配类型", 'TableCellHeader'),
                self._table_cell("CPU使用率", 'TableCellHeader'),
                self._table_cell("内存使用率", 'TableCellHeader'),
                self._table_cell("当前配置", 'TableCellHeader'),
                self._table_cell("建议", 'TableCellHeader'),
            ],
        ]

        for item in mismatch[:15]:
            mm_type = item.get("mismatchType", "unknown")
            type_map = {
                "cpu_rich_memory_poor": "CPU富/内存紧",
                "cpu_poor_memory_rich": "CPU紧/内存富",
                "both_underutilized": "双重过剩",
                "both_overutilized": "双重紧张",
            }
            type_text = type_map.get(mm_type, mm_type)

            config = f"{item.get('currentCpu', 0)}核/{item.get('currentMemory', 0):.0f}GB"
            rec = item.get("recommendation", "")  # 不再截断，让 Paragraph 自动换行

            table_data.append([
                self._table_cell(item.get("vmName", "")),
                self._table_cell(type_text),
                self._table_cell(f"{item.get('cpuUtilization', 0):.1f}%", 'TableCellSmall'),
                self._table_cell(f"{item.get('memoryUtilization', 0):.1f}%", 'TableCellSmall'),
                self._table_cell(config, 'TableCellSmall'),
                self._table_cell(rec),
            ])

        table = Table(table_data, colWidths=[4*cm, 2.5*cm, 1.5*cm, 1.5*cm, 2*cm, 5.8*cm])  # 总宽度 17.3cm
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # 居左对齐
            ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_BORDER),
            ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), self.font_bold),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(table)

        if len(mismatch) > 15:
            story.append(Spacer(0.3*cm, 0.3*cm))
            story.append(Paragraph(f"<i>... 还有 {len(mismatch) - 15} 台VM未显示</i>", styles['Explanation']))

        # VM 资源分析图表
        story.extend(self._build_vm_resource_charts(data, mismatch[:25], styles, "6.4 错配VM资源趋势"))

        return story

    def _build_inventory_section(self, data: Dict, styles: dict) -> List:
        """Build resource inventory section."""
        story = []

        title = Paragraph("7. 资源清单", styles['SectionTitle'])
        story.append(title)

        resources = data.get("resources", {})

        # Clusters
        clusters = resources.get("clusters", [])
        if clusters:
            story.append(Paragraph("<b>7.1 集群列表</b>", styles['SubsectionTitle']))

            table_data = [
                [
                    self._table_cell("集群名称", 'TableCellHeader'),
                    self._table_cell("数据中心", 'TableCellHeader'),
                    self._table_cell("总CPU", 'TableCellHeader'),
                    self._table_cell("总内存(GB)", 'TableCellHeader'),
                    self._table_cell("主机数", 'TableCellHeader'),
                    self._table_cell("VM数", 'TableCellHeader'),
                ],
            ]
            for c in clusters:
                table_data.append([
                    self._table_cell(c.get("name", "")),
                    self._table_cell(c.get("datacenter", "")),
                    self._table_cell(f"{c.get('total_cpu', 0):,.0f}"),
                    self._table_cell(f"{c.get('total_memory_gb', 0):,.1f}"),
                    self._table_cell(str(c.get('num_hosts', 0))),
                    self._table_cell(str(c.get('num_vms', 0))),
                ])

            table = Table(table_data, colWidths=[4.5*cm, 3*cm, 2.8*cm, 2.8*cm, 2.2*cm, 2*cm])  # 总宽度 17.3cm
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # 居左对齐
                ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_BORDER),
                ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), self.font_bold),
            ]))
            story.append(table)
            story.append(Spacer(0.5*cm, 0.5*cm))

        # Hosts
        hosts = resources.get("hosts", [])
        if hosts:
            story.append(Paragraph("<b>7.2 主机列表</b>", styles['SubsectionTitle']))

            table_data = [
                [
                    self._table_cell("主机名称", 'TableCellHeader'),
                    self._table_cell("IP地址", 'TableCellHeader'),
                    self._table_cell("CPU核数", 'TableCellHeader'),
                    self._table_cell("内存(GB)", 'TableCellHeader'),
                    self._table_cell("VM数", 'TableCellHeader'),
                    self._table_cell("状态", 'TableCellHeader'),
                ],
            ]
            for h in hosts[:30]:  # Limit to 30
                table_data.append([
                    self._table_cell(h.get("name", "")),
                    self._table_cell(h.get("ip_address", "")),
                    self._table_cell(str(h.get("cpu_cores", 0))),
                    self._table_cell(f"{h.get('memory_gb', 0):,.1f}"),
                    self._table_cell(str(h.get("num_vms", 0))),
                    self._table_cell(h.get("power_state", "")),
                ])

            table = Table(table_data, colWidths=[5*cm, 3*cm, 2*cm, 2.2*cm, 1.5*cm, 3.6*cm])  # 总宽度 17.3cm
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # 居左对齐
                ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_BORDER),
                ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), self.font_bold),
            ]))
            story.append(table)

            if len(hosts) > 30:
                story.append(Spacer(0.3*cm, 0.3*cm))
                story.append(Paragraph(f"<i>... 还有 {len(hosts) - 30} 台主机未显示</i>", styles['Explanation']))

            story.append(Spacer(0.5*cm, 0.5*cm))

        # VMs
        vms = resources.get("vms", [])
        if vms:
            story.append(Paragraph("<b>7.3 虚拟机列表</b>", styles['SubsectionTitle']))

            table_data = [
                [
                    self._table_cell("VM名称", 'TableCellHeader'),
                    self._table_cell("数据中心", 'TableCellHeader'),
                    self._table_cell("CPU", 'TableCellHeader'),
                    self._table_cell("内存(GB)", 'TableCellHeader'),
                    self._table_cell("状态", 'TableCellHeader'),
                    self._table_cell("IP地址", 'TableCellHeader'),
                ],
            ]
            for v in vms[:50]:  # Limit to 50
                table_data.append([
                    self._table_cell(v.get("name", "")),
                    self._table_cell(v.get("datacenter", "")),
                    self._table_cell(str(v.get("cpu_count", 0)), 'TableCellSmall'),
                    self._table_cell(f"{v.get('memory_gb', 0):,.1f}", 'TableCellSmall'),
                    self._table_cell(v.get("power_state", "")),
                    self._table_cell(v.get("ip_address", "") or "N/A"),
                ])

            table = Table(table_data, colWidths=[5*cm, 3*cm, 1.5*cm, 2*cm, 2*cm, 3.8*cm])  # 总宽度 17.3cm
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # 居左对齐
                ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_BORDER),
                ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), self.font_bold),
            ]))
            story.append(table)

            if len(vms) > 50:
                story.append(Spacer(0.3*cm, 0.3*cm))
                story.append(Paragraph(f"<i>... 还有 {len(vms) - 50} 台VM未显示</i>", styles['Explanation']))

        return story

    def _build_term_explanations(self, terms: List[Tuple[str, str]], styles: dict) -> List:
        """Build term explanation box."""
        story = []

        for term, definition in terms:
            term_para = f"<b>{term}:</b> {definition}"
            story.append(Paragraph(term_para, styles['Explanation']))

        return story

    def _get_grade_description(self, grade: str) -> str:
        """Get description for health grade."""
        descriptions = {
            "excellent": "平台运行状况优秀，资源配置合理，各项指标均处于健康状态。",
            "good": "平台运行状况良好，大部分指标正常，有少量优化空间。",
            "fair": "平台运行状况一般，存在一些资源分配不均或配置不合理的情况，建议优化。",
            "poor": "平台运行状况较差，存在明显的资源配置问题，需要重点关注和优化。",
            "critical": "平台运行状况危急，存在严重的资源问题，可能影响业务运行，急需处理。",
            "no_data": "暂无足够数据进行健康评分评估。",
        }
        return descriptions.get(grade, "未知等级")

    def _translate_severity(self, severity: str) -> str:
        """Translate severity to Chinese."""
        map_dict = {
            "critical": "危急",
            "high": "高",
            "medium": "中",
            "low": "低",
            "info": "信息",
        }
        return map_dict.get(severity, severity)

    def _build_vm_resource_charts(
        self,
        data: Dict,
        vm_list: List[Dict],
        styles: dict,
        subsection_title: str = "资源使用趋势",
    ) -> List:
        """Build VM resource usage trend charts.

        Args:
            data: Full report data dict
            vm_list: List of VM dicts with vm_id/vmId or vm_name/vmName
            styles: Document styles dict
            subsection_title: Title for the subsection

        Returns:
            List of flowables for the story
        """
        story = []

        vm_metrics = data.get("vm_metrics", {})
        vm_name_to_id = data.get("vm_name_to_id", {})

        if not vm_metrics and not vm_name_to_id:
            return story

        # Filter VMs that have metrics data
        vms_with_data = []
        for vm in vm_list:
            vm_id = vm.get("vm_id") or vm.get("vmId")
            vm_name = vm.get("vm_name") or vm.get("vmName", "")

            # Direct match by vm_id
            if vm_id and vm_id in vm_metrics:
                vms_with_data.append((vm_id, vm_name, vm_metrics[vm_id]))
            # Match by vm_name through vm_name_to_id mapping
            elif vm_name and vm_name in vm_name_to_id:
                mapped_vm_id = vm_name_to_id[vm_name]
                if mapped_vm_id in vm_metrics:
                    vms_with_data.append((mapped_vm_id, vm_name, vm_metrics[mapped_vm_id]))

        if not vms_with_data:
            return story

        # Add subsection title
        story.append(Spacer(0.5*cm, 0.5*cm))
        story.append(Paragraph(f"<b>{subsection_title}</b>", styles['SubsectionTitle']))

        # Limit to 20 VMs per section to avoid excessively long reports
        max_charts_per_section = 20
        for vm_id, vm_name, metrics in vms_with_data[:max_charts_per_section]:
            # Check if we have meaningful data
            if not any(metrics.values()):
                continue

            # Convert metrics to expected format
            cpu_data = metrics.get("cpu", [])
            memory_data = metrics.get("memory", [])
            disk_read_data = metrics.get("disk_read", [])
            disk_write_data = metrics.get("disk_write", [])
            net_rx_data = metrics.get("net_rx", [])
            net_tx_data = metrics.get("net_tx", [])

            # Skip if all data is empty
            if not any([cpu_data, memory_data, disk_read_data, disk_write_data, net_rx_data, net_tx_data]):
                continue

            # Normalize CPU and memory to percentages if needed
            cpu_normalized = [(t, min(100, v)) for t, v in cpu_data] if cpu_data else []
            memory_normalized = [(t, min(100, v)) for t, v in memory_data] if memory_data else []

            # Convert bytes to MB for disk and network (handle empty data)
            disk_read_mb = [(t, v / (1024*1024)) for t, v in disk_read_data] if disk_read_data else []
            disk_write_mb = [(t, v / (1024*1024)) for t, v in disk_write_data] if disk_write_data else []
            net_rx_mb = [(t, v / (1024*1024)) for t, v in net_rx_data] if net_rx_data else []
            net_tx_mb = [(t, v / (1024*1024)) for t, v in net_tx_data] if net_tx_data else []

            # Draw chart
            if self.charts:
                try:
                    chart = self.charts.draw_vm_resource_chart(
                        cpu_data=cpu_normalized,
                        memory_data=memory_normalized,
                        disk_read_data=disk_read_mb,
                        disk_write_data=disk_write_mb,
                        net_rx_data=net_rx_mb,
                        net_tx_data=net_tx_mb,
                        vm_name=vm_name,
                    )
                    chart.hAlign = 'CENTER'
                    story.append(chart)
                    story.append(Spacer(0.5*cm, 0.5*cm))
                except Exception as e:
                    logger.warning("failed_to_draw_vm_chart", vm_name=vm_name, error=str(e))

        if len(vms_with_data) > max_charts_per_section:
            story.append(Paragraph(
                f"<i>注：本章节共有 {len(vms_with_data)} 台VM的资源趋势图，"
                f"上方仅显示前 {max_charts_per_section} 台。"
                f"如需查看完整数据，请联系系统管理员获取原始数据文件。</i>",
                styles['Explanation']
            ))

        return story
