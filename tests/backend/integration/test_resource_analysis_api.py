"""Resource Analysis API Integration Tests.

Tests the /api/analysis/tasks/{task_id}/resource endpoint.
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
async def test_resource_analysis_with_mock_data():
    """测试资源分析端点（使用模拟数据）"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        mock_result = {
            "success": True,
            "data": {
                "rightSize": [
                    {
                        "vmName": "test-vm-1",
                        "datacenter": "dc1",
                        "cluster": "cluster1",
                        "hostIp": "192.168.1.10",
                        "currentCpu": 8,
                        "suggestedCpu": 2,
                        "currentMemory": 16,
                        "suggestedMemory": 4,
                        "cpuP95": 20.0,
                        "cpuMax": 25.0,
                        "cpuAvg": 18.0,
                        "memoryP95": 15.0,
                        "memoryMax": 20.0,
                        "memoryAvg": 14.0,
                        "adjustmentType": "down",
                        "riskLevel": "low",
                        "confidence": 80.0,
                        "recommendation": "建议缩容至 2 vCPU / 4GB RAM",
                    }
                ],
                "usagePattern": [
                    {
                        "vmName": "test-vm-2",
                        "datacenter": "dc1",
                        "cluster": "cluster1",
                        "hostIp": "192.168.1.11",
                        "optimizationType": "usage_pattern",
                        "usagePattern": "tidal",
                        "volatilityLevel": "high",
                        "coefficientOfVariation": 0.65,
                        "peakValleyRatio": 5.2,
                        "tidalDetails": {
                            "patternType": "day_active",
                            "dayAvg": 45.2,
                            "nightAvg": 8.5,
                        },
                        "recommendation": "VM呈现潮汐使用模式，建议配置自动调度策略",
                    }
                ],
                "mismatch": [
                    {
                        "vmName": "test-vm-3",
                        "datacenter": "dc1",
                        "cluster": "cluster1",
                        "hostIp": "192.168.1.12",
                        "hasMismatch": True,
                        "mismatchType": "cpu_rich_memory_poor",
                        "cpuUtilization": 15.2,
                        "memoryUtilization": 78.5,
                        "currentCpu": 8,
                        "currentMemory": 16,
                        "recommendation": "内存使用率较高但CPU使用率低，可能存在内存瓶颈，建议增加内存或降低CPU",
                    }
                ],
                "summary": {
                    "rightSizeCount": 1,
                    "usagePatternCount": 1,
                    "mismatchCount": 1,
                    "totalVmsAnalyzed": 3,
                },
            },
        }

        with patch("app.services.analysis.AnalysisService.run_resource_analysis", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result

            response = await client.post("/api/analysis/tasks/1/resource")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data

            # Verify response structure
            resource_data = data["data"]
            assert "rightSize" in resource_data
            assert "usagePattern" in resource_data
            assert "mismatch" in resource_data
            assert "summary" in resource_data

            # Verify summary
            summary = resource_data["summary"]
            assert summary["rightSizeCount"] == 1
            assert summary["usagePatternCount"] == 1
            assert summary["mismatchCount"] == 1
            assert summary["totalVmsAnalyzed"] == 3


@pytest.mark.asyncio
async def test_resource_analysis_task_not_found():
    """测试任务不存在时返回错误"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        mock_error = {
            "success": False,
            "error": {
                "code": "TASK_NOT_FOUND",
                "message": "Task not found",
            },
        }

        with patch("app.services.analysis.AnalysisService.run_resource_analysis", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_error

            response = await client.post("/api/analysis/tasks/99999/resource")

            # Should return 400 for error
            assert response.status_code == 400
            data = response.json()
            # FastAPI wraps HTTPException detail in a 'detail' key
            assert "detail" in data
            assert "code" in data["detail"]


@pytest.mark.asyncio
async def test_resource_analysis_with_mode():
    """测试使用指定模式运行资源分析"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        mock_result = {
            "success": True,
            "data": {
                "rightSize": [],
                "usagePattern": [],
                "mismatch": [],
                "summary": {
                    "rightSizeCount": 0,
                    "usagePatternCount": 0,
                    "mismatchCount": 0,
                    "totalVmsAnalyzed": 0,
                },
            },
        }

        with patch("app.services.analysis.AnalysisService.run_resource_analysis", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result

            # Request with mode
            response = await client.post(
                "/api/analysis/tasks/1/resource",
                json={"mode": "aggressive"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Verify the service was called
            assert mock_analyze.called


@pytest.mark.asyncio
async def test_resource_analysis_no_metrics():
    """测试无指标数据时的响应"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        mock_result = {
            "success": True,
            "data": {
                "rightSize": [],
                "usagePattern": [],
                "mismatch": [],
                "summary": {
                    "rightSizeCount": 0,
                    "usagePatternCount": 0,
                    "mismatchCount": 0,
                    "totalVmsAnalyzed": 0,
                },
            },
        }

        with patch("app.services.analysis.AnalysisService.run_resource_analysis", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result

            response = await client.post("/api/analysis/tasks/1/resource")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            resource_data = data["data"]
            assert resource_data["rightSize"] == []
            assert resource_data["usagePattern"] == []
            assert resource_data["mismatch"] == []


@pytest.mark.asyncio
async def test_get_resource_results():
    """测试获取资源分析结果"""
    async with AsyncClient(base_url="http://test", transport=transport) as client:
        mock_result = {
            "success": True,
            "data": {
                "rightSize": [
                    {
                        "vmName": "test-vm",
                        "currentCpu": 4,
                        "suggestedCpu": 2,
                    }
                ],
                "usagePattern": [],
                "mismatch": [],
                "summary": {
                    "rightSizeCount": 1,
                    "usagePatternCount": 0,
                    "mismatchCount": 0,
                    "totalVmsAnalyzed": 1,
                },
            },
        }

        with patch("app.services.analysis.AnalysisService.get_analysis_results", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_result

            response = await client.get("/api/analysis/tasks/1/resource")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data


@pytest.mark.asyncio
async def test_resource_analysis_response_schema_validation():
    """测试资源分析响应符合 schema 定义"""
    from app.schemas.analysis import ResourceAnalysisResult

    async with AsyncClient(base_url="http://test", transport=transport) as client:
        mock_result = {
            "success": True,
            "data": {
                "rightSize": [],
                "usagePattern": [],
                "mismatch": [],
                "summary": {
                    "rightSizeCount": 0,
                    "usagePatternCount": 0,
                    "mismatchCount": 0,
                    "totalVmsAnalyzed": 0,
                },
            },
        }

        with patch("app.services.analysis.AnalysisService.run_resource_analysis", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result

            response = await client.post("/api/analysis/tasks/1/resource")

            assert response.status_code == 200

            # Try to parse response with schema
            data = response.json()["data"]
            resource_result = ResourceAnalysisResult(**data)

            # Verify schema parsing
            assert resource_result.right_size == []
            assert resource_result.usage_pattern == []
            assert resource_result.mismatch == []
            assert resource_result.summary.right_size_count == 0
            assert resource_result.summary.usage_pattern_count == 0
            assert resource_result.summary.mismatch_count == 0


@pytest.mark.asyncio
async def test_resource_analysis_usage_pattern_types():
    """测试不同使用模式类型的响应"""
    from app.schemas.analysis import UsagePatternResult

    test_patterns = [
        ("stable", "low", 0.15, 1.2),
        ("burst", "moderate", 0.4, 2.5),
        ("tidal", "high", 0.65, 5.0),
    ]

    async with AsyncClient(base_url="http://test", transport=transport) as client:
        for pattern, volatility, cv, peak_valley in test_patterns:
            mock_result = {
                "success": True,
                "data": {
                    "rightSize": [],
                    "usagePattern": [
                        {
                            "vmName": f"test-vm-{pattern}",
                            "datacenter": "dc1",
                            "cluster": "cluster1",
                            "hostIp": "192.168.1.10",
                            "optimizationType": "usage_pattern",
                            "usagePattern": pattern,
                            "volatilityLevel": volatility,
                            "coefficientOfVariation": cv,
                            "peakValleyRatio": peak_valley,
                            "recommendation": f"VM使用模式为 {pattern}",
                        }
                    ],
                    "mismatch": [],
                    "summary": {
                        "rightSizeCount": 0,
                        "usagePatternCount": 1,
                        "mismatchCount": 0,
                        "totalVmsAnalyzed": 1,
                    },
                },
            }

            with patch("app.services.analysis.AnalysisService.run_resource_analysis", new_callable=AsyncMock) as mock_analyze:
                mock_analyze.return_value = mock_result

                response = await client.post("/api/analysis/tasks/1/resource")

                assert response.status_code == 200
                data = response.json()
                usage_pattern_data = data["data"]["usagePattern"][0]
                assert usage_pattern_data["usagePattern"] == pattern

                # Verify schema parsing
                pattern_result = UsagePatternResult(**usage_pattern_data)
                assert pattern_result.usage_pattern == pattern


@pytest.mark.asyncio
async def test_resource_analysis_mismatch_types():
    """测试不同错配类型的响应"""
    from app.schemas.analysis import MismatchResult

    test_mismatches = [
        ("cpu_rich_memory_poor", 15.0, 80.0),
        ("cpu_poor_memory_rich", 85.0, 15.0),
        ("both_underutilized", 15.0, 20.0),
        ("both_overutilized", 85.0, 80.0),
    ]

    async with AsyncClient(base_url="http://test", transport=transport) as client:
        for mismatch_type, cpu_util, mem_util in test_mismatches:
            mock_result = {
                "success": True,
                "data": {
                    "rightSize": [],
                    "usagePattern": [],
                    "mismatch": [
                        {
                            "vmName": f"test-vm-{mismatch_type}",
                            "datacenter": "dc1",
                            "cluster": "cluster1",
                            "hostIp": "192.168.1.10",
                            "hasMismatch": True,
                            "mismatchType": mismatch_type,
                            "cpuUtilization": cpu_util,
                            "memoryUtilization": mem_util,
                            "currentCpu": 4,
                            "currentMemory": 8,
                            "recommendation": f"配置错配: {mismatch_type}",
                        }
                    ],
                    "summary": {
                        "rightSizeCount": 0,
                        "usagePatternCount": 0,
                        "mismatchCount": 1,
                        "totalVmsAnalyzed": 1,
                    },
                },
            }

            with patch("app.services.analysis.AnalysisService.run_resource_analysis", new_callable=AsyncMock) as mock_analyze:
                mock_analyze.return_value = mock_result

                response = await client.post("/api/analysis/tasks/1/resource")

                assert response.status_code == 200
                data = response.json()
                mismatch_data = data["data"]["mismatch"][0]
                assert mismatch_data["mismatchType"] == mismatch_type

                # Verify schema parsing
                mismatch_result = MismatchResult(**mismatch_data)
                assert mismatch_result.mismatch_type == mismatch_type
