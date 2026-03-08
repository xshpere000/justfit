"""Connection Service - Business logic for connection management."""

from typing import List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models import Connection
from app.repositories.connection import ConnectionRepository
from app.core.errors import NotFoundError, ValidationError, AppError
from app.security.credentials import CredentialManager
from app.connectors.base import Connector
from app.connectors.vcenter import VCenterConnector
from app.connectors.uis import UISConnector


logger = structlog.get_logger()


class ConnectionService:
    """Service for managing cloud platform connections."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize connection service.

        Args:
            session: Database session
        """
        self.session = session
        self.repo = ConnectionRepository(session)
        self.credentials = CredentialManager()

    async def create_connection(
        self,
        name: str,
        platform: str,
        host: str,
        port: int,
        username: str,
        password: str,
        insecure: bool = False,
    ) -> Connection:
        """Create a new connection.

        Args:
            name: Connection name
            platform: Platform type (vcenter or h3c-uis)
            host: Host address
            port: Port number
            username: Username
            password: Password (will be encrypted)
            insecure: Skip SSL verification

        Returns:
            Created connection

        Raises:
            ValidationError: If validation fails
        """
        # Validate platform
        if platform not in ("vcenter", "h3c-uis"):
            raise ValidationError(
                f"Invalid platform: {platform}. Must be 'vcenter' or 'h3c-uis'"
            )

        # Check for duplicate name
        existing = await self.repo.get_by_name(name)
        if existing:
            raise ValidationError(f"Connection with name '{name}' already exists")

        # Create connection record (password not stored in DB)
        connection = await self.repo.create(
            name=name,
            platform=platform,
            host=host,
            port=port,
            username=username,
            insecure=insecure,
            status="disconnected",
        )

        # Store encrypted password
        await self.credentials.save_password(connection.id, password)

        logger.info(
            "connection_created",
            connection_id=connection.id,
            name=name,
            platform=platform,
        )

        return connection

    async def list_connections(self) -> List[Connection]:
        """List all connections.

        Returns:
            List of connections
        """
        return await self.repo.list_all()

    async def get_connection(self, id: int) -> Connection:
        """Get connection by ID.

        Args:
            id: Connection ID

        Returns:
            Connection

        Raises:
            NotFoundError: If connection not found
        """
        connection = await self.repo.get_by_id(id)
        if not connection:
            raise NotFoundError(f"Connection {id} not found")
        return connection

    async def update_connection(
        self,
        id: int,
        name: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        insecure: Optional[bool] = None,
    ) -> Connection:
        """Update connection.

        Args:
            id: Connection ID
            name: New name
            host: New host
            port: New port
            username: New username
            password: New password
            insecure: New insecure flag

        Returns:
            Updated connection

        Raises:
            NotFoundError: If connection not found
        """
        connection = await self.get_connection(id)

        updates = {}
        if name is not None:
            # Check for duplicate name
            existing = await self.repo.get_by_name(name)
            if existing and existing.id != id:
                raise ValidationError(f"Connection with name '{name}' already exists")
            updates["name"] = name
        if host is not None:
            updates["host"] = host
        if port is not None:
            updates["port"] = port
        if username is not None:
            updates["username"] = username
        if insecure is not None:
            updates["insecure"] = insecure

        if password is not None:
            await self.credentials.save_password(id, password)

        if updates:
            await self.repo.update(id, **updates)
            await self.session.refresh(connection)

        logger.info("connection_updated", connection_id=id)

        return connection

    async def delete_connection(self, id: int) -> None:
        """Delete connection.

        Args:
            id: Connection ID

        Raises:
            NotFoundError: If connection not found
        """
        connection = await self.get_connection(id)
        await self.credentials.delete_password(id)
        await self.repo.delete(id)

        logger.info("connection_deleted", connection_id=id, name=connection.name)

    async def test_connection(self, id: int) -> dict:
        """Test connection to cloud platform.

        Args:
            id: Connection ID

        Returns:
            Test result with status and message

        Raises:
            NotFoundError: If connection not found
            AppError: If connection test fails
        """
        connection = await self.get_connection(id)
        password = await self.credentials.get_password(id)

        if not password:
            raise ValidationError("Password not found for connection")

        # Create connector
        connector = self._create_connector(connection, password)

        # Test connection
        try:
            result = await connector.test_connection()
            status = "connected" if result.get("success") else "failed"
            message = result.get("message", "")

            # Update connection status
            await self.repo.update_status(id, status, last_sync="now" if status == "connected" else None)

            logger.info(
                "connection_tested",
                connection_id=id,
                status=status,
            )

            return {"status": status, "message": message}
        except Exception as e:
            logger.error("connection_test_failed", connection_id=id, error=str(e))
            await self.repo.update_status(id, "disconnected")
            raise AppError(
                "CONNECTION_TEST_FAILED",
                f"Connection test failed: {str(e)}",
            )

    async def get_connector(self, id: int) -> Connector:
        """Get initialized connector for connection.

        Args:
            id: Connection ID

        Returns:
            Initialized connector instance

        Raises:
            NotFoundError: If connection not found
            ValidationError: If password not found
        """
        connection = await self.get_connection(id)
        password = await self.credentials.get_password(id)

        if not password:
            raise ValidationError("Password not found for connection")

        return self._create_connector(connection, password)

    def _create_connector(self, connection: Connection, password: str) -> Connector:
        """Create connector instance.

        Args:
            connection: Connection model
            password: Decrypted password

        Returns:
            Connector instance
        """
        if connection.platform == "vcenter":
            return VCenterConnector(
                host=connection.host,
                port=connection.port,
                username=connection.username,
                password=password,
                insecure=connection.insecure,
            )
        elif connection.platform == "h3c-uis":
            return UISConnector(
                host=connection.host,
                port=connection.port,
                username=connection.username,
                password=password,
                insecure=connection.insecure,
            )
        else:
            raise ValidationError(f"Unsupported platform: {connection.platform}")
