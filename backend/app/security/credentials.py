"""Credential Manager - AES-256-GCM encryption for passwords."""

import json
import os
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import structlog

from app.config import settings


logger = structlog.get_logger()


class CredentialManager:
    """Manages encrypted credential storage."""

    def __init__(self) -> None:
        """Initialize credential manager."""
        self.key_path = settings.key_path
        self.credentials_path = settings.credentials_path
        self._ensure_files()

    def _ensure_files(self) -> None:
        """Ensure key and credentials files exist."""
        # Ensure data directory exists
        settings.ensure_data_dir()

        # Create encryption key if not exists
        if not self.key_path.exists():
            self.key_path.write_bytes(os.urandom(32))
            self.key_path.chmod(0o600)
            logger.info("encryption_key_created", path=str(self.key_path))

        # Create empty credentials file if not exists
        if not self.credentials_path.exists():
            self.credentials_path.write_text("{}")
            self.credentials_path.chmod(0o600)

    def _get_key(self) -> bytes:
        """Get encryption key.

        Returns:
            32-byte encryption key
        """
        return self.key_path.read_bytes()

    def _load_credentials(self) -> dict:
        """Load credentials from file.

        Returns:
            Credentials dictionary
        """
        try:
            data = self.credentials_path.read_text()
            return json.loads(data) if data else {}
        except Exception as e:
            logger.error("failed_to_load_credentials", error=str(e))
            return {}

    def _save_credentials(self, data: dict) -> None:
        """Save credentials to file.

        Args:
            data: Credentials dictionary
        """
        self.credentials_path.write_text(json.dumps(data, indent=2))
        self.credentials_path.chmod(0o600)

    async def save_password(self, connection_id: int, password: str) -> None:
        """Save encrypted password for connection.

        Args:
            connection_id: Connection ID
            password: Plain text password
        """
        key = self._get_key()
        aesgcm = AESGCM(key)

        # Generate nonce
        nonce = os.urandom(12)

        # Encrypt password
        ciphertext = aesgcm.encrypt(nonce, password.encode(), None)

        # Store as base64
        import base64
        encrypted_data = base64.b64encode(nonce + ciphertext).decode()

        # Load, update, save
        creds = self._load_credentials()
        creds[str(connection_id)] = encrypted_data
        self._save_credentials(creds)

        logger.debug("password_saved", connection_id=connection_id)

    async def get_password(self, connection_id: int) -> Optional[str]:
        """Get decrypted password for connection.

        Args:
            connection_id: Connection ID

        Returns:
            Decrypted password or None if not found
        """
        creds = self._load_credentials()
        encrypted_data = creds.get(str(connection_id))

        if not encrypted_data:
            return None

        try:
            key = self._get_key()
            aesgcm = AESGCM(key)

            # Decode base64
            import base64
            data = base64.b64decode(encrypted_data)

            # Split nonce and ciphertext
            nonce = data[:12]
            ciphertext = data[12:]

            # Decrypt
            password = aesgcm.decrypt(nonce, ciphertext, None).decode()

            logger.debug("password_retrieved", connection_id=connection_id)

            return password
        except Exception as e:
            logger.error("failed_to_decrypt_password", connection_id=connection_id, error=str(e))
            return None

    async def delete_password(self, connection_id: int) -> None:
        """Delete password for connection.

        Args:
            connection_id: Connection ID
        """
        creds = self._load_credentials()
        if str(connection_id) in creds:
            del creds[str(connection_id)]
            self._save_credentials(creds)
            logger.debug("password_deleted", connection_id=connection_id)
