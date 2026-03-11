#!/usr/bin/env python3.14
"""独立测试脚本：调试 vCenter 指标采集问题

测试不同的查询参数组合，找出为什么返回 0 个样本。
"""

import asyncio
from datetime import datetime, timedelta
from pyVmomi import vim, vmodl
from pyVim.connect import SmartConnect, Disconnect
import ssl

# vCenter 连接信息
VCENTER_HOST = "10.103.116.116"
VCENTER_PORT = 443
VCENTER_USER = "administrator@vsphere.local"
VCENTER_PASSWORD = "Admin@123."


def create_ssl_context():
    """创建 SSL 上下文（忽略证书验证）"""
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.verify_mode = ssl.CERT_NONE
    return context


def test_vcenter_metrics():
    """测试 vCenter 指标采集的不同参数组合"""

    print("=" * 80)
    print("vCenter 指标采集调试脚本")
    print("=" * 80)

    # 连接到 vCenter
    print(f"\n1. 连接到 vCenter: {VCENTER_HOST}")
    try:
        service_instance = SmartConnect(
            host=VCENTER_HOST,
            user=VCENTER_USER,
            pwd=VCENTER_PASSWORD,
            port=VCENTER_PORT,
            sslContext=create_ssl_context()
        )
        content = service_instance.RetrieveContent()
        print("   ✓ 连接成功")
    except Exception as e:
        print(f"   ✗ 连接失败: {e}")
        return

    # 获取 Performance Manager
    perf_manager = content.perfManager

    # 获取 counter 信息
    print("\n2. 获取性能计数器信息...")
    counter_info = {}
    for counter in perf_manager.perfCounter:
        counter_info[counter.key] = {
            'name': counter.groupInfo.label + "." + counter.nameInfo.label + "." + counter.rollupType,
            'group': counter.groupInfo.label,
            'name': counter.nameInfo.label,
            'rollup': counter.rollupType
        }

    # 查找我们需要的 counter keys
    # 先打印一些 counter 来了解格式
    print(f"   总共有 {len(counter_info)} 个 counters")
    print(f"   示例 counters (前 20 个):")
    for i, (key, info) in enumerate(list(counter_info.items())[:20]):
        print(f"     {key}: {info['name']}")

    needed_counters = {
        'cpu': 'cpu.usage.average',
        'memory': 'mem.usage.average',
        'disk_read': 'disk.read.average',
        'disk_write': 'disk.write.average',
        'net_rx': 'net.received.average',
        'net_tx': 'net.transmitted.average'
    }

    counter_keys = {}
    for key, info in counter_info.items():
        for needed_name, needed_full in needed_counters.items():
            if needed_full in info['name'].lower():  # 使用小写匹配，更宽松
                if needed_name not in counter_keys:  # 只保存第一个匹配的
                    counter_keys[needed_name] = key
                    print(f"   ✓ 找到 {needed_name}: key={key}, name={info['name']}")

    # 如果某些 counter 没找到，打印所有可用的
    missing = [name for name in needed_counters if name not in counter_keys]
    if missing:
        print(f"\n   ⚠️ 以下 counter 未找到: {missing}")
        print(f"   搜索相关 counters:")
        for key, info in counter_info.items():
            for needed_name in missing:
                if needed_name in info['name'].lower():
                    print(f"     {needed_name} -> {key}: {info['name']}")

    # 使用已找到的 counters
    if 'cpu' not in counter_keys:
        print("\n   ⚠️ 无法找到 cpu counter，尝试使用 657 (VCPU Usage)")
        counter_keys['cpu'] = 657
    if 'memory' not in counter_keys:
        print("   ⚠️ 无法找到 memory counter，跳过内存测试")

    # 获取第一个 VM
    print("\n3. 获取测试 VM...")
    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True
    )
    vms = container.view
    if not vms:
        print("   ✗ 没有找到 VM")
        Disconnect(service_instance)
        return

    test_vm = vms[0]
    vm_name = test_vm.name
    print(f"   ✓ 测试 VM: {vm_name}")
    container.Destroy()

    # 测试场景 1: 实时数据（20秒间隔，1小时范围）
    print("\n" + "=" * 80)
    print("测试场景 1: 实时数据（20秒间隔，1小时范围）")
    print("=" * 80)

    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)

    metric_ids = []
    if 'cpu' in counter_keys:
        metric_ids.append(vim.PerformanceManager.MetricId(counterId=counter_keys['cpu'], instance=""))
    if 'memory' in counter_keys:
        metric_ids.append(vim.PerformanceManager.MetricId(counterId=counter_keys['memory'], instance=""))

    if not metric_ids:
        print("   ✗ 没有可用的 metric IDs")
        return

    spec = vim.PerformanceManager.QuerySpec(
        entity=test_vm,
        metricId=metric_ids,
        intervalId=20,  # 实时数据
        maxSample=300,
        startTime=start_time,
        endTime=end_time
    )

    try:
        perf_stats = perf_manager.QueryStats(querySpec=[spec])
        if perf_stats and perf_stats[0]:
            sample_info = perf_stats[0].sampleInfo
            print(f"   样本数: {len(sample_info) if sample_info else 0}")
            if sample_info and len(sample_info) > 0:
                print(f"   第一个样本时间: {sample_info[0].timestamp}")
                print(f"   最后一个样本时间: {sample_info[-1].timestamp}")

            for stat in perf_stats[0].value:
                counter_id = stat.id.counterId
                values = stat.value if stat.value else []
                print(f"   Counter {counter_id} ({counter_info.get(counter_id, {}).get('name', 'unknown')}): {len(values)} 个值")
                if values:
                    print(f"     前 5 个值: {values[:5]}")
        else:
            print("   ✗ 没有返回数据")
    except Exception as e:
        print(f"   ✗ 查询失败: {e}")

    # 测试场景 2: 历史数据（5分钟间隔，3天范围）
    print("\n" + "=" * 80)
    print("测试场景 2: 历史数据（5分钟间隔，3天范围）")
    print("=" * 80)

    end_time = datetime.now()
    start_time = end_time - timedelta(days=3)

    # 重新构建 metric_ids（可能为空）
    metric_ids = []
    if 'cpu' in counter_keys:
        metric_ids.append(vim.PerformanceManager.MetricId(counterId=counter_keys['cpu'], instance=""))
    if 'memory' in counter_keys:
        metric_ids.append(vim.PerformanceManager.MetricId(counterId=counter_keys['memory'], instance=""))

    if not metric_ids:
        print("   ✗ 没有可用的 metric IDs，跳过此测试")
    else:
        spec = vim.PerformanceManager.QuerySpec(
            entity=test_vm,
            metricId=metric_ids,
        intervalId=300,  # 5分钟历史数据
        maxSample=1000,
        startTime=start_time,
        endTime=end_time
    )

    try:
        perf_stats = perf_manager.QueryStats(querySpec=[spec])
        if perf_stats and perf_stats[0]:
            sample_info = perf_stats[0].sampleInfo
            print(f"   样本数: {len(sample_info) if sample_info else 0}")
            if sample_info and len(sample_info) > 0:
                print(f"   第一个样本时间: {sample_info[0].timestamp}")
                print(f"   最后一个样本时间: {sample_info[-1].timestamp}")
            else:
                print("   ⚠️ sampleInfo 为空")

            for stat in perf_stats[0].value:
                counter_id = stat.id.counterId
                values = stat.value if stat.value else []
                print(f"   Counter {counter_id} ({counter_info.get(counter_id, {}).get('name', 'unknown')}): {len(values)} 个值")
                if values:
                    print(f"     前 5 个值: {values[:5]}")
        else:
            print("   ✗ 没有返回数据")
    except Exception as e:
        print(f"   ✗ 查询失败: {e}")

    # 测试场景 3: 历史数据（5分钟间隔，30天范围，maxSample=30000）
    print("\n" + "=" * 80)
    print("测试场景 3: 历史数据（5分钟间隔，30天范围，maxSample=30000）")
    print("=" * 80)

    end_time = datetime.now()
    start_time = end_time - timedelta(days=30)

    spec = vim.PerformanceManager.QuerySpec(
        entity=test_vm,
        metricId=metric_ids,
        intervalId=300,  # 5分钟历史数据
        maxSample=30000,
        startTime=start_time,
        endTime=end_time
    )

    try:
        perf_stats = perf_manager.QueryStats(querySpec=[spec])
        if perf_stats and perf_stats[0]:
            sample_info = perf_stats[0].sampleInfo
            print(f"   样本数: {len(sample_info) if sample_info else 0}")
            if sample_info and len(sample_info) > 0:
                print(f"   第一个样本时间: {sample_info[0].timestamp}")
                print(f"   最后一个样本时间: {sample_info[-1].timestamp}")
            else:
                print("   ⚠️ sampleInfo 为空")

            for stat in perf_stats[0].value:
                counter_id = stat.id.counterId
                values = stat.value if stat.value else []
                print(f"   Counter {counter_id} ({counter_info.get(counter_id, {}).get('name', 'unknown')}): {len(values)} 个值")
                if values:
                    print(f"     前 5 个值: {values[:5]}")
        else:
            print("   ✗ 没有返回数据 - 可能是 maxSample 太大或时间范围问题")
    except Exception as e:
        print(f"   ✗ 查询失败: {e}")

    # 测试场景 4: 不指定 intervalId，让 vCenter 自动选择
    print("\n" + "=" * 80)
    print("测试场景 4: 不指定 intervalId（让 vCenter 自动选择）")
    print("=" * 80)

    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)

    spec = vim.PerformanceManager.QuerySpec(
        entity=test_vm,
        metricId=metric_ids,
        # 不指定 intervalId
        maxSample=5000,
        startTime=start_time,
        endTime=end_time
    )

    try:
        perf_stats = perf_manager.QueryStats(querySpec=[spec])
        if perf_stats and perf_stats[0]:
            sample_info = perf_stats[0].sampleInfo
            print(f"   样本数: {len(sample_info) if sample_info else 0}")
            if sample_info and len(sample_info) > 0:
                print(f"   第一个样本时间: {sample_info[0].timestamp}")
                print(f"   最后一个样本时间: {sample_info[-1].timestamp}")

            for stat in perf_stats[0].value:
                counter_id = stat.id.counterId
                values = stat.value if stat.value else []
                print(f"   Counter {counter_id}: {len(values)} 个值")
        else:
            print("   ✗ 没有返回数据")
    except Exception as e:
        print(f"   ✗ 查询失败: {e}")

    # 测试场景 5: 查询可用的历史数据范围
    print("\n" + "=" * 80)
    print("测试场景 5: 检查 VM 可用的历史数据范围")
    print("=" * 80)

    try:
        # 获取 VM 的可用统计信息
        perf_provider_summary = perf_manager.QueryPerfProviderSummary(entity=test_vm)
        print(f"   实时数据支持: {perf_provider_summary.refreshRate}")
        print(f"   当前统计配置: {perf_provider_summary.summary}")

        # 尝试获取最近的统计数据
        spec = vim.PerformanceManager.QuerySpec(
            entity=test_vm,
            metricId=metric_ids,
            maxSample=100
        )

        perf_stats = perf_manager.QueryStats(querySpec=[spec])
        if perf_stats and perf_stats[0]:
            sample_info = perf_stats[0].sampleInfo
            print(f"   最近数据样本数: {len(sample_info) if sample_info else 0}")
            if sample_info and len(sample_info) > 0:
                print(f"   最近数据时间: {sample_info[-1].timestamp}")
                if len(sample_info) > 1:
                    print(f"   最老数据时间: {sample_info[0].timestamp}")
                    time_span = sample_info[-1].timestamp - sample_info[0].timestamp
                    print(f"   数据跨度: {time_span.days} 天")
        else:
            print("   ⚠️ 无法获取统计数据")
    except Exception as e:
        print(f"   ✗ 查询失败: {e}")

    # 断开连接
    Disconnect(service_instance)
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    test_vcenter_metrics()
