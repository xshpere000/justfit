"""Application Configuration."""

import os
import sys
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_default_data_dir() -> Path:
    """Get platform-specific default data directory.

    Returns:
        - Windows: %LOCALAPPDATA%\\justfit (e.g., C:\\Users\\<user>\\AppData\\Local\\justfit)
        - Linux/macOS: ~/.local/share/justfit
    """
    if os.name == "nt":  # Windows
        # Use LOCALAPPDATA environment variable on Windows
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "justfit"
        # Fallback to user home directory
        return Path.home() / "AppData" / "Local" / "justfit"
    else:  # Linux, macOS, etc.
        return Path.home() / ".local" / "share" / "justfit"


def _get_default_debug() -> bool:
    """Disable debug defaults for frozen executables."""
    return not getattr(sys, "frozen", False)


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_prefix="JUSTFIT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields from .env
    )

    # API Settings
    API_PORT: int = 22631
    API_HOST: str = "127.0.0.1"
    DEBUG: bool = _get_default_debug()

    # Database Settings
    DATA_DIR: Path = _get_default_data_dir()
    DB_NAME: str = "justfit.db"

    # Security Settings
    SECRET_KEY_FILE: str = ".key"
    CREDENTIALS_FILE: str = "credentials.enc"

    # Analysis Settings
    DEFAULT_METRIC_DAYS: int = 30
    METRIC_INTERVAL_SECONDS: int = 20

    # vCenter Settings
    VCENTER_TIMEOUT: int = 30
    VCENTER_MAX_RETRIES: int = 3

    @property
    def db_path(self) -> Path:
        """Get database path."""
        return self.DATA_DIR / self.DB_NAME

    @property
    def key_path(self) -> Path:
        """Get encryption key path."""
        return self.DATA_DIR / self.SECRET_KEY_FILE

    @property
    def credentials_path(self) -> Path:
        """Get credentials file path."""
        return self.DATA_DIR / self.CREDENTIALS_FILE

    def ensure_data_dir(self) -> None:
        """Ensure data directory exists."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.ensure_data_dir()
    return settings


# Global settings instance
settings = get_settings()
