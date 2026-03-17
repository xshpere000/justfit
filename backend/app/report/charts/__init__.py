"""Chart drawing package for PDF report generation.

Public API (unchanged from old charts.py):
  PDFCharts   — main chart class
  COLORS      — color palette dict
  GRADE_COLORS — grade-level color dict
"""

from .constants import COLORS, GRADE_COLORS, ChartStyle, REPORTLAB_AVAILABLE
from .base import ChartBase
from .overview import OverviewCharts
from .vm_resource import VMResourceCharts


class PDFCharts(ChartBase, OverviewCharts, VMResourceCharts):
    """Unified chart drawer: gauge, bar, pie, radar, VM resource trend, etc.

    Inherits from:
      ChartBase       — font setup + geometry primitives (arc, pie slice, cos/sin)
      OverviewCharts  — gauge, bar, comparison, pie, radar, horizontal bar
      VMResourceCharts — 4-panel VM resource line chart
    """


__all__ = [
    "PDFCharts",
    "COLORS",
    "GRADE_COLORS",
    "ChartStyle",
    "REPORTLAB_AVAILABLE",
]
