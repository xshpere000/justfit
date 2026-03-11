"""Integration tests for PDF report generation.

This test uses mock data to generate a complete PDF report,
verifying that all components work together correctly.
"""

import sys
import os
from pathlib import Path

# Add backend directory to Python path BEFORE any other imports
project_root = Path(__file__).parent.parent.parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

# Also ensure project root is in path for potential resource access
sys.path.insert(0, str(project_root))

# Set working directory to project root for relative path resolution
os.chdir(project_root)

import pytest
from datetime import datetime, timezone
from typing import Dict, Any, List

# Import reportlab units for testing
from reportlab.lib.units import cm


class MockAsyncSession:
    """Mock database session for testing."""

    def __init__(self):
        self.data = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def get_mock_report_data() -> Dict[str, Any]:
    """Generate comprehensive mock data for PDF report testing.

    Returns:
        Complete report data structure matching ReportBuilder output
    """
    return {
        "task": {
            "id": 1,
            "name": "测试评估任务",
            "type": "collection",
            "status": "completed",
            "created_at": "2026-03-09T10:00:00",
            "completed_at": "2026-03-09T12:00:00",
        },
        "connection": {
            "name": "测试-vCenter",
            "platform": "vmware",
        },
        "summary": {
            "total_clusters": 3,
            "total_hosts": 12,
            "total_vms": 156,
            "powered_on_vms": 142,
            "powered_off_vms": 14,
            "total_cpu_mhz": 480000,
            "total_memory_gb": 3840.0,
        },
        "resources": {
            "clusters": [
                {
                    "name": "Cluster-Production",
                    "datacenter": "DC1",
                    "total_cpu": 192000,
                    "total_memory_gb": 1536.0,
                    "num_hosts": 5,
                    "num_vms": 65,
                },
                {
                    "name": "Cluster-Development",
                    "datacenter": "DC1",
                    "total_cpu": 144000,
                    "total_memory_gb": 1152.0,
                    "num_hosts": 4,
                    "num_vms": 48,
                },
                {
                    "name": "Cluster-Testing",
                    "datacenter": "DC2",
                    "total_cpu": 144000,
                    "total_memory_gb": 1152.0,
                    "num_hosts": 3,
                    "num_vms": 43,
                },
            ],
            "hosts": [
                {
                    "name": "esxi-prod-01.example.com",
                    "datacenter": "DC1",
                    "ip_address": "10.0.1.101",
                    "cpu_cores": 24,
                    "cpu_mhz": 2400,
                    "memory_gb": 256.0,
                    "num_vms": 15,
                    "power_state": "poweredon",
                    "overall_status": "green",
                },
                {
                    "name": "esxi-prod-02.example.com",
                    "datacenter": "DC1",
                    "ip_address": "10.0.1.102",
                    "cpu_cores": 24,
                    "cpu_mhz": 2400,
                    "memory_gb": 256.0,
                    "num_vms": 18,
                    "power_state": "poweredon",
                    "overall_status": "green",
                },
                {
                    "name": "esxi-prod-03.example.com",
                    "datacenter": "DC1",
                    "ip_address": "10.0.1.103",
                    "cpu_cores": 24,
                    "cpu_mhz": 2400,
                    "memory_gb": 256.0,
                    "num_vms": 12,
                    "power_state": "poweredon",
                    "overall_status": "yellow",
                },
            ],
            "vms": [
                {
                    "name": "web-server-prod-01",
                    "datacenter": "DC1",
                    "cpu_count": 4,
                    "memory_gb": 16.0,
                    "power_state": "poweredon",
                    "guest_os": "Ubuntu Linux",
                    "ip_address": "10.0.10.51",
                    "host_ip": "10.0.1.101",
                    "connection_state": "connected",
                    "overall_status": "green",
                },
                {
                    "name": "db-server-prod-01",
                    "datacenter": "DC1",
                    "cpu_count": 8,
                    "memory_gb": 32.0,
                    "power_state": "poweredon",
                    "guest_os": "CentOS Linux",
                    "ip_address": "10.0.10.61",
                    "host_ip": "10.0.1.102",
                    "connection_state": "connected",
                    "overall_status": "green",
                },
                {
                    "name": "app-server-prod-01",
                    "datacenter": "DC1",
                    "cpu_count": 4,
                    "memory_gb": 8.0,
                    "power_state": "poweredon",
                    "guest_os": "Windows Server",
                    "ip_address": "10.0.10.71",
                    "host_ip": "10.0.1.101",
                    "connection_state": "connected",
                    "overall_status": "green",
                },
            ],
        },
        "analysis": {
            "health": {
                "overallScore": 78.5,
                "grade": "good",
                "balanceScore": 82.0,
                "overcommitScore": 75.0,
                "hotspotScore": 68.0,
                "clusterCount": 3,
                "hostCount": 12,
                "vmCount": 156,
                "avgVmDensity": 13.0,
                "findings": [
                    {
                        "severity": "medium",
                        "category": "balance",
                        "cluster": "Cluster-Production",
                        "description": "Cluster-Production 中主机间VM分布略显不均，变异系数为0.45",
                        "details": {},
                    },
                    {
                        "severity": "low",
                        "category": "overcommit",
                        "cluster": "Cluster-Development",
                        "description": "Cluster-Development 的CPU超配比为1.8，处于合理范围内",
                        "details": {},
                    },
                ],
                "recommendations": [
                    "建议对 Cluster-Production 中的VM进行轻微调度，以改善负载均衡",
                    "关注 esxi-prod-03 的资源使用情况，其整体状态为黄色",
                ],
            },
            "idle": [
                {
                    "vmId": 101,
                    "vmName": "test-server-legacy-01",
                    "cluster": "Cluster-Development",
                    "hostIp": "10.0.1.104",
                    "idleType": "powered_off",
                    "confidence": 95.0,
                    "riskLevel": "critical",
                    "daysInactive": 45,
                    "cpuUsageP95": 0.0,
                    "memoryUsageP95": 0.0,
                    "cpuCores": 4,
                    "memoryGb": 16.0,
                    "recommendation": "该虚拟机已关机45天，建议删除或归档以释放资源",
                },
                {
                    "vmId": 102,
                    "vmName": "backup-server-temp-02",
                    "cluster": "Cluster-Testing",
                    "hostIp": "10.0.1.108",
                    "idleType": "idle_powered_on",
                    "confidence": 88.0,
                    "riskLevel": "high",
                    "daysInactive": 21,
                    "cpuUsageP95": 3.2,
                    "memoryUsageP95": 12.5,
                    "cpuCores": 2,
                    "memoryGb": 8.0,
                    "recommendation": "该虚拟机CPU和内存使用率极低，建议关机或迁移到低配主机",
                },
                {
                    "vmId": 103,
                    "vmName": "dev-server-idle-03",
                    "cluster": "Cluster-Development",
                    "hostIp": "10.0.1.105",
                    "idleType": "low_activity",
                    "confidence": 72.0,
                    "riskLevel": "medium",
                    "daysInactive": 14,
                    "cpuUsageP95": 8.5,
                    "memoryUsageP95": 18.3,
                    "cpuCores": 4,
                    "memoryGb": 16.0,
                    "recommendation": "该虚拟机活跃度较低，建议检查是否仍需运行",
                },
            ],
            "resource": {
                "rightSize": [
                    {
                        "vmId": 201,
                        "vmName": "web-server-overprovisioned",
                        "cluster": "Cluster-Production",
                        "hostIp": "10.0.1.101",
                        "currentCpu": 8,
                        "suggestedCpu": 4,
                        "currentMemory": 32.0,
                        "suggestedMemory": 16.0,
                        "cpuP95": 22.5,
                        "cpuMax": 45.0,
                        "cpuAvg": 18.2,
                        "memoryP95": 35.8,
                        "memoryMax": 52.0,
                        "memoryAvg": 28.5,
                        "adjustmentType": "down_significant",
                        "riskLevel": "low",
                        "confidence": 85.0,
                        "recommendation": "建议大幅缩容至 4 vCPU / 16GB RAM，可节省50%资源",
                    },
                    {
                        "vmId": 202,
                        "vmName": "app-server-underprovisioned",
                        "cluster": "Cluster-Production",
                        "hostIp": "10.0.1.102",
                        "currentCpu": 2,
                        "suggestedCpu": 4,
                        "currentMemory": 4.0,
                        "suggestedMemory": 8.0,
                        "cpuP95": 88.5,
                        "cpuMax": 95.0,
                        "cpuAvg": 75.2,
                        "memoryP95": 92.3,
                        "memoryMax": 98.0,
                        "memoryAvg": 85.5,
                        "adjustmentType": "up",
                        "riskLevel": "high",
                        "confidence": 92.0,
                        "recommendation": "CPU和内存使用率持续偏高，建议扩容至 4 vCPU / 8GB RAM",
                    },
                    {
                        "vmId": 203,
                        "vmName": "batch-server-overallocated",
                        "cluster": "Cluster-Development",
                        "hostIp": "10.0.1.104",
                        "currentCpu": 16,
                        "suggestedCpu": 8,
                        "currentMemory": 64.0,
                        "suggestedMemory": 32.0,
                        "cpuP95": 28.3,
                        "cpuMax": 55.0,
                        "cpuAvg": 22.1,
                        "memoryP95": 32.5,
                        "memoryMax": 58.0,
                        "memoryAvg": 25.8,
                        "adjustmentType": "down",
                        "riskLevel": "low",
                        "confidence": 78.0,
                        "recommendation": "建议缩容至 8 vCPU / 32GB RAM",
                    },
                ],
                "usagePattern": [
                    {
                        "vmId": 301,
                        "vmName": "report-server-tidal",
                        "datacenter": "DC1",
                        "cluster": "Cluster-Production",
                        "hostIp": "10.0.1.101",
                        "optimizationType": "usage_pattern",
                        "usagePattern": "tidal",
                        "volatilityLevel": "high",
                        "coefficientOfVariation": 0.72,
                        "peakValleyRatio": 4.5,
                        "tidalDetails": {
                            "patternType": "day_active",
                            "dayAvg": 65.3,
                            "nightAvg": 12.8,
                            "hourlyAvg": {
                                "9": 45.2, "10": 58.5, "11": 72.3, "12": 65.8,
                                "13": 62.5, "14": 68.2, "15": 75.5, "16": 72.1,
                                "17": 55.3, "18": 42.8, "19": 28.5, "20": 18.2,
                            },
                        },
                        "recommendation": "呈现明显的潮汐模式，白天活跃夜间空闲，建议配置自动调度",
                        "details": {},
                    },
                    {
                        "vmId": 302,
                        "vmName": "batch-server-burst",
                        "datacenter": "DC1",
                        "cluster": "Cluster-Development",
                        "hostIp": "10.0.1.104",
                        "optimizationType": "usage_pattern",
                        "usagePattern": "burst",
                        "volatilityLevel": "high",
                        "coefficientOfVariation": 0.85,
                        "peakValleyRatio": 6.2,
                        "tidalDetails": None,
                        "recommendation": "呈现突发使用模式，建议配置自动扩缩容策略",
                        "details": {},
                    },
                    {
                        "vmId": 303,
                        "vmName": "core-server-stable",
                        "datacenter": "DC1",
                        "cluster": "Cluster-Production",
                        "hostIp": "10.0.1.102",
                        "optimizationType": "usage_pattern",
                        "usagePattern": "stable",
                        "volatilityLevel": "low",
                        "coefficientOfVariation": 0.15,
                        "peakValleyRatio": 1.3,
                        "tidalDetails": None,
                        "recommendation": "使用率稳定，当前配置合理",
                        "details": {},
                    },
                ],
                "mismatch": [
                    {
                        "vmId": 401,
                        "vmName": "server-cpu-rich-memory-poor",
                        "datacenter": "DC1",
                        "cluster": "Cluster-Production",
                        "hostIp": "10.0.1.101",
                        "optimizationType": "resource_mismatch",
                        "hasMismatch": True,
                        "mismatchType": "cpu_rich_memory_poor",
                        "cpuUtilization": 15.2,
                        "memoryUtilization": 82.5,
                        "currentCpu": 8,
                        "currentMemory": 16.0,
                        "recommendation": "CPU使用率低但内存使用率高，建议降低CPU配置或增加内存",
                        "details": {},
                    },
                    {
                        "vmId": 402,
                        "vmName": "server-cpu-poor-memory-rich",
                        "datacenter": "DC1",
                        "cluster": "Cluster-Development",
                        "hostIp": "10.0.1.104",
                        "optimizationType": "resource_mismatch",
                        "hasMismatch": True,
                        "mismatchType": "cpu_poor_memory_rich",
                        "cpuUtilization": 78.3,
                        "memoryUtilization": 22.8,
                        "currentCpu": 4,
                        "currentMemory": 32.0,
                        "recommendation": "CPU使用率高但内存使用率低，建议增加CPU配置或降低内存",
                        "details": {},
                    },
                    {
                        "vmId": 403,
                        "vmName": "server-both-underutilized",
                        "datacenter": "DC2",
                        "cluster": "Cluster-Testing",
                        "hostIp": "10.0.1.108",
                        "optimizationType": "resource_mismatch",
                        "hasMismatch": True,
                        "mismatchType": "both_underutilized",
                        "cpuUtilization": 18.5,
                        "memoryUtilization": 25.3,
                        "currentCpu": 8,
                        "currentMemory": 32.0,
                        "recommendation": "CPU和内存使用率都偏低，资源被过度分配",
                        "details": {},
                    },
                ],
                "summary": {
                    "rightSizeCount": 3,
                    "usagePatternCount": 3,
                    "mismatchCount": 3,
                    "totalVmsAnalyzed": 156,
                },
            },
        },
        # VM metrics time-series data for charts (vm_id -> metrics mapping)
        "vm_metrics": {
            101: {  # test-server-legacy-01 (idle)
                "cpu": _generate_time_series(base=5, variance=2, points=50),
                "memory": _generate_time_series(base=10, variance=5, points=50),
                "disk_read": _generate_time_series(base=1048576, variance=500000, points=50),  # ~1 MB/s
                "disk_write": _generate_time_series(base=524288, variance=200000, points=50),  # ~0.5 MB/s
                "net_rx": _generate_time_series(base=2097152, variance=1000000, points=50),  # ~2 MB/s
                "net_tx": _generate_time_series(base=1048576, variance=500000, points=50),  # ~1 MB/s
            },
            102: {  # backup-server-temp-02 (idle)
                "cpu": _generate_time_series(base=3, variance=1, points=50),
                "memory": _generate_time_series(base=12, variance=3, points=50),
                "disk_read": _generate_time_series(base=5242880, variance=2000000, points=50),  # ~5 MB/s
                "disk_write": _generate_time_series(base=2097152, variance=1000000, points=50),  # ~2 MB/s
                "net_rx": _generate_time_series(base=1048576, variance=500000, points=50),  # ~1 MB/s
                "net_tx": _generate_time_series(base=524288, variance=200000, points=50),  # ~0.5 MB/s
            },
            103: {  # dev-server-idle-03 (idle)
                "cpu": _generate_time_series(base=8, variance=3, points=50),
                "memory": _generate_time_series(base=18, variance=5, points=50),
                "disk_read": _generate_time_series(base=3145728, variance=1500000, points=50),  # ~3 MB/s
                "disk_write": _generate_time_series(base=1572864, variance=700000, points=50),  # ~1.5 MB/s
                "net_rx": _generate_time_series(base=3145728, variance=1500000, points=50),  # ~3 MB/s
                "net_tx": _generate_time_series(base=1048576, variance=500000, points=50),  # ~1 MB/s
            },
            201: {  # web-server-overprovisioned (right size)
                "cpu": _generate_time_series(base=22, variance=8, points=50),
                "memory": _generate_time_series(base=35, variance=10, points=50),
                "disk_read": _generate_time_series(base=10485760, variance=5000000, points=50),  # ~10 MB/s
                "disk_write": _generate_time_series(base=5242880, variance=2000000, points=50),  # ~5 MB/s
                "net_rx": _generate_time_series(base=10485760, variance=5000000, points=50),  # ~10 MB/s
                "net_tx": _generate_time_series(base=8388608, variance=3000000, points=50),  # ~8 MB/s
            },
            202: {  # app-server-underprovisioned (right size)
                "cpu": _generate_time_series(base=88, variance=10, points=50),
                "memory": _generate_time_series(base=92, variance=8, points=50),
                "disk_read": _generate_time_series(base=20971520, variance=8000000, points=50),  # ~20 MB/s
                "disk_write": _generate_time_series(base=10485760, variance=4000000, points=50),  # ~10 MB/s
                "net_rx": _generate_time_series(base=20971520, variance=8000000, points=50),  # ~20 MB/s
                "net_tx": _generate_time_series(base=15728640, variance=6000000, points=50),  # ~15 MB/s
            },
            301: {  # report-server-tidal (usage pattern - tidal)
                "cpu": _generate_time_series(base=65, variance=30, points=50),  # High variance for tidal
                "memory": _generate_time_series(base=55, variance=20, points=50),
                "disk_read": _generate_time_series(base=15728640, variance=10000000, points=50),  # ~15 MB/s
                "disk_write": _generate_time_series(base=5242880, variance=3000000, points=50),  # ~5 MB/s
                "net_rx": _generate_time_series(base=15728640, variance=10000000, points=50),  # ~15 MB/s
                "net_tx": _generate_time_series(base=10485760, variance=6000000, points=50),  # ~10 MB/s
            },
            401: {  # server-cpu-rich-memory-poor (mismatch)
                "cpu": _generate_time_series(base=15, variance=5, points=50),
                "memory": _generate_time_series(base=82, variance=10, points=50),
                "disk_read": _generate_time_series(base=5242880, variance=2000000, points=50),  # ~5 MB/s
                "disk_write": _generate_time_series(base=2097152, variance=1000000, points=50),  # ~2 MB/s
                "net_rx": _generate_time_series(base=5242880, variance=2000000, points=50),  # ~5 MB/s
                "net_tx": _generate_time_series(base=2097152, variance=1000000, points=50),  # ~2 MB/s
            },
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _generate_time_series(base: float, variance: float, points: int = 50) -> List[tuple]:
    """Generate mock time-series data for VM metrics.

    Args:
        base: Base value for the metric
        variance: Variance range (+/-)
        points: Number of data points to generate

    Returns:
        List of (timestamp, value) tuples
    """
    import random
    import time

    result = []
    now = time.time()
    interval = 86400 / points  # Distribute points over a day

    for i in range(points):
        timestamp = now - (86400 * 7) + (i * interval * 7)  # 7 days of data
        # Add some random variation
        value = max(0, base + (random.random() - 0.5) * 2 * variance)
        result.append((timestamp, value))

    return result


@pytest.mark.asyncio
async def test_pdf_report_generation_full(tmp_path):
    """Test complete PDF report generation with mock data.

    This test verifies that the PDFReportGenerator can handle
    all types of data and generate a valid PDF file.

    Args:
        tmp_path: Pytest temporary path fixture
    """
    # Import here to avoid import errors if reportlab is not installed
    from app.report.pdf import PDFReportGenerator

    # Get mock data
    data = get_mock_report_data()

    # Create output path
    output_path = tmp_path / "test_report.pdf"

    # Generate PDF
    generator = PDFReportGenerator()
    result_path = generator.generate(data, str(output_path))

    # Verify PDF file was created
    assert Path(result_path).exists()
    assert Path(result_path).stat().st_size > 0

    # Verify file extension
    assert result_path.endswith(".pdf")

    # Verify file is reasonably sized (should be > 10KB for a report with charts)
    file_size = Path(result_path).stat().st_size
    assert file_size > 10000, f"PDF file too small: {file_size} bytes"


@pytest.mark.asyncio
async def test_pdf_report_generation_minimal(tmp_path):
    """Test PDF report generation with minimal data.

    This test verifies edge cases like empty analysis results.

    Args:
        tmp_path: Pytest temporary path fixture
    """
    from app.report.pdf import PDFReportGenerator

    # Minimal data with empty analysis results
    data = {
        "task": {
            "id": 1,
            "name": "最小测试任务",
            "type": "collection",
            "status": "completed",
            "created_at": "2026-03-09T10:00:00",
            "completed_at": "2026-03-09T12:00:00",
        },
        "connection": {
            "name": "测试平台",
            "platform": "vmware",
        },
        "summary": {
            "total_clusters": 0,
            "total_hosts": 0,
            "total_vms": 0,
            "powered_on_vms": 0,
            "powered_off_vms": 0,
            "total_cpu_mhz": 0,
            "total_memory_gb": 0.0,
        },
        "resources": {
            "clusters": [],
            "hosts": [],
            "vms": [],
        },
        "analysis": {
            "health": None,
            "idle": [],
            "resource": {
                "rightSize": [],
                "usagePattern": [],
                "mismatch": [],
            },
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    output_path = tmp_path / "test_minimal_report.pdf"

    generator = PDFReportGenerator()
    result_path = generator.generate(data, str(output_path))

    assert Path(result_path).exists()
    assert Path(result_path).stat().st_size > 0


@pytest.mark.asyncio
async def test_pdf_report_with_custom_logo(tmp_path):
    """Test PDF generation with custom logo path.

    Args:
        tmp_path: Pytest temporary path fixture
    """
    from app.report.pdf import PDFReportGenerator

    data = get_mock_report_data()
    output_path = tmp_path / "test_with_logo.pdf"

    # Use the actual logo from assets
    logo_path = Path(__file__).parent.parent.parent.parent / "backend" / "app" / "report" / "assets" / "logo.png"

    generator = PDFReportGenerator(logo_path=str(logo_path) if logo_path.exists() else None)
    result_path = generator.generate(data, str(output_path))

    assert Path(result_path).exists()
    assert Path(result_path).stat().st_size > 0


@pytest.mark.asyncio
async def test_report_builder_summaries(tmp_path):
    """Test ReportBuilder summary methods.

    This verifies that the summary methods in ReportBuilder
    work correctly with mock data.

    Args:
        tmp_path: Pytest temporary path fixture
    """
    from app.report.builder import ReportBuilder

    # Create mock builder (no real DB needed for summaries)
    builder = ReportBuilder(None)

    # Test idle summary
    idle_data = get_mock_report_data()["analysis"]["idle"]
    idle_summary = builder.build_idle_summary(idle_data)

    assert idle_summary["total"] == 3
    assert idle_summary["by_type"]["powered_off"] == 1
    assert idle_summary["by_type"]["idle_powered_on"] == 1
    assert idle_summary["by_type"]["low_activity"] == 1
    assert idle_summary["potential_savings"]["cpu_cores"] == 10
    assert idle_summary["potential_savings"]["memory_gb"] == 40.0

    # Test resource summary
    resource_data = get_mock_report_data()["analysis"]["resource"]
    resource_summary = builder.build_resource_summary(resource_data)

    assert resource_summary["right_size"]["total"] == 3
    assert resource_summary["right_size"]["downsize_candidates"] == 2
    assert resource_summary["right_size"]["upsize_candidates"] == 1
    assert resource_summary["usage_pattern"]["total"] == 3
    assert resource_summary["mismatch"]["total"] == 3

    # Test health summary
    health_data = get_mock_report_data()["analysis"]["health"]
    health_summary = builder.build_health_summary(health_data)

    assert health_summary["overall_score"] == 78.5
    assert health_summary["grade"] == "good"
    assert health_summary["grade_text"] == "良好"

    # Test savings estimate
    savings = builder.build_savings_estimate(idle_data, resource_data)

    # Calculate expected values from mock data
    # Idle: 4 + 2 + 4 = 10 CPU cores, 16 + 8 + 16 = 40 GB memory
    expected_idle_cpu = sum(item.get("cpuCores", 0) for item in idle_data)
    expected_idle_mem = sum(item.get("memoryGb", 0) for item in idle_data)

    # Right Size: total_current - total_suggested (may be reduced by upsizing VMs)
    # current: 8 + 2 + 16 = 26, suggested: 4 + 4 + 8 = 16, diff = 10
    # current_mem: 32 + 4 + 64 = 100, suggested_mem: 16 + 8 + 32 = 56, diff = 44
    right_size = resource_data.get("rightSize", [])
    current_cpu = sum(r.get("currentCpu", 0) for r in right_size)
    suggested_cpu = sum(r.get("suggestedCpu", 0) for r in right_size)
    current_memory = sum(r.get("currentMemory", 0) for r in right_size)
    suggested_memory = sum(r.get("suggestedMemory", 0) for r in right_size)
    expected_rightsize_cpu = max(0, current_cpu - suggested_cpu)
    expected_rightsize_mem = max(0, current_memory - suggested_memory)

    assert savings["total_cpu_savings"] == expected_idle_cpu + expected_rightsize_cpu
    assert savings["total_memory_savings_gb"] == expected_idle_mem + expected_rightsize_mem


@pytest.mark.asyncio
async def test_charts_drawing(tmp_path):
    """Test chart drawing functionality.

    Args:
        tmp_path: Pytest temporary path fixture
    """
    from app.report.charts import PDFCharts
    from reportlab.graphics import renderPDF

    charts = PDFCharts()

    # Test gauge chart
    gauge = charts.draw_gauge_chart(78.5, "测试仪表盘")
    assert gauge is not None
    assert gauge.width == 10 * cm

    # Test bar chart
    bar = charts.draw_bar_chart([3, 12, 156], ["集群", "主机", "VM"], "测试柱状图")
    assert bar is not None

    # Test pie chart
    pie = charts.draw_pie_chart([1, 1, 1], ["关机", "开机闲置", "低活跃"], "测试饼图")
    assert pie is not None

    # Test comparison chart
    comp = charts.draw_comparison_chart([8, 2, 16], [4, 4, 8], ["VM1", "VM2", "VM3"])
    assert comp is not None

    # Test radar chart
    radar = charts.draw_radar_chart([75, 82, 68], ["超配", "均衡", "热点"], "测试雷达图")
    assert radar is not None

    # Test horizontal bar chart
    hbar = charts.draw_horizontal_bar_chart([("A", 10), ("B", 20)], "测试横向柱状图")
    assert hbar is not None

    # Test saving charts to file
    chart_output = tmp_path / "test_chart.pdf"
    with open(chart_output, "wb") as f:
        renderPDF.drawToFile(gauge, str(chart_output))
    assert chart_output.exists()


@pytest.mark.asyncio
async def test_empty_data_handling(tmp_path):
    """Test handling of empty/None data in charts.

    Args:
        tmp_path: Pytest temporary path fixture
    """
    from app.report.charts import PDFCharts

    charts = PDFCharts()

    # Test bar chart with empty data
    bar = charts.draw_bar_chart([], [], "空数据柱状图")
    assert bar is not None

    # Test pie chart with empty data
    pie = charts.draw_pie_chart([], [], "空数据饼图")
    assert pie is not None

    # Test radar chart with empty data
    radar = charts.draw_radar_chart([], [], "空数据雷达图")
    assert radar is not None


if __name__ == "__main__":
    """Run tests directly for development."""
    import asyncio
    from tempfile import TemporaryDirectory

    async def run_tests():
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            print("Testing full PDF generation...")
            await test_pdf_report_generation_full(tmp_path)
            print("✓ Full PDF generation test passed")

            print("Testing minimal PDF generation...")
            await test_pdf_report_generation_minimal(tmp_path)
            print("✓ Minimal PDF generation test passed")

            print("Testing with custom logo...")
            await test_pdf_report_with_custom_logo(tmp_path)
            print("✓ Custom logo test passed")

            print("Testing report builder summaries...")
            await test_report_builder_summaries(tmp_path)
            print("✓ Report builder summaries test passed")

            print("Testing charts drawing...")
            await test_charts_drawing(tmp_path)
            print("✓ Charts drawing test passed")

            print("Testing empty data handling...")
            await test_empty_data_handling(tmp_path)
            print("✓ Empty data handling test passed")

            print("\nAll tests passed! ✓")
            print(f"Test PDFs saved to: {tmp_path}")

    asyncio.run(run_tests())
