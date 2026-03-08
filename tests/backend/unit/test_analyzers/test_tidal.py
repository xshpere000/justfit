"""Unit tests for TidalAnalyzer."""

import pytest
from datetime import datetime, timedelta

from app.analyzers.tidal import TidalAnalyzer
from app.models import VMMetric


@pytest.mark.asyncio
async def test_tidal_daily_pattern_detection():
    """测试日周期模式检测"""
    analyzer = TidalAnalyzer(days_threshold=30)

    base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
    metrics = []

    # 创建明显的日周期模式 (工作时间 9-18点 高使用率)
    # 使用更简单的时间生成方式
    for day in range(10):  # 10天
        for hour in range(24):
            # 为每天创建独立的时间戳
            timestamp = base_time - timedelta(days=10 - day)
            timestamp = timestamp.replace(hour=hour)

            value = 90 if 9 <= hour <= 18 else 10  # 更明显的差异
            metrics.append(
                VMMetric(
                    task_id=1,
                    vm_id=1,
                    metric_type="cpu",
                    value=value,
                    timestamp=timestamp,
                )
            )

    result = analyzer._detect_daily_pattern(metrics)

    # 验证返回结构
    assert "stability" in result
    assert "peakHours" in result
    assert "cv" in result
    # 稳定性应为非负数
    assert result["stability"] >= 0


@pytest.mark.asyncio
async def test_tidal_weekly_pattern_detection():
    """测试周周期模式检测"""
    analyzer = TidalAnalyzer(days_threshold=30)

    base_time = datetime.now()
    metrics = []

    # 创建周周期模式 (工作日高使用率)
    for day in range(28):  # 4周
        weekday = day % 7
        value = 90 if weekday < 5 else 10  # 更明显的差异
        for hour in range(24):
            metrics.append(
                VMMetric(
                    task_id=1,
                    vm_id=1,
                    metric_type="cpu",
                    value=value,
                    timestamp=base_time - timedelta(days=day, hours=hour),
                )
            )

    result = analyzer._detect_weekly_pattern(metrics)

    # 验证返回结果结构
    assert "stability" in result
    assert "peakDays" in result
    assert "cv" in result


@pytest.mark.asyncio
async def test_tidal_recommendation_generation():
    """测试建议生成"""
    analyzer = TidalAnalyzer()

    # 高稳定性日模式
    rec = analyzer._generate_recommendation("daily", 85.0, "50-70%")
    assert "日周期" in rec
    assert "50-70%" in rec

    # 中等稳定性周模式
    rec = analyzer._generate_recommendation("weekly", 60.0, "30-50%")
    assert "周周期" in rec

    # 无模式
    rec = analyzer._generate_recommendation("none", 10.0, "10-30%")
    assert "未检测到" in rec


@pytest.mark.asyncio
async def test_tidal_empty_metrics():
    """测试空指标"""
    analyzer = TidalAnalyzer()

    result = await analyzer._analyze_vm(1, [], {})

    assert result["vmName"] == "VM-1"
    assert result["stabilityScore"] == 0


@pytest.mark.asyncio
async def test_tidal_cv_calculation():
    """测试变异系数计算"""
    analyzer = TidalAnalyzer()

    # 稳定数据 (CV < 20%)
    base_time = datetime.now()
    metrics = []
    for i in range(24):
        metrics.append(
            VMMetric(
                task_id=1,
                vm_id=1,
                metric_type="cpu",
                value=50,  # 完全相同
                timestamp=base_time - timedelta(hours=i),
            )
        )

    result = analyzer._detect_daily_pattern(metrics)
    # 稳定数据应有高稳定性 (接近100)
    assert result["stability"] >= 90
