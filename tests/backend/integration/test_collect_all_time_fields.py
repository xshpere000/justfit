"""采集测试平台所有虚拟机的时间字段数据。

运行: PYTHONPATH=backend pytest tests/backend/integration/test_collect_all_time_fields.py -v -s
"""

import asyncio
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import pytest

# vCenter
from app.connectors.vcenter import VCenterConnector

# UIS
from app.connectors.uis import UISConnector

load_dotenv()


def format_duration(seconds):
    """格式化时长为可读格式"""
    if seconds is None:
        return "N/A"

    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60

    if days > 0:
        return f"{days}天{hours}小时"
    elif hours > 0:
        return f"{hours}小时{minutes}分钟"
    else:
        return f"{minutes}分钟"


def format_datetime(dt):
    """格式化datetime为可读格式"""
    if dt is None:
        return "N/A"
    return dt.strftime('%Y-%m-%d %H:%M:%S')


@pytest.fixture
async def vcenter_connector():
    """Create vCenter connector."""
    host = os.getenv("VCENTER_IP", "10.103.116.116")
    username = os.getenv("VCENTER_USER_NAME", "administrator@vsphere.local")
    password = os.getenv("VCENTER_PASSWD", "Admin@123.")

    conn = VCenterConnector(
        host=host,
        port=443,
        username=username,
        password=password,
        insecure=True,
    )
    yield conn
    await conn.close()


@pytest.fixture
async def uis_connector():
    """Create UIS connector."""
    host = os.getenv("UIS_IP", "10.103.115.8")
    username = os.getenv("UIS_USER_NAME", "admin")
    password = os.getenv("UIS_PASSWD", "Admin@123.")

    conn = UISConnector(
        host=host,
        port=443,
        username=username,
        password=password,
        insecure=True,
    )
    yield conn
    await conn.close()


@pytest.mark.asyncio
async def test_collect_vcenter_all_vms(vcenter_connector: VCenterConnector):
    """采集 vCenter 所有虚拟机的时间字段"""
    vms = await vcenter_connector.get_vms()

    print(f"\n{'='*100}")
    print(f"vCenter 平台 - 所有虚拟机时间字段采集 (共 {len(vms)} 个VM)")
    print(f"{'='*100}\n")

    print(f"{'序号':<5} {'VM名称':<30} {'电源状态':<12} {'创建时间':<20} {'开机时长':<15} {'关机时长':<15}")
    print(f"{'-'*100}")

    for i, vm in enumerate(vms, 1):
        power_state = vm.power_state or "N/A"
        create_time = format_datetime(vm.vm_create_time)
        uptime = format_duration(vm.uptime_duration)
        downtime = format_duration(vm.downtime_duration)

        print(f"{i:<5} {vm.name:<30} {power_state:<12} {create_time:<20} {uptime:<15} {downtime:<15}")

    # 统计信息
    print(f"\n{'='*100}")
    print(f"统计信息:")
    print(f"{'='*100}")

    powered_on = [vm for vm in vms if vm.power_state and vm.power_state.lower() in ["poweredon", "powered on"]]
    powered_off = [vm for vm in vms if vm.power_state and vm.power_state.lower() in ["poweredoff", "powered off"]]

    print(f"开机VM: {len(powered_on)} 个")
    print(f"关机VM: {len(powered_off)} 个")

    create_time_count = sum(1 for vm in vms if vm.vm_create_time is not None)
    uptime_count = sum(1 for vm in vms if vm.uptime_duration is not None)
    downtime_count = sum(1 for vm in vms if vm.downtime_duration is not None)

    print(f"\n字段覆盖率:")
    print(f"  vm_create_time: {create_time_count}/{len(vms)} ({create_time_count*100//len(vms)}%)")
    print(f"  uptime_duration: {uptime_count}/{len(vms)} ({uptime_count*100//len(vms)}%)")
    print(f"  downtime_duration: {downtime_count}/{len(vms)} ({downtime_count*100//len(vms)}%)")


@pytest.mark.asyncio
async def test_collect_uis_all_vms(uis_connector: UISConnector):
    """采集 UIS 所有虚拟机的时间字段"""
    vms = await uis_connector.get_vms()

    print(f"\n{'='*100}")
    print(f"UIS 平台 - 所有虚拟机时间字段采集 (共 {len(vms)} 个VM)")
    print(f"{'='*100}\n")

    print(f"{'序号':<5} {'VM名称':<30} {'电源状态':<12} {'创建时间':<20} {'开机时长':<15} {'关机时长':<15}")
    print(f"{'-'*100}")

    for i, vm in enumerate(vms, 1):
        power_state = vm.power_state or "N/A"
        create_time = format_datetime(vm.vm_create_time)
        uptime = format_duration(vm.uptime_duration)
        downtime = format_duration(vm.downtime_duration)

        print(f"{i:<5} {vm.name:<30} {power_state:<12} {create_time:<20} {uptime:<15} {downtime:<15}")

    # 统计信息
    print(f"\n{'='*100}")
    print(f"统计信息:")
    print(f"{'='*100}")

    powered_on = [vm for vm in vms if vm.power_state == "poweredon"]
    powered_off = [vm for vm in vms if vm.power_state == "poweredoff"]

    print(f"开机VM: {len(powered_on)} 个")
    print(f"关机VM: {len(powered_off)} 个")

    create_time_count = sum(1 for vm in vms if vm.vm_create_time is not None)
    uptime_count = sum(1 for vm in vms if vm.uptime_duration is not None)
    downtime_count = sum(1 for vm in vms if vm.downtime_duration is not None)

    print(f"\n字段覆盖率:")
    print(f"  vm_create_time: {create_time_count}/{len(vms)} ({create_time_count*100//len(vms)}%)")
    print(f"  uptime_duration: {uptime_count}/{len(vms)} ({uptime_count*100//len(vms)}%)")
    print(f"  downtime_duration: {downtime_count}/{len(vms)} ({downtime_count*100//len(vms)}%)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
