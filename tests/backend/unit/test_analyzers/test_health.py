"""Unit tests for HealthAnalyzer.

Tests the platform health assessment including:
- Resource overcommit analysis
- Load balance analysis
- VM density (hotspot) analysis
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from app.analyzers.health import HealthAnalyzer


# ============ Fixtures ============

@pytest.fixture
def mock_clusters():
    """Create mock cluster objects."""
    clusters = []

    # Cluster 1: High overcommit
    cluster1 = MagicMock()
    cluster1.id = 1
    cluster1.name = "cluster-high-overcommit"
    cluster1.datacenter = "dc1"
    cluster1.total_cpu = 60000  # ~20 cores @ 3000MHz
    cluster1.total_memory = 60 * 1024**3  # 60GB
    cluster1.num_hosts = 3
    cluster1.num_vms = 5
    clusters.append(cluster1)

    # Cluster 2: Balanced
    cluster2 = MagicMock()
    cluster2.id = 2
    cluster2.name = "cluster-balanced"
    cluster2.datacenter = "dc1"
    cluster2.total_cpu = 120000  # ~40 cores
    cluster2.total_memory = 128 * 1024**3  # 128GB
    cluster2.num_hosts = 4
    cluster2.num_vms = 8
    clusters.append(cluster2)

    return clusters


@pytest.fixture
def mock_hosts():
    """Create mock host objects."""
    hosts = []

    # Host 1: High VM density (hotspot)
    host1 = MagicMock()
    host1.id = 1
    host1.name = "esxi-hotspot-01"
    host1.datacenter = "dc1"
    host1.ip_address = "192.168.1.10"
    host1.cpu_cores = 4
    host1.memory_bytes = 64 * 1024**3  # 64GB
    host1.num_vms = 30  # 7.5 VM/CPU - high density
    host1.power_state = "poweredOn"
    hosts.append(host1)

    # Host 2: Normal load
    host2 = MagicMock()
    host2.id = 2
    host2.name = "esxi-normal-01"
    host2.datacenter = "dc1"
    host2.ip_address = "192.168.1.11"
    host2.cpu_cores = 16
    host2.memory_bytes = 128 * 1024**3
    host2.num_vms = 20  # 1.25 VM/CPU - normal
    host2.power_state = "poweredOn"
    hosts.append(host2)

    # Host 3: Light load
    host3 = MagicMock()
    host3.id = 3
    host3.name = "esxi-light-01"
    host3.datacenter = "dc1"
    host3.ip_address = "192.168.1.12"
    host3.cpu_cores = 16
    host3.memory_bytes = 128 * 1024**3
    host3.num_vms = 5  # 0.31 VM/CPU - light
    host3.power_state = "poweredOn"
    hosts.append(host3)

    # Host 4: Severe hotspot
    host4 = MagicMock()
    host4.id = 4
    host4.name = "esxi-severe-01"
    host4.datacenter = "dc1"
    host4.ip_address = "192.168.1.13"
    host4.cpu_cores = 2
    host4.memory_bytes = 32 * 1024**3
    host4.num_vms = 25  # 12.5 VM/CPU - severe
    host4.power_state = "poweredOn"
    hosts.append(host4)

    return hosts


@pytest.fixture
def mock_vms():
    """Create mock VM objects."""
    vms = []

    # VMs for cluster-high-overcommit (5 VMs with high allocation)
    for i in range(5):
        vm = MagicMock()
        vm.id = i + 1
        vm.name = f"vm-overcommit-{i+1}"
        vm.datacenter = "dc1"
        vm.uuid = f"uuid-{i+1}"
        vm.cluster_key = f"dc1:cluster-high-overcommit"
        vm.cpu_count = 8  # High CPU
        vm.memory_bytes = 16 * 1024**3  # 16GB
        vm.power_state = "poweredOn"
        vm.host_name = "esxi-host-01"
        vm.host_ip = "192.168.1.10"
        vms.append(vm)

    # VMs for cluster-balanced (8 VMs with normal allocation)
    for i in range(8):
        vm = MagicMock()
        vm.id = i + 6
        vm.name = f"vm-balanced-{i+1}"
        vm.datacenter = "dc1"
        vm.uuid = f"uuid-{i+6}"
        vm.cluster_key = f"dc1:cluster-balanced"
        vm.cpu_count = 4
        vm.memory_bytes = 8 * 1024**3  # 8GB
        vm.power_state = "poweredOn"
        vm.host_name = "esxi-host-02"
        vm.host_ip = "192.168.1.11"
        vms.append(vm)

    return vms


@pytest.fixture
def mock_task(mock_clusters):
    """Create mock task."""
    task = MagicMock()
    task.id = 1
    task.connection_id = 1
    return task


# ============ Overcommit Analysis Tests ============

class TestOvercommitAnalysis:
    """Tests for resource overcommit analysis."""

    @pytest.mark.asyncio
    async def test_overcommit_score_no_overcommit(self):
        """Test score when there's no overcommit."""
        analyzer = HealthAnalyzer()

        # Allocated = Physical, ratio = 1.0
        score = analyzer._calculate_overcommit_score(1.0, 1.0)
        assert score == 100

    @pytest.mark.asyncio
    async def test_overcommit_score_light_overcommit(self):
        """Test score with light overcommit (1.0-1.2)."""
        analyzer = HealthAnalyzer()

        score = analyzer._calculate_overcommit_score(1.1, 1.15)
        assert score == 85

    @pytest.mark.asyncio
    async def test_overcommit_score_moderate_overcommit(self):
        """Test score with moderate overcommit (1.2-1.5)."""
        analyzer = HealthAnalyzer()

        score = analyzer._calculate_overcommit_score(1.3, 1.4)
        assert score == 65

    @pytest.mark.asyncio
    async def test_overcommit_score_high_overcommit(self):
        """Test score with high overcommit (1.5-2.0)."""
        analyzer = HealthAnalyzer()

        score = analyzer._calculate_overcommit_score(1.7, 1.8)
        assert score == 40

    @pytest.mark.asyncio
    async def test_overcommit_score_severe_overcommit(self):
        """Test score with severe overcommit (>2.0)."""
        analyzer = HealthAnalyzer()

        score = analyzer._calculate_overcommit_score(2.5, 2.2)
        assert score == 20

    def test_assess_overcommit_risk_low(self):
        """Test risk assessment for low overcommit."""
        analyzer = HealthAnalyzer()

        assert analyzer._assess_overcommit_risk(0.8) == "low"
        assert analyzer._assess_overcommit_risk(1.0) == "low"

    def test_assess_overcommit_risk_medium(self):
        """Test risk assessment for medium overcommit."""
        analyzer = HealthAnalyzer()

        assert analyzer._assess_overcommit_risk(1.1) == "medium"
        assert analyzer._assess_overcommit_risk(1.2) == "medium"

    def test_assess_overcommit_risk_high(self):
        """Test risk assessment for high overcommit."""
        analyzer = HealthAnalyzer()

        assert analyzer._assess_overcommit_risk(1.3) == "high"
        assert analyzer._assess_overcommit_risk(1.5) == "high"

    def test_assess_overcommit_risk_critical(self):
        """Test risk assessment for critical overcommit."""
        analyzer = HealthAnalyzer()

        assert analyzer._assess_overcommit_risk(1.6) == "critical"
        assert analyzer._assess_overcommit_risk(2.0) == "critical"

    def test_assess_overcommit_risk_severe(self):
        """Test risk assessment for severe overcommit."""
        analyzer = HealthAnalyzer()

        assert analyzer._assess_overcommit_risk(2.5) == "severe"


# ============ Balance Analysis Tests ============

class TestBalanceAnalysis:
    """Tests for load balance analysis."""

    def test_assess_balance_level_excellent(self):
        """Test excellent balance level (CV < 0.2)."""
        analyzer = HealthAnalyzer()

        level, score = analyzer._assess_balance_level(0.1)
        assert level == "excellent"
        assert score == 100

        level, score = analyzer._assess_balance_level(0.19)
        assert level == "excellent"
        assert score == 100

    def test_assess_balance_level_good(self):
        """Test good balance level (0.2 <= CV < 0.4)."""
        analyzer = HealthAnalyzer()

        level, score = analyzer._assess_balance_level(0.2)
        assert level == "good"
        assert score == 80

        level, score = analyzer._assess_balance_level(0.35)
        assert level == "good"
        assert score == 80

    def test_assess_balance_level_fair(self):
        """Test fair balance level (0.4 <= CV < 0.6)."""
        analyzer = HealthAnalyzer()

        level, score = analyzer._assess_balance_level(0.4)
        assert level == "fair"
        assert score == 60

        level, score = analyzer._assess_balance_level(0.55)
        assert level == "fair"
        assert score == 60

    def test_assess_balance_level_poor(self):
        """Test poor balance level (CV >= 0.6)."""
        analyzer = HealthAnalyzer()

        level, score = analyzer._assess_balance_level(0.6)
        assert level == "poor"
        assert score == 40

        level, score = analyzer._assess_balance_level(0.8)
        assert level == "poor"
        assert score == 40


# ============ Hotspot Analysis Tests ============

class TestHotspotAnalysis:
    """Tests for VM density (hotspot) analysis."""

    def test_assess_hotspot_risk_low(self):
        """Test low risk (VM density < 3)."""
        analyzer = HealthAnalyzer()

        assert analyzer._assess_hotspot_risk(1.0) == "low"
        assert analyzer._assess_hotspot_risk(2.5) == "low"

    def test_assess_hotspot_risk_medium(self):
        """Test medium risk (3 <= VM density < 5)."""
        analyzer = HealthAnalyzer()

        assert analyzer._assess_hotspot_risk(3.0) == "medium"
        assert analyzer._assess_hotspot_risk(4.5) == "medium"

    def test_assess_hotspot_risk_high(self):
        """Test high risk (5 <= VM density < 7)."""
        analyzer = HealthAnalyzer()

        assert analyzer._assess_hotspot_risk(5.0) == "high"
        assert analyzer._assess_hotspot_risk(6.5) == "high"

    def test_assess_hotspot_risk_critical(self):
        """Test critical risk (7 <= VM density < 10)."""
        analyzer = HealthAnalyzer()

        assert analyzer._assess_hotspot_risk(7.0) == "critical"
        assert analyzer._assess_hotspot_risk(9.5) == "critical"

    def test_assess_hotspot_risk_severe(self):
        """Test severe risk (VM density >= 10)."""
        analyzer = HealthAnalyzer()

        assert analyzer._assess_hotspot_risk(10.0) == "severe"
        assert analyzer._assess_hotspot_risk(15.0) == "severe"

    def test_hotspot_recommendation_severe(self):
        """Test recommendation for severe hotspot."""
        analyzer = HealthAnalyzer()

        rec = analyzer._get_hotspot_recommendation("test-host", 12.0, "severe")
        assert "严重过载" in rec
        assert "12.0" in rec
        assert "迁移" in rec

    def test_hotspot_recommendation_critical(self):
        """Test recommendation for critical hotspot."""
        analyzer = HealthAnalyzer()

        rec = analyzer._get_hotspot_recommendation("test-host", 8.0, "critical")
        assert "高负载" in rec
        assert "8.0" in rec
        assert "迁移" in rec

    def test_hotspot_recommendation_high(self):
        """Test recommendation for high risk hotspot."""
        analyzer = HealthAnalyzer()

        rec = analyzer._get_hotspot_recommendation("test-host", 6.0, "high")
        assert "负载较高" in rec
        assert "6.0" in rec
        assert "关注" in rec


# ============ Grade Determination Tests ============

class TestGradeDetermination:
    """Tests for health grade determination."""

    def test_grade_excellent(self):
        """Test excellent grade (score >= 90)."""
        analyzer = HealthAnalyzer()

        assert analyzer._determine_grade(90) == "excellent"
        assert analyzer._determine_grade(95) == "excellent"
        assert analyzer._determine_grade(100) == "excellent"

    def test_grade_good(self):
        """Test good grade (75 <= score < 90)."""
        analyzer = HealthAnalyzer()

        assert analyzer._determine_grade(75) == "good"
        assert analyzer._determine_grade(80) == "good"
        assert analyzer._determine_grade(89) == "good"

    def test_grade_fair(self):
        """Test fair grade (60 <= score < 75)."""
        analyzer = HealthAnalyzer()

        assert analyzer._determine_grade(60) == "fair"
        assert analyzer._determine_grade(70) == "fair"
        assert analyzer._determine_grade(74) == "fair"

    def test_grade_poor(self):
        """Test poor grade (40 <= score < 60)."""
        analyzer = HealthAnalyzer()

        assert analyzer._determine_grade(40) == "poor"
        assert analyzer._determine_grade(50) == "poor"
        assert analyzer._determine_grade(59) == "poor"

    def test_grade_critical(self):
        """Test critical grade (score < 40)."""
        analyzer = HealthAnalyzer()

        assert analyzer._determine_grade(0) == "critical"
        assert analyzer._determine_grade(20) == "critical"
        assert analyzer._determine_grade(39) == "critical"


# ============ Integration Tests ============

class TestHealthAnalyzerIntegration:
    """Integration tests for HealthAnalyzer."""

    @pytest.mark.asyncio
    async def test_empty_result(self):
        """Test empty result when no data available."""
        analyzer = HealthAnalyzer()

        result = analyzer._empty_result()

        assert result["success"] is True
        assert result["data"]["overallScore"] == 0.0
        assert result["data"]["grade"] == "no_data"
        assert result["data"]["clusterCount"] == 0
        assert result["data"]["hostCount"] == 0
        assert result["data"]["vmCount"] == 0
        assert result["data"]["findings"] == []
        assert result["data"]["recommendations"] == []

    @pytest.mark.asyncio
    async def test_build_cluster_data(self, mock_clusters, mock_vms):
        """Test cluster data building."""
        analyzer = HealthAnalyzer()

        cluster_data = analyzer._build_cluster_data(mock_clusters, mock_vms)

        assert len(cluster_data) == 2
        assert "dc1:cluster-high-overcommit" in cluster_data
        assert "dc1:cluster-balanced" in cluster_data

    @pytest.mark.asyncio
    async def test_overcommit_analysis_results(self, mock_clusters, mock_vms):
        """Test overcommit analysis produces valid results."""
        analyzer = HealthAnalyzer()

        cluster_data = analyzer._build_cluster_data(mock_clusters, mock_vms)
        results, score = await analyzer._analyze_overcommit(cluster_data)

        assert len(results) == 2
        assert 0 <= score <= 100

        # Check result structure
        for result in results:
            assert "clusterName" in result
            assert "physicalCpuCores" in result
            assert "physicalMemoryGb" in result
            assert "allocatedCpu" in result
            assert "allocatedMemoryGb" in result
            assert "cpuOvercommit" in result
            assert "memoryOvercommit" in result
            assert "cpuRisk" in result
            assert "memoryRisk" in result

            # Valid risk levels
            assert result["cpuRisk"] in ["low", "medium", "high", "critical", "severe"]
            assert result["memoryRisk"] in ["low", "medium", "high", "critical", "severe"]

    @pytest.mark.asyncio
    async def test_balance_analysis_results(self, mock_clusters, mock_hosts):
        """Test balance analysis produces valid results."""
        analyzer = HealthAnalyzer()

        cluster_data = analyzer._build_cluster_data(mock_clusters, [])
        results, score = await analyzer._analyze_balance(cluster_data, mock_hosts)

        assert len(results) > 0
        assert 0 <= score <= 100

        # Check result structure
        for result in results:
            assert "clusterName" in result
            assert "hostCount" in result
            assert "vmCounts" in result
            assert "meanVmCount" in result
            assert "stdDev" in result
            assert "coefficientOfVariation" in result
            assert "balanceLevel" in result
            assert "balanceScore" in result

            # Valid balance levels
            assert result["balanceLevel"] in ["excellent", "good", "fair", "poor"]

    @pytest.mark.asyncio
    async def test_hotspot_analysis_results(self, mock_hosts):
        """Test hotspot analysis produces valid results."""
        analyzer = HealthAnalyzer()

        hotspots, score, avg_density = await analyzer._analyze_hotspot(mock_hosts)

        assert 0 <= score <= 100
        assert avg_density >= 0

        # Should detect hotspot hosts
        assert len(hotspots) > 0

        # Check result structure
        for hotspot in hotspots:
            assert "hostName" in hotspot
            assert "ipAddress" in hotspot
            assert "vmCount" in hotspot
            assert "cpuCores" in hotspot
            assert "memoryGb" in hotspot
            assert "vmDensity" in hotspot
            assert "riskLevel" in hotspot
            assert "recommendation" in hotspot

            # Valid risk levels (should be high/critical/severe for hotspots)
            assert hotspot["riskLevel"] in ["high", "critical", "severe"]

    @pytest.mark.asyncio
    async def test_findings_generation(self):
        """Test findings are generated correctly."""
        analyzer = HealthAnalyzer()

        # Create sample results
        overcommit_results = [{
            "clusterName": "test-cluster",
            "cpuOvercommit": 1.8,
            "memoryOvercommit": 1.6,
            "cpuRisk": "critical",
            "memoryRisk": "high",
        }]

        balance_results = [{
            "clusterName": "unbalanced-cluster",
            "coefficientOfVariation": 0.7,
            "balanceLevel": "poor",
        }]

        hotspot_hosts = [{
            "hostName": "hotspot-host",
            "vmDensity": 12.0,
            "riskLevel": "severe",
            "vmCount": 24,
            "cpuCores": 2,
        }]

        findings = analyzer._generate_findings(
            overcommit_results,
            balance_results,
            hotspot_hosts,
            50,  # overcommit_score
            40,  # balance_score
            30,  # hotspot_score
        )

        # Should have findings from all three categories
        assert len(findings) >= 3

        # Check finding structure
        for finding in findings:
            assert "severity" in finding
            assert "category" in finding
            assert "description" in finding
            assert "details" in finding

            # Valid categories
            assert finding["category"] in ["overcommit", "balance", "hotspot"]

            # Valid severities
            assert finding["severity"] in ["low", "medium", "high", "critical", "severe"]

    @pytest.mark.asyncio
    async def test_recommendations_generation(self):
        """Test recommendations are generated correctly."""
        analyzer = HealthAnalyzer()

        overcommit_results = [{
            "clusterName": "high-overcommit-cluster",
            "cpuRisk": "critical",
            "memoryRisk": "high",
        }]

        balance_results = [{
            "clusterName": "poor-balance-cluster",
            "balanceLevel": "poor",
        }]

        hotspot_hosts = [{
            "hostName": "critical-hotspot",
            "riskLevel": "critical",
        }]

        recommendations = analyzer._generate_recommendations(
            overcommit_results,
            balance_results,
            hotspot_hosts,
        )

        # Should have recommendations
        assert len(recommendations) > 0

        # Each recommendation should be a non-empty string
        for rec in recommendations:
            assert isinstance(rec, str)
            assert len(rec) > 0


# ============ Edge Cases ============

class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_zero_cpu_cores(self):
        """Test handling of zero CPU cores."""
        analyzer = HealthAnalyzer()

        # Should not crash with zero cores
        risk = analyzer._assess_hotspot_risk(0)  # Zero density
        assert risk == "low"

    def test_zero_physical_resources(self):
        """Test handling of zero physical resources."""
        analyzer = HealthAnalyzer()

        # Should handle zero physical resources gracefully
        score = analyzer._calculate_overcommit_score(0, 0)
        assert score == 100  # No overcommit when no resources

    def test_single_host_balance(self):
        """Test balance with single host (std dev = 0)."""
        analyzer = HealthAnalyzer()

        # Single host should be considered perfectly balanced
        level, score = analyzer._assess_balance_level(0)
        assert level == "excellent"
        assert score == 100
