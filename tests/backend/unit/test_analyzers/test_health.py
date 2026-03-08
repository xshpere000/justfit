"""Unit tests for HealthAnalyzer."""

import pytest
from unittest.mock import MagicMock

from app.analyzers.health import HealthAnalyzer


def test_balance_score_calculation():
    """测试资源均衡度评分"""
    analyzer = HealthAnalyzer()

    # 创建模拟主机 - 均匀分布
    hosts = []
    for i in range(5):
        host = MagicMock()
        host.num_vms = 10  # 完全均匀
        hosts.append(host)

    score = analyzer._calculate_balance_score([], hosts, [])

    # 完全均匀应得满分
    assert score == 100


def test_balance_score_uneven():
    """测试不均衡分布评分"""
    analyzer = HealthAnalyzer()

    # 创建不均衡分布
    hosts = []
    for i, num_vms in enumerate([1, 1, 1, 50, 50]):
        host = MagicMock()
        host.num_vms = num_vms
        hosts.append(host)

    score = analyzer._calculate_balance_score([], hosts, [])

    # 不均衡应得低分
    assert score <= 60


def test_overcommit_score_calculation():
    """测试超配风险评分"""
    analyzer = HealthAnalyzer()

    # 模拟集群和VM - 理想超配范围
    clusters = []
    for i in range(2):
        cluster = MagicMock()
        cluster.total_cpu = 100000  # 100GHz
        cluster.total_memory = 100 * 1024**3  # 100GB
        clusters.append(cluster)

    vms = []
    for i in range(20):
        vm = MagicMock()
        vm.cpu_count = 10  # 每个 VM 10核
        vm.memory_bytes = 8 * 1024**3  # 每个 VM 8GB
        vms.append(vm)

    # 总VM: 200核, 160GB
    # 总集群: 200核(200000MHz), 200GB
    # CPU超配: 200/200 = 1x (低于理想2-4x)
    # Memory超配: 160/200 = 0.8x (低于理想1.5-2.5x)
    score = analyzer._calculate_overcommit_score(clusters, vms)

    assert 0 <= score <= 100


def test_hotspot_score_calculation():
    """测试热点集中度评分"""
    analyzer = HealthAnalyzer()

    # 创建模拟主机和VM - 均匀分布
    hosts = []
    for i in range(4):
        host = MagicMock()
        host.ip_address = f"192.168.1.{10+i}"
        hosts.append(host)

    vms = []
    # VM均匀分布
    for i in range(8):
        vm = MagicMock()
        vm.host_ip = f"192.168.1.{10 + (i % 4)}"
        vm.power_state = "poweredon"
        vm.cpu_count = 4
        vm.memory_bytes = 8 * 1024**3
        vms.append(vm)

    score = analyzer._calculate_hotspot_score(hosts, vms)

    # 均匀分布应得高分
    assert score >= 70


def test_range_score():
    """测试范围评分函数"""
    analyzer = HealthAnalyzer()

    # 在理想范围内
    assert analyzer._range_score(250, 200, 400) == 100
    assert analyzer._range_score(200, 200, 400) == 100
    assert analyzer._range_score(400, 200, 400) == 100

    # 低于理想范围
    score_low = analyzer._range_score(100, 200, 400)
    assert score_low < 100
    assert score_low > 0

    # 高于理想范围
    score_high = analyzer._range_score(600, 200, 400)
    assert score_high < 100
    assert score_high > 0


def test_empty_result():
    """测试空结果"""
    analyzer = HealthAnalyzer()

    result = analyzer._empty_result()

    # _empty_result 返回嵌套结构
    assert result["success"] is True
    assert result["data"]["overallScore"] == 0
    assert result["data"]["grade"] == "no_data"
    assert result["data"]["clusterCount"] == 0
    assert result["data"]["hostCount"] == 0
    assert result["data"]["vmCount"] == 0


def test_findings_generation():
    """测试发现生成"""
    analyzer = HealthAnalyzer()

    # 低均衡度 -> 应生成发现
    findings = analyzer._generate_findings(
        balance_score=50,
        overcommit_score=80,
        hotspot_score=80,
    )

    assert len(findings) > 0
    assert any(f["type"] == "balance" for f in findings)

    # 所有高分 -> 无发现
    findings_good = analyzer._generate_findings(
        balance_score=90,
        overcommit_score=90,
        hotspot_score=90,
    )

    assert len(findings_good) == 0


def test_findings_severity_levels():
    """测试发现严重程度"""
    analyzer = HealthAnalyzer()

    # 极低均衡度 -> 高严重度
    findings = analyzer._generate_findings(
        balance_score=40,  # < 50
        overcommit_score=80,
        hotspot_score=80,
    )

    balance_finding = next((f for f in findings if f["type"] == "balance"), None)
    assert balance_finding is not None
    assert balance_finding["severity"] == "high"
