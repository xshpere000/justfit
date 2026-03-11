"""Unit tests for ResourceAnalyzer."""

import pytest
from datetime import datetime, timedelta

from app.analyzers.resource_analyzer import (
    ResourceAnalyzer,
    UsagePatternAnalyzer,
    MismatchDetector,
)
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
async def test_usage_pattern_stable():
    """测试稳定使用模式识别"""
    analyzer = UsagePatternAnalyzer()

    base_time = datetime.now()
    metrics = []

    # 创建稳定的CPU使用率指标 (45%左右，变异系数 < 0.3)
    for i in range(50):
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=45.0 + (i % 5 - 2),  # 43-47 之间波动
                timestamp=base_time - timedelta(minutes=i * 5),
            )
        )

    vm_info = {
        "name": "stable-vm",
        "cluster": "cluster1",
        "host_ip": "192.168.1.10",
    }

    result = await analyzer._analyze_vm(1, metrics, vm_info)

    assert result["usagePattern"] == "stable"
    assert result["volatilityLevel"] == "low"
    assert result["coefficientOfVariation"] < 0.3
    assert "稳定" in result["recommendation"]


@pytest.mark.asyncio
async def test_usage_pattern_burst():
    """测试突发使用模式识别"""
    analyzer = UsagePatternAnalyzer()

    base_time = datetime.now()
    metrics = []

    # 创建突发使用模式 (高变异系数 0.3-0.5)
    for i in range(50):
        value = 30.0 + (i % 10) * 10  # 30-120 之间大幅波动
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=value,
                timestamp=base_time - timedelta(minutes=i * 5),
            )
        )

    vm_info = {
        "name": "burst-vm",
        "cluster": "cluster1",
        "host_ip": "192.168.1.10",
    }

    result = await analyzer._analyze_vm(1, metrics, vm_info)

    assert result["usagePattern"] == "burst"
    assert result["volatilityLevel"] == "moderate"
    assert result["coefficientOfVariation"] >= 0.3


@pytest.mark.asyncio
async def test_usage_pattern_tidal():
    """测试潮汐使用模式识别"""
    analyzer = UsagePatternAnalyzer()

    base_time = datetime.now()
    metrics = []

    # 创建潮汐模式 (白天高，夜间低)
    for i in range(100):
        hour = (base_time - timedelta(hours=i)).hour
        # 白天 (9-18点) 高使用率，夜间低使用率
        if 9 <= hour <= 18:
            value = 60.0 + (i % 20)
        else:
            value = 5.0 + (i % 5)
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=value,
                timestamp=base_time - timedelta(hours=i),
            )
        )

    vm_info = {
        "name": "tidal-vm",
        "cluster": "cluster1",
        "host_ip": "192.168.1.10",
    }

    result = await analyzer._analyze_vm(1, metrics, vm_info)

    assert result["usagePattern"] == "tidal"
    assert result["volatilityLevel"] == "high"
    assert result["coefficientOfVariation"] > 0.5
    assert result["peakValleyRatio"] > 3.0
    assert result["tidalDetails"] is not None


@pytest.mark.asyncio
async def test_usage_pattern_insufficient_data():
    """测试数据不足的情况"""
    analyzer = UsagePatternAnalyzer(min_samples=24)

    base_time = datetime.now()
    metrics = []

    # 只创建10个样本（少于最小要求的24个）
    for i in range(10):
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=45.0,
                timestamp=base_time - timedelta(minutes=i * 5),
            )
        )

    vm_info = {
        "name": "test-vm",
        "cluster": "cluster1",
        "host_ip": "192.168.1.10",
    }

    result = await analyzer._analyze_vm(1, metrics, vm_info)

    assert result["usagePattern"] == "unknown"
    assert result["volatilityLevel"] == "unknown"
    assert "数据不足" in result["recommendation"]


@pytest.mark.asyncio
async def test_usage_pattern_tidal_details_day_active():
    """测试潮汐模式详细分析 - 白天活跃"""
    analyzer = UsagePatternAnalyzer()

    base_time = datetime.now()
    metrics = []

    # 创建白天活跃模式
    for i in range(288):  # 24小时，每5分钟一个样本
        hour = (base_time - timedelta(minutes=i * 5)).hour
        if 9 <= hour <= 18:
            value = 60.0
        else:
            value = 10.0
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=value,
                timestamp=base_time - timedelta(minutes=i * 5),
            )
        )

    tidal_details = analyzer._analyze_tidal_details(metrics)

    assert tidal_details["patternType"] == "day_active"
    assert tidal_details["dayAvg"] > tidal_details["nightAvg"] * 2


@pytest.mark.asyncio
async def test_mismatch_detector_cpu_rich_memory_poor():
    """测试 CPU富裕内存紧张检测"""
    detector = MismatchDetector()

    # VM 配置
    cpu_count = 8
    memory_bytes = 16 * 1024**3
    host_cpu_mhz = 2600

    base_time = datetime.now()
    metrics = []

    for i in range(50):
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=cpu_storage_value(20.0, cpu_count, host_cpu_mhz),  # CPU 低使用率
                timestamp=base_time - timedelta(minutes=i * 5),
            )
        )
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="memory",
                value=memory_storage_value(80.0, memory_bytes),  # 内存高使用率
                timestamp=base_time - timedelta(minutes=i * 5),
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

    result = await detector._analyze_vm(1, metrics, vm_info)

    assert result["hasMismatch"] is True
    assert result["mismatchType"] == "cpu_rich_memory_poor"
    assert "内存" in result["recommendation"]


@pytest.mark.asyncio
async def test_mismatch_detector_cpu_poor_memory_rich():
    """测试 CPU紧张内存富裕检测"""
    detector = MismatchDetector()

    # VM 配置
    cpu_count = 4
    memory_bytes = 32 * 1024**3
    host_cpu_mhz = 2600

    base_time = datetime.now()
    metrics = []

    for i in range(50):
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=cpu_storage_value(85.0, cpu_count, host_cpu_mhz),  # CPU 高使用率
                timestamp=base_time - timedelta(minutes=i * 5),
            )
        )
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="memory",
                value=memory_storage_value(20.0, memory_bytes),  # 内存低使用率
                timestamp=base_time - timedelta(minutes=i * 5),
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

    result = await detector._analyze_vm(1, metrics, vm_info)

    assert result["hasMismatch"] is True
    assert result["mismatchType"] == "cpu_poor_memory_rich"
    assert "CPU" in result["recommendation"]


@pytest.mark.asyncio
async def test_mismatch_detector_both_underutilized():
    """测试双重过剩检测"""
    detector = MismatchDetector()

    base_time = datetime.now()
    metrics = []

    for i in range(50):
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=cpu_storage_value(15.0, 8, 2600),  # CPU 低使用率
                timestamp=base_time - timedelta(minutes=i * 5),
            )
        )
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="memory",
                value=memory_storage_value(20.0, 16 * 1024**3),  # 内存低使用率
                timestamp=base_time - timedelta(minutes=i * 5),
            )
        )

    vm_info = {
        "name": "test-vm",
        "cluster": "cluster1",
        "cpu_count": 8,
        "memory_bytes": 16 * 1024**3,
        "host_cpu_mhz": 2600,
        "host_ip": "192.168.1.10",
    }

    result = await detector._analyze_vm(1, metrics, vm_info)

    assert result["hasMismatch"] is True
    assert result["mismatchType"] == "both_underutilized"
    assert "降配" in result["recommendation"]


@pytest.mark.asyncio
async def test_mismatch_detector_both_overutilized():
    """测试双重紧张检测"""
    detector = MismatchDetector()

    base_time = datetime.now()
    metrics = []

    for i in range(50):
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=cpu_storage_value(85.0, 2, 2600),  # CPU 高使用率
                timestamp=base_time - timedelta(minutes=i * 5),
            )
        )
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="memory",
                value=memory_storage_value(80.0, 4 * 1024**3),  # 内存高使用率
                timestamp=base_time - timedelta(minutes=i * 5),
            )
        )

    vm_info = {
        "name": "test-vm",
        "cluster": "cluster1",
        "cpu_count": 2,
        "memory_bytes": 4 * 1024**3,
        "host_cpu_mhz": 2600,
        "host_ip": "192.168.1.10",
    }

    result = await detector._analyze_vm(1, metrics, vm_info)

    assert result["hasMismatch"] is True
    assert result["mismatchType"] == "both_overutilized"
    assert "扩容" in result["recommendation"]


@pytest.mark.asyncio
async def test_mismatch_detector_no_mismatch():
    """测试无错配情况"""
    detector = MismatchDetector()

    base_time = datetime.now()
    metrics = []

    for i in range(50):
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=cpu_storage_value(55.0, 4, 2600),  # CPU 中等使用率
                timestamp=base_time - timedelta(minutes=i * 5),
            )
        )
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="memory",
                value=memory_storage_value(50.0, 8 * 1024**3),  # 内存中等使用率
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

    result = await detector._analyze_vm(1, metrics, vm_info)

    assert result["hasMismatch"] is False
    assert result["mismatchType"] is None
    assert "合理" in result["recommendation"]


@pytest.mark.asyncio
async def test_mismatch_detector_percentile_calculation():
    """测试百分位数计算"""
    detector = MismatchDetector()

    values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

    p95 = detector._percentile(values, 95)
    assert p95 == 100

    p50 = detector._percentile(values, 50)
    assert p50 == 60


@pytest.mark.asyncio
async def test_resource_analyzer_combined():
    """测试综合资源分析"""
    analyzer = ResourceAnalyzer(mode="saving")

    base_time = datetime.now()
    vm_metrics = {
        1: [],
        2: [],
    }

    # VM 1: 需要缩容
    for i in range(100):
        vm_metrics[1].append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=20.0,
                timestamp=base_time - timedelta(minutes=i * 5),
            )
        )
        vm_metrics[1].append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="memory",
                value=20.0,
                timestamp=base_time - timedelta(minutes=i * 5),
            )
        )

    # VM 2: 潮汐模式
    for i in range(100):
        hour = (base_time - timedelta(hours=i)).hour
        value = 60.0 if 9 <= hour <= 18 else 5.0
        vm_metrics[2].append(
            VMMetric(
                task_id=1,
                vm_id=2,
                metric_type="cpu",
                value=value,
                timestamp=base_time - timedelta(hours=i),
            )
        )

    vm_data = {
        1: {
            "name": "vm-1",
            "cluster": "cluster1",
            "cpu_count": 8,
            "memory_bytes": 16 * 1024**3,
            "memory_gb": 16,
            "host_ip": "192.168.1.10",
        },
        2: {
            "name": "vm-2",
            "cluster": "cluster1",
            "cpu_count": 4,
            "memory_bytes": 8 * 1024**3,
            "memory_gb": 8,
            "host_ip": "192.168.1.11",
        },
    }

    result = await analyzer.analyze(1, vm_metrics, vm_data)

    assert "rightSize" in result
    assert "usagePattern" in result
    assert "mismatch" in result
    assert "summary" in result
    assert result["summary"]["totalVmsAnalyzed"] == 2


@pytest.mark.asyncio
async def test_usage_pattern_classify_pattern():
    """测试使用模式分类逻辑"""
    analyzer = UsagePatternAnalyzer()

    # 稳定模式: CV < 0.3
    pattern, level, rec = analyzer._classify_pattern(0.2, 1.5)
    assert pattern == "stable"
    assert level == "low"

    # 突发模式: CV > 0.3 但不满足潮汐条件
    pattern, level, rec = analyzer._classify_pattern(0.4, 2.0)
    assert pattern == "burst"
    assert level == "moderate"

    # 潮汐模式: CV > 0.5 且峰谷比 > 3
    pattern, level, rec = analyzer._classify_pattern(0.6, 4.0)
    assert pattern == "tidal"
    assert level == "high"


@pytest.mark.asyncio
async def test_mismatch_detector_custom_thresholds():
    """测试自定义阈值"""
    detector = MismatchDetector(
        cpu_low_threshold=20.0,
        cpu_high_threshold=80.0,
        memory_low_threshold=20.0,
        memory_high_threshold=80.0,
    )

    # VM 配置
    cpu_count = 8
    memory_bytes = 16 * 1024**3
    host_cpu_mhz = 2600

    base_time = datetime.now()
    metrics = []

    for i in range(50):
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=cpu_storage_value(15.0, cpu_count, host_cpu_mhz),  # 低于自定义20%阈值
                timestamp=base_time - timedelta(minutes=i * 5),
            )
        )
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="memory",
                value=memory_storage_value(85.0, memory_bytes),  # 高于自定义80%阈值
                timestamp=base_time - timedelta(minutes=i * 5),
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

    result = await detector._analyze_vm(1, metrics, vm_info)

    # 使用自定义阈值应该检测到错配 (CPU富裕内存紧张)
    assert result["hasMismatch"] is True
    assert result["mismatchType"] == "cpu_rich_memory_poor"
