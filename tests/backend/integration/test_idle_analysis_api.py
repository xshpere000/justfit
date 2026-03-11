"""Idle Detection Analysis API Integration Tests.

Tests the /api/analysis/tasks/{task_id}/idle endpoint.
"""

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

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
async def test_idle_analysis_modes_api():
    """测试闲置检测分析模式包含在模式 API 中"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        response = await client.get("/api/analysis/modes")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Check that idle config exists in all modes
        for mode_name in ["safe", "saving", "aggressive"]:
            assert mode_name in data["data"]
            # idle config should exist (may be empty dict if not defined)
            assert "idle" in data["data"][mode_name]

            idle_config = data["data"][mode_name]["idle"]
            # Check config structure (camelCase for API responses)
            assert "days" in idle_config
            assert "cpuThreshold" in idle_config
            assert "memoryThreshold" in idle_config
            assert "minConfidence" in idle_config


@pytest.mark.asyncio
async def test_idle_analysis_with_mock_data():
    """测试闲置检测分析端点（使用模拟数据）"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        # Mock the service method to avoid needing real database
        mock_result = {
            "success": True,
            "data": [
                {
                    "vmName": "test-zombie-vm",
                    "vmId": 1,
                    "cluster": "cluster1",
                    "hostIp": "192.168.1.10",
                    "isIdle": True,
                    "idleType": "powered_off",
                    "confidence": 95,
                    "riskLevel": "critical",
                    "daysInactive": 100,
                    "lastActivityTime": "2024-01-01T00:00:00Z",
                    "downtimeDuration": 8640000,
                    "recommendation": "VM已关机100天，建议归档或删除",
                    "details": {"powerState": "poweredOff"},
                },
                {
                    "vmName": "idle-powered-on-vm",
                    "vmId": 2,
                    "cluster": "cluster1",
                    "hostIp": "192.168.1.11",
                    "cpuCores": 4,
                    "memoryGb": 8.0,
                    "uptimeDuration": 2592000,
                    "isIdle": True,
                    "idleType": "idle_powered_on",
                    "confidence": 85,
                    "riskLevel": "high",
                    "activityScore": 8,
                    "cpuUsageP95": 3.2,
                    "memoryUsageP95": 8.5,
                    "diskIoP95": 1.2,
                    "networkP95": 0.5,
                    "dataQuality": "high",
                    "recommendation": "VM完全闲置（P95 CPU 3.2%，内存 8.5%），建议关闭或降配",
                    "details": {"powerState": "poweredOn"},
                },
            ],
        }

        with patch("app.services.analysis.AnalysisService.run_idle_analysis", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result

            response = await client.post("/api/analysis/tasks/1/idle")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data

            # Verify response structure
            idle_data = data["data"]
            assert isinstance(idle_data, list)
            assert len(idle_data) == 2

            # Verify first idle VM (powered off)
            first_vm = idle_data[0]
            assert first_vm["vmName"] == "test-zombie-vm"
            assert first_vm["idleType"] == "powered_off"
            assert first_vm["confidence"] == 95
            assert first_vm["riskLevel"] == "critical"
            assert first_vm["daysInactive"] == 100

            # Verify second idle VM (powered on but idle)
            second_vm = idle_data[1]
            assert second_vm["vmName"] == "idle-powered-on-vm"
            assert second_vm["idleType"] == "idle_powered_on"
            assert second_vm["confidence"] == 85
            assert second_vm["activityScore"] == 8
            assert second_vm["cpuUsageP95"] == 3.2


@pytest.mark.asyncio
async def test_idle_analysis_task_not_found():
    """测试任务不存在时返回错误"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        # Mock service to return task not found error
        mock_error = {
            "success": False,
            "error": {
                "code": "TASK_NOT_FOUND",
                "message": "Task not found",
            },
        }

        with patch("app.services.analysis.AnalysisService.run_idle_analysis", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_error

            response = await client.post("/api/analysis/tasks/99999/idle")

            # Should return 400 for error
            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
            assert "code" in data["detail"]


@pytest.mark.asyncio
async def test_idle_analysis_with_custom_config():
    """测试使用自定义配置运行闲置检测"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        mock_result = {
            "success": True,
            "data": [
                {
                    "vmName": "custom-idle-vm",
                    "vmId": 1,
                    "cluster": "cluster1",
                    "hostIp": "192.168.1.10",
                    "isIdle": True,
                    "idleType": "idle_powered_on",
                    "confidence": 75,
                    "riskLevel": "high",
                    "activityScore": 12,
                    "cpuUsageP95": 5.0,
                    "memoryUsageP95": 10.0,
                    "recommendation": "VM低活跃，建议观察或降配",
                    "details": {},
                },
            ],
        }

        with patch("app.services.analysis.AnalysisService.run_idle_analysis", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result

            # Request with custom config
            custom_config = {
                "mode": "custom",
                "config": {
                    "days": 30,
                    "cpu_threshold": 5.0,
                    "memory_threshold": 10.0,
                    "min_confidence": 70.0,
                },
            }

            response = await client.post(
                "/api/analysis/tasks/1/idle",
                json=custom_config
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Verify the service was called
            assert mock_analyze.called


@pytest.mark.asyncio
async def test_idle_analysis_empty_results():
    """测试无闲置VM时的响应"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        mock_result = {
            "success": True,
            "data": [],
        }

        with patch("app.services.analysis.AnalysisService.run_idle_analysis", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result

            response = await client.post("/api/analysis/tasks/1/idle")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"] == []


@pytest.mark.asyncio
async def test_get_idle_results():
    """测试获取闲置检测结果"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        mock_result = {
            "success": True,
            "data": [
                {
                    "vmName": "stored-idle-vm",
                    "vmId": 1,
                    "cluster": "cluster1",
                    "hostIp": "192.168.1.10",
                    "isIdle": True,
                    "idleType": "powered_off",
                    "confidence": 85,
                    "riskLevel": "high",
                    "daysInactive": 50,
                    "recommendation": "VM已关机50天，建议联系负责人确认后处理",
                    "details": {},
                },
            ],
        }

        with patch("app.services.analysis.AnalysisService.get_analysis_results", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_result

            response = await client.get("/api/analysis/tasks/1/idle")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert len(data["data"]) == 1


@pytest.mark.asyncio
async def test_idle_analysis_response_schema_validation():
    """测试闲置检测响应符合 schema 定义"""
    from app.schemas.idle import IdleDetectionResult

    async with AsyncClient(base_url="http://test", transport=transport) as client:
        mock_result = {
            "success": True,
            "data": [
                {
                    "vmName": "schema-test-vm",
                    "vmId": 1,
                    "cluster": "cluster1",
                    "hostIp": "192.168.1.10",
                    "isIdle": True,
                    "idleType": "low_activity",
                    "confidence": 70,
                    "riskLevel": "medium",
                    "activityScore": 25,
                    "cpuUsageP95": 15.0,
                    "memoryUsageP95": 20.0,
                    "dataQuality": "medium",
                    "recommendation": "VM低活跃，建议观察或降配",
                    "details": {},
                },
            ],
        }

        with patch("app.services.analysis.AnalysisService.run_idle_analysis", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result

            response = await client.post("/api/analysis/tasks/1/idle")

            assert response.status_code == 200

            # Try to parse response with schema
            data = response.json()["data"]
            idle_result = IdleDetectionResult(**data[0])

            # Verify schema parsing
            assert idle_result.vm_name == "schema-test-vm"
            assert idle_result.idle_type == "low_activity"
            assert idle_result.confidence == 70
            assert idle_result.risk_level == "medium"


@pytest.mark.asyncio
async def test_idle_analysis_all_types():
    """测试所有闲置类型"""
    from app.schemas.idle import IdleDetectionResult
    from app.analyzers.idle_detector import IdleSubType

    async with AsyncClient(base_url="http://test", transport=transport) as client:
        # Test all three idle types
        test_cases = [
            ("powered_off", 95, "critical", 100, None),
            ("idle_powered_on", 85, "high", 8, 3.2),
            ("low_activity", 70, "medium", 25, 15.0),
        ]

        for idle_type, confidence, risk_level, activity_score, cpu_p95 in test_cases:
            mock_data = {
                "vmName": f"{idle_type}-vm",
                "vmId": 1,
                "cluster": "cluster1",
                "hostIp": "192.168.1.10",
                "isIdle": True,
                "idleType": idle_type,
                "confidence": confidence,
                "riskLevel": risk_level,
                "recommendation": "Test recommendation",
                "details": {},
            }

            # Add type-specific fields
            if idle_type == IdleSubType.POWERED_OFF.value:
                mock_data["daysInactive"] = 100
                mock_data["downtimeDuration"] = 8640000
            else:
                mock_data["cpuCores"] = 4
                mock_data["memoryGb"] = 8.0
                mock_data["activityScore"] = activity_score
                mock_data["cpuUsageP95"] = cpu_p95
                mock_data["memoryUsageP95"] = 20.0
                mock_data["diskIoP95"] = 5.0
                mock_data["networkP95"] = 5.0
                mock_data["dataQuality"] = "high"

            mock_result = {"success": True, "data": [mock_data]}

            with patch("app.services.analysis.AnalysisService.run_idle_analysis", new_callable=AsyncMock) as mock_analyze:
                mock_analyze.return_value = mock_result

                response = await client.post("/api/analysis/tasks/1/idle")

                assert response.status_code == 200
                data = response.json()["data"][0]
                assert data["idleType"] == idle_type
                assert data["confidence"] == confidence

                # Verify schema validation
                idle_result = IdleDetectionResult(**data)
                assert idle_result.idle_type == idle_type


@pytest.mark.asyncio
async def test_idle_analysis_with_mode():
    """测试使用预设模式运行闲置检测"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        mock_result = {
            "success": True,
            "data": [
                {
                    "vmName": "mode-test-vm",
                    "vmId": 1,
                    "cluster": "cluster1",
                    "hostIp": "192.168.1.10",
                    "isIdle": True,
                    "idleType": "powered_off",
                    "confidence": 70,
                    "riskLevel": "medium",
                    "daysInactive": 20,
                    "recommendation": "VM已关机20天，建议确认是否仍需要",
                    "details": {},
                },
            ],
        }

        with patch("app.services.analysis.AnalysisService.run_idle_analysis", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result

            # Test with "safe" mode
            response = await client.post(
                "/api/analysis/tasks/1/idle",
                json={"mode": "safe"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Verify the service was called
            assert mock_analyze.called
