"""Overview chart types: gauge, bar, comparison, pie, radar, horizontal bar."""

from typing import List, Optional, Tuple

from .constants import (
    COLORS, GRADE_COLORS,
    Drawing, Rect, String, Line, Polygon,
    colors, cm,
)


class OverviewCharts:
    """Mixin: simple overview charts used in report summary sections."""

    # ── Gauge / dial ─────────────────────────────────────────────────────

    def draw_gauge_chart(
        self,
        score: float,
        title: str = "",
        max_score: float = 100,
        width: float = 10 * cm,
        height: float = 6 * cm,
    ) -> Drawing:
        """Semi-circle gauge chart for health scores."""
        drawing = Drawing(width, height)

        if score >= 80:
            gauge_color = GRADE_COLORS["excellent"]
        elif score >= 60:
            gauge_color = GRADE_COLORS["good"]
        elif score >= 40:
            gauge_color = GRADE_COLORS["fair"]
        else:
            gauge_color = GRADE_COLORS["poor"]

        cx, cy = width / 2, height / 2.8
        radius = min(width, height) / 2.8

        # Background arc then score arc
        self._draw_arc(drawing, cx, cy, radius, 180, 360, colors.HexColor("#E5E7EB"), 20)
        score_angle = 180 + (score / max_score) * 180
        self._draw_arc(drawing, cx, cy, radius, 180, score_angle, gauge_color, 20)

        # Score text
        score_text = String(cx, cy, f"{score:.0f}", textAnchor="middle")
        score_text.fontName = self.font_bold
        score_text.fontSize = 36
        score_text.fillColor = COLORS["primary"]
        drawing.add(score_text)

        # Max label
        max_text = String(cx, cy - 0.6 * cm, f"/ {max_score:.0f}", textAnchor="middle")
        max_text.fontName = self.font_name
        max_text.fontSize = 14
        max_text.fillColor = COLORS["gray"]
        drawing.add(max_text)

        if title:
            title_obj = String(cx, height - 0.5 * cm, title, textAnchor="middle")
            title_obj.fontName = self.font_bold
            title_obj.fontSize = 16
            title_obj.fillColor = COLORS["title_color"]
            drawing.add(title_obj)

        label_y_offset = 0.3 * cm
        min_label = String(cx - radius, cy + label_y_offset, "0", textAnchor="middle")
        min_label.fontName = self.font_name
        min_label.fontSize = 10
        min_label.fillColor = COLORS["gray"]
        drawing.add(min_label)

        max_label = String(cx + radius, cy + label_y_offset, str(int(max_score)),
                           textAnchor="middle")
        max_label.fontName = self.font_name
        max_label.fontSize = 10
        max_label.fillColor = COLORS["gray"]
        drawing.add(max_label)

        return drawing

    # ── Vertical bar ─────────────────────────────────────────────────────

    def draw_bar_chart(
        self,
        data: List[float],
        labels: List[str],
        title: str = "",
        y_label: str = "",
        colors_list: Optional[List] = None,
        width: float = 14 * cm,
        height: float = 6 * cm,
    ) -> Drawing:
        """Vertical bar chart."""
        drawing = Drawing(width, height)

        if not data:
            msg = String(width / 2, height / 2, "无数据", textAnchor="middle")
            msg.fontName = self.font_name
            msg.fontSize = 14
            msg.fillColor = COLORS["gray"]
            drawing.add(msg)
            return drawing

        margin = 1 * cm
        chart_width = width - 2 * margin
        chart_height = height - 2 * margin - 0.5 * cm

        if title:
            title_obj = String(width / 2, height - 0.3 * cm, title, textAnchor="middle")
            title_obj.fontName = self.font_bold
            title_obj.fontSize = 12
            title_obj.fillColor = COLORS["title_color"]
            drawing.add(title_obj)

        max_value = max(data) if data else 100
        if max_value == 0:
            max_value = 100
        y_scale = chart_height / (max_value * 1.1)

        bar_width = chart_width / len(data) * 0.7
        bar_spacing = chart_width / len(data)

        for i, (value, label) in enumerate(zip(data, labels)):
            x = margin + i * bar_spacing + bar_spacing * 0.15
            bar_height = value * y_scale
            y = height - margin - 0.5 * cm - bar_height

            bar_color = (colors_list[i] if colors_list and i < len(colors_list)
                         else COLORS["primary"])

            bar = Rect(x, y, bar_width, bar_height)
            bar.fillColor = bar_color
            bar.strokeColor = colors.white
            bar.strokeWidth = 1
            drawing.add(bar)

            value_text = String(x + bar_width / 2, y - 0.3 * cm,
                                f"{value:.0f}", textAnchor="middle")
            value_text.fontName = self.font_name
            value_text.fontSize = 9
            value_text.fillColor = COLORS["primary"]
            drawing.add(value_text)

            display_label = label[:7] + ".." if len(label) > 8 else label
            label_text = String(x + bar_width / 2, height - margin + 0.2 * cm,
                                display_label, textAnchor="middle")
            label_text.fontName = self.font_name
            label_text.fontSize = 8
            label_text.fillColor = COLORS["gray"]
            drawing.add(label_text)

        if y_label:
            y_label_obj = String(0.3 * cm, height / 2, y_label, textAnchor="middle")
            y_label_obj.fontName = self.font_name
            y_label_obj.fontSize = 10
            y_label_obj.fillColor = COLORS["gray"]
            drawing.add(y_label_obj)

        return drawing

    # ── Grouped bar (current vs suggested) ───────────────────────────────

    def draw_comparison_chart(
        self,
        current: List[float],
        suggested: List[float],
        labels: List[str],
        title: str = "",
        width: float = 14 * cm,
        height: float = 6 * cm,
    ) -> Drawing:
        """Grouped bar chart: current (blue) vs suggested (green)."""
        drawing = Drawing(width, height)

        if not current:
            return drawing

        margin = 1 * cm
        chart_width = width - 2 * margin
        chart_height = height - 2 * cm

        if title:
            title_obj = String(width / 2, height - 0.3 * cm, title, textAnchor="middle")
            title_obj.fontName = self.font_bold
            title_obj.fontSize = 12
            title_obj.fillColor = COLORS["title_color"]
            drawing.add(title_obj)

        all_values = current + suggested
        max_value = max(all_values) if all_values else 100
        if max_value == 0:
            max_value = 100
        y_scale = chart_height / (max_value * 1.1)

        group_width = chart_width / len(labels)
        bar_width = group_width * 0.3
        gap = group_width * 0.1

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

            sug_text = String(sug_x + bar_width / 2, sug_y - 0.3 * cm,
                              f"{sug_val:.0f}", textAnchor="middle")
            sug_text.fontName = self.font_name
            sug_text.fontSize = 7
            sug_text.fillColor = COLORS["success"]
            drawing.add(sug_text)

            # Group label
            display_label = label[:9] + ".." if len(label) > 10 else label
            label_text = String(group_x + group_width / 2, height - 2 * cm + 0.3 * cm,
                                display_label, textAnchor="middle")
            label_text.fontName = self.font_name
            label_text.fontSize = 8
            label_text.fillColor = COLORS["gray"]
            drawing.add(label_text)

        # Legend (fixed positions, correct order)
        legend_y = 0.5 * cm
        legend_x = width - 3 * cm

        cur_legend = Rect(legend_x, legend_y, 0.3 * cm, 0.3 * cm)
        cur_legend.fillColor = COLORS["info"]
        drawing.add(cur_legend)
        cur_label = String(legend_x + 0.4 * cm, legend_y + 0.15 * cm, "当前",
                           textAnchor="start")
        cur_label.fontName = self.font_name
        cur_label.fontSize = 8
        cur_label.fillColor = COLORS["gray"]
        drawing.add(cur_label)

        sug_legend = Rect(legend_x + 1 * cm, legend_y, 0.3 * cm, 0.3 * cm)
        sug_legend.fillColor = COLORS["success"]
        drawing.add(sug_legend)
        sug_label = String(legend_x + 1.4 * cm, legend_y + 0.15 * cm, "建议",
                           textAnchor="start")
        sug_label.fontName = self.font_name
        sug_label.fontSize = 8
        sug_label.fillColor = COLORS["gray"]
        drawing.add(sug_label)

        return drawing

    # ── Pie ──────────────────────────────────────────────────────────────

    def draw_pie_chart(
        self,
        data: List[float],
        labels: List[str],
        title: str = "",
        colors_list: Optional[List] = None,
        width: float = 10 * cm,
        height: float = 8 * cm,
    ) -> Drawing:
        """Pie chart with percentage labels and bottom legend."""
        drawing = Drawing(width, height)

        if not data or sum(data) == 0:
            msg = String(width / 2, height / 2, "无数据", textAnchor="middle")
            msg.fontName = self.font_name
            msg.fontSize = 14
            msg.fillColor = COLORS["gray"]
            drawing.add(msg)
            return drawing

        default_colors = [
            COLORS["primary"], COLORS["success"], COLORS["warning"],
            COLORS["danger"], COLORS["info"], COLORS["purple"],
        ]
        if colors_list is None:
            colors_list = default_colors[:len(data)]

        if title:
            title_obj = String(width / 2, height - 0.3 * cm, title, textAnchor="middle")
            title_obj.fontName = self.font_bold
            title_obj.fontSize = 12
            title_obj.fillColor = COLORS["title_color"]
            drawing.add(title_obj)

        cx, cy = width / 2, height / 2 + 0.3 * cm
        radius = min(width, height) / 3
        total = sum(data)
        current_angle = 0

        for value, label, color in zip(data, labels, colors_list):
            if value == 0:
                continue
            slice_angle = (value / total) * 360
            end_angle = current_angle + slice_angle

            self._draw_pie_slice(drawing, cx, cy, radius, current_angle, end_angle, color)

            percent = (value / total) * 100
            mid_angle = (current_angle + end_angle) / 2
            lx = cx + radius * 0.7 * self._cos(mid_angle)
            ly = cy + radius * 0.7 * self._sin(mid_angle)
            pct_text = String(lx, ly, f"{percent:.0f}%", textAnchor="middle")
            pct_text.fontName = self.font_bold
            pct_text.fontSize = 10
            pct_text.fillColor = colors.white
            drawing.add(pct_text)

            current_angle = end_angle

        # Legend: 3 columns
        legend_y = 0.3 * cm
        legend_x = 0.5 * cm
        for i, (label, color) in enumerate(zip(labels, colors_list)):
            lx = legend_x + (i % 3) * 3 * cm
            box = Rect(lx, legend_y, 0.3 * cm, 0.3 * cm)
            box.fillColor = color
            drawing.add(box)
            label_obj = String(lx + 0.4 * cm, legend_y + 0.15 * cm, label,
                               textAnchor="start")
            label_obj.fontName = self.font_name
            label_obj.fontSize = 8
            label_obj.fillColor = COLORS["gray"]
            drawing.add(label_obj)

        return drawing

    # ── Radar ────────────────────────────────────────────────────────────

    def draw_radar_chart(
        self,
        scores: List[float],
        labels: List[str],
        title: str = "",
        max_score: float = 100,
        width: float = 10 * cm,
        height: float = 10 * cm,
    ) -> Drawing:
        """Radar / spider chart for multi-dimensional scores."""
        drawing = Drawing(width, height)

        if not scores:
            return drawing

        if title:
            title_obj = String(width / 2, height - 0.3 * cm, title, textAnchor="middle")
            title_obj.fontName = self.font_bold
            title_obj.fontSize = 12
            title_obj.fillColor = COLORS["title_color"]
            drawing.add(title_obj)

        cx, cy = width / 2, height / 2 + 0.3 * cm
        radius = min(width, height) / 3
        n = len(scores)
        angle_step = 360 / n

        # Background grid (5 rings)
        for i in range(1, 6):
            grid_radius = radius * i / 5
            pts: list = []
            for j in range(n):
                angle = j * angle_step - 90
                pts.extend([cx + grid_radius * self._cos(angle),
                             cy + grid_radius * self._sin(angle)])
            grid = Polygon(pts)
            grid.fillColor = None
            grid.strokeColor = COLORS["grid_color"]
            grid.strokeWidth = 0.5
            drawing.add(grid)

        # Axis lines and labels
        for i, label in enumerate(labels):
            angle = i * angle_step - 90
            ax = cx + radius * self._cos(angle)
            ay = cy + radius * self._sin(angle)
            axis = Line(cx, cy, ax, ay)
            axis.strokeColor = COLORS["grid_color"]
            axis.strokeWidth = 0.5
            drawing.add(axis)

            lx = cx + radius * 1.15 * self._cos(angle)
            ly = cy + radius * 1.15 * self._sin(angle)
            label_obj = String(lx, ly, label, textAnchor="middle")
            label_obj.fontName = self.font_name
            label_obj.fontSize = 8
            label_obj.fillColor = COLORS["gray"]
            drawing.add(label_obj)

        # Data polygon
        data_pts: list = []
        for idx, (score, label) in enumerate(zip(scores, labels)):
            norm = min(score / max_score, 1.0)
            angle = idx * angle_step - 90
            px = cx + radius * norm * self._cos(angle)
            py = cy + radius * norm * self._sin(angle)
            data_pts.extend([px, py])

            val_text = String(px, py, f"{score:.0f}", textAnchor="middle")
            val_text.fontName = self.font_bold
            val_text.fontSize = 9
            val_text.fillColor = COLORS["primary"]
            drawing.add(val_text)

        data_poly = Polygon(data_pts)
        data_poly.fillColor = COLORS["primary"]
        data_poly.fillOpacity = 0.3
        data_poly.strokeColor = COLORS["primary"]
        data_poly.strokeWidth = 2
        drawing.add(data_poly)

        return drawing

    # ── Horizontal bar ───────────────────────────────────────────────────

    def draw_horizontal_bar_chart(
        self,
        data: List[Tuple[str, float]],
        title: str = "",
        colors_list: Optional[List] = None,
        width: float = 14 * cm,
        height: float = 8 * cm,
    ) -> Drawing:
        """Horizontal bar chart."""
        drawing = Drawing(width, height)

        if not data:
            msg = String(width / 2, height / 2, "无数据", textAnchor="middle")
            msg.fontName = self.font_name
            msg.fontSize = 14
            msg.fillColor = COLORS["gray"]
            drawing.add(msg)
            return drawing

        margin_left = 2 * cm
        margin_right = 1 * cm
        margin_top = 0.8 * cm
        margin_bottom = 0.5 * cm

        chart_width = width - margin_left - margin_right
        n = len(data)
        bar_height = (height - margin_top - margin_bottom) / n * 0.7
        bar_spacing = (height - margin_top - margin_bottom) / n

        if title:
            title_obj = String(width / 2, height - 0.3 * cm, title, textAnchor="middle")
            title_obj.fontName = self.font_bold
            title_obj.fontSize = 12
            title_obj.fillColor = COLORS["title_color"]
            drawing.add(title_obj)

        max_value = max(v for _, v in data) if data else 100
        if max_value == 0:
            max_value = 100
        x_scale = chart_width / (max_value * 1.1)

        for i, (label, value) in enumerate(data):
            y = height - margin_top - i * bar_spacing - bar_height
            bar_width = value * x_scale

            bar_color = (colors_list[i] if colors_list and i < len(colors_list)
                         else COLORS["primary"])

            bar = Rect(margin_left, y, bar_width, bar_height)
            bar.fillColor = bar_color
            bar.strokeColor = colors.white
            bar.strokeWidth = 1
            drawing.add(bar)

            value_text = String(margin_left + bar_width + 0.2 * cm, y + bar_height / 2,
                                f"{value:.0f}", textAnchor="start")
            value_text.fontName = self.font_bold
            value_text.fontSize = 9
            value_text.fillColor = COLORS["primary"]
            drawing.add(value_text)

            label_text = String(margin_left - 0.2 * cm, y + bar_height / 2,
                                label, textAnchor="end")
            label_text.fontName = self.font_name
            label_text.fontSize = 9
            label_text.fillColor = COLORS["gray"]
            drawing.add(label_text)

        return drawing
