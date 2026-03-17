"""Connection Repository."""

from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Connection
from .base import BaseRepository


class ConnectionRepository(BaseRepository[Connection]):
    """Repository for Connection model."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize connection repository."""
        super().__init__(Connection, session)

    async def list_by_status(self, status: str) -> List[Connection]:
        """List connections by status."""
        result = await self.session.execute(
            select(Connection).where(Connection.status == status)
        )
        return list(result.scalars().all())

    async def list_connected(self) -> List[Connection]:
        """List all connected connections."""
        return await self.list_by_status("connected")

    async def update_status(
        self,
        id: int,
        status: str,
        last_sync: Optional[str] = None,
    ) -> Optional[Connection]:
        """Update connection status."""
        from datetime import datetime
        values = {"status": status}
        if last_sync == "now":
            values["last_sync"] = datetime.now()

        await self.session.execute(
            select(Connection).where(Connection.id == id)
        )
        result = await self.session.execute(
            update(Connection).where(Connection.id == id).values(**values)
        )
        await self.session.flush()
        return await self.get_by_id(id)
