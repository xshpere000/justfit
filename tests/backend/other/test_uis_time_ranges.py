#!/usr/bin/env python3.14
"""测试 UIS API cycle=0 在不同时间跨度下的数据量"""

import asyncio
from datetime import datetime, timedelta
import httpx


async def test_uis_cycle0_limits():
    """测试不同时间跨度下 cycle=0 返回的数据量"""

    host = "10.103.115.8"
    base_url = f"https://{host}:443/uis"
    test_vm_id = 14

    async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=30.0) as client:
        # 登录
        login_params = {
            "encrypt": "false",
            "loginType": "authorCenter",
            "name": "admin",
            "password": "Admin@123."
        }

        resp = await client.post(
            f"{base_url}/spring_check",
            params=login_params,
            headers={"Content-Type": "application/json"}
        )

        if resp.status_code != 200 or resp.json().get('loginFailErrorCode'):
            print(f"❌ 登录失败")
            return

        print("✅ 登录成功\n")

        end_time = datetime.now()

        # 测试不同时间跨度
        test_spans = [
            (1, "1 天"),
            (2, "2 天"),
            (3, "3 天"),
            (5, "5 天"),
            (7, "7 天"),
            (14, "14 天"),
            (30, "30 天"),
        ]

        print("=" * 80)
        print("cycle=0 数据量限制测试")
        print("=" * 80)

        results = []

        for days, desc in test_spans:
            start_time = end_time - timedelta(days=days)

            start_time_str = start_time.strftime('%Y-%m-%d %H')
            end_time_str = end_time.strftime('%Y-%m-%d %H')

            params = {
                "domainId": test_vm_id,
                "cycle": 0,
                "startTime": start_time_str,
                "endTime": end_time_str,
                "type": 0  # CPU
            }

            try:
                resp = await client.get(
                    f"{base_url}/uis/report/cpuMemVm",
                    params=params
                )

                if resp.status_code == 200:
                    data = resp.json()

                    if isinstance(data, list) and len(data) > 0:
                        avg_data = None
                        for item in data:
                            if "平均" in item.get("title", ""):
                                avg_data = item.get("list", [])
                                break

                        if avg_data:
                            actual_hours = len(avg_data)
                            coverage = actual_hours / (days * 24) * 100

                            results.append({
                                "days": days,
                                "desc": desc,
                                "requested_hours": days * 24,
                                "actual_hours": actual_hours,
                                "coverage": coverage
                            })

                            print(f"{desc:8s} | 请求: {days * 24:4d} 小时 | 实际: {actual_hours:4d} 小时 | 覆盖率: {coverage:6.1f}%")

                            # 显示最早和最晚时间
                            if len(avg_data) >= 2:
                                first = avg_data[0].get('name')
                                last = avg_data[-1].get('name')
                                print(f"         | 时间范围: {first} ~ {last}")
                            print()
                        else:
                            print(f"{desc:8s} | ❌ 无数据\n")
                    else:
                        print(f"{desc:8s} | ❌ 返回空\n")
                else:
                    print(f"{desc:8s} | ❌ HTTP {resp.status_code}\n")

            except Exception as e:
                print(f"{desc:8s} | ❌ 异常: {e}\n")

        # 分析规律
        print("=" * 80)
        print("规律分析")
        print("=" * 80)

        # 找出返回数据量相同的时间跨度
        from collections import defaultdict
        hour_groups = defaultdict(list)
        for r in results:
            hour_groups[r['actual_hours']].append(r['desc'])

        print("\n按返回数据量分组:")
        for hours in sorted(hour_groups.keys(), reverse=True):
            print(f"  {hours:3d} 小时: {', '.join(hour_groups[hours])}")

        # 找出最大返回数据量
        max_hours = max(r['actual_hours'] for r in results)
        print(f"\n最大返回数据量: {max_hours} 小时")

        # 找出数据量开始下降的临界点
        print("\n数据覆盖分析:")
        for r in results:
            status = "✅" if r['coverage'] >= 80 else "⚠️ " if r['coverage'] >= 10 else "❌"
            print(f"  {status} {r['desc']:8s}: {r['coverage']:5.1f}% ({r['actual_hours']}/{r['requested_hours']} 小时)")

        print("\n" + "=" * 80)
        print("结论")
        print("=" * 80)

        if max_hours < 100:
            print(f"UIS API cycle=0 有数据量限制：")
            print(f"  - 最多返回 {max_hours} 个小时数据点")
            print(f"  - 相当于 {max_hours / 24:.1f} 天的小时级数据")
            print(f"\n建议使用策略：")
            print(f"  - 1-2 天查询: 使用 cycle=0 (小时级)")
            print(f"  - 3 天以上: 使用 cycle=1 (天级)")
        else:
            print(f"UIS API cycle=0 支持较长时间跨度的小时级数据查询")


if __name__ == "__main__":
    asyncio.run(test_uis_cycle0_limits())
