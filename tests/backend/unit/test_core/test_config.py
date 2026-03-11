"""Tests for application configuration with cross-platform support."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from app.config import Settings, _get_default_data_dir


class TestGetDefaultDataDir:
    """Test cross-platform data directory detection."""

    def test_current_platform_data_dir(self):
        """Test data directory on current platform."""
        data_dir = _get_default_data_dir()
        assert data_dir.name == "justfit"
        assert "justfit" in str(data_dir)

        # Verify it's an absolute path
        assert data_dir.is_absolute()

    def test_custom_data_dir_from_env(self):
        """Test that JUSTFIT_DATA_DIR environment variable overrides default."""
        custom_dir = "/tmp/custom_justfit_data"
        with patch.dict(os.environ, {"JUSTFIT_DATA_DIR": custom_dir}):
            settings = Settings()
            assert str(settings.DATA_DIR) == custom_dir

    @pytest.mark.skipif(os.name != "nt", reason="Windows-only test")
    def test_windows_data_dir_with_localappdata(self):
        """Test data directory on Windows with LOCALAPPDATA set."""
        fake_app_data = os.environ.get("LOCALAPPDATA", "")
        if fake_app_data:
            data_dir = _get_default_data_dir()
            # Should be %LOCALAPPDATA%\justfit
            assert "justfit" in str(data_dir)
            # Verify it's under LOCALAPPDATA
            assert fake_app_data in str(data_dir)

    @pytest.mark.skipif(os.name == "nt", reason="Unix-only test")
    def test_unix_data_dir(self):
        """Test data directory on Unix-like systems (Linux/macOS)."""
        data_dir = _get_default_data_dir()
        # Should be ~/.local/share/justfit
        assert str(data_dir).endswith(".local/share/justfit")
        assert data_dir == Path.home() / ".local" / "share" / "justfit"


class TestSettings:
    """Test Settings class."""

    def test_db_path_property(self):
        """Test database path property."""
        settings = Settings()
        assert settings.db_path == settings.DATA_DIR / "justfit.db"

    def test_key_path_property(self):
        """Test encryption key path property."""
        settings = Settings()
        assert settings.key_path == settings.DATA_DIR / ".key"

    def test_credentials_path_property(self):
        """Test credentials path property."""
        settings = Settings()
        assert settings.credentials_path == settings.DATA_DIR / "credentials.enc"

    def test_ensure_data_dir(self, tmp_path):
        """Test ensure_data_dir creates directory."""
        custom_dir = tmp_path / "test_justfit"
        settings = Settings(DATA_DIR=custom_dir)
        settings.ensure_data_dir()
        assert custom_dir.exists()
        assert custom_dir.is_dir()
