"""VM resource usage trend chart: 2×2 panel line chart with summary statistics.

Bug fixes applied here (vs. original charts.py):
  1. Legend ordering reversed  — use enumerate() instead of reversed index formula.
  2. net_send color = CPU blue  — net_send now uses COLORS["net_send"] (cyan).
  3. Y-axis label not rotated   — use reportlab Group transform for 90° CCW rotation.
  4. Legend drawn inside data loop — separated into two passes so empty-data series
     still have correct legend item positions.
  5. X-axis time labels added   — head/mid/tail timestamps, rotated 45°, only on
     line panels (not the summary statistics panel).
"""

import math
from datetime import datetime
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
            y_label="速率",
            rate_scale=True,
        )

        # Panel 3: Network I/O
        self._draw_line_panel(
            drawing, panels[2][0], panels[2][1], p_width, p_height,
            [("网络接收", net_rx_data, net_rx_color), ("网络发送", net_tx_data, net_tx_color)],
            y_label="速率",
            rate_scale=True,
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
        rate_scale: bool = False,
    ) -> None:
        """Draw one line-chart panel.

        FIX 1 — Legend order: enumerate() preserves series order left-to-right.
        FIX 2 — Legend/data loop decoupled: legend is always drawn for every
                 series, regardless of whether the data line was drawn.
        FIX 3 — Y-axis label: rotated 90° CCW via reportlab Group transform.
        FIX 5 — X-axis: head/mid/tail time labels, rotated 45°, with bottom axis line.
        """
        # ── Layout constants ──────────────────────────────────────────────
        margin = 0.4 * cm
        # Extra bottom space for X-axis labels (rotated 45°, font 6pt ≈ 0.21cm,
        # diagonal projection ≈ font_size * sin45 ≈ 0.15cm + gap 0.05cm → 0.45cm total)
        X_LABEL_RESERVE = 0.45 * cm
        chart_width = width - 2 * margin
        # Reserve top 0.3 cm for legend, bottom X_LABEL_RESERVE for X-axis labels
        chart_height = height - margin - X_LABEL_RESERVE - 0.3 * cm
        # chart_y: Y coordinate of the chart bottom edge (data area starts here)
        chart_y = y + margin + X_LABEL_RESERVE

        # ── Global timestamp range across ALL series ──────────────────────
        # Compute once so all three line panels share the same X mapping.
        all_ts = [t for _, data, _ in series for t, _ in data]
        has_data = len(all_ts) >= 2
        if has_data:
            global_min_ts = min(all_ts)
            global_max_ts = max(all_ts)
            time_span = global_max_ts - global_min_ts if global_max_ts > global_min_ts else 1
        else:
            global_min_ts = global_max_ts = time_span = 0

        # ── Panel border ─────────────────────────────────────────────────
        border = Rect(x, y, width, height)
        border.fillColor = None
        border.strokeColor = COLORS["grid_color"]
        border.strokeWidth = 0.5
        drawing.add(border)

        # ── Y-axis label — rotated 90° CCW using Group transform ─────────
        # FIX 3: was `drawing.add(String(...))` without any rotation applied.
        if y_label:
            lx = x + 0.25 * cm
            ly = chart_y + chart_height / 2
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

        # ── Y scale ───────────────────────────────────────────────────────
        all_vals = [v for _, data, _ in series for _, v in data]
        max_data = max(all_vals) if all_vals else 0

        if y_max is not None:
            max_value = y_max
            tick_fmt = "{:.0f}"
        elif rate_scale:
            # Dynamic rate tiers (MB/s): pick smallest tier >= max_data
            # Tiers: 0.1 0.5 1 5 10 50 100 500 1000 MB/s
            RATE_TIERS = [0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0, 500.0, 1000.0]
            max_value = next((t for t in RATE_TIERS if t >= max_data), RATE_TIERS[-1])

            def _fmt_rate(v: float) -> str:
                if max_value < 1.0:
                    return f"{v * 1024:.0f}KB/s" if v > 0 else "0"
                elif max_value < 10.0:
                    return f"{v:.1f}MB/s" if v > 0 else "0"
                else:
                    return f"{v:.0f}MB/s" if v > 0 else "0"

            tick_fmt = None  # use _fmt_rate instead
        else:
            max_value = max_data if max_data > 0 else 100
            if max_value >= 10:
                tick_fmt = "{:.0f}"
            elif max_value >= 1:
                tick_fmt = "{:.1f}"
            else:
                tick_fmt = "{:.2f}"

        # ── Horizontal grid lines + Y-axis tick labels (6 lines = 5 intervals) ──
        # ReportLab Y axis increases upward: i=0 → bottom (value=0), i=5 → top (value=max)
        for i in range(6):
            gy = chart_y + chart_height * i / 5
            grid_line = Line(x + margin, gy, x + margin + chart_width, gy)
            grid_line.strokeColor = COLORS["grid_color"]
            grid_line.strokeWidth = 0.3
            drawing.add(grid_line)

            tick_val = max_value * i / 5
            if rate_scale and y_max is None:
                label_str = _fmt_rate(tick_val)
            else:
                label_str = tick_fmt.format(tick_val)
            tick_text = String(x + margin - 0.1 * cm, gy,
                               label_str, textAnchor="end")
            tick_text.fontName = self.font_name
            tick_text.fontSize = 6
            tick_text.fillColor = COLORS["gray"]
            drawing.add(tick_text)

        # ── Pass 1: draw data lines ───────────────────────────────────────
        for label, data, color in series:
            if not data or len(data) < 2:
                continue

            points = []
            for ts, value in data:
                norm = (ts - global_min_ts) / time_span if time_span > 0 else 0
                px = x + margin + norm * chart_width
                py = chart_y + (value / max_value) * chart_height
                points.append((px, py))

            for i in range(len(points) - 1):
                seg = Line(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])
                seg.strokeColor = color
                seg.strokeWidth = 1.5
                drawing.add(seg)

        # ── X-axis bottom line ────────────────────────────────────────────
        x_axis_line = Line(x + margin, chart_y, x + margin + chart_width, chart_y)
        x_axis_line.strokeColor = COLORS["axis_color"]
        x_axis_line.strokeWidth = 0.5
        drawing.add(x_axis_line)

        # ── X-axis time labels: head / mid / tail, rotated 45° ───────────
        # Only draw when there is enough timestamp data to be meaningful.
        if has_data:
            mid_ts = (global_min_ts + global_max_ts) / 2
            x_ticks = [
                (global_min_ts, x + margin),                       # head
                (mid_ts,        x + margin + chart_width / 2),     # mid
                (global_max_ts, x + margin + chart_width),         # tail
            ]
            FONT_SIZE_X = 6
            # Rotation angle: 45° CW (labels lean right-downward)
            angle_rad = math.radians(45)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            # Vertical drop from baseline to bottom of rotated text:
            # ≈ font_size (in points) * sin45 ≈ font_size * 0.707
            # Baseline sits at chart_y - small_gap
            label_base_y = chart_y - 0.08 * cm

            for ts, tick_x in x_ticks:
                try:
                    label_str = datetime.fromtimestamp(ts).strftime("%m-%d")
                except (OSError, OverflowError, ValueError):
                    # Timestamp out of range or invalid — skip gracefully
                    continue

                t_str = String(0, 0, label_str, textAnchor="start")
                t_str.fontName = self.font_name
                t_str.fontSize = FONT_SIZE_X
                t_str.fillColor = COLORS["gray"]
                # 45° CW rotation: maps local (u,v) → screen (u*cos+v*sin + tx, -u*sin+v*cos + ty)
                # Affine: (a=cos, b=-sin, c=sin, d=cos, e=tx, f=ty)
                t_group = Group(t_str)
                t_group.transform = (cos_a, -sin_a, sin_a, cos_a, tick_x, label_base_y)
                drawing.add(t_group)

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

        def _fmt_io(v: float) -> str:
            if v < 1.0:
                return f"{v * 1024:.1f} KB/s"
            else:
                return f"{v:.1f} MB/s"

        stats = [
            ("CPU 平均",  f"{cpu_avg:.1f}%",    cpu_color),
            ("内存 平均", f"{mem_avg:.1f}%",    memory_color),
            ("磁盘 I/O",  _fmt_io(disk_avg),    disk_color),
            ("网络 I/O",  _fmt_io(net_avg),     net_color),
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
