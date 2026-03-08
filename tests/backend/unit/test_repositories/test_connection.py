"""Unit tests for ConnectionRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.connection import ConnectionRepository
from app.models import Connection


@pytest.mark.asyncio
async def test_connection_repository_create(db_session: AsyncSession):
    """测试创建连接"""
    repo = ConnectionRepository(db_session)

    connection = await repo.create(
        name="Test Connection",
        platform="vcenter",
        host="10.0.0.1",
        port=443,
        username="admin",
    )

    assert connection.id is not None
    assert connection.name == "Test Connection"
    assert connection.platform == "vcenter"
    assert connection.status == "disconnected"


@pytest.mark.asyncio
async def test_connection_repository_get_by_id(db_session: AsyncSession):
    """测试通过 ID 获取连接"""
    repo = ConnectionRepository(db_session)

    # 先创建
    created = await repo.create(
        name="Test Connection",
        platform="vcenter",
        host="10.0.0.1",
        port=443,
        username="admin",
    )

    # 再获取
    found = await repo.get_by_id(created.id)

    assert found is not None
    assert found.id == created.id
    assert found.name == "Test Connection"


@pytest.mark.asyncio
async def test_connection_repository_list_all(db_session: AsyncSession):
    """测试列出所有连接"""
    repo = ConnectionRepository(db_session)

    # 创建多个连接
    await repo.create(
        name="Connection 1",
        platform="vcenter",
        host="10.0.0.1",
        port=443,
        username="admin",
    )
    await repo.create(
        name="Connection 2",
        platform="h3c-uis",
        host="10.0.0.2",
        port=443,
        username="admin",
    )

    # 列出所有
    connections = await repo.list_all()

    assert len(connections) >= 2


@pytest.mark.asyncio
async def test_connection_repository_update(db_session: AsyncSession):
    """测试更新连接"""
    repo = ConnectionRepository(db_session)

    # 创建
    created = await repo.create(
        name="Original Name",
        platform="vcenter",
        host="10.0.0.1",
        port=443,
        username="admin",
    )

    # 更新
    updated = await repo.update(
        created.id,
        name="Updated Name",
        host="10.0.0.2",
    )

    assert updated.name == "Updated Name"
    assert updated.host == "10.0.0.2"


@pytest.mark.asyncio
async def test_connection_repository_delete(db_session: AsyncSession):
    """测试删除连接"""
    repo = ConnectionRepository(db_session)

    # 创建
    created = await repo.create(
        name="To Delete",
        platform="vcenter",
        host="10.0.0.1",
        port=443,
        username="admin",
    )

    # 删除
    deleted = await repo.delete(created.id)

    assert deleted is True

    # 验证已删除
    found = await repo.get_by_id(created.id)
    assert found is None


@pytest.mark.asyncio
async def test_connection_repository_get_by_name(db_session: AsyncSession):
    """测试通过名称获取连接"""
    repo = ConnectionRepository(db_session)

    # 创建
    created = await repo.create(
        name="Unique Name",
        platform="vcenter",
        host="10.0.0.1",
        port=443,
        username="admin",
    )

    # 获取
    found = await repo.get_by_name("Unique Name")

    assert found is not None
    assert found.id == created.id
    assert found.name == "Unique Name"
