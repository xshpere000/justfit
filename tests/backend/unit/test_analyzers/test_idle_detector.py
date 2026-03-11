"""Unit tests for IdleDetector."""

import pytest
from datetime import datetime, timedelta, timezone

from app.analyzers.idle_detector import IdleDetector, IdleSubType
from app.models import VMMetric


# 辅助函数：将百分比值转换为存储的绝对值
def cpu_storage_value(percentage: float, cpu_count: int, host_cpu_mhz: int = 2600) -> float:
    """计算 CPU 存储值：percentage / 100 * cpu_count * host_cpu_mhz"""
    return percentage / 100 * cpu_count * host_cpu_mhz


def memory_storage_value(percentage: float, memory_bytes: int) -> float:
    """计算内存存储值（bytes）：percentage / 100 * memory_bytes"""
    return percentage / 100 * memory_bytes


@pytest.mark.asyncio
async def test_critical_zombie_90_days():
    """测试：关机90天的VM被识别为危急僵尸"""
    detector = IdleDetector(min_confidence=60.0)

    vm_info = {
        "name": "old-server",
        "cluster": "cluster1",
        "host_ip": "192.168.1.10",
        "downtime_duration": 100 * 86400,  # 100天，单位秒
        "vm_create_time": datetime.now(timezone.utc) - timedelta(days=200),
        "power_state": "poweredOff",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
    }

    vm_metrics = {}
    vm_data = {1: vm_info}

    results = await detector.analyze(1, vm_metrics, vm_data)

    assert len(results) == 1
    result = results[0]
    assert result["idleType"] == IdleSubType.POWERED_OFF.value
    assert result["confidence"] == 95
    assert result["riskLevel"] == "critical"
    assert result["daysInactive"] == 100
    assert result["downtimeDuration"] == 100 * 86400


@pytest.mark.asyncio
async def test_high_prob_zombie_30_days():
    """测试：关机30天的VM被识别为高疑似僵尸"""
    detector = IdleDetector(min_confidence=60.0)

    vm_info = {
        "name": "unused-server",
        "cluster": "cluster1",
        "host_ip": "192.168.1.11",
        "downtime_duration": 35 * 86400,  # 35天，单位秒
        "power_state": "poweredOff",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
    }

    vm_metrics = {}
    vm_data = {1: vm_info}

    results = await detector.analyze(1, vm_metrics, vm_data)

    assert len(results) == 1
    result = results[0]
    assert result["idleType"] == IdleSubType.POWERED_OFF.value
    assert result["confidence"] == 85
    assert result["riskLevel"] == "high"


@pytest.mark.asyncio
async def test_medium_prob_zombie_14_days():
    """测试：关机14天的VM被识别为潜在僵尸"""
    detector = IdleDetector(min_confidence=60.0)

    vm_info = {
        "name": "idle-server",
        "cluster": "cluster1",
        "host_ip": "192.168.1.12",
        "downtime_duration": 15 * 86400,  # 15天
        "power_state": "poweredOff",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
    }

    vm_metrics = {}
    vm_data = {1: vm_info}

    results = await detector.analyze(1, vm_metrics, vm_data)

    assert len(results) == 1
    result = results[0]
    assert result["idleType"] == IdleSubType.POWERED_OFF.value
    assert result["confidence"] == 70
    assert result["riskLevel"] == "medium"


@pytest.mark.asyncio
async def test_recently_powered_off_excluded():
    """测试：最近关机的VM被排除"""
    detector = IdleDetector(min_confidence=60.0)

    vm_info = {
        "name": "recent-server",
        "cluster": "cluster1",
        "host_ip": "192.168.1.13",
        "downtime_duration": 7 * 86400,  # 7天，低于阈值
        "power_state": "poweredOff",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
    }

    vm_metrics = {}
    vm_data = {1: vm_info}

    results = await detector.analyze(1, vm_metrics, vm_data)

    assert len(results) == 0  # 关机时间短，不识别为僵尸


@pytest.mark.asyncio
async def test_template_vm_excluded():
    """测试：模板VM被排除"""
    detector = IdleDetector(min_confidence=60.0)

    vm_info = {
        "name": "ubuntu-template",
        "cluster": "cluster1",
        "host_ip": "192.168.1.14",
        "downtime_duration": 100 * 86400,
        "power_state": "poweredOff",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
    }

    vm_metrics = {}
    vm_data = {1: vm_info}

    results = await detector.analyze(1, vm_metrics, vm_data)

    assert len(results) == 0  # 模板VM被排除


@pytest.mark.asyncio
async def test_template_vm_with_dash_tmpl():
    """测试：带 -tmpl 后缀的模板VM被排除"""
    detector = IdleDetector(min_confidence=60.0)

    vm_info = {
        "name": "centos7-tmpl",
        "cluster": "cluster1",
        "host_ip": "192.168.1.15",
        "downtime_duration": 100 * 86400,
        "power_state": "poweredOff",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
    }

    vm_metrics = {}
    vm_data = {1: vm_info}

    results = await detector.analyze(1, vm_metrics, vm_data)

    assert len(results) == 0


@pytest.mark.asyncio
async def test_test_vm_confidence_reduced():
    """测试：测试VM置信度降低"""
    detector = IdleDetector(min_confidence=60.0)

    vm_info = {
        "name": "test-server-01",
        "cluster": "cluster1",
        "host_ip": "192.168.1.16",
        "downtime_duration": 50 * 86400,
        "power_state": "poweredOff",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
    }

    vm_metrics = {}
    vm_data = {1: vm_info}

    results = await detector.analyze(1, vm_metrics, vm_data)

    assert len(results) == 1
    result = results[0]
    assert result["confidence"] < 85  # 置信度被降低20分


@pytest.mark.asyncio
async def test_demo_vm_confidence_reduced():
    """测试：demo VM置信度降低"""
    detector = IdleDetector(min_confidence=60.0)

    vm_info = {
        "name": "demo-app",
        "cluster": "cluster1",
        "host_ip": "192.168.1.17",
        "downtime_duration": 50 * 86400,
        "power_state": "poweredOff",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
    }

    vm_metrics = {}
    vm_data = {1: vm_info}

    results = await detector.analyze(1, vm_metrics, vm_data)

    assert len(results) == 1
    result = results[0]
    assert result["confidence"] < 85


@pytest.mark.asyncio
async def test_new_vm_observation_period():
    """测试：新创建VM给予观察期"""
    detector = IdleDetector(min_confidence=60.0)

    vm_info = {
        "name": "new-server",
        "cluster": "cluster1",
        "host_ip": "192.168.1.18",
        "downtime_duration": None,  # 没有关机时长
        "vm_create_time": datetime.now(timezone.utc) - timedelta(days=3),  # 3天前创建
        "power_state": "poweredOff",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
    }

    vm_metrics = {}
    vm_data = {1: vm_info}

    results = await detector.analyze(1, vm_metrics, vm_data)

    assert len(results) == 0  # 新VM在观察期内


@pytest.mark.asyncio
async def test_idle_powered_on_complete_idle():
    """测试：开机但完全闲置的VM"""
    detector = IdleDetector(min_confidence=60.0)

    # 创建极低使用率指标
    base_time = datetime.now(timezone.utc)
    metrics = []
    for i in range(144):  # 144个样本
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=cpu_storage_value(2.0, 4, 2600),  # 2% CPU -> 存储值
                timestamp=base_time - timedelta(hours=i),
            )
        )
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="memory",
                value=memory_storage_value(5.0, 8 * 1024**3),  # 5% 内存 -> 存储值(MB)
                timestamp=base_time - timedelta(hours=i),
            )
        )
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="disk_read",
                value=1.0,  # 极低磁盘
                timestamp=base_time - timedelta(hours=i),
            )
        )
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="net_rx",
                value=0.5,  # 极低网络
                timestamp=base_time - timedelta(hours=i),
            )
        )

    vm_info = {
        "name": "idle-powered-on",
        "cluster": "cluster1",
        "host_ip": "192.168.1.19",
        "power_state": "poweredOn",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
        "host_cpu_mhz": 2600,  # 主机 CPU 频率
        "uptime_duration": 2592000,  # 30天开机时长
    }

    vm_metrics = {1: metrics}
    vm_data = {1: vm_info}

    results = await detector.analyze(1, vm_metrics, vm_data)

    assert len(results) == 1
    result = results[0]
    assert result["idleType"] == IdleSubType.IDLE_POWERED_ON.value
    assert result["activityScore"] < 15
    assert result["isIdle"] is True
    assert result["cpuCores"] == 4
    assert result["memoryGb"] == 8.0


@pytest.mark.asyncio
async def test_low_activity_vm():
    """测试：低活动VM被识别"""
    detector = IdleDetector(min_confidence=60.0)

    # 创建中等偏低使用率指标
    base_time = datetime.now(timezone.utc)
    metrics = []
    for i in range(144):
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=cpu_storage_value(15.0, 4, 2600),  # 15% CPU -> 存储值
                timestamp=base_time - timedelta(hours=i),
            )
        )
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="memory",
                value=memory_storage_value(15.0, 8 * 1024**3),  # 15% 内存 -> 存储值(MB)
                timestamp=base_time - timedelta(hours=i),
            )
        )
        # 添加磁盘和网络指标以达到 LOW_ACTIVITY 分数范围 (15-29)
        # CPU 15% = 10分, Memory 15% = 0分, 需要再 5-19 分
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="disk_read",
                value=10.0,  # 10 bytes/s -> 5 分
                timestamp=base_time - timedelta(hours=i),
            )
        )
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="net_rx",
                value=10.0,  # 10 bytes/s -> 5 分
                timestamp=base_time - timedelta(hours=i),
            )
        )

    vm_info = {
        "name": "low-activity-vm",
        "cluster": "cluster1",
        "host_ip": "192.168.1.20",
        "power_state": "poweredOn",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
        "host_cpu_mhz": 2600,
    }

    vm_metrics = {1: metrics}
    vm_data = {1: vm_info}

    results = await detector.analyze(1, vm_metrics, vm_data)

    assert len(results) == 1
    result = results[0]
    assert result["idleType"] == IdleSubType.LOW_ACTIVITY.value
    assert 15 <= result["activityScore"] < 30


@pytest.mark.asyncio
async def test_normal_vm_not_idle():
    """测试：正常使用VM不被识别为闲置"""
    detector = IdleDetector(min_confidence=60.0)

    # 创建正常使用率指标
    base_time = datetime.now(timezone.utc)
    metrics = []
    for i in range(144):
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=cpu_storage_value(50.0, 4, 2600),  # 50% CPU -> 存储值
                timestamp=base_time - timedelta(hours=i),
            )
        )
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="memory",
                value=memory_storage_value(60.0, 8 * 1024**3),  # 60% 内存 -> 存储值(MB)
                timestamp=base_time - timedelta(hours=i),
            )
        )

    vm_info = {
        "name": "normal-vm",
        "cluster": "cluster1",
        "host_ip": "192.168.1.21",
        "power_state": "poweredOn",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
        "host_cpu_mhz": 2600,
    }

    vm_metrics = {1: metrics}
    vm_data = {1: vm_info}

    results = await detector.analyze(1, vm_metrics, vm_data)

    assert len(results) == 0  # 正常VM不应被识别为闲置


@pytest.mark.asyncio
async def test_activity_score_calculation():
    """测试：活动评分计算正确"""
    detector = IdleDetector()

    # 测试不同组合的活动评分

    # 高CPU + 高内存 = 高分
    score = detector._calculate_activity_score(60.0, 50.0, 200.0, 150.0)
    assert score >= 30  # CPU 40分 + 内存 30分 = 至少70分

    # 低CPU + 低内存 = 低分
    score = detector._calculate_activity_score(3.0, 5.0, 1.0, 0.5)
    assert score < 15  # 所有指标都低于阈值

    # 中等使用率 = 中等分数
    # CPU 25% -> 20分, 内存 25% -> 15分, 磁盘 60 -> 10分, 网络 60 -> 10分 = 55分
    score = detector._calculate_activity_score(25.0, 25.0, 60.0, 60.0)
    assert 40 <= score <= 60


@pytest.mark.asyncio
async def test_percentile_calculation():
    """测试：百分位数计算正确"""
    detector = IdleDetector()

    # 创建有序指标值
    base_time = datetime.now(timezone.utc)
    metrics = []
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0]
    for val in values:
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=val,
                timestamp=base_time,
            )
        )

    stats = detector._calculate_percentiles(metrics)

    assert stats["min"] == 1.0
    assert stats["max"] == 30.0
    assert stats["p50"] >= 5.0  # 中位数附近
    assert stats["p95"] >= 25.0  # 95分位数
    assert stats["avg"] == sum(values) / len(values)


@pytest.mark.asyncio
async def test_volatility_calculation():
    """测试：波动性计算正确"""
    detector = IdleDetector()

    # 稳定数据
    stable_values = [10.0, 10.0, 10.0, 10.0, 10.0]
    volatility = detector._calculate_volatility(stable_values)
    assert volatility == 0.0  # 无波动

    # 波动数据
    volatile_values = [5.0, 10.0, 15.0, 20.0, 25.0]
    volatility = detector._calculate_volatility(volatile_values)
    assert volatility > 0.3  # 高波动

    # 单个数据点
    single_value = [10.0]
    volatility = detector._calculate_volatility(single_value)
    assert volatility == 0.0


@pytest.mark.asyncio
async def test_risk_level_classification():
    """测试：风险等级分类正确"""
    detector = IdleDetector()

    assert detector._get_risk_level(95) == "critical"
    assert detector._get_risk_level(85) == "high"
    assert detector._get_risk_level(70) == "medium"
    assert detector._get_risk_level(40) == "low"


@pytest.mark.asyncio
async def test_data_quality_assessment():
    """测试：数据质量评估正确"""
    detector = IdleDetector(days_threshold=7)

    # 高质量数据（样本充足，期望: 7*24*180 = 30240）
    # 30000样本 -> 覆盖率 ~99% -> high
    metrics_by_type = {
        "cpu": [VMMetric(task_id=1, vm_id=1, metric_type="cpu", value=10.0, timestamp=datetime.now())
                for _ in range(15000)],
        "memory": [VMMetric(task_id=1, vm_id=1, metric_type="memory", value=20.0, timestamp=datetime.now())
                   for _ in range(15000)],
    }
    quality = detector._assess_data_quality(metrics_by_type)
    assert quality == "high"

    # 中等质量数据
    metrics_by_type = {
        "cpu": [VMMetric(task_id=1, vm_id=1, metric_type="cpu", value=10.0, timestamp=datetime.now())
                for _ in range(10000)],
        "memory": [VMMetric(task_id=1, vm_id=1, metric_type="memory", value=20.0, timestamp=datetime.now())
                   for _ in range(10000)],
    }
    quality = detector._assess_data_quality(metrics_by_type)
    assert quality == "medium"

    # 低质量数据（样本不足）
    metrics_by_type = {
        "cpu": [VMMetric(task_id=1, vm_id=1, metric_type="cpu", value=10.0, timestamp=datetime.now())
                for _ in range(100)],
    }
    quality = detector._assess_data_quality(metrics_by_type)
    assert quality == "low"


@pytest.mark.asyncio
async def test_multiple_vms_analysis():
    """测试：多VM分析正确"""
    detector = IdleDetector(min_confidence=60.0)

    base_time = datetime.now(timezone.utc)

    # 创建多个VM的测试数据
    vm_data = {}
    vm_metrics = {}

    # VM1: 关机僵尸
    vm_data[1] = {
        "name": "zombie-vm",
        "cluster": "cluster1",
        "host_ip": "192.168.1.30",
        "downtime_duration": 100 * 86400,
        "power_state": "poweredOff",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
    }

    # VM2: 开机闲置
    vm_data[2] = {
        "name": "idle-vm",
        "cluster": "cluster1",
        "host_ip": "192.168.1.31",
        "power_state": "poweredOn",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
        "host_cpu_mhz": 2600,
    }
    vm_metrics[2] = [
        VMMetric(task_id=1, vm_id=2, metric_type="cpu", value=cpu_storage_value(2.0, 4, 2600), timestamp=base_time - timedelta(hours=i))
        for i in range(100)
    ]

    # VM3: 正常VM
    vm_data[3] = {
        "name": "normal-vm",
        "cluster": "cluster1",
        "host_ip": "192.168.1.32",
        "power_state": "poweredOn",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
        "host_cpu_mhz": 2600,
    }
    vm_metrics[3] = [
        VMMetric(task_id=1, vm_id=3, metric_type="cpu", value=cpu_storage_value(50.0, 4, 2600), timestamp=base_time - timedelta(hours=i))
        for i in range(100)
    ]

    results = await detector.analyze(1, vm_metrics, vm_data)

    # 应该识别出2个闲置VM（关机僵尸 + 开机闲置）
    assert len(results) == 2
    idle_types = {r["idleType"] for r in results}
    assert IdleSubType.POWERED_OFF.value in idle_types
    assert IdleSubType.IDLE_POWERED_ON.value in idle_types


@pytest.mark.asyncio
async def test_powered_off_without_metrics():
    """测试：关机VM没有指标也能正确检测"""
    detector = IdleDetector(min_confidence=60.0)

    vm_info = {
        "name": "old-server",
        "cluster": "cluster1",
        "host_ip": "192.168.1.40",
        "downtime_duration": 90 * 86400,
        "power_state": "poweredOff",
        "cpu_count": 4,
        "memory_bytes": 8 * 1024**3,
    }

    vm_metrics = {}  # 没有指标
    vm_data = {1: vm_info}

    results = await detector.analyze(1, vm_metrics, vm_data)

    assert len(results) == 1
    assert results[0]["idleType"] == IdleSubType.POWERED_OFF.value
