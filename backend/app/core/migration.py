"""Data Migration Module.

This module handles version-based data migration and cleanup.
On first startup of a new version, it cleans up legacy data and creates a version marker.
"""

import logging
import shutil
from pathlib import Path
from typing import Optional

from app.config import settings
from app import __version__


logger = logging.getLogger(__name__)


# Version file name
VERSION_FILE = "version"


def get_version_path() -> Path:
    """Get the path to the version marker file."""
    return settings.DATA_DIR / VERSION_FILE


def get_stored_version() -> Optional[str]:
    """Get the stored version from the version file.

    Returns:
        The stored version string, or None if the file doesn't exist.
    """
    version_path = get_version_path()
    if not version_path.exists():
        return None
    try:
        return version_path.read_text().strip()
    except Exception as e:
        logger.warning(f"Failed to read version file: {e}")
        return None


def set_version(version: str) -> None:
    """Write the current version to the version file.

    Args:
        version: The version string to write.
    """
    version_path = get_version_path()
    try:
        settings.ensure_data_dir()
        version_path.write_text(version)
        logger.info(f"Version file created: {version}")
    except Exception as e:
        logger.error(f"Failed to write version file: {e}")


def clean_legacy_data() -> None:
    """Clean up legacy data files from previous versions.

    This removes:
    - Database file (justfit.db)
    - Encryption key (.key)
    - Encrypted credentials (credentials.enc)
    - Log directory (logs/)
    - WAL files (justfit.db-wal, justfit.db-shm)
    """
    data_dir = settings.DATA_DIR

    # Files and directories to remove
    items_to_remove = [
        settings.db_path,           # Database
        settings.key_path,          # Encryption key
        settings.credentials_path,  # Encrypted credentials
        data_dir / "logs",          # Log directory
        data_dir / "justfit.db-wal",  # WAL file
        data_dir / "justfit.db-shm",  # SHM file
    ]

    for item in items_to_remove:
        try:
            if item.is_dir():
                shutil.rmtree(item)
                logger.info(f"Removed directory: {item}")
            elif item.is_file():
                item.unlink()
                logger.info(f"Removed file: {item}")
        except FileNotFoundError:
            # Item doesn't exist, skip
            pass
        except Exception as e:
            logger.warning(f"Failed to remove {item}: {e}")


def migrate() -> None:
    """Run migration on application startup.

    Checks if the current version matches the stored version.
    If different (or no version file exists), performs a clean migration.
    """
    stored_version = get_stored_version()
    current_version = __version__

    if stored_version == current_version:
        # Same version, no migration needed
        logger.info(f"Version {current_version} already initialized, skipping migration")
        return

    # Version mismatch or first startup - perform clean migration
    if stored_version is None:
        logger.info(f"First startup of version {current_version}, cleaning legacy data")
    else:
        logger.info(f"Version mismatch: stored={stored_version}, current={current_version}, cleaning legacy data")

    # Clean up legacy data
    clean_legacy_data()

    # Create version marker
    set_version(current_version)

    logger.info(f"Migration to version {current_version} completed")
