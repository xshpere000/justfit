#!/usr/bin/env python3.14
"""测试修复后的 vCenter connector 能否正确采集 VCF 指标"""

import sys
sys.path.insert(0, '/home/worker/pengxin/TEMP/justfit/backend')

from datetime import datetime, timedelta
from app.connectors.vcenter import VCenterConnector

async def test_vcf_collection():
    """测试 VCF 的指标采集"""

    print("="*70)
    print("测试 VCF 指标采集（修复后的代码）")
    print("="*70)

    # 创建 connector
    connector = VCenterConnector(
        host="10.103.116.116",
        port=443,
        username="administrator@vsphere.local",
        password="Admin@123.",
        insecure=True
    )

    try:
        # 测试 30 天指标采集（不需要先获取 VM，直接用参数）
        print(f"\n测试 30 天指标采集...")
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)

        # 使用实际的 VM 信息
        metrics = await connector.get_vm_metrics(
            datacenter="Datacenter",
            vm_name="VCF",
            vm_uuid="564d784a-fbe8-7d9c-1b7c-e89321f4388b",
            start_time=start_time,
            end_time=end_time,
            cpu_count=4,
            total_memory_bytes=8 * 1024 * 1024 * 1024
        )

        if metrics:
            print(f"✓ 成功采集指标!")
            print(f"  CPU: {metrics.cpu_mhz:.2f} MHz")
            print(f"  Memory: {metrics.memory_bytes / 1024 / 1024 / 1024:.2f} GB")
            print(f"  CPU samples: {metrics.cpu_samples}")
            print(f"  Memory samples: {metrics.memory_samples}")

            if metrics.hourly_series:
                print(f"\n✓ Hourly series 数据:")
                print(f"  小时数据点数: {len(metrics.hourly_series)}")
                if len(metrics.hourly_series) > 0:
                    print(f"  最早: {datetime.fromtimestamp(metrics.hourly_series[0][0] / 1000)}")
                    print(f"  最新: {datetime.fromtimestamp(metrics.hourly_series[-1][0] / 1000)}")

                    # 显示前 3 个数据点
                    print(f"\n  前 3 个数据点示例:")
                    for i, point in enumerate(metrics.hourly_series[:3]):
                        ts = datetime.fromtimestamp(point[0] / 1000)
                        print(f"    {ts}: CPU={point[1]:.1f}MHz, Mem={point[4]/1024/1024/1024:.2f}GB")
            else:
                print(f"\n⚠️ 没有 hourly_series 数据")

            return True
        else:
            print(f"✗ 返回 None")
            return False

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            await connector.close()
        except:
            pass

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(test_vcf_collection())
    sys.exit(0 if success else 1)
