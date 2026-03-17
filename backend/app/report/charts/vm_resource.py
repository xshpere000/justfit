"""VM resource usage trend chart: 2×2 panel line chart with summary statistics.

Bug fixes applied here (vs. original charts.py):
  1. Legend ordering reversed  — use enumerate() instead of reversed index formula.
  2. net_send color = CPU blue  — net_send now uses COLORS["net_send"] (cyan).
  3. Y-axis label not rotated   — use reportlab Group transform for 90° CCW rotation.
  4. Legend drawn inside data loop — separated into two passes so empty-data series
     still have correct legend item positions.
"""

from typing import List, Optional, Tuple

from .constants import (
    COLORS,
    Drawing, Rect, String, Line, Group,
    cm,
)


class VMResourceCharts:
    """Mixin: VM resource usage trend charts (4-panel line chart)."""

    def draw_vm_resource_chart(
        self,
        cpu_data: List[Tuple[float, float]],
        memory_data: List[Tuple[float, float]],
        disk_read_data: List[Tuple[float, float]],
        disk_write_data: List[Tuple[float, float]],
        net_rx_data: List[Tuple[float, float]],
        net_tx_data: List[Tuple[float, float]],
        vm_name: str = "",
        width: float = 16 * cm,
        height: float = 12 * cm,
    ) -> Drawing:
        """Draw a 2×2 panel line chart for VM resource usage trends.

        Panels:
          Top-left  : CPU (blue) + Memory (green)   — y% axis
          Top-right : Disk Read (orange) + Disk Write (red)  — MB/s axis
          Bottom-left : Net RX (purple) + Net TX (cyan)  — MB/s axis
          Bottom-right: Summary statistics text
        """
        drawing = Drawing(width, height)

        # Per-metric colors — each series has a unique color across all panels
        cpu_color    = COLORS["info"]       # blue
        memory_color = COLORS["success"]    # green
        disk_color   = COLORS["warning"]    # orange
        disk_w_color = COLORS["danger"]     # red
        net_rx_color = COLORS["purple"]     # purple
        net_tx_color = COLORS["net_send"]   # cyan  ← was COLORS["info"] (same as CPU, BUG)

        # Chart title
        if vm_name:
            title_obj = String(width / 2, height - 0.3 * cm,
                               f"{vm_name} - 资源使用趋势", textAnchor="middle")
            title_obj.fontName = self.font_bold
            title_obj.fontSize = 11
            title_obj.fillColor = COLORS["title_color"]
            drawing.add(title_obj)

        # 2×2 grid layout
        p_margin = 0.5 * cm
        title_h = 0.8 * cm
        p_width  = (width - 3 * p_margin) / 2
        p_height = (height - title_h - 3 * p_margin) / 2

        # (x, y) = bottom-left corner of each panel
        panels = [
            (p_margin,              height - title_h - p_margin - p_height),   # top-left
            (p_margin * 2 + p_width, height - title_h - p_margin - p_height),  # top-right
            (p_margin,              height - title_h - p_margin * 2 - p_height * 2),  # bottom-left
            (p_margin * 2 + p_width, height - title_h - p_margin * 2 - p_height * 2),  # bottom-right
        ]

        # Panel 1: CPU & Memory
        self._draw_line_panel(
            drawing, panels[0][0], panels[0][1], p_width, p_height,
            [("CPU", cpu_data, cpu_color), ("内存", memory_data, memory_color)],
            y_label="使用率 (%)",
            y_max=100,
        )

        # Panel 2: Disk I/O
        self._draw_line_panel(
            drawing, panels[1][0], panels[1][1], p_width, p_height,
            [("磁盘读", disk_read_data, disk_color), ("磁盘写", disk_write_data, disk_w_color)],
            y_label="速率 (MB/s)",
        )

        # Panel 3: Network I/O
        self._draw_line_panel(
            drawing, panels[2][0], panels[2][1], p_width, p_height,
            [("网络接收", net_rx_data, net_rx_color), ("网络发送", net_tx_data, net_tx_color)],
            y_label="速率 (MB/s)",
        )

        # Panel 4: Summary statistics
        self._draw_summary_panel(
            drawing, panels[3][0], panels[3][1], p_width, p_height,
            cpu_data, memory_data, disk_read_data, disk_write_data,
            net_rx_data, net_tx_data,
            cpu_color, memory_color, disk_color, net_rx_color,
        )

        return drawing

    # ── Single line-chart panel ───────────────────────────────────────────

    def _draw_line_panel(
        self,
        drawing: Drawing,
        x: float,
        y: float,
        width: float,
        height: float,
        series: List[Tuple[str, List[Tuple[float, float]], object]],
        y_label: str = "",
        y_max: Optional[float] = None,
    ) -> None:
        """Draw one line-chart panel.

        FIX 1 — Legend order: enumerate() preserves series order left-to-right.
        FIX 2 — Legend/data loop decoupled: legend is always drawn for every
                 series, regardless of whether the data line was drawn.
        FIX 3 — Y-axis label: rotated 90° CCW via reportlab Group transform.
        """
        margin = 0.4 * cm
        chart_width = width - 2 * margin
        # Reserve top 0.3 cm inside the panel for the legend row
        chart_height = height - 2 * margin - 0.3 * cm

        # Panel border
        border = Rect(x, y, width, height)
        border.fillColor = None
        border.strokeColor = COLORS["grid_color"]
        border.strokeWidth = 0.5
        drawing.add(border)

        # Y-axis label — rotated 90° CCW using Group transform
        # FIX 3: was `drawing.add(String(...))` without any rotation applied.
        if y_label:
            lx = x + 0.25 * cm
            ly = y + height / 2
            y_str = String(0, 0, y_label, textAnchor="middle")
            y_str.fontName = self.font_name
            y_str.fontSize = 7
            y_str.fillColor = COLORS["gray"]
            # Affine transform: 90° CCW rotation + translate to (lx, ly)
            # Maps local (u, v) → screen (−v + lx, u + ly)
            # i.e. (a=0, b=1, c=−1, d=0, e=lx, f=ly)
            lbl_group = Group(y_str)
            lbl_group.transform = (0, 1, -1, 0, lx, ly)
            drawing.add(lbl_group)

        # Y scale
        all_vals = [v for _, data, _ in series for _, v in data]
        max_value = max(all_vals) if all_vals else 100
        if max_value == 0:
            max_value = 100
        if y_max is not None:
            max_value = y_max

        # Horizontal grid lines + Y-axis tick labels (6 lines = 5 intervals)
        for i in range(6):
            gy = y + margin + chart_height * i / 5
            grid_line = Line(x + margin, gy, x + margin + chart_width, gy)
            grid_line.strokeColor = COLORS["grid_color"]
            grid_line.strokeWidth = 0.3
            drawing.add(grid_line)

            tick_val = max_value * (5 - i) / 5
            tick_text = String(x + margin - 0.1 * cm, gy,
                               f"{tick_val:.0f}", textAnchor="end")
            tick_text.fontName = self.font_name
            tick_text.fontSize = 6
            tick_text.fillColor = COLORS["gray"]
            drawing.add(tick_text)

        # ── Pass 1: draw data lines ───────────────────────────────────────
        for label, data, color in series:
            if not data or len(data) < 2:
                continue

            min_ts = min(t for t, _ in data)
            max_ts = max(t for t, _ in data)
            time_span = max_ts - min_ts if max_ts > min_ts else 1

            points = []
            for ts, value in data:
                norm = (ts - min_ts) / time_span if time_span > 0 else 0
                px = x + margin + norm * chart_width
                py = y + margin + (value / max_value) * chart_height
                points.append((px, py))

            for i in range(len(points) - 1):
                seg = Line(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])
                seg.strokeColor = color
                seg.strokeWidth = 1.5
                drawing.add(seg)

        # ── Pass 2: draw legend (always, in series definition order) ──────
        # FIX 1: use idx from enumerate() so series[0] → leftmost legend item.
        # FIX 2: separate from data loop so empty-data series don't displace
        #        legend items of subsequent series.
        LEGEND_ITEM_WIDTH = 2.0 * cm  # wide enough for 4-char CJK labels
        legend_y = y + height - 0.3 * cm
        for idx, (label, _data, color) in enumerate(series):
            legend_x = x + margin + idx * LEGEND_ITEM_WIDTH

            box = Rect(legend_x, legend_y, 0.15 * cm, 0.15 * cm)
            box.fillColor = color
            drawing.add(box)

            label_obj = String(legend_x + 0.2 * cm, legend_y + 0.1 * cm,
                               label, textAnchor="start")
            label_obj.fontName = self.font_name
            label_obj.fontSize = 7
            label_obj.fillColor = COLORS["gray"]
            drawing.add(label_obj)

    # ── Summary statistics panel ──────────────────────────────────────────

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
        cpu_color: object,
        memory_color: object,
        disk_color: object,
        net_color: object,
    ) -> None:
        """Draw summary statistics (avg / max) for each metric."""
        border = Rect(x, y, width, height)
        border.fillColor = None
        border.strokeColor = COLORS["grid_color"]
        border.strokeWidth = 0.5
        drawing.add(border)

        title_str = String(x + width / 2, y + height - 0.4 * cm, "统计摘要",
                           textAnchor="middle")
        title_str.fontName = self.font_bold
        title_str.fontSize = 9
        title_str.fillColor = COLORS["title_color"]
        drawing.add(title_str)

        def _avg_max(data: List[Tuple[float, float]]) -> Tuple[float, float]:
            if not data:
                return 0.0, 0.0
            vals = [v for _, v in data]
            return sum(vals) / len(vals), max(vals)

        cpu_avg, _  = _avg_max(cpu_data)
        mem_avg, _  = _avg_max(memory_data)

        # Disk: average of all read+write samples combined
        disk_vals = [v for _, v in disk_read_data] + [v for _, v in disk_write_data]
        disk_avg = sum(disk_vals) / len(disk_vals) if disk_vals else 0.0

        # Network: average of all rx+tx samples combined
        net_vals = [v for _, v in net_rx_data] + [v for _, v in net_tx_data]
        net_avg = sum(net_vals) / len(net_vals) if net_vals else 0.0

        stats = [
            ("CPU 平均",  f"{cpu_avg:.1f}%",    cpu_color),
            ("内存 平均", f"{mem_avg:.1f}%",    memory_color),
            ("磁盘 I/O",  f"{disk_avg:.1f} MB/s", disk_color),
            ("网络 I/O",  f"{net_avg:.1f} MB/s",  net_color),
        ]

        start_y = y + height - 1.2 * cm
        row_h = 0.7 * cm
        col_w = width / 2

        for i, (label, value, color) in enumerate(stats):
            row, col = divmod(i, 2)
            sx = x + col * col_w + 0.3 * cm
            sy = start_y - row * row_h

            lbl_obj = String(sx, sy, label, textAnchor="start")
            lbl_obj.fontName = self.font_name
            lbl_obj.fontSize = 7
            lbl_obj.fillColor = COLORS["gray"]
            drawing.add(lbl_obj)

            val_obj = String(sx, sy - 0.3 * cm, value, textAnchor="start")
            val_obj.fontName = self.font_bold
            val_obj.fontSize = 9
            val_obj.fillColor = color
            drawing.add(val_obj)
