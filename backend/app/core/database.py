"""Database Configuration and Session Management."""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event

from app.config import settings


# 在创建 engine 之前设置 SQLAlchemy logger 级别，避免大量 SQL 日志
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)


def _set_wal_mode(dbapi_conn, connection_record):
    """Enable WAL mode for better SQLite concurrency."""
    cursor = dbapi_conn.cursor()
    try:
        # 启用外键约束（SQLite 默认不启用）
        cursor.execute("PRAGMA foreign_keys=ON")
        # 启用 WAL 模式以提高并发性能
        cursor.execute("PRAGMA journal_mode=WAL")
        # 设置更长的超时时间（30秒）
        cursor.execute("PRAGMA busy_timeout=30000")
        # 设置同步模式为 NORMAL（在 WAL 模式下更安全）
        cursor.execute("PRAGMA synchronous=NORMAL")
    except Exception as e:
        logging.warning(f"Failed to set SQLite PRAGMA: {e}")
    finally:
        cursor.close()


# Create async engine with WAL mode enabled
engine = create_async_engine(
    f"sqlite+aiosqlite:///{settings.db_path}",
    echo=False,  # 关闭 SQLAlchemy 的 echo 输出，避免重复日志
    connect_args={
        "check_same_thread": False,
    },
    # 使用连接池但限制大小，避免 SQLite 并发问题
    pool_size=5,
    max_overflow=0,
)

# 为新连接设置 WAL 模式
event.listen(engine.sync_engine, "connect", _set_wal_mode)

# Create async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
