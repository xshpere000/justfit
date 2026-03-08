"""Settings Model."""

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Text, DateTime, func
from typing import Optional

from app.core.database import Base
from app.models import TimestampMixin


class Settings(Base, TimestampMixin):
    """Application settings."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[str] = mapped_column(Text, default="")
