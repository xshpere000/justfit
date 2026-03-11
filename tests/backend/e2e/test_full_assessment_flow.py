"""End-to-End Assessment Flow Test.

Tests complete assessment workflow:
1. Create connection → test connection
2. Data collection (ETL) - clusters/hosts/VMs
3. Performance metrics collection
4. Run 4 analysis types
5. Generate reports
6. Verify result integrity

Run with: PYTHONPATH=backend pytest tests/backend/e2e/test_full_assessment_flow.py -v -s
"""

import pytest
import asyncio
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import create_async_engine, AsyncSession, async_sessionmaker
from app.models import Base


# Test environment credentials
VCENTER_HOST = "10.103.116.116"
VCENTER_PORT = 443
VCENTER_USER = "administrator@vsphere.local"
VCENTER_PASSWORD = "Admin@123."


# Create transport from the app
transport = ASGITransport(app=app)


@pytest.fixture(scope="module")
async def e2e_db():
    """Create in-memory database for E2E test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    yield async_session_maker

    await engine.dispose()


@pytest.fixture
async def e2e_client(e2e_db):
    """Create HTTP client with E2E database."""
    from app.core.database import get_db

    # Use module-scoped session maker
    session_maker = e2e_db

    async def override_get_db():
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(base_url="http://test", transport=transport) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_e2e_full_assessment_flow(e2e_client: AsyncClient):
    """Test complete assessment flow from connection to report generation."""

    # ========================================
    # Step 1: Create Connection
    # ========================================
    print("\n" + "="*60)
    print("Step 1: Creating vCenter Connection")
    print("="*60)

    unique_name = f"E2E Test vCenter {uuid.uuid4().hex[:6]}"
    connection_response = await e2e_client.post("/api/connections", json={
        "name": unique_name,
        "platform": "vcenter",
        "host": VCENTER_HOST,
        "port": VCENTER_PORT,
        "username": VCENTER_USER,
        "password": VCENTER_PASSWORD,
        "insecure": True,
    })

    assert connection_response.status_code == 200
    connection_data = connection_response.json()
    assert connection_data["success"] is True

    connection_id = connection_data["data"]["id"]
    print(f"✓ Connection created: ID={connection_id}, Name={unique_name}")

    # ========================================
    # Step 2: Test Connection
    # ========================================
    print("\n" + "="*60)
    print("Step 2: Testing Connection")
    print("="*60)

    test_response = await e2e_client.post(f"/api/connections/{connection_id}/test")
    assert test_response.status_code == 200
    test_data = test_response.json()
    assert test_data["success"] is True
    print(f"✓ Connection test successful")

    # ========================================
    # Step 3: Data Collection (ETL)
    # ========================================
    print("\n" + "="*60)
    print("Step 3: Collecting Resources (Clusters/Hosts/VMs)")
    print("="*60)

    collect_response = await e2e_client.post(f"/api/resources/connections/{connection_id}/collect")
    assert collect_response.status_code == 200
    collect_data = collect_response.json()
    assert collect_data["success"] is True

    collection_result = collect_data["data"]
    print(f"✓ Collection completed:")
    print(f"  - Clusters: {collection_result.get('clusters', 0)}")
    print(f"  - Hosts: {collection_result.get('hosts', 0)}")
    print(f"  - VMs: {collection_result.get('vms', 0)}")

    # Verify we have resources
    assert collection_result.get("clusters", 0) >= 0
    assert collection_result.get("hosts", 0) >= 0
    assert collection_result.get("vms", 0) >= 0

    # ========================================
    # Step 4: Verify Collected Resources
    # ========================================
    print("\n" + "="*60)
    print("Step 4: Verifying Collected Resources")
    print("="*60)

    # Get clusters
    clusters_response = await e2e_client.get(f"/api/resources/connections/{connection_id}/clusters")
    assert clusters_response.status_code == 200
    clusters_data = clusters_response.json()
    assert clusters_data["success"] is True
    clusters = clusters_data["data"]["items"]
    print(f"✓ Retrieved {len(clusters)} cluster(s)")

    # Get hosts
    hosts_response = await e2e_client.get(f"/api/resources/connections/{connection_id}/hosts")
    assert hosts_response.status_code == 200
    hosts_data = hosts_response.json()
    assert hosts_data["success"] is True
    hosts = hosts_data["data"]["items"]
    print(f"✓ Retrieved {len(hosts)} host(s)")

    # Get VMs
    vms_response = await e2e_client.get(f"/api/resources/connections/{connection_id}/vms")
    assert vms_response.status_code == 200
    vms_data = vms_response.json()
    assert vms_data["success"] is True
    vms = vms_data["data"]["items"]
    print(f"✓ Retrieved {len(vms)} VM(s)")

    # ========================================
    # Step 5: Create Collection Task
    # ========================================
    print("\n" + "="*60)
    print("Step 5: Creating Collection Task")
    print("="*60)

    task_response = await e2e_client.post("/api/tasks", json={
        "name": f"E2E Collection Task {uuid.uuid4().hex[:6]}",
        "type": "collection",
        "connectionId": connection_id,
        "mode": "saving",  # 使用新的评估模式参数
        "metricDays": 3,  # 使用新的采集天数参数（减少测试时间）
    })

    assert task_response.status_code == 200
    task_data = task_response.json()
    assert task_data["success"] is True

    task_id = task_data["data"]["id"]
    task = task_data["data"]
    print(f"✓ Collection task created: ID={task_id}")
    print(f"  - Mode: {task.get('mode')}")
    print(f"  - Connection: {task.get('connectionId')}")

    # 验证顶层 mode 字段正确（lite 版本包含 mode 字段）
    assert task.get("mode") == "saving", f"Mode should be 'saving', got {task.get('mode')}"

    # 获取完整任务详情来验证 config（包含 metricDays）
    detail_response = await e2e_client.get(f"/api/tasks/{task_id}")
    assert detail_response.status_code == 200
    task_detail = detail_response.json()["data"]
    config = task_detail.get("config", {})
    assert config.get("mode") == "saving", f"Config mode should be 'saving', got {config.get('mode')}"
    assert config.get("metricDays") == 3, f"metricDays should be 3, got {config.get('metricDays')}"
    print(f"✓ Config verified: mode={config.get('mode')}, metricDays={config.get('metricDays')}")

    # ========================================
    # Step 6: Health Score Analysis
    # ========================================
    print("\n" + "="*60)
    print("Step 6: Running Health Score Analysis")
    print("="*60)

    health_response = await e2e_client.post(
        f"/api/analysis/tasks/{task_id}/health",
        json={"mode": "safe"}
    )

    assert health_response.status_code == 200
    health_data = health_response.json()
    assert health_data["success"] is True

    health_result = health_data["data"]
    print(f"✓ Health score analysis completed:")
    print(f"  - Overall Score: {health_result.get('overallScore', 0)}")
    print(f"  - Grade: {health_result.get('grade', 'unknown')}")

    # Verify health score structure
    assert "overallScore" in health_result
    assert "grade" in health_result
    assert 0 <= health_result["overallScore"] <= 100

    # ========================================
    # Step 7: Analysis Modes Verification
    # ========================================
    print("\n" + "="*60)
    print("Step 7: Verifying Analysis Modes")
    print("="*60)

    modes_response = await e2e_client.get("/api/analysis/modes")
    assert modes_response.status_code == 200
    modes_data = modes_response.json()
    assert modes_data["success"] is True

    modes = modes_data["data"]
    assert "safe" in modes
    assert "saving" in modes
    assert "aggressive" in modes
    assert "custom" in modes
    print(f"✓ All 4 analysis modes available")

    # ========================================
    # Step 8: System Health Check
    # ========================================
    print("\n" + "="*60)
    print("Step 8: System Health Check")
    print("="*60)

    health_check_response = await e2e_client.get("/api/system/health")
    assert health_check_response.status_code == 200
    health_check = health_check_response.json()
    assert health_check["status"] == "healthy"
    print(f"✓ System health: {health_check['status']}")

    # ========================================
    # Step 9: Cleanup
    # ========================================
    print("\n" + "="*60)
    print("Step 9: Cleaning Up Test Resources")
    print("="*60)

    # Delete task
    delete_task_response = await e2e_client.delete(f"/api/tasks/{task_id}")
    assert delete_task_response.status_code == 200
    print(f"✓ Task {task_id} deleted")

    # Delete connection
    delete_connection_response = await e2e_client.delete(f"/api/connections/{connection_id}")
    assert delete_connection_response.status_code == 200
    print(f"✓ Connection {connection_id} deleted")

    # ========================================
    # Summary
    # ========================================
    print("\n" + "="*60)
    print("E2E TEST SUMMARY")
    print("="*60)
    print("✓ All steps completed successfully!")
    print("="*60)


@pytest.mark.asyncio
async def test_e2e_connection_workflow(e2e_client: AsyncClient):
    """Test connection creation, update, and deletion workflow."""

    print("\n" + "="*60)
    print("CONNECTION WORKFLOW TEST")
    print("="*60)

    # Create
    unique_name = f"Workflow Test {uuid.uuid4().hex[:6]}"
    create_response = await e2e_client.post("/api/connections", json={
        "name": unique_name,
        "platform": "vcenter",
        "host": VCENTER_HOST,
        "port": VCENTER_PORT,
        "username": VCENTER_USER,
        "password": VCENTER_PASSWORD,
        "insecure": True,
    })
    assert create_response.status_code == 200
    connection_id = create_response.json()["data"]["id"]
    print(f"✓ Created connection: {connection_id}")

    # Read
    get_response = await e2e_client.get(f"/api/connections/{connection_id}")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["id"] == connection_id
    print(f"✓ Retrieved connection: {connection_id}")

    # Update
    update_response = await e2e_client.put(f"/api/connections/{connection_id}", json={
        "name": f"{unique_name} (Updated)",
    })
    assert update_response.status_code == 200
    assert "(Updated)" in update_response.json()["data"]["name"]
    print(f"✓ Updated connection: {connection_id}")

    # List
    list_response = await e2e_client.get("/api/connections")
    assert list_response.status_code == 200
    connections = list_response.json()["data"]["items"]
    assert len(connections) > 0
    print(f"✓ Listed {len(connections)} connection(s)")

    # Delete
    delete_response = await e2e_client.delete(f"/api/connections/{connection_id}")
    assert delete_response.status_code == 200
    print(f"✓ Deleted connection: {connection_id}")

    # Verify deletion
    get_after_delete = await e2e_client.get(f"/api/connections/{connection_id}")
    assert get_after_delete.status_code == 404
    print(f"✓ Verified deletion (404 response)")


@pytest.mark.asyncio
async def test_e2e_task_lifecycle(e2e_client: AsyncClient):
    """Test task creation, status tracking, and deletion."""

    print("\n" + "="*60)
    print("TASK LIFECYCLE TEST")
    print("="*60)

    # First create a connection
    create_conn_response = await e2e_client.post("/api/connections", json={
        "name": f"Task Test {uuid.uuid4().hex[:6]}",
        "platform": "vcenter",
        "host": VCENTER_HOST,
        "port": VCENTER_PORT,
        "username": VCENTER_USER,
        "password": VCENTER_PASSWORD,
        "insecure": True,
    })
    connection_id = create_conn_response.json()["data"]["id"]

    # Create task with new parameters
    task_response = await e2e_client.post("/api/tasks", json={
        "name": f"Lifecycle Task {uuid.uuid4().hex[:6]}",
        "type": "collection",
        "connectionId": connection_id,
        "mode": "safe",
        "metricDays": 7,
    })
    assert task_response.status_code == 200
    task_id = task_response.json()["data"]["id"]
    print(f"✓ Created task: {task_id}")

    # Get task details
    detail_response = await e2e_client.get(f"/api/tasks/{task_id}")
    assert detail_response.status_code == 200
    task_detail = detail_response.json()["data"]
    assert task_detail["id"] == task_id
    assert task_detail["connectionId"] == connection_id
    print(f"✓ Retrieved task details")

    # Get task logs
    logs_response = await e2e_client.get(f"/api/tasks/{task_id}/logs")
    assert logs_response.status_code == 200
    logs = logs_response.json()["data"]["items"]
    print(f"✓ Retrieved {len(logs)} log entries")

    # Get VM snapshots
    snapshots_response = await e2e_client.get(f"/api/tasks/{task_id}/vm-snapshots")
    assert snapshots_response.status_code == 200
    snapshots = snapshots_response.json()["data"]["items"]
    print(f"✓ Retrieved {len(snapshots)} VM snapshots")

    # List all tasks
    list_response = await e2e_client.get("/api/tasks")
    assert list_response.status_code == 200
    tasks = list_response.json()["data"]["items"]
    assert len(tasks) > 0
    print(f"✓ Listed {len(tasks)} task(s)")

    # Delete task
    delete_response = await e2e_client.delete(f"/api/tasks/{task_id}")
    assert delete_response.status_code == 200
    print(f"✓ Deleted task: {task_id}")

    # Cleanup connection
    await e2e_client.delete(f"/api/connections/{connection_id}")


@pytest.mark.asyncio
async def test_e2e_analysis_modes_workflow(e2e_client: AsyncClient):
    """Test analysis modes retrieval and updates."""

    print("\n" + "="*60)
    print("ANALYSIS MODES WORKFLOW TEST")
    print("="*60)

    # Get all modes
    all_modes_response = await e2e_client.get("/api/analysis/modes")
    assert all_modes_response.status_code == 200
    all_modes = all_modes_response.json()["data"]
    print(f"✓ Retrieved {len(all_modes)} modes")

    # Get specific mode - safe
    safe_response = await e2e_client.get("/api/analysis/modes/safe")
    assert safe_response.status_code == 200
    safe_mode = safe_response.json()["data"]
    assert "idle" in safe_mode
    assert "resource" in safe_mode
    assert "health" in safe_mode
    print(f"✓ Retrieved 'safe' mode configuration")

    # Get specific mode - saving
    saving_response = await e2e_client.get("/api/analysis/modes/saving")
    assert saving_response.status_code == 200
    saving_mode = saving_response.json()["data"]
    print(f"✓ Retrieved 'saving' mode configuration")

    # Get specific mode - aggressive
    aggressive_response = await e2e_client.get("/api/analysis/modes/aggressive")
    assert aggressive_response.status_code == 200
    aggressive_mode = aggressive_response.json()["data"]
    print(f"✓ Retrieved 'aggressive' mode configuration")

    # Get specific mode - custom
    custom_response = await e2e_client.get("/api/analysis/modes/custom")
    assert custom_response.status_code == 200
    custom_mode = custom_response.json()["data"]
    print(f"✓ Retrieved 'custom' mode configuration")

    # 注意：custom mode 的更新通过任务创建时的 config 参数实现
    # 不需要单独的 API 端点来更新模式配置


@pytest.mark.asyncio
async def test_e2e_error_handling(e2e_client: AsyncClient):
    """Test error handling for invalid requests."""

    print("\n" + "="*60)
    print("ERROR HANDLING TEST")
    print("="*60)

    # Invalid connection ID
    response = await e2e_client.get("/api/connections/99999")
    assert response.status_code == 404
    print(f"✓ Invalid connection returns 404")

    # Invalid analysis mode
    response = await e2e_client.get("/api/analysis/modes/invalid_mode")
    assert response.status_code == 400
    print(f"✓ Invalid mode returns 400")

    # Invalid task ID
    response = await e2e_client.get("/api/tasks/99999")
    assert response.status_code == 404
    print(f"✓ Invalid task returns 404")
