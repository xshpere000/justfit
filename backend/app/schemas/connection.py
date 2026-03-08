"""Connection Schemas."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


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


class ConnectionCreate(BaseSchema):
    """Connection creation request."""

    name: str = Field(..., min_length=1, max_length=100)
    platform: str = Field(..., pattern="^(vcenter|h3c-uis)$")
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(default=443, ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)
    insecure: bool = Field(default=False)


class ConnectionUpdate(BaseSchema):
    """Connection update request."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    host: Optional[str] = Field(None, min_length=1, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = Field(None, min_length=1, max_length=100)
    password: Optional[str] = Field(None, min_length=1)
    insecure: Optional[bool] = None


class ConnectionResponse(BaseSchema):
    """Connection response."""

    success: bool = True
    data: Optional["ConnectionData"] = None
    message: Optional[str] = None
    error: Optional[dict] = None


class ConnectionData(BaseSchema):
    """Connection data."""

    id: int
    name: str
    platform: str
    host: str
    port: int
    username: str
    insecure: bool
    status: str
    lastSync: Optional[datetime] = None
    createdAt: datetime
    updatedAt: datetime
