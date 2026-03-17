"""Base chart class: font initialization and low-level drawing primitives."""

import math
from pathlib import Path

from .constants import (
    ChartStyle,
    Drawing, Polygon,
    colors,
    REPORTLAB_AVAILABLE,
)


class ChartBase:
    """Font setup and geometry primitives shared by all chart types."""

    def __init__(self, font_name: str = "Helvetica") -> None:
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for chart generation")

        # Prefer bundled Chinese font when available
        bundled_font = Path(__file__).parent.parent / "assets" / "simhei.ttf"
        if bundled_font.exists():
            try:
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont
                pdfmetrics.registerFont(TTFont("CNChartFont", str(bundled_font)))
                self.font_name = "CNChartFont"
                self.font_bold = "CNChartFont"
            except Exception:
                self.font_name = font_name
                self.font_bold = font_name
        else:
            self.font_name = font_name
            self.font_bold = font_name

        self.style = ChartStyle(font_name=self.font_name)

    # ── Arc / pie primitives ──────────────────────────────────────────────

    def _draw_arc(
        self,
        drawing: Drawing,
        cx: float, cy: float, radius: float,
        start_angle: float, end_angle: float,
        color: object,
        thickness: float,
    ) -> None:
        path = self._create_arc_path(cx, cy, radius, start_angle, end_angle, thickness)
        path.fillColor = color
        path.strokeColor = None
        drawing.add(path)

    def _create_arc_path(
        self,
        cx: float, cy: float, radius: float,
        start_angle: float, end_angle: float,
        thickness: float,
    ) -> Polygon:
        points: list = []
        steps = max(1, int(abs(end_angle - start_angle) / 5))
        for i in range(steps + 1):
            angle = start_angle + (end_angle - start_angle) * i / steps
            r = radius + thickness / 2
            points.extend([cx + r * self._cos(angle), cy + r * self._sin(angle)])
        for i in range(steps, -1, -1):
            angle = start_angle + (end_angle - start_angle) * i / steps
            r = radius - thickness / 2
            points.extend([cx + r * self._cos(angle), cy + r * self._sin(angle)])
        return Polygon(points)

    def _draw_pie_slice(
        self,
        drawing: Drawing,
        cx: float, cy: float, radius: float,
        start_angle: float, end_angle: float,
        color: object,
    ) -> None:
        points = [cx, cy]
        steps = max(5, int(abs(end_angle - start_angle) / 5))
        for i in range(steps + 1):
            angle = start_angle + (end_angle - start_angle) * i / steps
            points.extend([cx + radius * self._cos(angle), cy + radius * self._sin(angle)])
        poly = Polygon(points)
        poly.fillColor = color
        poly.strokeColor = colors.white
        poly.strokeWidth = 1
        drawing.add(poly)

    # ── Math helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _cos(angle_degrees: float) -> float:
        return math.cos(math.radians(angle_degrees))

    @staticmethod
    def _sin(angle_degrees: float) -> float:
        return math.sin(math.radians(angle_degrees))
