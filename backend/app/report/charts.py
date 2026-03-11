"""PDF Chart Drawing Module - Creates charts for report generation.

This module provides drawing utilities for various chart types using reportlab's
graphics primitives. No external charting library dependency for simple charts.
"""

from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path

try:
    from reportlab.graphics.shapes import Drawing, Rect, Circle, String, Line, Polygon
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.validators import Auto
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Configure matplotlib for Chinese fonts if available
try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    # Find Chinese font
    _font_path = Path(__file__).parent / "assets" / "simhei.ttf"
    if _font_path.exists():
        _font_prop = fm.FontProperties(fname=str(_font_path))
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False  # Fix minus sign display
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    _font_prop = None


# Color scheme
COLORS = {
    "primary": colors.HexColor("#1E3A8A"),
    "success": colors.HexColor("#10B981"),
    "warning": colors.HexColor("#F59E0B"),
    "danger": colors.HexColor("#EF4444"),
    "info": colors.HexColor("#3B82F6"),
    "purple": colors.HexColor("#8B5CF6"),
    "gray": colors.HexColor("#6B7280"),
    "bg_light": colors.HexColor("#F9FAFB"),
    # Additional colors for charts
    "title_color": colors.HexColor("#111827"),
    "axis_color": colors.HexColor("#9CA3AF"),
    "grid_color": colors.HexColor("#E5E7EB"),
}

GRADE_COLORS = {
    "excellent": colors.HexColor("#10B981"),
    "good": colors.HexColor("#3B82F6"),
    "fair": colors.HexColor("#F59E0B"),
    "poor": colors.HexColor("#EF4444"),
    "critical": colors.HexColor("#DC2626"),
}


@dataclass
class ChartStyle:
    """Chart style configuration."""

    width: float = 12 * cm
    height: float = 6 * cm
    font_name: str = "Helvetica"
    title_color: colors.Color = colors.HexColor("#111827")
    axis_color: colors.Color = colors.HexColor("#9CA3AF")
    grid_color: colors.Color = colors.HexColor("#E5E7EB")


class PDFCharts:
    """PDF chart drawing utilities."""

    def __init__(self, font_name: str = "Helvetica") -> None:
        """Initialize chart drawer.

        Args:
            font_name: Font name for text elements
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for chart generation")

        # Try to use Chinese font if available
        from pathlib import Path
        bundled_font = Path(__file__).parent / "assets" / "simhei.ttf"
        if bundled_font.exists():
            try:
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont
                pdfmetrics.registerFont(TTFont('CNChartFont', str(bundled_font)))
                self.font_name = 'CNChartFont'
                self.font_bold = 'CNChartFont'
            except Exception:
                self.font_name = font_name
                self.font_bold = font_name
        else:
            self.font_name = font_name
            self.font_bold = font_name

        self.style = ChartStyle(font_name=self.font_name)

    def draw_gauge_chart(
        self,
        score: float,
        title: str = "",
        max_score: float = 100,
        width: float = 10 * cm,
        height: float = 6 * cm,
    ) -> Drawing:
        """Draw a gauge/dial chart for scores.

        Args:
            score: Current score value
            title: Chart title
            max_score: Maximum score value
            width: Drawing width
            height: Drawing height (increased to 6cm to prevent overflow)

        Returns:
            Drawing object
        """
        drawing = Drawing(width, height)

        # Calculate colors based on score
        if score >= 80:
            gauge_color = GRADE_COLORS["excellent"]
        elif score >= 60:
            gauge_color = GRADE_COLORS["good"]
        elif score >= 40:
            gauge_color = GRADE_COLORS["fair"]
        else:
            gauge_color = GRADE_COLORS["poor"]

        # Draw background arc (semi-circle)
        # Position circle higher (cy = height / 2.5) to ensure arc fits within drawing
        cx, cy = width / 2, height / 2.8
        # Smaller radius to ensure content stays within bounds
        radius = min(width, height) / 2.8

        # Background gray arc
        self._draw_arc(drawing, cx, cy, radius, 180, 360, colors.HexColor("#E5E7EB"), 20)

        # Score arc (colored portion)
        score_angle = 180 + (score / max_score) * 180
        self._draw_arc(drawing, cx, cy, radius, 180, score_angle, gauge_color, 20)

        # Draw score text
        score_text = String(cx, cy, f"{score:.0f}", textAnchor="middle")
        score_text.fontName = self.font_bold
        score_text.fontSize = 36
        score_text.fillColor = COLORS["primary"]
        drawing.add(score_text)

        # Draw max score label
        max_text = String(cx, cy - 0.6 * cm, f"/ {max_score:.0f}", textAnchor="middle")
        max_text.fontName = self.font_name
        max_text.fontSize = 14
        max_text.fillColor = COLORS["gray"]
        drawing.add(max_text)

        # Draw title
        if title:
            title_obj = String(cx, height - 0.5 * cm, title, textAnchor="middle")
            title_obj.fontName = self.font_bold
            title_obj.fontSize = 16
            title_obj.fillColor = COLORS["title_color"]
            drawing.add(title_obj)

        # Draw min/max labels - aligned with arc ends
        label_y_offset = 0.3 * cm  # Distance below arc
        # Align labels with arc ends for better visual alignment
        min_label = String(cx - radius, cy + label_y_offset, "0", textAnchor="middle")
        min_label.fontName = self.font_name
        min_label.fontSize = 10
        min_label.fillColor = COLORS["gray"]
        drawing.add(min_label)

        max_label = String(cx + radius, cy + label_y_offset, str(int(max_score)), textAnchor="middle")
        max_label.fontName = self.font_name
        max_label.fontSize = 10
        max_label.fillColor = COLORS["gray"]
        drawing.add(max_label)

        return drawing

    def draw_bar_chart(
        self,
        data: List[float],
        labels: List[str],
        title: str = "",
        y_label: str = "",
        colors_list: Optional[List[colors.Color]] = None,
        width: float = 14 * cm,
        height: float = 6 * cm,
    ) -> Drawing:
        """Draw a vertical bar chart.

        Args:
            data: Data values
            labels: Bar labels
            title: Chart title
            y_label: Y-axis label
            colors_list: Optional list of colors for each bar
            width: Drawing width
            height: Drawing height

        Returns:
            Drawing object
        """
        drawing = Drawing(width, height)

        if not data:
            # Empty chart message
            msg = String(width / 2, height / 2, "无数据", textAnchor="middle")
            msg.fontName = self.font_name
            msg.fontSize = 14
            msg.fillColor = COLORS["gray"]
            drawing.add(msg)
            return drawing

        # Chart area
        margin = 1 * cm
        chart_width = width - 2 * margin
        chart_height = height - 2 * margin - 0.5 * cm

        # Draw title
        if title:
            title_obj = String(width / 2, height - 0.3 * cm, title, textAnchor="middle")
            title_obj.fontName = self.font_bold
            title_obj.fontSize = 12
            title_obj.fillColor = COLORS["title_color"]
            drawing.add(title_obj)

        # Calculate scales
        max_value = max(data) if data else 100
        if max_value == 0:
            max_value = 100  # Default scale for empty data
        y_scale = chart_height / (max_value * 1.1)  # Add 10% headroom

        bar_width = chart_width / len(data) * 0.7
        bar_spacing = chart_width / len(data)

        # Draw bars
        for i, (value, label) in enumerate(zip(data, labels)):
            x = margin + i * bar_spacing + bar_spacing * 0.15
            bar_height = value * y_scale
            y = height - margin - 0.5 * cm - bar_height

            # Choose color
            if colors_list and i < len(colors_list):
                bar_color = colors_list[i]
            else:
                bar_color = COLORS["primary"]

            # Draw bar
            bar = Rect(x, y, bar_width, bar_height)
            bar.fillColor = bar_color
            bar.strokeColor = colors.white
            bar.strokeWidth = 1
            drawing.add(bar)

            # Draw value on top
            value_text = String(x + bar_width / 2, y - 0.3 * cm, f"{value:.0f}", textAnchor="middle")
            value_text.fontName = self.font_name
            value_text.fontSize = 9
            value_text.fillColor = COLORS["primary"]
            drawing.add(value_text)

            # Draw label below
            label_text = String(x + bar_width / 2, height - margin + 0.2 * cm, label, textAnchor="middle")
            label_text.fontName = self.font_name
            label_text.fontSize = 8
            label_text.fillColor = COLORS["gray"]
            # Truncate long labels
            if len(label) > 8:
                label = label[:7] + ".."
            label_text.text = label
            drawing.add(label_text)

        # Draw y-axis label
        if y_label:
            y_label_obj = String(0.3 * cm, height / 2, y_label, textAnchor="middle")
            y_label_obj.fontName = self.font_name
            y_label_obj.fontSize = 10
            y_label_obj.fillColor = COLORS["gray"]
            drawing.add(y_label_obj)

        return drawing

    def draw_comparison_chart(
        self,
        current: List[float],
        suggested: List[float],
        labels: List[str],
        title: str = "",
        width: float = 14 * cm,
        height: float = 6 * cm,
    ) -> Drawing:
        """Draw a grouped bar chart comparing current vs suggested values.

        Args:
            current: Current values
            suggested: Suggested values
            labels: Bar labels
            title: Chart title
            width: Drawing width
            height: Drawing height

        Returns:
            Drawing object
        """
        drawing = Drawing(width, height)

        if not current:
            return drawing

        # Chart area
        margin = 1 * cm
        chart_width = width - 2 * margin
        chart_height = height - 2 * cm

        # Draw title
        if title:
            title_obj = String(width / 2, height - 0.3 * cm, title, textAnchor="middle")
            title_obj.fontName = self.font_bold
            title_obj.fontSize = 12
            title_obj.fillColor = COLORS["title_color"]
            drawing.add(title_obj)

        # Calculate scales
        all_values = current + suggested
        max_value = max(all_values) if all_values else 100
        y_scale = chart_height / (max_value * 1.1)

        # Group settings
        group_width = chart_width / len(labels)
        bar_width = group_width * 0.3
        gap = group_width * 0.1

        # Draw bars for each group
        for i, (cur_val, sug_val, label) in enumerate(zip(current, suggested, labels)):
            group_x = margin + i * group_width

            # Current bar (blue)
            cur_height = cur_val * y_scale
            cur_x = group_x + gap
            cur_y = height - 2 * cm - cur_height
            cur_bar = Rect(cur_x, cur_y, bar_width, cur_height)
            cur_bar.fillColor = COLORS["info"]
            cur_bar.strokeColor = colors.white
            drawing.add(cur_bar)

            # Current value
            cur_text = String(cur_x + bar_width / 2, cur_y - 0.3 * cm,
                            f"{cur_val:.0f}", textAnchor="middle")
            cur_text.fontName = self.font_name
            cur_text.fontSize = 7
            cur_text.fillColor = COLORS["info"]
            drawing.add(cur_text)

            # Suggested bar (green)
            sug_height = sug_val * y_scale
            sug_x = group_x + gap + bar_width
            sug_y = height - 2 * cm - sug_height
            sug_bar = Rect(sug_x, sug_y, bar_width, sug_height)
            sug_bar.fillColor = COLORS["success"]
            sug_bar.strokeColor = colors.white
            drawing.add(sug_bar)

            # Suggested value
            sug_text = String(sug_x + bar_width / 2, sug_y - 0.3 * cm,
                            f"{sug_val:.0f}", textAnchor="middle")
            sug_text.fontName = self.font_name
            sug_text.fontSize = 7
            sug_text.fillColor = COLORS["success"]
            drawing.add(sug_text)

            # Label
            label_text = String(group_x + group_width / 2, height - 2 * cm + 0.3 * cm,
                              label, textAnchor="middle")
            label_text.fontName = self.font_name
            label_text.fontSize = 8
            label_text.fillColor = COLORS["gray"]
            if len(label) > 10:
                label_text.text = label[:9] + ".."
            drawing.add(label_text)

        # Legend
        legend_y = 0.5 * cm
        legend_x = width - 3 * cm

        # Current legend
        cur_legend = Rect(legend_x, legend_y, 0.3 * cm, 0.3 * cm)
        cur_legend.fillColor = COLORS["info"]
        drawing.add(cur_legend)
        cur_label = String(legend_x + 0.4 * cm, legend_y + 0.15 * cm, "当前", textAnchor="start")
        cur_label.fontName = self.font_name
        cur_label.fontSize = 8
        cur_label.fillColor = COLORS["gray"]
        drawing.add(cur_label)

        # Suggested legend
        sug_legend = Rect(legend_x + 1 * cm, legend_y, 0.3 * cm, 0.3 * cm)
        sug_legend.fillColor = COLORS["success"]
        drawing.add(sug_legend)
        sug_label = String(legend_x + 1.4 * cm, legend_y + 0.15 * cm, "建议", textAnchor="start")
        sug_label.fontName = self.font_name
        sug_label.fontSize = 8
        sug_label.fillColor = COLORS["gray"]
        drawing.add(sug_label)

        return drawing

    def draw_pie_chart(
        self,
        data: List[float],
        labels: List[str],
        title: str = "",
        colors_list: Optional[List[colors.Color]] = None,
        width: float = 10 * cm,
        height: float = 8 * cm,
    ) -> Drawing:
        """Draw a pie chart.

        Args:
            data: Data values
            labels: Segment labels
            title: Chart title
            colors_list: Optional list of colors
            width: Drawing width
            height: Drawing height

        Returns:
            Drawing object
        """
        drawing = Drawing(width, height)

        if not data or sum(data) == 0:
            msg = String(width / 2, height / 2, "无数据", textAnchor="middle")
            msg.fontName = self.font_name
            msg.fontSize = 14
            msg.fillColor = COLORS["gray"]
            drawing.add(msg)
            return drawing

        # Default colors
        default_colors = [
            COLORS["primary"], COLORS["success"], COLORS["warning"],
            COLORS["danger"], COLORS["info"], COLORS["purple"],
        ]

        if colors_list is None:
            colors_list = default_colors[:len(data)]

        # Draw title
        if title:
            title_obj = String(width / 2, height - 0.3 * cm, title, textAnchor="middle")
            title_obj.fontName = self.font_bold
            title_obj.fontSize = 12
            title_obj.fillColor = COLORS["title_color"]
            drawing.add(title_obj)

        # Pie parameters
        cx, cy = width / 2, height / 2 + 0.3 * cm
        radius = min(width, height) / 3

        total = sum(data)
        current_angle = 0

        # Draw pie slices
        for i, (value, label, color) in enumerate(zip(data, labels, colors_list)):
            if value == 0:
                continue

            slice_angle = (value / total) * 360
            end_angle = current_angle + slice_angle

            # Draw slice
            self._draw_pie_slice(drawing, cx, cy, radius, current_angle, end_angle, color)

            # Draw label (percentage)
            percent = (value / total) * 100
            label_angle = (current_angle + end_angle) / 2
            label_radius = radius * 0.7
            lx = cx + label_radius * self._cos(label_angle)
            ly = cy + label_radius * self._sin(label_angle)

            percent_text = String(lx, ly, f"{percent:.0f}%", textAnchor="middle")
            percent_text.fontName = self.font_bold
            percent_text.fontSize = 10
            percent_text.fillColor = colors.white
            drawing.add(percent_text)

            current_angle = end_angle

        # Draw legend
        legend_y = 0.3 * cm
        legend_x = 0.5 * cm

        for i, (label, color) in enumerate(zip(labels, colors_list)):
            row = i // 3
            col = i % 3

            lx = legend_x + col * 3 * cm
            ly = legend_y

            # Color box
            box = Rect(lx, ly, 0.3 * cm, 0.3 * cm)
            box.fillColor = color
            drawing.add(box)

            # Label text
            label_obj = String(lx + 0.4 * cm, ly + 0.15 * cm, label, textAnchor="start")
            label_obj.fontName = self.font_name
            label_obj.fontSize = 8
            label_obj.fillColor = COLORS["gray"]
            drawing.add(label_obj)

        return drawing

    def draw_radar_chart(
        self,
        scores: List[float],
        labels: List[str],
        title: str = "",
        max_score: float = 100,
        width: float = 10 * cm,
        height: float = 10 * cm,
    ) -> Drawing:
        """Draw a radar/spider chart for multi-dimensional scores.

        Args:
            scores: Score values for each dimension
            labels: Dimension labels
            title: Chart title
            max_score: Maximum score value
            width: Drawing width
            height: Drawing height

        Returns:
            Drawing object
        """
        drawing = Drawing(width, height)

        if not scores:
            return drawing

        # Draw title
        if title:
            title_obj = String(width / 2, height - 0.3 * cm, title, textAnchor="middle")
            title_obj.fontName = self.font_bold
            title_obj.fontSize = 12
            title_obj.fillColor = COLORS["title_color"]
            drawing.add(title_obj)

        # Radar parameters
        cx, cy = width / 2, height / 2 + 0.3 * cm
        radius = min(width, height) / 3

        num_dimensions = len(scores)
        angle_step = 360 / num_dimensions

        # Draw background grid (concentric polygons)
        for i in range(1, 6):
            grid_radius = radius * i / 5
            points = []
            for j in range(num_dimensions):
                angle = j * angle_step - 90  # Start from top
                x = cx + grid_radius * self._cos(angle)
                y = cy + grid_radius * self._sin(angle)
                points.extend([x, y])

            grid = Polygon(points)
            grid.fillColor = None
            grid.strokeColor = COLORS["grid_color"]
            grid.strokeWidth = 0.5
            drawing.add(grid)

        # Draw axis lines and labels
        for i, label in enumerate(labels):
            angle = i * angle_step - 90
            x = cx + radius * self._cos(angle)
            y = cy + radius * self._sin(angle)

            # Axis line
            axis = Line(cx, cy, x, y)
            axis.strokeColor = COLORS["grid_color"]
            axis.strokeWidth = 0.5
            drawing.add(axis)

            # Label
            label_radius = radius * 1.15
            lx = cx + label_radius * self._cos(angle)
            ly = cy + label_radius * self._sin(angle)

            label_obj = String(lx, ly, label, textAnchor="middle")
            label_obj.fontName = self.font_name
            label_obj.fontSize = 8
            label_obj.fillColor = COLORS["gray"]
            drawing.add(label_obj)

        # Draw data polygon
        data_points = []
        for score, label in zip(scores, labels):
            normalized_score = min(score / max_score, 1.0)
            angle = labels.index(label) * angle_step - 90
            x = cx + radius * normalized_score * self._cos(angle)
            y = cy + radius * normalized_score * self._sin(angle)
            data_points.extend([x, y])

            # Draw score value
            value_text = String(x, y, f"{score:.0f}", textAnchor="middle")
            value_text.fontName = self.font_bold
            value_text.fontSize = 9
            value_text.fillColor = COLORS["primary"]
            drawing.add(value_text)

        # Data polygon
        data_poly = Polygon(data_points)
        data_poly.fillColor = COLORS["primary"]
        data_poly.fillOpacity = 0.3
        data_poly.strokeColor = COLORS["primary"]
        data_poly.strokeWidth = 2
        drawing.add(data_poly)

        return drawing

    def draw_horizontal_bar_chart(
        self,
        data: List[Tuple[str, float]],
        title: str = "",
        colors_list: Optional[List[colors.Color]] = None,
        width: float = 14 * cm,
        height: float = 8 * cm,
    ) -> Drawing:
        """Draw a horizontal bar chart.

        Args:
            data: List of (label, value) tuples
            title: Chart title
            colors_list: Optional list of colors
            width: Drawing width
            height: Drawing height

        Returns:
            Drawing object
        """
        drawing = Drawing(width, height)

        if not data:
            msg = String(width / 2, height / 2, "无数据", textAnchor="middle")
            msg.fontName = self.font_name
            msg.fontSize = 14
            msg.fillColor = COLORS["gray"]
            drawing.add(msg)
            return drawing

        # Chart area
        margin_left = 2 * cm
        margin_right = 1 * cm
        margin_top = 0.8 * cm
        margin_bottom = 0.5 * cm

        chart_width = width - margin_left - margin_right
        bar_height = (height - margin_top - margin_bottom) / len(data) * 0.7
        bar_spacing = (height - margin_top - margin_bottom) / len(data)

        # Draw title
        if title:
            title_obj = String(width / 2, height - 0.3 * cm, title, textAnchor="middle")
            title_obj.fontName = self.font_bold
            title_obj.fontSize = 12
            title_obj.fillColor = COLORS["title_color"]
            drawing.add(title_obj)

        # Calculate scale
        max_value = max(v for _, v in data) if data else 100
        # Avoid division by zero when all values are 0
        if max_value == 0:
            max_value = 100
        x_scale = chart_width / (max_value * 1.1)

        # Draw bars
        for i, (label, value) in enumerate(data):
            y = height - margin_top - i * bar_spacing - bar_height
            bar_width = value * x_scale

            # Choose color
            if colors_list and i < len(colors_list):
                bar_color = colors_list[i]
            else:
                bar_color = COLORS["primary"]

            # Draw bar
            bar = Rect(margin_left, y, bar_width, bar_height)
            bar.fillColor = bar_color
            bar.strokeColor = colors.white
            bar.strokeWidth = 1
            drawing.add(bar)

            # Draw value at end of bar
            value_text = String(margin_left + bar_width + 0.2 * cm, y + bar_height / 2,
                              f"{value:.0f}", textAnchor="start")
            value_text.fontName = self.font_bold
            value_text.fontSize = 9
            value_text.fillColor = COLORS["primary"]
            drawing.add(value_text)

            # Draw label
            label_text = String(margin_left - 0.2 * cm, y + bar_height / 2,
                              label, textAnchor="end")
            label_text.fontName = self.font_name
            label_text.fontSize = 9
            label_text.fillColor = COLORS["gray"]
            drawing.add(label_text)

        return drawing

    def _draw_arc(
        self,
        drawing: Drawing,
        cx: float,
        cy: float,
        radius: float,
        start_angle: float,
        end_angle: float,
        color: colors.Color,
        thickness: float,
    ) -> None:
        """Draw an arc segment.

        Args:
            drawing: Drawing object to add to
            cx: Center X
            cy: Center Y
            radius: Radius
            start_angle: Start angle in degrees
            end_angle: End angle in degrees
            color: Arc color
            thickness: Arc thickness
        """
        # Create arc as a thick path
        path = self._create_arc_path(cx, cy, radius, start_angle, end_angle, thickness)
        path.fillColor = color
        path.strokeColor = None
        drawing.add(path)

    def _create_arc_path(
        self,
        cx: float,
        cy: float,
        radius: float,
        start_angle: float,
        end_angle: float,
        thickness: float,
    ) -> Polygon:
        """Create a polygon representing an arc segment.

        Simplified arc drawing using line segments.
        """
        points = []
        steps = max(1, int(abs(end_angle - start_angle) / 5))

        # Outer arc
        for i in range(steps + 1):
            angle = start_angle + (end_angle - start_angle) * i / steps
            outer_r = radius + thickness / 2
            x = cx + outer_r * self._cos(angle)
            y = cy + outer_r * self._sin(angle)
            points.extend([x, y])

        # Inner arc (reverse)
        for i in range(steps, -1, -1):
            angle = start_angle + (end_angle - start_angle) * i / steps
            inner_r = radius - thickness / 2
            x = cx + inner_r * self._cos(angle)
            y = cy + inner_r * self._sin(angle)
            points.extend([x, y])

        return Polygon(points)

    def _draw_pie_slice(
        self,
        drawing: Drawing,
        cx: float,
        cy: float,
        radius: float,
        start_angle: float,
        end_angle: float,
        color: colors.Color,
    ) -> None:
        """Draw a pie slice.

        Args:
            drawing: Drawing object
            cx: Center X
            cy: Center Y
            radius: Radius
            start_angle: Start angle in degrees
            end_angle: End angle in degrees
            color: Slice color
        """
        points = [cx, cy]  # Start from center

        # Add arc points
        steps = max(5, int(abs(end_angle - start_angle) / 5))
        for i in range(steps + 1):
            angle = start_angle + (end_angle - start_angle) * i / steps
            x = cx + radius * self._cos(angle)
            y = cy + radius * self._sin(angle)
            points.extend([x, y])

        slice_poly = Polygon(points)
        slice_poly.fillColor = color
        slice_poly.strokeColor = colors.white
        slice_poly.strokeWidth = 1
        drawing.add(slice_poly)

    @staticmethod
    def _cos(angle_degrees: float) -> float:
        """Cosine with degrees input."""
        import math
        return math.cos(math.radians(angle_degrees))

    @staticmethod
    def _sin(angle_degrees: float) -> float:
        """Sine with degrees input."""
        import math
        return math.sin(math.radians(angle_degrees))

    def draw_vm_resource_chart(
        self,
        cpu_data: List[Tuple[float, float]],  # (timestamp, value)
        memory_data: List[Tuple[float, float]],
        disk_read_data: List[Tuple[float, float]],
        disk_write_data: List[Tuple[float, float]],
        net_rx_data: List[Tuple[float, float]],
        net_tx_data: List[Tuple[float, float]],
        vm_name: str = "",
        width: float = 16 * cm,
        height: float = 12 * cm,
    ) -> Drawing:
        """Draw VM resource usage line chart with 4 panels.

        Args:
            cpu_data: CPU usage data points (timestamp_value, usage_percent)
            memory_data: Memory usage data points
            disk_read_data: Disk read rate data points
            disk_write_data: Disk write rate data points
            net_rx_data: Network receive data points
            net_tx_data: Network transmit data points
            vm_name: VM name for title
            width: Drawing width
            height: Drawing height

        Returns:
            Drawing object with 4 panel line chart
        """
        drawing = Drawing(width, height)

        # Colors for each metric type (use unified color system)
        cpu_color = COLORS["info"]      # Blue - CPU
        memory_color = COLORS["success"]  # Green - Memory
        disk_color = COLORS["warning"]    # Orange - Disk
        net_color = COLORS["purple"]      # Purple - Network

        # Draw title
        if vm_name:
            title_obj = String(width / 2, height - 0.3 * cm,
                             f"{vm_name} - 资源使用趋势", textAnchor="middle")
            title_obj.fontName = self.font_bold
            title_obj.fontSize = 11
            title_obj.fillColor = COLORS["title_color"]
            drawing.add(title_obj)

        # Panel configuration: 2x2 grid
        panel_margin = 0.5 * cm
        title_height = 0.8 * cm
        panel_width = (width - 3 * panel_margin) / 2
        panel_height = (height - title_height - 3 * panel_margin) / 2

        # Panel positions: (x, y) for top-left of each panel
        panels = [
            (panel_margin, height - title_height - panel_margin - panel_height),  # Top-left
            (panel_margin * 2 + panel_width, height - title_height - panel_margin - panel_height),  # Top-right
            (panel_margin, height - title_height - panel_margin * 2 - panel_height * 2),  # Bottom-left
            (panel_margin * 2 + panel_width, height - title_height - panel_margin * 2 - panel_height * 2),  # Bottom-right
        ]

        # Panel 1: CPU & Memory (combined on same chart)
        self._draw_line_panel(
            drawing,
            panels[0][0], panels[0][1],
            panel_width, panel_height,
            [("CPU", cpu_data, cpu_color), ("内存", memory_data, memory_color)],
            y_label="使用率 (%)",
            y_max=100,
        )

        # Panel 2: Disk I/O
        self._draw_line_panel(
            drawing,
            panels[1][0], panels[1][1],
            panel_width, panel_height,
            [("磁盘读", disk_read_data, disk_color), ("磁盘写", disk_write_data, COLORS["danger"])],
            y_label="速率 (MB/s)",
        )

        # Panel 3: Network I/O
        self._draw_line_panel(
            drawing,
            panels[2][0], panels[2][1],
            panel_width, panel_height,
            [("网络接收", net_rx_data, net_color), ("网络发送", net_tx_data, COLORS["info"])],
            y_label="速率 (MB/s)",
        )

        # Panel 4: Summary text
        self._draw_summary_panel(
            drawing,
            panels[3][0], panels[3][1],
            panel_width, panel_height,
            cpu_data, memory_data, disk_read_data, disk_write_data, net_rx_data, net_tx_data,
        )

        return drawing

    def _draw_line_panel(
        self,
        drawing: Drawing,
        x: float,
        y: float,
        width: float,
        height: float,
        series: List[Tuple[str, List[Tuple[float, float]], colors.Color]],  # (label, data, color)
        y_label: str = "",
        y_max: Optional[float] = None,
    ) -> None:
        """Draw a single line chart panel.

        Args:
            drawing: Drawing object
            x: Panel X position
            y: Panel Y position
            width: Panel width
            height: Panel height
            series: List of (label, data, color) tuples
            y_label: Y-axis label
            y_max: Maximum Y value (auto-calculate if None)
        """
        margin = 0.4 * cm
        chart_width = width - 2 * margin
        chart_height = height - 2 * margin - 0.3 * cm

        # Draw panel border
        border = Rect(x, y, width, height)
        border.fillColor = None
        border.strokeColor = COLORS["grid_color"]
        border.strokeWidth = 0.5
        drawing.add(border)

        # Draw Y-axis label
        if y_label:
            y_label_obj = String(x + 0.2 * cm, y + height / 2, y_label, textAnchor="middle")
            y_label_obj.fontName = self.font_name
            y_label_obj.fontSize = 7
            y_label_obj.fillColor = COLORS["gray"]
            # Rotate -90 degrees
            from reportlab.lib import colors
            drawing.add(y_label_obj)

        # Calculate Y scale
        all_values = []
        for _, data, _ in series:
            all_values.extend([v for _, v in data])
        max_value = max(all_values) if all_values else 100
        if max_value == 0:
            max_value = 100
        if y_max is not None:
            max_value = y_max

        # Draw grid lines (5 horizontal)
        for i in range(6):
            grid_y = y + margin + (chart_height * i / 5)
            grid_line = Line(x + margin, grid_y, x + margin + chart_width, grid_y)
            grid_line.strokeColor = COLORS["grid_color"]
            grid_line.strokeWidth = 0.3
            drawing.add(grid_line)

            # Y-axis labels
            label_val = max_value * (5 - i) / 5
            label_text = String(x + margin - 0.1 * cm, grid_y, f"{label_val:.0f}", textAnchor="end")
            label_text.fontName = self.font_name
            label_text.fontSize = 6
            label_text.fillColor = COLORS["gray"]
            drawing.add(label_text)

        # Draw data lines
        for label, data, color in series:
            if not data or len(data) < 2:
                continue

            # Convert data points to coordinates
            points = []
            min_timestamp = min(t for t, _ in data)
            max_timestamp = max(t for t, _ in data)
            time_span = max_timestamp - min_timestamp if max_timestamp > min_timestamp else 1

            for timestamp, value in data:
                # Normalize time to 0-1 range
                norm_time = (timestamp - min_timestamp) / time_span if time_span > 0 else 0
                px = x + margin + norm_time * chart_width
                py = y + margin + (value / max_value) * chart_height
                points.append((px, py))

            # Draw line
            for i in range(len(points) - 1):
                line = Line(points[i][0], points[i][1], points[i+1][0], points[i+1][1])
                line.strokeColor = color
                line.strokeWidth = 1.5
                drawing.add(line)

            # Draw legend
            legend_y = y + height - 0.3 * cm
            legend_x = x + margin + (len(series) - list(series).index((label, data, color)) - 1) * 1.5 * cm

            # Color box
            box = Rect(legend_x, legend_y, 0.15 * cm, 0.15 * cm)
            box.fillColor = color
            drawing.add(box)

            # Label
            label_obj = String(legend_x + 0.2 * cm, legend_y + 0.1 * cm, label, textAnchor="start")
            label_obj.fontName = self.font_name
            label_obj.fontSize = 7
            label_obj.fillColor = COLORS["gray"]
            drawing.add(label_obj)

    def _draw_summary_panel(
        self,
        drawing: Drawing,
        x: float,
        y: float,
        width: float,
        height: float,
        cpu_data: List[Tuple[float, float]],
        memory_data: List[Tuple[float, float]],
        disk_read_data: List[Tuple[float, float]],
        disk_write_data: List[Tuple[float, float]],
        net_rx_data: List[Tuple[float, float]],
        net_tx_data: List[Tuple[float, float]],
    ) -> None:
        """Draw summary statistics panel.

        Args:
            drawing: Drawing object
            x: Panel X position
            y: Panel Y position
            width: Panel width
            height: Panel height
            ...data: Metric data lists
        """
        # Draw panel border
        border = Rect(x, y, width, height)
        border.fillColor = None
        border.strokeColor = COLORS["grid_color"]
        border.strokeWidth = 0.5
        drawing.add(border)

        # Title
        title = String(x + width / 2, y + height - 0.4 * cm, "统计摘要", textAnchor="middle")
        title.fontName = self.font_bold
        title.fontSize = 9
        title.fillColor = COLORS["title_color"]
        drawing.add(title)

        # Calculate statistics
        def calc_stats(data):
            if not data:
                return 0, 0
            values = [v for _, v in data]
            return sum(values) / len(values), max(values) if values else 0

        cpu_avg, cpu_max = calc_stats(cpu_data)
        mem_avg, mem_max = calc_stats(memory_data)
        disk_avg = (calc_stats(disk_read_data)[0] + calc_stats(disk_write_data)[0]) / 2
        net_avg = (calc_stats(net_rx_data)[0] + calc_stats(net_tx_data)[0]) / 2

        # Draw statistics in 2x2 grid
        stats = [
            ("CPU 平均", f"{cpu_avg:.1f}%", COLORS["info"]),
            ("内存 平均", f"{mem_avg:.1f}%", COLORS["success"]),
            ("磁盘 I/O", f"{disk_avg:.1f} MB/s", COLORS["warning"]),
            ("网络 I/O", f"{net_avg:.1f} MB/s", COLORS["purple"]),
        ]

        start_y = y + height - 1.2 * cm
        row_height = 0.7 * cm
        col_width = width / 2

        for i, (label, value, color) in enumerate(stats):
            row = i // 2
            col = i % 2
            stat_x = x + col * col_width + 0.3 * cm
            stat_y = start_y - row * row_height

            # Label
            label_obj = String(stat_x, stat_y, label, textAnchor="start")
            label_obj.fontName = self.font_name
            label_obj.fontSize = 7
            label_obj.fillColor = COLORS["gray"]
            drawing.add(label_obj)

            # Value
            value_obj = String(stat_x, stat_y - 0.3 * cm, value, textAnchor="start")
            value_obj.fontName = self.font_bold
            value_obj.fontSize = 9
            value_obj.fillColor = color
            drawing.add(value_obj)
