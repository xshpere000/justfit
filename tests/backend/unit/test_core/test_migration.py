"""Tests for data migration module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.core.migration import (
    get_version_path,
    get_stored_version,
    set_version,
    clean_legacy_data,
    migrate,
)
from app.config import Settings


@pytest.fixture
def temp_data_dir(tmp_path: Path):
    """Create a temporary data directory for testing."""
    data_dir = tmp_path / "justfit"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def mock_settings(temp_data_dir: Path):
    """Mock settings with temporary data directory."""
    settings = MagicMock(spec=Settings)
    settings.DATA_DIR = temp_data_dir
    settings.db_path = temp_data_dir / "justfit.db"
    settings.key_path = temp_data_dir / ".key"
    settings.credentials_path = temp_data_dir / "credentials.enc"
    settings.ensure_data_dir = MagicMock()
    return settings


def test_get_version_path(mock_settings):
    """Test getting version file path."""
    with patch("app.core.migration.settings", mock_settings):
        version_path = get_version_path()
        assert version_path == mock_settings.DATA_DIR / "version"


def test_get_stored_version_no_file(mock_settings):
    """Test getting version when no version file exists."""
    with patch("app.core.migration.settings", mock_settings):
        version = get_stored_version()
        assert version is None


def test_set_and_get_version(mock_settings):
    """Test setting and getting version."""
    with patch("app.core.migration.settings", mock_settings):
        set_version("0.0.3")
        version = get_stored_version()
        assert version == "0.0.3"


def test_clean_legacy_data(mock_settings, temp_data_dir):
    """Test cleaning legacy data files."""
    # Create some legacy files
    (temp_data_dir / "justfit.db").touch()
    (temp_data_dir / ".key").touch()
    (temp_data_dir / "credentials.enc").touch()
    (temp_data_dir / "logs").mkdir()
    (temp_data_dir / "logs" / "test.log").touch()
    (temp_data_dir / "justfit.db-wal").touch()
    (temp_data_dir / "justfit.db-shm").touch()

    with patch("app.core.migration.settings", mock_settings):
        clean_legacy_data()

    # Verify all files are removed
    assert not (temp_data_dir / "justfit.db").exists()
    assert not (temp_data_dir / ".key").exists()
    assert not (temp_data_dir / "credentials.enc").exists()
    assert not (temp_data_dir / "logs").exists()
    assert not (temp_data_dir / "justfit.db-wal").exists()
    assert not (temp_data_dir / "justfit.db-shm").exists()


def test_migrate_first_startup(mock_settings, temp_data_dir):
    """Test migration on first startup (no version file)."""
    with patch("app.core.migration.settings", mock_settings):
        with patch("app.core.migration.__version__", "0.0.3"):
            migrate()

    # Version file should be created
    assert (temp_data_dir / "version").exists()
    assert (temp_data_dir / "version").read_text() == "0.0.3"


def test_migrate_version_change(mock_settings, temp_data_dir):
    """Test migration when version changes."""
    # Create old version file
    (temp_data_dir / "version").write_text("0.0.2")

    # Create some legacy files
    (temp_data_dir / "justfit.db").touch()

    with patch("app.core.migration.settings", mock_settings):
        with patch("app.core.migration.__version__", "0.0.3"):
            migrate()

    # Version should be updated
    assert (temp_data_dir / "version").read_text() == "0.0.3"
    # Legacy files should be removed
    assert not (temp_data_dir / "justfit.db").exists()


def test_migrate_same_version(mock_settings, temp_data_dir):
    """Test migration when version is the same."""
    # Create version file with current version
    (temp_data_dir / "version").write_text("0.0.3")

    # Create a file that should NOT be removed
    (temp_data_dir / "justfit.db").touch()

    with patch("app.core.migration.settings", mock_settings):
        with patch("app.core.migration.__version__", "0.0.3"):
            migrate()

    # File should still exist (no cleanup)
    assert (temp_data_dir / "justfit.db").exists()
