"""Base Repository with common CRUD operations."""

from typing import Generic, TypeVar, Optional, List

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            model: SQLAlchemy model class
            session: Async database session
        """
        self.model = model
        self.session = session

    async def create(self, **kwargs) -> ModelType:
        """Create a new record."""
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """Get record by ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> List[ModelType]:
        """List all records with pagination."""
        result = await self.session.execute(
            select(self.model).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, id: int, **kwargs) -> Optional[ModelType]:
        """Update record by ID."""
        await self.session.execute(
            update(self.model).where(self.model.id == id).values(**kwargs)
        )
        await self.session.flush()
        return await self.get_by_id(id)

    async def delete(self, id: int) -> bool:
        """Delete record by ID."""
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        await self.session.flush()
        return result.rowcount > 0

    async def count(self) -> int:
        """Count all records."""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar() or 0
