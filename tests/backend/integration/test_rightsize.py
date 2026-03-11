"""RightSize Analyzer Integration Tests.

测试资源配置优化分析器的功能。
"""

import pytest
from datetime import datetime
from app.analyzers.rightsize import RightSizeAnalyzer
from app.models.metric import VMMetric


@pytest.fixture
def sample_vm_metrics():
    """创建示例 VM 指标数据."""
    now = datetime.now()

    # VM 1: 低使用率 (应建议缩容)
    # 4 vCPU, 16GB 内存
    # CPU 使用率 ~10%, 内存使用率 ~20%
    vm1_metrics = []
    for i in range(72):  # 3天数据，每小时1个点
        ts = datetime.fromtimestamp(now.timestamp() - i * 3600)
        # CPU: 4核 * 2095 MHz * 10% = ~838 MHz
        vm1_metrics.append(VMMetric(
            task_id=1, vm_id=1, metric_type="cpu",
            value=838.0, timestamp=ts
        ))
        # Memory: 16GB * 20% = ~3.4GB = ~3.6B bytes
        vm1_metrics.append(VMMetric(
            task_id=1, vm_id=1, metric_type="memory",
            value=3.6 * 1024**3, timestamp=ts
        ))

    # VM 2: 高使用率 (应建议扩容)
    # 2 vCPU, 4GB 内存
    # CPU 使用率 ~90%, 内存使用率 ~85%
    vm2_metrics = []
    for i in range(72):  # 3天数据
        ts = datetime.fromtimestamp(now.timestamp() - i * 3600)
        # CPU: 2核 * 2095 MHz * 90% = ~3771 MHz
        vm2_metrics.append(VMMetric(
            task_id=1, vm_id=2, metric_type="cpu",
            value=3771.0, timestamp=ts
        ))
        # Memory: 4GB * 85% = ~3.4GB = ~3.6B bytes
        vm2_metrics.append(VMMetric(
            task_id=1, vm_id=2, metric_type="memory",
            value=3.6 * 1024**3, timestamp=ts
        ))

    # VM 3: 配置合理
    # 4 vCPU, 8GB 内存
    # CPU 使用率 ~50%, 内存使用率 ~60%
    vm3_metrics = []
    for i in range(72):  # 3天数据
        ts = datetime.fromtimestamp(now.timestamp() - i * 3600)
        # CPU: 4核 * 2095 MHz * 50% = ~4190 MHz
        vm3_metrics.append(VMMetric(
            task_id=1, vm_id=3, metric_type="cpu",
            value=4190.0, timestamp=ts
        ))
        # Memory: 8GB * 60% = ~4.8GB = ~5.2B bytes
        vm3_metrics.append(VMMetric(
            task_id=1, vm_id=3, metric_type="memory",
            value=5.2 * 1024**3, timestamp=ts
        ))

    return {
        1: vm1_metrics,
        2: vm2_metrics,
        3: vm3_metrics,
    }


@pytest.fixture
def sample_vm_data():
    """创建示例 VM 基础数据."""
    return {
        1: {
            "name": "low-usage-vm",
            "cluster": "cluster-1",
            "host_ip": "10.0.0.1",
            "cpu_count": 4,
            "memory_bytes": 16 * 1024**3,  # 16GB
            "host_cpu_mhz": 2095,
            "host_name": "host-1",
        },
        2: {
            "name": "high-usage-vm",
            "cluster": "cluster-1",
            "host_ip": "10.0.0.1",
            "cpu_count": 2,
            "memory_bytes": 4 * 1024**3,  # 4GB
            "host_cpu_mhz": 2095,
            "host_name": "host-1",
        },
        3: {
            "name": "balanced-vm",
            "cluster": "cluster-1",
            "host_ip": "10.0.0.1",
            "cpu_count": 4,
            "memory_bytes": 8 * 1024**3,  # 8GB
            "host_cpu_mhz": 2095,
            "host_name": "host-1",
        },
    }


@pytest.mark.asyncio
async def test_rightsize_analyzer_low_usage_vm(sample_vm_metrics, sample_vm_data):
    """测试低使用率 VM 的分析."""
    analyzer = RightSizeAnalyzer(days_threshold=3, min_confidence=50.0)

    results = await analyzer.analyze(
        task_id=1,
        vm_metrics={1: sample_vm_metrics[1]},
        vm_data=sample_vm_data
    )

    assert len(results) > 0, "应该返回分析结果"

    result = results[0]
    assert result["vmName"] == "low-usage-vm"
    assert result["currentCpu"] == 4
    assert result["currentMemory"] == 16.0

    # 低使用率应该建议缩容
    assert result["adjustmentType"] in ("down", "down_significant"), \
        f"低使用率VM应该建议缩容，实际: {result['adjustmentType']}"

    # 推荐配置应该小于当前配置
    assert result["recommendedCpu"] < result["currentCpu"], \
        f"推荐CPU应该更小: {result['recommendedCpu']} < {result['currentCpu']}"

    # 置信度应该足够高
    assert result["confidence"] >= 50.0, \
        f"3天数据应该有足够置信度: {result['confidence']}"


@pytest.mark.asyncio
async def test_rightsize_analyzer_high_usage_vm(sample_vm_metrics, sample_vm_data):
    """测试高使用率 VM 的分析."""
    analyzer = RightSizeAnalyzer(days_threshold=3, min_confidence=50.0)

    results = await analyzer.analyze(
        task_id=1,
        vm_metrics={2: sample_vm_metrics[2]},
        vm_data=sample_vm_data
    )

    assert len(results) > 0

    result = results[0]
    assert result["vmName"] == "high-usage-vm"

    # 高使用率应该建议扩容或保持
    assert result["adjustmentType"] in ("up", "up_significant", "none"), \
        f"高使用率VM应该建议扩容: {result['adjustmentType']}"


@pytest.mark.asyncio
async def test_rightsize_analyzer_confidence_calculation(sample_vm_metrics, sample_vm_data):
    """测试置信度计算."""
    analyzer = RightSizeAnalyzer(days_threshold=3, min_confidence=50.0)

    results = await analyzer.analyze(
        task_id=1,
        vm_metrics={1: sample_vm_metrics[1]},
        vm_data=sample_vm_data
    )

    result = results[0]

    # 3天 = 72小时，每小时2个数据点(cpu + memory) = 144个数据点
    # expected_samples = 3 * 24 = 48 (应该是按小时计算，每种指标24个点)
    # total_samples = 72(cpu) + 72(memory) = 144
    # confidence = min(100, 144 / 48 * 100) = 100%
    expected_samples = 3 * 24  # 每小时1个数据点
    actual_samples = result["details"]["cpuSamples"] + result["details"]["memorySamples"]

    assert result["confidence"] == 100.0, \
        f"3天完整数据应该有100%%置信度，实际: {result['confidence']}, 样本数: {actual_samples}/{expected_samples}"


@pytest.mark.asyncio
async def test_rightsize_analyzer_risk_calculation(sample_vm_metrics, sample_vm_data):
    """测试风险等级计算."""
    analyzer = RightSizeAnalyzer(days_threshold=3, min_confidence=50.0)

    results = await analyzer.analyze(
        task_id=1,
        vm_metrics={1: sample_vm_metrics[1]},
        vm_data=sample_vm_data
    )

    result = results[0]

    # 稳定的低使用率应该是低风险
    assert result["riskLevel"] in ("low", "medium"), \
        f"稳定的低使用率应该是低风险: {result['riskLevel']}"


def test_normalize_cpu():
    """测试 CPU 标准化."""
    analyzer = RightSizeAnalyzer()

    assert analyzer._normalize_cpu(0.5) == 1
    assert analyzer._normalize_cpu(1.5) == 2
    assert analyzer._normalize_cpu(3) == 4
    assert analyzer._normalize_cpu(6) == 8
    assert analyzer._normalize_cpu(10) == 12
    assert analyzer._normalize_cpu(100) == 64  # 最大标准


def test_normalize_memory():
    """测试内存标准化."""
    analyzer = RightSizeAnalyzer()

    assert analyzer._normalize_memory(0.3) == 0.5
    assert analyzer._normalize_memory(1.5) == 2
    assert analyzer._normalize_memory(3) == 4
    assert analyzer._normalize_memory(10) == 16
    assert analyzer._normalize_memory(100) == 128  # 100GB -> 128GB
    assert analyzer._normalize_memory(300) == 256  # 最大标准


def test_percentile():
    """测试百分位数计算."""
    analyzer = RightSizeAnalyzer()

    values = [10, 20, 30, 40, 50]
    assert analyzer._percentile(values, 50) == 30  # 中位数
    assert analyzer._percentile(values, 95) == 50  # 接近最大值


def test_calculate_risk():
    """测试风险等级计算."""
    analyzer = RightSizeAnalyzer()

    # CV < 0.2 -> low
    assert analyzer._calculate_risk(2, 20) == "low"  # CV = 0.1

    # 0.2 < CV < 0.4 -> medium
    assert analyzer._calculate_risk(5, 20) == "medium"  # CV = 0.25

    # CV > 0.4 -> high
    assert analyzer._calculate_risk(10, 20) == "high"  # CV = 0.5
