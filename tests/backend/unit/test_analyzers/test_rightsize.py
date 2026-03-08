"""Unit tests for RightSizeAnalyzer."""

import pytest
from datetime import datetime, timedelta

from app.analyzers.rightsize import RightSizeAnalyzer
from app.models import VMMetric


@pytest.mark.asyncio
async def test_rightsize_downsize_recommendation():
    """测试缩容建议"""
    analyzer = RightSizeAnalyzer(
        cpu_buffer_percent=20.0,
        memory_buffer_percent=20.0,
        min_confidence=60.0,
    )

    base_time = datetime.now()
    metrics = []

    # 创建低使用率指标 (P95 约 20%)
    for i in range(100):
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=20.0,
                timestamp=base_time - timedelta(hours=i),
            )
        )
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="memory",
                value=20.0,  # 20% of 16GB = 3.2GB
                timestamp=base_time - timedelta(hours=i),
            )
        )

    vm_info = {
        "name": "test-vm",
        "cluster": "cluster1",
        "cpu_count": 8,  # 8核
        "memory_bytes": 16 * 1024**3,  # 16GB (原始数据)
        "memory_gb": 16,  # 16GB (分析器需要)
        "host_ip": "192.168.1.10",
    }

    result = await analyzer._analyze_vm(1, metrics, vm_info)

    assert result["vmName"] == "test-vm"
    assert result["currentCpu"] == 8
    assert result["suggestedCpu"] <= 4  # 应建议缩容
    assert "down" in result["adjustmentType"]  # down 或 down_significant


@pytest.mark.asyncio
async def test_rightsize_cpu_standard_configs():
    """测试 CPU 标准化配置"""
    analyzer = RightSizeAnalyzer()

    # CPU 标准配置: [1, 2, 4, 8, 12, 16, 24, 32, 48, 64]
    assert analyzer._normalize_cpu(0.5) == 1
    assert analyzer._normalize_cpu(1.0) == 1
    assert analyzer._normalize_cpu(1.5) == 2
    assert analyzer._normalize_cpu(3) == 4
    assert analyzer._normalize_cpu(6) == 8
    assert analyzer._normalize_cpu(10) == 12
    assert analyzer._normalize_cpu(20) == 24
    assert analyzer._normalize_cpu(60) == 64
    assert analyzer._normalize_cpu(100) == 64  # 最大值


@pytest.mark.asyncio
async def test_rightsize_memory_standard_configs():
    """测试内存标准化配置"""
    analyzer = RightSizeAnalyzer()

    # 内存标准配置: [0.5, 1, 2, 4, 8, 16, 32, 64, 128, 256] GB
    assert analyzer._normalize_memory(0.3) == 0.5
    assert analyzer._normalize_memory(0.5) == 0.5
    assert analyzer._normalize_memory(1.5) == 2
    assert analyzer._normalize_memory(3) == 4
    assert analyzer._normalize_memory(6) == 8
    assert analyzer._normalize_memory(12) == 16
    assert analyzer._normalize_memory(48) == 64
    assert analyzer._normalize_memory(200) == 256


@pytest.mark.asyncio
async def test_rightsize_percentile_calculation():
    """测试百分位数计算"""
    analyzer = RightSizeAnalyzer()

    values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

    p95 = analyzer._percentile(values, 95)
    # index = int(10 * 95 / 100) = 9, sorted_values[9] = 100
    assert p95 == 100

    p50 = analyzer._percentile(values, 50)
    # index = int(10 * 50 / 100) = 5, sorted_values[5] = 60
    assert p50 == 60


@pytest.mark.asyncio
async def test_rightsize_risk_assessment():
    """测试风险评估"""
    analyzer = RightSizeAnalyzer()

    # 低变异 - 低风险
    low_stddev = 1.0
    assert analyzer._calculate_risk(low_stddev, 8) == "low"

    # 中等变异 - 中风险
    med_stddev = 2.0
    assert analyzer._calculate_risk(med_stddev, 8) == "medium"

    # 高变异 - 高风险
    high_stddev = 4.0
    assert analyzer._calculate_risk(high_stddev, 8) == "high"


@pytest.mark.asyncio
async def test_rightsize_upsize_recommendation():
    """测试扩容建议"""
    analyzer = RightSizeAnalyzer(
        cpu_buffer_percent=20.0,
        min_confidence=60.0,
    )

    base_time = datetime.now()
    metrics = []

    # 创建高使用率指标 (CPU 和内存都高)
    for i in range(100):
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=95.0,  # CPU 95%
                timestamp=base_time - timedelta(hours=i),
            )
        )
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="memory",
                value=85.0,  # Memory 85%
                timestamp=base_time - timedelta(hours=i),
            )
        )

    vm_info = {
        "name": "test-vm",
        "cluster": "cluster1",
        "cpu_count": 2,  # 2核但使用率95%
        "memory_bytes": 4 * 1024**3,
        "memory_gb": 4,  # 4GB 但使用率85%
        "host_ip": "192.168.1.10",
    }

    result = await analyzer._analyze_vm(1, metrics, vm_info)

    # CPU 或 内存任一需要扩容即为 up
    assert "up" in result["adjustmentType"] or result["suggestedCpu"] > 2 or result["suggestedMemory"] > 4
