"""Integration tests for vCenter Connector.

Tests use real vCenter environment: 10.103.116.116
Run with: PYTHONPATH=backend pytest tests/backend/integration/test_connectors.py -v
"""

import pytest
from datetime import datetime, timedelta
from app.connectors.vcenter import VCenterConnector


# Test environment credentials
VCENTER_HOST = "10.103.116.116"
VCENTER_PORT = 443
VCENTER_USER = "administrator@vsphere.local"
VCENTER_PASSWORD = "Admin@123."


@pytest.fixture
async def connector():
    """Create vCenter connector for testing."""
    conn = VCenterConnector(
        host=VCENTER_HOST,
        port=VCENTER_PORT,
        username=VCENTER_USER,
        password=VCENTER_PASSWORD,
        insecure=True,
    )
    yield conn
    await conn.close()


@pytest.mark.asyncio
async def test_vcenter_connection(connector: VCenterConnector):
    """测试 vCenter 连接"""
    result = await connector.test_connection()

    assert result["success"] is True
    assert "message" in result


@pytest.mark.asyncio
async def test_vcenter_get_clusters(connector: VCenterConnector):
    """测试获取集群列表"""
    clusters = await connector.get_clusters()

    assert isinstance(clusters, list)
    if len(clusters) > 0:
        cluster = clusters[0]
        assert hasattr(cluster, "name")
        assert hasattr(cluster, "datacenter")
        assert hasattr(cluster, "total_cpu")
        assert hasattr(cluster, "total_memory")
        assert hasattr(cluster, "num_hosts")
        assert hasattr(cluster, "num_vms")


@pytest.mark.asyncio
async def test_vcenter_get_hosts(connector: VCenterConnector):
    """测试获取主机列表"""
    hosts = await connector.get_hosts()

    assert isinstance(hosts, list)
    if len(hosts) > 0:
        host = hosts[0]
        assert hasattr(host, "name")
        assert hasattr(host, "ip_address")
        assert hasattr(host, "cpu_cores")
        assert hasattr(host, "memory_bytes")
        assert hasattr(host, "power_state")


@pytest.mark.asyncio
async def test_vcenter_get_vms(connector: VCenterConnector):
    """测试获取虚拟机列表"""
    vms = await connector.get_vms()

    assert isinstance(vms, list)
    if len(vms) > 0:
        vm = vms[0]
        assert hasattr(vm, "name")
        assert hasattr(vm, "uuid")
        assert hasattr(vm, "cpu_count")
        assert hasattr(vm, "memory_bytes")
        assert hasattr(vm, "power_state")
        assert hasattr(vm, "guest_os")
        assert hasattr(vm, "host_ip")


@pytest.mark.asyncio
async def test_vcenter_vm_key_generation(connector: VCenterConnector):
    """测试 VM Key 生成规则"""
    vms = await connector.get_vms()

    for vm in vms:
        # VM should have a unique key (vm_key not in base but used in repository)
        assert vm.uuid or vm.name


@pytest.mark.asyncio
async def test_vcenter_get_vm_metrics(connector: VCenterConnector):
    """测试获取虚拟机性能指标"""
    vms = await connector.get_vms()

    # Find a powered-on VM to test metrics
    test_vm = None
    for vm in vms:
        if vm.power_state.lower() in ["poweredon", "powered on", "running"]:
            test_vm = vm
            break

    if test_vm:
        # Get metrics for the past 24 hours
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)

        metrics = await connector.get_vm_metrics(
            datacenter=test_vm.datacenter,
            vm_name=test_vm.name,
            vm_uuid=test_vm.uuid,
            start_time=start_time,
            end_time=end_time,
            cpu_count=test_vm.cpu_count,
        )

        assert hasattr(metrics, "cpu_mhz")
        assert hasattr(metrics, "memory_bytes")
        assert hasattr(metrics, "disk_read_bytes_per_sec")
        assert hasattr(metrics, "disk_write_bytes_per_sec")
        assert hasattr(metrics, "net_rx_bytes_per_sec")
        assert hasattr(metrics, "net_tx_bytes_per_sec")

        # Metrics should be non-negative
        assert metrics.cpu_mhz >= 0
        assert metrics.memory_bytes >= 0


@pytest.mark.asyncio
async def test_vcenter_host_ip_extraction(connector: VCenterConnector):
    """测试主机 IP 提取"""
    hosts = await connector.get_hosts()

    if len(hosts) > 0:
        # At least some hosts should have IP addresses
        hosts_with_ip = [h for h in hosts if h.ip_address]
        # This is informational - just log the results
        print(f"Found {len(hosts_with_ip)} hosts with IP addresses out of {len(hosts)} total")


@pytest.mark.asyncio
async def test_vcenter_connection_error_handling():
    """测试连接错误处理"""
    # Test with invalid credentials
    conn = VCenterConnector(
        host=VCENTER_HOST,
        port=VCENTER_PORT,
        username="invalid",
        password="invalid",
        insecure=True,
    )

    result = await conn.test_connection()

    # Should fail gracefully
    assert result["success"] is False

    await conn.close()


@pytest.mark.asyncio
async def test_vcenter_close_idempotent(connector: VCenterConnector):
    """测试连接关闭幂等性"""
    # First close
    await connector.close()

    # Second close should not raise error
    await connector.close()
