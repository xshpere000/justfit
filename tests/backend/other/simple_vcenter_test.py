#!/usr/bin/env python3.14
"""简化的 vCenter 指标采集调试脚本

请提供你的采集示例，我会对比差异。
"""

from datetime import datetime, timedelta
from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
import ssl

VCENTER_HOST = "10.103.116.116"
VCENTER_USER = "administrator@vsphere.local"
VCENTER_PASSWORD = "Admin@123."


def main():
    print("连接 vCenter...")
    si = SmartConnect(
        host=VCENTER_HOST,
        user=VCENTER_USER,
        pwd=VCENTER_PASSWORD,
        port=443,
        sslContext=ssl._create_unverified_context()
    )

    content = si.RetrieveContent()
    perf_mgr = content.perfManager

    # 获取所有 counters
    print("\n可用的 counters (前 30 个):")
    counters = perf_mgr.perfCounter
    for c in counters[:30]:
        print(f"  Key={c.key}: {c.groupInfo.label}.{c.nameInfo.label}.{c.rollupType}")

    # 获取一个 VM
    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True
    )
    vms = container.view
    test_vm = vms[0]
    print(f"\n测试 VM: {test_vm.name}")

    # 检查可用的历史数据
    print("\n检查可用历史数据...")
    provider_summary = perf_mgr.QueryPerfProviderSummary(entity=test_vm)
    print(f"  实时间隔: {provider_summary.refreshRate} 秒")

    # 测试不同的查询方式
    print("\n" + "="*60)
    print("测试 1: 不指定时间范围，只指定 maxSample")
    print("="*60)

    # 先找一个 counter
    cpu_counter = None
    for c in counters:
        if 'cpu' in c.nameInfo.label.lower() and 'usage' in c.nameInfo.label.lower():
            cpu_counter = c
            break

    if not cpu_counter:
        # 尝试 VCPU Usage
        for c in counters:
            if c.key == 657:  # VCPU Usage
                cpu_counter = c
                break

    if cpu_counter:
        print(f"使用 counter: {cpu_counter.groupInfo.label}.{cpu_counter.nameInfo.label}.{cpu_counter.rollupType} (key={cpu_counter.key})")

        metric_id = vim.PerformanceManager.MetricId(
            counterId=cpu_counter.key,
            instance=""
        )

        spec = vim.PerformanceManager.QuerySpec(
            entity=test_vm,
            metricId=[metric_id],
            maxSample=100
        )

        try:
            results = perf_mgr.QueryStats(querySpec=[spec])
            if results and results[0]:
                print(f"  ✓ 返回了数据")
                print(f"  样本数: {len(results[0].sampleInfo) if results[0].sampleInfo else 0}")

                if results[0].sampleInfo and len(results[0].sampleInfo) > 0:
                    print(f"  最新样本时间: {results[0].sampleInfo[-1].timestamp}")
                    if len(results[0].sampleInfo) > 1:
                        print(f"  最老样本时间: {results[0].sampleInfo[0].timestamp}")
                        time_span = results[0].sampleInfo[-1].timestamp - results[0].sampleInfo[0].timestamp
                        print(f"  数据跨度: {time_span.days} 天 {time_span.seconds // 3600} 小时")

                for stat in results[0].value:
                    print(f"  值的数量: {len(stat.value) if stat.value else 0}")
                    if stat.value and len(stat.value) > 0:
                        print(f"  前 5 个值: {stat.value[:5]}")
            else:
                print(f"  ✗ 没有返回数据")
        except Exception as e:
            print(f"  ✗ 错误: {e}")

    print("\n" + "="*60)
    print("测试 2: 指定 7 天时间范围")
    print("="*60)

    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)

    spec = vim.PerformanceManager.QuerySpec(
        entity=test_vm,
        metricId=[metric_id],
        startTime=start_time,
        endTime=end_time,
        maxSample=5000
    )

    try:
        results = perf_mgr.QueryStats(querySpec=[spec])
        if results and results[0]:
            print(f"  ✓ 返回了数据")
            print(f"  样本数: {len(results[0].sampleInfo) if results[0].sampleInfo else 0}")

            if results[0].sampleInfo and len(results[0].sampleInfo) > 0:
                print(f"  最新样本时间: {results[0].sampleInfo[-1].timestamp}")
                if len(results[0].sampleInfo) > 1:
                    print(f"  最老样本时间: {results[0].sampleInfo[0].timestamp}")

            for stat in results[0].value:
                print(f"  值的数量: {len(stat.value) if stat.value else 0}")
        else:
            print(f"  ✗ 没有返回数据")
    except Exception as e:
        print(f"  ✗ 错误: {e}")

    print("\n" + "="*60)
    print("测试 3: 指定 30 天时间范围")
    print("="*60)

    end_time = datetime.now()
    start_time = end_time - timedelta(days=30)

    spec = vim.PerformanceManager.QuerySpec(
        entity=test_vm,
        metricId=[metric_id],
        startTime=start_time,
        endTime=end_time,
        maxSample=30000
    )

    try:
        results = perf_mgr.QueryStats(querySpec=[spec])
        if results and results[0]:
            print(f"  ✓ 返回了数据")
            print(f"  样本数: {len(results[0].sampleInfo) if results[0].sampleInfo else 0}")

            if results[0].sampleInfo and len(results[0].sampleInfo) > 0:
                print(f"  最新样本时间: {results[0].sampleInfo[-1].timestamp}")
                if len(results[0].sampleInfo) > 1:
                    print(f"  最老样本时间: {results[0].sampleInfo[0].timestamp}")

            for stat in results[0].value:
                print(f"  值的数量: {len(stat.value) if stat.value else 0}")
        else:
            print(f"  ✗ 没有返回数据 - 这可能是问题所在！")
    except Exception as e:
        print(f"  ✗ 错误: {e}")

    container.Destroy()
    Disconnect(si)

    print("\n" + "="*60)
    print("如果你有可以正常采集 30 天数据的示例代码，")
    print("请提供给我参考，我会对比找出差异。")
    print("="*60)


if __name__ == "__main__":
    main()
