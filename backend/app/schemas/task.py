"""Task Schemas."""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime

from app.schemas.connection import to_camel, BaseSchema


class TaskCreate(BaseSchema):
    """Task creation request."""

    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., pattern="^(collection|analysis)$")
    connection_id: Optional[int] = None
    config: Optional[dict] = None
    mode: str = Field(default="saving", pattern="^(safe|saving|aggressive|custom)$", alias="mode")
    base_mode: Optional[str] = Field(default=None, pattern="^(safe|saving|aggressive)$", alias="baseMode")
    metric_days: Optional[int] = Field(default=None, ge=1, le=90, alias="metricDays")


class TaskResponse(BaseSchema):
    """Task response."""

    id: int
    name: str
    type: str
    status: str
    progress: float
    error: Optional[str] = None
    connection_id: Optional[int] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
