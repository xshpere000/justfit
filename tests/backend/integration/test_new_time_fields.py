"""测试新的时间字段数据模型。

运行: PYTHONPATH=backend pytest tests/backend/integration/test_new_time_fields.py -v -s
"""

import asyncio
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import pytest

# vCenter
from app.connectors.vcenter import VCenterConnector

# UIS
from app.connectors.uis import UISConnector

load_dotenv()


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
async def test_vcenter_new_time_fields(vcenter_connector: VCenterConnector):
    """测试 vCenter 新的时间字段"""
    vms = await vcenter_connector.get_vms()

    print(f"\n{'='*60}")
    print(f"vCenter 新时间字段测试 (VM总数: {len(vms)})")
    print(f"{'='*60}\n")

    # 分类统计
    powered_on = [vm for vm in vms if vm.power_state and vm.power_state.lower() in ["poweredon", "powered on"]]
    powered_off = [vm for vm in vms if vm.power_state and vm.power_state.lower() in ["poweredoff", "powered off"]]

    print(f"开机VM: {len(powered_on)}")
    print(f"关机VM: {len(powered_off)}\n")

    # 检查开机VM的字段
    if powered_on:
        print(f"开机VM示例 (前3个):")
        for vm in powered_on[:3]:
            print(f"\n  VM: {vm.name}")
            print(f"    vm_create_time: {vm.vm_create_time}")
            print(f"    uptime_duration: {vm.uptime_duration} 秒")

            if vm.uptime_duration:
                # 转换为可读格式
                hours = vm.uptime_duration // 3600
                minutes = (vm.uptime_duration % 3600) // 60
                print(f"    ⏱️ 开机时长: {hours}小时 {minutes}分钟")

            if vm.downtime_duration:
                print(f"    ⚠️ 开机VM不应该有 downtime_duration")

    # 检查关机VM的字段
    if powered_off:
        print(f"\n关机VM示例 (前3个):")
        for vm in powered_off[:3]:
            print(f"\n  VM: {vm.name}")
            print(f"    vm_create_time: {vm.vm_create_time}")
            print(f"    downtime_duration: {vm.downtime_duration} 秒")

            if vm.downtime_duration:
                # 转换为可读格式
                days = vm.downtime_duration // 86400
                hours = (vm.downtime_duration % 86400) // 3600
                print(f"    ⏱️ 关机时长: {days}天 {hours}小时")

            if vm.uptime_duration:
                print(f"    ⚠️ 关机VM不应该有 uptime_duration")

    # 统计覆盖率
    create_time_count = sum(1 for vm in vms if vm.vm_create_time is not None)
    uptime_count = sum(1 for vm in vms if vm.uptime_duration is not None)
    downtime_count = sum(1 for vm in vms if vm.downtime_duration is not None)

    print(f"\n{'='*60}")
    print(f"覆盖率统计:")
    print(f"  vm_create_time: {create_time_count}/{len(vms)} ({create_time_count*100//len(vms)}%)")
    print(f"  uptime_duration: {uptime_count}/{len(vms)} ({uptime_count*100//len(vms)}%)")
    print(f"  downtime_duration: {downtime_count}/{len(vms)} ({downtime_count*100//len(vms)}%)")
    print(f"{'='*60}\n")

    # 验证：开机VM不应该有 downtime_duration
    for vm in powered_on:
        assert vm.downtime_duration is None, f"开机VM {vm.name} 不应该有 downtime_duration"

    # 验证：关机VM不应该有 uptime_duration
    for vm in powered_off:
        assert vm.uptime_duration is None, f"关机VM {vm.name} 不应该有 uptime_duration"


@pytest.mark.asyncio
async def test_uis_new_time_fields(uis_connector: UISConnector):
    """测试 UIS 新的时间字段"""
    vms = await uis_connector.get_vms()

    print(f"\n{'='*60}")
    print(f"UIS 新时间字段测试 (VM总数: {len(vms)})")
    print(f"{'='*60}\n")

    # 分类统计
    powered_on = [vm for vm in vms if vm.power_state == "poweredon"]
    powered_off = [vm for vm in vms if vm.power_state == "poweredoff"]

    print(f"开机VM: {len(powered_on)}")
    print(f"关机VM: {len(powered_off)}\n")

    # 检查开机VM的字段
    if powered_on:
        print(f"开机VM示例 (前3个):")
        for vm in powered_on[:3]:
            print(f"\n  VM: {vm.name}")
            print(f"    vm_create_time: {vm.vm_create_time}")
            print(f"    uptime_duration: {vm.uptime_duration} 秒")

            if vm.uptime_duration:
                # 转换为可读格式
                hours = vm.uptime_duration // 3600
                minutes = (vm.uptime_duration % 3600) // 60
                print(f"    ⏱️ 开机时长: {hours}小时 {minutes}分钟")

    # 检查关机VM的字段
    if powered_off:
        print(f"\n关机VM示例:")
        for vm in powered_off[:3]:
            print(f"\n  VM: {vm.name}")
            print(f"    vm_create_time: {vm.vm_create_time}")
            print(f"    downtime_duration: {vm.downtime_duration} 秒")

            if vm.downtime_duration:
                # 转换为可读格式
                days = vm.downtime_duration // 86400
                hours = (vm.downtime_duration % 86400) // 3600
                print(f"    ⏱️ 关机时长: {days}天 {hours}小时")

    # 统计覆盖率
    create_time_count = sum(1 for vm in vms if vm.vm_create_time is not None)
    uptime_count = sum(1 for vm in vms if vm.uptime_duration is not None)
    downtime_count = sum(1 for vm in vms if vm.downtime_duration is not None)

    print(f"\n{'='*60}")
    print(f"覆盖率统计:")
    print(f"  vm_create_time: {create_time_count}/{len(vms)} ({create_time_count*100//len(vms)}%)")
    print(f"  uptime_duration: {uptime_count}/{len(vms)} ({uptime_count*100//len(vms)}%)")
    print(f"  downtime_duration: {downtime_count}/{len(vms)} ({downtime_count*100//len(vms)}%)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
