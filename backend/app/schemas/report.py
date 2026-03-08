"""Report Schemas."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class BaseSchema(BaseModel):
    """Base schema with camelCase alias."""

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ReportCreateRequest(BaseSchema):
    """Report creation request."""

    format: Literal["excel", "pdf"] = Field(
        ...,
        description="Report format",
    )
    include_raw_data: bool = Field(
        default=False,
        description="Include raw data in report",
    )


class ReportResponse(BaseSchema):
    """Report response."""

    id: int
    task_id: int
    format: str
    file_path: str
    file_size: int
    created_at: str


class ReportListResponse(BaseSchema):
    """Report list response."""

    success: bool
    data: list[ReportResponse]
    message: Optional[str] = None


class ReportGenerationResponse(BaseSchema):
    """Report generation response."""

    success: bool
    data: Optional[dict] = None
    message: Optional[str] = None
    error: Optional[dict] = None
