"""Unit tests for RightSizeAnalyzer."""

import pytest
from datetime import datetime, timedelta

from app.analyzers.rightsize import RightSizeAnalyzer
from app.models import VMMetric


# 辅助函数：将百分比值转换为存储的绝对值
def cpu_storage_value(percentage: float, cpu_count: int, host_cpu_mhz: int = 2600) -> float:
    """计算 CPU 存储值：percentage / 100 * cpu_count * host_cpu_mhz"""
    return percentage / 100 * cpu_count * host_cpu_mhz


def memory_storage_value(percentage: float, memory_bytes: int) -> float:
    """计算内存存储值（MB）：percentage / 100 * memory_mb"""
    memory_mb = memory_bytes / (1024 * 1024)
    return percentage / 100 * memory_mb


@pytest.mark.asyncio
async def test_rightsize_downsize_recommendation():
    """测试缩容建议"""
    analyzer = RightSizeAnalyzer(
        cpu_buffer_percent=20.0,
        memory_buffer_percent=20.0,
        min_confidence=60.0,
    )

    # VM 配置
    cpu_count = 8
    memory_bytes = 16 * 1024**3
    host_cpu_mhz = 2600

    base_time = datetime.now()
    metrics = []

    # 创建低使用率指标 (P95 约 20%)
    for i in range(100):
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=cpu_storage_value(20.0, cpu_count, host_cpu_mhz),
                timestamp=base_time - timedelta(hours=i),
            )
        )
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="memory",
                value=memory_storage_value(20.0, memory_bytes),
                timestamp=base_time - timedelta(hours=i),
            )
        )

    vm_info = {
        "name": "test-vm",
        "cluster": "cluster1",
        "cpu_count": cpu_count,
        "memory_bytes": memory_bytes,
        "host_cpu_mhz": host_cpu_mhz,
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
    assert analyzer._normalize_memory(0.8) == 1
    assert analyzer._normalize_memory(1.5) == 2
    assert analyzer._normalize_memory(3) == 4
    assert analyzer._normalize_memory(6) == 8
    assert analyzer._normalize_memory(12) == 16
    assert analyzer._normalize_memory(40) == 64
    assert analyzer._normalize_memory(200) == 256  # 最大值


@pytest.mark.asyncio
async def test_rightsize_upsize_recommendation():
    """测试扩容建议"""
    analyzer = RightSizeAnalyzer(
        cpu_buffer_percent=20.0,
        memory_buffer_percent=20.0,
        min_confidence=60.0,
    )

    # VM 配置
    cpu_count = 2
    memory_bytes = 4 * 1024**3
    host_cpu_mhz = 2600

    base_time = datetime.now()
    metrics = []

    # 创建高使用率指标 (P95 约 95%)
    for i in range(100):
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=cpu_storage_value(95.0, cpu_count, host_cpu_mhz),
                timestamp=base_time - timedelta(hours=i),
            )
        )
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="memory",
                value=memory_storage_value(85.0, memory_bytes),
                timestamp=base_time - timedelta(hours=i),
            )
        )

    vm_info = {
        "name": "test-vm",
        "cluster": "cluster1",
        "cpu_count": cpu_count,
        "memory_bytes": memory_bytes,
        "host_cpu_mhz": host_cpu_mhz,
        "host_ip": "192.168.1.10",
    }

    result = await analyzer._analyze_vm(1, metrics, vm_info)

    # CPU 或 内存任一需要扩容即为 up
    assert "up" in result["adjustmentType"] or result["suggestedCpu"] > 2 or result["recommendedMemoryMb"] > 4 * 1024


@pytest.mark.asyncio
async def test_rightsize_no_change_needed():
    """测试：配置合理，无需调整"""
    analyzer = RightSizeAnalyzer(
        cpu_buffer_percent=20.0,
        memory_buffer_percent=20.0,
        min_confidence=60.0,
    )

    # VM 配置
    cpu_count = 4
    memory_bytes = 8 * 1024**3
    host_cpu_mhz = 2600

    base_time = datetime.now()
    metrics = []

    # 创建中等使用率指标 (P95 约 60%)
    for i in range(100):
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=cpu_storage_value(60.0, cpu_count, host_cpu_mhz),
                timestamp=base_time - timedelta(hours=i),
            )
        )
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="memory",
                value=memory_storage_value(55.0, memory_bytes),
                timestamp=base_time - timedelta(hours=i),
            )
        )

    vm_info = {
        "name": "test-vm",
        "cluster": "cluster1",
        "cpu_count": cpu_count,
        "memory_bytes": memory_bytes,
        "host_cpu_mhz": host_cpu_mhz,
        "host_ip": "192.168.1.10",
    }

    result = await analyzer._analyze_vm(1, metrics, vm_info)

    assert result["adjustmentType"] == "none"


@pytest.mark.asyncio
async def test_rightsize_risk_calculation():
    """测试风险等级计算"""
    analyzer = RightSizeAnalyzer()

    # 低风险：CV < 0.2 (stddev/current < 0.2)
    assert analyzer._calculate_risk(2, 16) == "low"  # CV = 2/16 = 0.125

    # 中风险：0.2 <= CV < 0.4
    assert analyzer._calculate_risk(5, 16) == "medium"  # CV = 5/16 = 0.3125

    # 高风险：CV >= 0.4
    assert analyzer._calculate_risk(8, 16) == "high"  # CV = 8/16 = 0.5


@pytest.mark.asyncio
async def test_rightsize_confidence_calculation():
    """测试置信度计算"""
    analyzer = RightSizeAnalyzer(days_threshold=14)

    # 高置信度：足够样本 (days_threshold * 288 = 4032 个预期样本)
    metrics = []
    base_time = datetime.now()
    for i in range(4000):  # 接近完整样本
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=cpu_storage_value(50.0, 4, 2600),
                timestamp=base_time - timedelta(minutes=i * 5),
            )
        )

    vm_info = {
        "name": "test-vm",
        "cluster": "cluster1",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
        "host_cpu_mhz": 2600,
        "host_ip": "192.168.1.10",
    }

    result = await analyzer._analyze_vm(1, metrics, vm_info)

    # 应该有高置信度
    assert result["confidence"] >= 80
