"""Unit tests for ZombieAnalyzer."""

import pytest
from datetime import datetime, timedelta

from app.analyzers.zombie import ZombieAnalyzer
from app.models import VMMetric


@pytest.mark.asyncio
async def test_zombie_analyzer_low_usage_vm():
    """测试低使用率 VM 被识别为僵尸 VM"""
    analyzer = ZombieAnalyzer(
        days_threshold=30,
        cpu_threshold=10.0,
        memory_threshold=20.0,
        disk_io_threshold=5.0,
        network_threshold=5.0,
        min_confidence=70.0,
    )

    # 创建低使用率指标
    base_time = datetime.now()
    metrics = []
    for i in range(100):  # 100个样本
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=3.0,  # CPU < 10%
                timestamp=base_time - timedelta(hours=i),
            )
        )
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="memory",
                value=10.0,  # Memory < 20%
                timestamp=base_time - timedelta(hours=i),
            )
        )

    vm_info = {
        "name": "test-zombie-vm",
        "cluster": "cluster1",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
        "host_ip": "192.168.1.10",
    }

    result = await analyzer._analyze_vm(1, metrics, vm_info)

    assert result["vmName"] == "test-zombie-vm"
    assert result["cpuUsage"] == 3.0
    assert result["memoryUsage"] == 10.0
    assert result["confidence"] >= 70
    assert result["severity"] in ["high", "critical"]


@pytest.mark.asyncio
async def test_zombie_analyzer_normal_usage_vm():
    """测试正常使用率 VM 不被识别"""
    analyzer = ZombieAnalyzer(min_confidence=70.0)

    # 创建正常使用率指标
    base_time = datetime.now()
    metrics = []
    for i in range(100):
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=50.0,  # 正常 CPU 使用率
                timestamp=base_time - timedelta(hours=i),
            )
        )
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="memory",
                value=60.0,  # 正常内存使用率
                timestamp=base_time - timedelta(hours=i),
            )
        )

    vm_info = {
        "name": "test-normal-vm",
        "cluster": "cluster1",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
        "host_ip": "192.168.1.10",
    }

    result = await analyzer._analyze_vm(1, metrics, vm_info)

    # 正常 VM 置信度应低于阈值
    assert result["confidence"] < 70
    assert result["severity"] in ["low", "medium"]


@pytest.mark.asyncio
async def test_zombie_analyzer_confidence_scoring():
    """测试置信度评分计算"""
    analyzer = ZombieAnalyzer(min_confidence=50.0)

    base_time = datetime.now()
    metrics = []

    # 极低使用率 - 应获得最高置信度
    for i in range(50):
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=2.0,  # CPU < 5%
                timestamp=base_time - timedelta(hours=i),
            )
        )
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="memory",
                value=5.0,  # Memory < 10%
                timestamp=base_time - timedelta(hours=i),
            )
        )

    vm_info = {
        "name": "test-zombie",
        "cluster": "cluster1",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
        "host_ip": "192.168.1.10",
    }

    result = await analyzer._analyze_vm(1, metrics, vm_info)

    # CPU < 5%: +40, Memory < 10%: +30, 至少 70 分
    assert result["confidence"] >= 70
    assert result["severity"] == "critical"


@pytest.mark.asyncio
async def test_zombie_analyzer_empty_metrics():
    """测试空指标情况"""
    analyzer = ZombieAnalyzer()

    vm_info = {
        "name": "test-vm",
        "cluster": "cluster1",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
        "host_ip": "192.168.1.10",
    }

    result = await analyzer._analyze_vm(1, [], vm_info)

    # 空指标应返回 0 值
    assert result["cpuUsage"] == 0
    assert result["memoryUsage"] == 0
