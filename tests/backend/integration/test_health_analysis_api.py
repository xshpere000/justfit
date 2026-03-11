"""Health Analysis API Integration Tests.

Tests the /api/analysis/tasks/{task_id}/health endpoint.
"""

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch

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
async def test_health_analysis_modes_api():
    """测试健康评估分析模式包含在模式 API 中"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        response = await client.get("/api/analysis/modes")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Check that health config exists in all modes (custom may be empty)
        for mode_name in ["safe", "saving", "aggressive"]:
            assert mode_name in data["data"]
            assert "health" in data["data"][mode_name]

            health_config = data["data"][mode_name]["health"]
            # Check config structure (camelCase for API responses)
            assert "overcommitThreshold" in health_config
            assert "hotspotThreshold" in health_config
            assert "balanceThreshold" in health_config

            # Verify thresholds are ratios, not percentages
            assert health_config["overcommitThreshold"] < 10  # Should be ~1.2-2.0
            assert health_config["hotspotThreshold"] < 20  # Should be ~5-10

        # Custom mode has empty health config by default
        assert "custom" in data["data"]
        assert "health" in data["data"]["custom"]
        # Custom health config may be empty dict


@pytest.mark.asyncio
async def test_health_analysis_with_mock_data():
    """测试健康评估分析端点（使用模拟数据）"""
    from sqlalchemy.ext.asyncio import AsyncSession

    async with AsyncClient(base_url="http://test", transport=transport) as client:
        # Mock the service method to avoid needing real database
        mock_result = {
            "success": True,
            "data": {
                "overallScore": 75.0,
                "grade": "good",
                "subScores": {
                    "overcommit": 80.0,
                    "balance": 70.0,
                    "hotspot": 75.0,
                },
                "clusterCount": 2,
                "hostCount": 8,
                "vmCount": 45,
                "overcommitResults": [
                    {
                        "clusterName": "cluster-1",
                        "physicalCpuCores": 20.0,
                        "physicalMemoryGb": 64.0,
                        "allocatedCpu": 30,
                        "allocatedMemoryGb": 80.0,
                        "cpuOvercommit": 1.5,
                        "memoryOvercommit": 1.25,
                        "cpuRisk": "critical",
                        "memoryRisk": "medium",
                    }
                ],
                "balanceResults": [
                    {
                        "clusterName": "cluster-1",
                        "hostCount": 4,
                        "vmCounts": [10, 12, 11, 10],
                        "meanVmCount": 10.75,
                        "stdDev": 0.83,
                        "coefficientOfVariation": 0.077,
                        "balanceLevel": "excellent",
                        "balanceScore": 100.0,
                    }
                ],
                "hotspotHosts": [
                    {
                        "hostName": "esxi-01",
                        "ipAddress": "192.168.1.10",
                        "vmCount": 20,
                        "cpuCores": 4,
                        "memoryGb": 64.0,
                        "vmDensity": 5.0,
                        "riskLevel": "high",
                        "recommendation": "esxi-01 主机负载较高（VM密度 5.0），建议关注并准备迁移",
                    }
                ],
                "overcommitScore": 80.0,
                "balanceScore": 100.0,
                "hotspotScore": 60.0,
                "avgVmDensity": 4.5,
                "findings": [
                    {
                        "severity": "critical",
                        "category": "overcommit",
                        "cluster": "cluster-1",
                        "description": "cluster-1 CPU超配比例 1.5，风险等级: critical",
                        "details": {
                            "cpuOvercommit": 1.5,
                            "memoryOvercommit": 1.25,
                        },
                    }
                ],
                "recommendations": [
                    "cluster-1 资源超配比例较高，建议评估是否需要扩容或迁移VM",
                ],
            },
        }

        with patch("app.services.analysis.AnalysisService.run_health_analysis", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result

            response = await client.post("/api/analysis/tasks/1/health")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data

            # Verify response structure
            health_data = data["data"]
            assert "overallScore" in health_data
            assert "grade" in health_data
            assert "subScores" in health_data
            assert "clusterCount" in health_data
            assert "hostCount" in health_data
            assert "vmCount" in health_data

            # Verify data types
            assert isinstance(health_data["overallScore"], (int, float))
            assert health_data["grade"] in ["excellent", "good", "fair", "poor", "critical", "no_data"]
            assert isinstance(health_data["clusterCount"], int)
            assert isinstance(health_data["hostCount"], int)
            assert isinstance(health_data["vmCount"], int)


@pytest.mark.asyncio
async def test_health_analysis_task_not_found():
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

        with patch("app.services.analysis.AnalysisService.run_health_analysis", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_error

            response = await client.post("/api/analysis/tasks/99999/health")

            # Should return 400 for error
            assert response.status_code == 400
            data = response.json()
            # FastAPI HTTPException wraps error in "detail"
            assert "detail" in data
            assert "code" in data["detail"]


@pytest.mark.asyncio
async def test_health_analysis_with_custom_config():
    """测试使用自定义配置运行健康评估"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        mock_result = {
            "success": True,
            "data": {
                "overallScore": 80.0,
                "grade": "good",
                "subScores": {"overcommit": 85.0, "balance": 75.0, "hotspot": 80.0},
                "clusterCount": 1,
                "hostCount": 4,
                "vmCount": 20,
                "overcommitResults": [],
                "balanceResults": [],
                "hotspotHosts": [],
                "overcommitScore": 85.0,
                "balanceScore": 75.0,
                "hotspotScore": 80.0,
                "avgVmDensity": 3.0,
                "findings": [],
                "recommendations": [],
            },
        }

        with patch("app.services.analysis.AnalysisService.run_health_analysis", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result

            # Request with custom config
            custom_config = {
                "mode": "custom",
                "config": {
                    "overcommit_threshold": 1.3,
                    "hotspot_threshold": 6.0,
                    "balance_threshold": 0.5,
                },
            }

            response = await client.post(
                "/api/analysis/tasks/1/health",
                json=custom_config
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Verify the service was called
            assert mock_analyze.called


@pytest.mark.asyncio
async def test_get_health_results():
    """测试获取健康评估结果"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        mock_result = {
            "success": True,
            "data": {
                "overallScore": 70.0,
                "grade": "good",
                "subScores": {"overcommit": 75.0, "balance": 65.0, "hotspot": 70.0},
                "clusterCount": 2,
                "hostCount": 6,
                "vmCount": 30,
                "findings": [],
                "recommendations": [],
            },
        }

        with patch("app.services.analysis.AnalysisService.get_analysis_results", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_result

            response = await client.get("/api/analysis/tasks/1/health")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data


@pytest.mark.asyncio
async def test_health_analysis_response_schema_validation():
    """测试健康评估响应符合 schema 定义"""
    from app.schemas.health import PlatformHealthResult

    async with AsyncClient(base_url="http://test", transport=transport) as client:
        mock_result = {
            "success": True,
            "data": {
                "overallScore": 85.0,
                "grade": "good",
                "subScores": {
                    "overcommit": 90.0,
                    "balance": 80.0,
                    "hotspot": 85.0,
                },
                "clusterCount": 3,
                "hostCount": 12,
                "vmCount": 60,
                "overcommitResults": [],
                "balanceResults": [],
                "hotspotHosts": [],
                "overcommitScore": 90.0,
                "balanceScore": 80.0,
                "hotspotScore": 85.0,
                "avgVmDensity": 4.0,
                "findings": [],
                "recommendations": [],
            },
        }

        with patch("app.services.analysis.AnalysisService.run_health_analysis", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result

            response = await client.post("/api/analysis/tasks/1/health")

            assert response.status_code == 200

            # Try to parse response with schema
            data = response.json()["data"]
            health_result = PlatformHealthResult(**data)

            # Verify schema parsing
            assert health_result.overall_score == 85.0
            assert health_result.grade == "good"
            assert health_result.cluster_count == 3
            assert health_result.host_count == 12
            assert health_result.vm_count == 60


@pytest.mark.asyncio
async def test_health_analysis_empty_data():
    """测试无数据时的健康评估响应"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        mock_result = {
            "success": True,
            "data": {
                "overallScore": 0.0,
                "grade": "no_data",
                "subScores": {
                    "overcommit": 0.0,
                    "balance": 0.0,
                    "hotspot": 0.0,
                },
                "clusterCount": 0,
                "hostCount": 0,
                "vmCount": 0,
                "overcommitResults": [],
                "balanceResults": [],
                "hotspotHosts": [],
                "overcommitScore": 0.0,
                "balanceScore": 0.0,
                "hotspotScore": 0.0,
                "avgVmDensity": 0.0,
                "findings": [],
                "recommendations": [],
            },
        }

        with patch("app.services.analysis.AnalysisService.run_health_analysis", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result

            response = await client.post("/api/analysis/tasks/1/health")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            health_data = data["data"]
            assert health_data["grade"] == "no_data"
            assert health_data["clusterCount"] == 0


@pytest.mark.asyncio
async def test_health_analysis_grade_boundaries():
    """测试健康等级边界条件"""
    from app.schemas.health import PlatformHealthResult

    test_cases = [
        (90.0, "excellent"),
        (75.0, "good"),
        (60.0, "fair"),
        (40.0, "poor"),
        (20.0, "critical"),
    ]

    async with AsyncClient(base_url="http://test", transport=transport) as client:
        for score, expected_grade in test_cases:
            mock_result = {
                "success": True,
                "data": {
                    "overallScore": score,
                    "grade": expected_grade,
                    "subScores": {"overcommit": score, "balance": score, "hotspot": score},
                    "clusterCount": 1,
                    "hostCount": 4,
                    "vmCount": 10,
                    "overcommitResults": [],
                    "balanceResults": [],
                    "hotspotHosts": [],
                    "overcommitScore": score,
                    "balanceScore": score,
                    "hotspotScore": score,
                    "avgVmDensity": 3.0,
                    "findings": [],
                    "recommendations": [],
                },
            }

            with patch("app.services.analysis.AnalysisService.run_health_analysis", new_callable=AsyncMock) as mock_analyze:
                mock_analyze.return_value = mock_result

                response = await client.post("/api/analysis/tasks/1/health")

                assert response.status_code == 200
                data = response.json()
                assert data["data"]["grade"] == expected_grade
