"""调试 UIS 性能指标 API，验证数据格式和单位。

运行: PYTHONPATH=backend pytest tests/backend/integration/debug_uis_metrics_api.py -v -s
"""

import asyncio
import os
import json
from datetime import datetime, timezone, timedelta

import httpx

# 直接读取环境变量
def get_env(key, default=""):
    with open('/home/worker/pengxin/TEMP/justfit/.env', 'r') as f:
        for line in f:
            if line.startswith(key + '='):
                return line.strip().split('=', 1)[1]
    return default


async def test_uis_metrics_api():
    """测试 UIS 性能指标 API"""

    host = get_env("UIS_IP", "10.103.115.8")
    username = get_env("UIS_USER_NAME", "admin")
    password = get_env("UIS_PASSWD", "Admin@123.")

    base_url = f"https://{host}:443/uis"

    async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=30.0) as client:
        # 登录
        login_params = {
            "encrypt": "false",
            "loginType": "authorCenter",
            "name": username,
            "password": password
        }

        print("=" * 100)
        print("步骤 1: 登录 UIS")
        print("=" * 100)

        resp = await client.post(
            f"{base_url}/spring_check",
            params=login_params,
            headers={"Content-Type": "application/json"}
        )
        resp.raise_for_status()
        login_info = resp.json()

        if login_info.get('loginFailErrorCode'):
            print(f"❌ 登录失败: {login_info.get('loginFailMessage', '未知错误')}")
            return

        print("✅ 登录成功")

        # 获取 VM 列表
        print("\n" + "=" * 100)
        print("步骤 2: 获取 VM 列表")
        print("=" * 100)

        resp = await client.get(
            f"{base_url}/uis/btnSeries/resourceDetail",
            params={'offset': 0, 'limit': 10}
        )
        resp.raise_for_status()
        result = resp.json()

        if not result.get('success'):
            print(f"❌ 获取 VM 列表失败: {result.get('failureMessage')}")
            return

        vms = result.get('data', [])
        print(f"✅ 获取到 {len(vms)} 个 VM")

        if not vms:
            print("没有 VM，退出测试")
            return

        # 选择第一个 VM 进行测试
        test_vm = vms[0]
        vm_id = test_vm['id']
        vm_name = test_vm['name']

        print(f"\n测试 VM: {vm_name} (ID: {vm_id})")

        # 测试时间范围：使用 cycle=1（天级别），查询最近 7 天
        use_cycle = 1
        from datetime import timedelta
        end_time_dt = datetime.now(timezone.utc)
        start_time_dt = end_time_dt - timedelta(days=7)
        start_time_str = start_time_dt.strftime('%Y-%m-%d')
        end_time_str = end_time_dt.strftime('%Y-%m-%d')

        print(f"时间范围: {start_time_str} ~ {end_time_str}")

        # API 配置（用户脚本中的路径是 /uis/uis/report/xxx，但我们的 base_url 已经包含 /uis，所以去掉一个 /uis）
        api_configs = [
            {
                "name": "CPU 利用率",
                "url": "/uis/report/cpuMemVm",
                "params": {"domainId": vm_id, "cycle": use_cycle, "startTime": start_time_str, "endTime": end_time_str, "type": 0}
            },
            {
                "name": "内存利用率",
                "url": "/uis/report/cpuMemVm",
                "params": {"domainId": vm_id, "cycle": use_cycle, "startTime": start_time_str, "endTime": end_time_str, "type": 1}
            },
            {
                "name": "磁盘读速率",
                "url": "/uis/report/diskVm",
                "params": {"domainId": vm_id, "cycle": use_cycle, "startTime": start_time_str, "endTime": end_time_str, "type": 0}
            },
            {
                "name": "磁盘写速率",
                "url": "/uis/report/diskVm",
                "params": {"domainId": vm_id, "cycle": use_cycle, "startTime": start_time_str, "endTime": end_time_str, "type": 1}
            },
            {
                "name": "网络读速率",
                "url": "/uis/report/netSpVm",
                "params": {"domainId": vm_id, "cycle": use_cycle, "startTime": start_time_str, "endTime": end_time_str, "type": 0}
            },
            {
                "name": "网络写速率",
                "url": "/uis/report/netSpVm",
                "params": {"domainId": vm_id, "cycle": use_cycle, "startTime": start_time_str, "endTime": end_time_str, "type": 1}
            },
        ]

        results = {}

        for config in api_configs:
            print("\n" + "-" * 100)
            print(f"测试 API: {config['name']}")
            print(f"URL: {config['url']}")
            print(f"参数: {config['params']}")

            try:
                resp = await client.get(
                    f"{base_url}{config['url']}",
                    params=config['params']
                )

                print(f"状态码: {resp.status_code}")

                if resp.status_code == 200:
                    data = resp.json()
                    results[config['name']] = data

                    # 打印数据结构
                    print(f"✅ 响应成功")
                    print(f"数据类型: {type(data)}")

                    if isinstance(data, list) and len(data) > 0:
                        first_item = data[0]
                        print(f"数组长度: {len(data)}")
                        print(f"第一个元素结构:")
                        print(json.dumps(first_item, indent=2, ensure_ascii=False))

                        # 尝试提取数值
                        if 'list' in first_item and isinstance(first_item['list'], list) and len(first_item['list']) > 0:
                            first_data_point = first_item['list'][0]
                            if 'rate' in first_data_point:
                                rate = first_data_point['rate']
                                print(f"-> rate 值示例: {rate}")

                    elif isinstance(data, dict):
                        if data.get('success'):
                            print(f"✅ API 返回 success=True")
                            actual_data = data.get('data')
                            if actual_data:
                                print(f"数据: {json.dumps(actual_data, indent=2, ensure_ascii=False)[:500]}...")
                        else:
                            print(f"❌ API 返回 success=False: {data.get('failureMessage')}")
                    else:
                        print(f"响应数据: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                else:
                    print(f"❌ 请求失败: {resp.text[:200]}")

            except Exception as e:
                print(f"❌ 异常: {e}")

        # 保存完整结果到文件
        print("\n" + "=" * 100)
        print("保存完整结果到文件")
        print("=" * 100)

        output_file = "/tmp/uis_metrics_api_response.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"✅ 完整结果已保存到: {output_file}")

        # 分析数据单位
        print("\n" + "=" * 100)
        print("数据单位分析")
        print("=" * 100)

        print("""
基于返回的数据，推测单位如下：
- CPU 利用率 rate: 百分比 (0-100)，需要转换为 CPU 核心数
- 内存利用率 rate: 百分比 (0-100)，需要转换为字节数
- 磁盘读/写速率 rate: 可能是 KB/s，需要转换为 bytes/s
- 网络读/写速率 rate: 可能是 KB/s，需要转换为 bytes/s

需要验证的转换公式：
- cpu_mhz = (cpu_rate / 100) * cpu_count
- memory_bytes = (memory_rate / 100) * total_memory_bytes
- disk_read_bytes_per_sec = disk_read_rate * 1024
- disk_write_bytes_per_sec = disk_write_rate * 1024
- net_rx_bytes_per_sec = net_in_rate * 1024
- net_tx_bytes_per_sec = net_out_rate * 1024
        """)


if __name__ == "__main__":
    asyncio.run(test_uis_metrics_api())
