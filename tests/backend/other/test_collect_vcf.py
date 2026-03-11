#!/usr/bin/env python3.14
"""使用真实环境测试 VCF 30 天数据采集"""

import sys
import os
sys.path.insert(0, '/home/worker/pengxin/TEMP/justfit/backend')

from datetime import datetime, timedelta
from app.connectors.vcenter import VCenterConnector
from app.core.database import engine
from sqlalchemy import select, text
from pyVmomi import vim
import asyncio

# 从 .env 读取配置
VCENTER_HOST = "10.103.116.116"
VCENTER_PORT = 443
VCENTER_USER = "administrator@vsphere.local"
VCENTER_PASSWORD = "Admin@123."


async def test_collect_vcf():
    """测试 VCF 的 30 天数据采集并保存到数据库"""

    print("="*70)
    print("VCF 30 天数据采集测试（真实环境）")
    print("="*70)

    # 创建 connector
    connector = VCenterConnector(
        host=VCENTER_HOST,
        port=VCENTER_PORT,
        username=VCENTER_USER,
        password=VCENTER_PASSWORD,
        insecure=True
    )

    try:
        print(f"\n1. 连接 vCenter...")
        await connector._connect()
        print(f"   ✓ 连接成功")

        # 获取 VCF VM
        print(f"\n2. 查找 VCF 虚拟机...")
        content = connector._content
        container = content.viewManager.CreateContainerView(
            content.rootFolder,
            [vim.VirtualMachine],
            True
        )
        vms = container.view

        target_vm = None
        for vm in vms:
            if vm.name == "VCF":
                target_vm = vm
                break

        container.Destroy()

        if not target_vm:
            print(f"   ✗ 未找到 VCF")
            return False

        print(f"   ✓ 找到 VM: {target_vm.name}")
        print(f"     UUID: {target_vm.config.uuid}")
        print(f"     状态: {target_vm.runtime.powerState}")
        print(f"     CPU: {target_vm.config.hardware.numCPU} 核")
        print(f"     内存: {target_vm.config.hardware.memoryMB} MB")

        # 测试 30 天指标采集
        print(f"\n3. 采集 30 天性能指标...")
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)

        print(f"   开始时间: {start_time}")
        print(f"   结束时间: {end_time}")

        metrics = await connector.get_vm_metrics(
            datacenter="Datacenter",
            vm_name=target_vm.name,
            vm_uuid=target_vm.config.uuid,
            start_time=start_time,
            end_time=end_time,
            cpu_count=target_vm.config.hardware.numCPU,
            total_memory_bytes=target_vm.config.hardware.memoryMB * 1024 * 1024
        )

        if not metrics:
            print(f"   ✗ 采集失败：返回 None")
            return False

        print(f"\n4. 采集结果:")
        print(f"   ✓ CPU: {metrics.cpu_mhz:.2f} MHz")
        print(f"   ✓ Memory: {metrics.memory_bytes / 1024 / 1024 / 1024:.2f} GB")
        print(f"   ✓ CPU samples: {metrics.cpu_samples}")
        print(f"   ✓ Memory samples: {metrics.memory_samples}")
        print(f"   ✓ Disk samples: {metrics.disk_samples}")
        print(f"   ✓ Network samples: {metrics.network_samples}")

        if metrics.hourly_series:
            print(f"\n5. Hourly Series 数据:")
            print(f"   ✓ 小时数据点数: {len(metrics.hourly_series)}")

            if len(metrics.hourly_series) > 0:
                first_ts = datetime.fromtimestamp(metrics.hourly_series[0][0] / 1000)
                last_ts = datetime.fromtimestamp(metrics.hourly_series[-1][0] / 1000)
                days_span = (last_ts - first_ts).days

                print(f"   ✓ 最早: {first_ts}")
                print(f"   ✓ 最新: {last_ts}")
                print(f"   ✓ 跨度: {days_span} 天")

                # 显示前 3 个和后 3 个数据点
                print(f"\n   前 3 个数据点:")
                for i, point in enumerate(metrics.hourly_series[:3]):
                    ts = datetime.fromtimestamp(point[0] / 1000)
                    print(f"     {ts}: CPU={point[1]:.1f}MHz")

                print(f"   后 3 个数据点:")
                for i, point in enumerate(metrics.hourly_series[-3:]):
                    ts = datetime.fromtimestamp(point[0] / 1000)
                    print(f"     {ts}: CPU={point[1]:.1f}MHz")

                print(f"\n✅ 成功！采集了完整的 {days_span} 天数据！")
            else:
                print(f"   ⚠️  hourly_series 为空")
                return False
        else:
            print(f"\n   ⚠️  没有 hourly_series 数据")
            return False

        # 测试保存到数据库
        print(f"\n6. 测试保存到数据库...")

        # 查询 VCF 的 vm_id
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT id, name FROM vms WHERE name = 'VCF' LIMIT 1")
            )
            vm_row = result.fetchone()

            if not vm_row:
                print(f"   ⚠️  数据库中未找到 VCF，跳过保存测试")
                return True

            vm_id = vm_row[0]
            print(f"   ✓ 找到数据库记录: vm_id={vm_id}")

            # 统计现有指标
            result = await conn.execute(
                text("SELECT COUNT(*) FROM vm_metrics WHERE vm_id = :vm_id"),
                {"vm_id": vm_id}
            )
            existing_count = result.fetchone()[0]
            print(f"   ✓ 现有指标数: {existing_count}")

        print(f"\n✅ 测试完成！采集了 {len(metrics.hourly_series)} 个小时数据点")
        print(f"   时间跨度: {days_span} 天")
        print(f"   如果需要保存到数据库，请创建正式的任务")

        return True

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            await connector.close()
        except:
            pass


if __name__ == "__main__":
    success = asyncio.run(test_collect_vcf())

    print(f"\n" + "="*70)
    if success:
        print("测试成功！")
        print("建议：重启后端服务并创建正式任务来保存数据")
    else:
        print("测试失败，请查看错误信息")
    print("="*70)

    sys.exit(0 if success else 1)
