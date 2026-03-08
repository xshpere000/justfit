"""API Integration tests."""

import pytest
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app


# Create transport from the app
transport = ASGITransport(app=app)


@pytest.fixture(scope="session")
def event_loop():
    """Event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_create_connection_api():
    """测试创建连接 API"""
    import uuid
    unique_name = f"Test vCenter {uuid.uuid4().hex[:6]}"

    async with AsyncClient(base_url="http://test", transport=transport) as client:
        response = await client.post("/api/connections", json={
            "name": unique_name,
            "platform": "vcenter",
            "host": "10.103.116.116",
            "port": 443,
            "username": "administrator@vsphere.local",
            "password": "Admin@123.",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data


@pytest.mark.asyncio
async def test_list_connections_api():
    """测试连接列表 API"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        response = await client.get("/api/connections")

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        # API 返回 {success: true, data: {items: [...], total: N}} 格式
        assert "data" in result
        assert "items" in result["data"]
        assert "total" in result["data"]


@pytest.mark.asyncio
async def test_analysis_modes_api():
    """测试分析模式 API"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        response = await client.get("/api/analysis/modes")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "safe" in data["data"]


@pytest.mark.asyncio
async def test_invalid_mode_returns_400():
    """测试无效模式返回 400"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        response = await client.get("/api/analysis/modes/invalid")

        assert response.status_code == 400


@pytest.mark.asyncio
async def test_system_health_api():
    """测试系统健康检查 API"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        response = await client.get("/api/system/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_system_version_api():
    """测试系统版本 API"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        response = await client.get("/api/system/version")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data


@pytest.mark.asyncio
async def test_connection_endpoints():
    """测试连接相关的多个端点"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        # 1. 测试连接列表
        list_response = await client.get("/api/connections")
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert list_data["success"] is True

        # 2. 测试分析模式
        modes_response = await client.get("/api/analysis/modes")
        assert modes_response.status_code == 200
        modes_data = modes_response.json()
        assert modes_data["success"] is True

        # 3. 测试系统健康
        health_response = await client.get("/api/system/health")
        assert health_response.status_code == 200

        # 4. 测试系统版本
        version_response = await client.get("/api/system/version")
        assert version_response.status_code == 200
        assert "version" in version_response.json()
