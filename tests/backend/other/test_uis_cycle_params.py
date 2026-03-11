#!/usr/bin/env python3.14
"""测试 UIS API 的 cycle 参数和时间格式支持

测试目标：
1. cycle=0 是否支持小时级别的历史数据查询
2. cycle=1 天级别数据的准确格式
3. 不同时间格式的支持情况
"""

import asyncio
import json
from datetime import datetime, timedelta
import httpx


async def test_uis_api():
    """测试 UIS API 的不同参数组合"""

    # UIS 连接信息
    host = "10.103.115.8"
    port = 443
    username = "admin"
    password = "Admin@123."
    base_url = f"https://{host}:{port}/uis"

    # 测试 VM (centos-8, VM ID=14)
    test_vm_id = 14

    async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=30.0) as client:
        # 登录
        print("=" * 80)
        print("步骤 1: 登录 UIS")
        print("=" * 80)

        login_params = {
            "encrypt": "false",
            "loginType": "authorCenter",
            "name": username,
            "password": password
        }

        resp = await client.post(
            f"{base_url}/spring_check",
            params=login_params,
            headers={"Content-Type": "application/json"}
        )

        if resp.status_code != 200:
            print(f"❌ 登录失败: {resp.status_code}")
            return

        login_info = resp.json()
        if login_info.get('loginFailErrorCode'):
            print(f"❌ 登录失败: {login_info.get('loginFailMessage')}")
            return

        print("✅ 登录成功\n")

        # 测试用例配置
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)

        test_cases = [
            {
                "name": "测试 1: cycle=0 (小时) + 时间格式(YYYY-MM-DD HH)",
                "cycle": 0,
                "time_format": "hour",
                "start_time": start_time,
                "end_time": end_time,
            },
            {
                "name": "测试 2: cycle=0 (小时) + 时间格式(YYYY-MM-DD)",
                "cycle": 0,
                "time_format": "day",
                "start_time": start_time,
                "end_time": end_time,
            },
            {
                "name": "测试 3: cycle=1 (天) + 时间格式(YYYY-MM-DD)",
                "cycle": 1,
                "time_format": "day",
                "start_time": start_time,
                "end_time": end_time,
            },
            {
                "name": "测试 4: cycle=2 (周?) + 时间格式(YYYY-MM-DD)",
                "cycle": 2,
                "time_format": "day",
                "start_time": start_time,
                "end_time": end_time,
            },
            {
                "name": "测试 5: cycle=3 (月?) + 时间格式(YYYY-MM-DD)",
                "cycle": 3,
                "time_format": "day",
                "start_time": start_time,
                "end_time": end_time,
            },
        ]

        results = {}

        for test_case in test_cases:
            print("\n" + "=" * 80)
            print(test_case["name"])
            print("=" * 80)

            cycle = test_case["cycle"]
            time_format = test_case["time_format"]

            # 根据时间格式选择
            if time_format == "hour":
                start_time_str = test_case["start_time"].strftime('%Y-%m-%d %H')
                end_time_str = test_case["end_time"].strftime('%Y-%m-%d %H')
            else:
                start_time_str = test_case["start_time"].strftime('%Y-%m-%d')
                end_time_str = test_case["end_time"].strftime('%Y-%m-%d')

            params = {
                "domainId": test_vm_id,
                "cycle": cycle,
                "startTime": start_time_str,
                "endTime": end_time_str,
                "type": 0  # CPU
            }

            print(f"参数: {params}")

            try:
                resp = await client.get(
                    f"{base_url}/uis/report/cpuMemVm",
                    params=params
                )

                print(f"HTTP 状态码: {resp.status_code}")

                if resp.status_code == 200:
                    data = resp.json()
                    print(f"响应类型: {type(data)}")

                    if isinstance(data, list):
                        print(f"数组长度: {len(data)}")

                        if len(data) > 0:
                            print(f"第一个元素: {json.dumps(data[0], ensure_ascii=False)}")

                            # 尝试提取"平均值"数据
                            avg_data = None
                            for item in data:
                                if "平均" in item.get("title", ""):
                                    avg_data = item.get("list", [])
                                    break

                            if avg_data:
                                print(f"✅ 找到'平均值'数据，共 {len(avg_data)} 个数据点")

                                # 显示前 3 个和后 3 个数据点
                                print(f"\n前 3 个数据点:")
                                for i, point in enumerate(avg_data[:3]):
                                    print(f"  {point.get('name')}: rate={point.get('rate')}")

                                if len(avg_data) > 3:
                                    print(f"\n后 3 个数据点:")
                                    for i, point in enumerate(avg_data[-3:]):
                                        print(f"  {point.get('name')}: rate={point.get('rate')}")

                                results[test_case["name"]] = {
                                    "success": True,
                                    "data_points": len(avg_data),
                                    "sample_data": avg_data[:3] if len(avg_data) >= 3 else avg_data
                                }
                            else:
                                print(f"⚠️  未找到'平均值'数据")
                                results[test_case["name"]] = {
                                    "success": False,
                                    "reason": "No average data found"
                                }
                        else:
                            print(f"⚠️  返回空数组")
                            results[test_case["name"]] = {
                                "success": False,
                                "reason": "Empty array"
                            }
                    else:
                        print(f"响应数据: {json.dumps(data, ensure_ascii=False)[:200]}")
                        results[test_case["name"]] = {
                            "success": False,
                            "reason": f"Unexpected response type: {type(data)}"
                        }
                else:
                    print(f"❌ HTTP 错误: {resp.text[:200]}")
                    results[test_case["name"]] = {
                        "success": False,
                        "reason": f"HTTP {resp.status_code}"
                    }

            except Exception as e:
                print(f"❌ 异常: {e}")
                results[test_case["name"]] = {
                    "success": False,
                    "reason": str(e)
                }

        # 保存完整结果
        print("\n" + "=" * 80)
        print("测试结果汇总")
        print("=" * 80)

        output_file = "/tmp/uis_cycle_test_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n完整结果已保存到: {output_file}\n")

        for test_name, result in results.items():
            if result.get("success"):
                print(f"✅ {test_name}")
                print(f"   数据点数: {result['data_points']}")
            else:
                print(f"❌ {test_name}")
                print(f"   失败原因: {result.get('reason')}")
            print()

        # 分析结论
        print("=" * 80)
        print("结论分析")
        print("=" * 80)

        successful_tests = [name for name, result in results.items() if result.get("success")]

        if successful_tests:
            print("✅ 支持的参数组合:")
            for test_name in successful_tests:
                print(f"   - {test_name}")
        else:
            print("⚠️  所有测试都失败了")

        print("\n建议:")
        if any("cycle=0" in name and result.get("success") for name, result in results.items()):
            print("   - cycle=0 支持小时级别历史数据，可以使用")
        elif any("cycle=1" in name and result.get("success") for name, result in results.items()):
            print("   - cycle=1 支持天级别历史数据")
            print("   - 如果需要更细粒度，考虑分批次查询或使用其他 API")
        else:
            print("   - 需要查阅 UIS API 文档确认正确的参数用法")


if __name__ == "__main__":
    asyncio.run(test_uis_api())
