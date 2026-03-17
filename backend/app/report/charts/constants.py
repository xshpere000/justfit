"""Shared reportlab imports, color palette, and chart style configuration."""

from dataclasses import dataclass, field
from typing import Any

try:
    from reportlab.graphics.shapes import (
        Drawing, Rect, Circle, String, Line, Polygon, Group,
    )
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    REPORTLAB_AVAILABLE = True
except ImportError:
    Drawing = Rect = Circle = String = Line = Polygon = Group = None  # type: ignore
    colors = None  # type: ignore
    cm = 28.35  # 1 cm in points (fallback)
    REPORTLAB_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    _font_prop = None


if REPORTLAB_AVAILABLE:
    COLORS = {
        "primary":     colors.HexColor("#1E3A8A"),
        "success":     colors.HexColor("#10B981"),
        "warning":     colors.HexColor("#F59E0B"),
        "danger":      colors.HexColor("#EF4444"),
        "info":        colors.HexColor("#3B82F6"),   # 蓝 — CPU 专用
        "purple":      colors.HexColor("#8B5CF6"),   # 紫 — 网络接收专用
        "net_send":    colors.HexColor("#06B6D4"),   # 青 — 网络发送专用（与 CPU 蓝区分）
        "gray":        colors.HexColor("#6B7280"),
        "bg_light":    colors.HexColor("#F9FAFB"),
        "title_color": colors.HexColor("#111827"),
        "axis_color":  colors.HexColor("#9CA3AF"),
        "grid_color":  colors.HexColor("#E5E7EB"),
    }
    GRADE_COLORS = {
        "excellent": colors.HexColor("#10B981"),
        "good":      colors.HexColor("#3B82F6"),
        "fair":      colors.HexColor("#F59E0B"),
        "poor":      colors.HexColor("#EF4444"),
        "critical":  colors.HexColor("#DC2626"),
    }
else:
    COLORS = {}
    GRADE_COLORS = {}


@dataclass
class ChartStyle:
    """Chart style configuration."""

    width: float = 12 * cm
    height: float = 6 * cm
    font_name: str = "Helvetica"
    title_color: Any = field(default=None)
    axis_color: Any = field(default=None)
    grid_color: Any = field(default=None)

    def __post_init__(self) -> None:
        if REPORTLAB_AVAILABLE and self.title_color is None:
            self.title_color = COLORS["title_color"]
            self.axis_color = COLORS["axis_color"]
            self.grid_color = COLORS["grid_color"]
