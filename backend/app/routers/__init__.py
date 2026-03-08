"""API Routers."""

from .connection import router as connection_router
from .task import router as task_router
from .resource import router as resource_router
from .analysis import router as analysis_router
from .report import router as report_router

__all__ = [
    "connection_router",
    "task_router",
    "resource_router",
    "analysis_router",
    "report_router",
]
