#!/usr/bin/env python3.14
"""测试 UIS API cycle=0 查询 30 天数据会返回多少"""

import asyncio
import json
from datetime import datetime, timedelta
import httpx


async def test_uis_30days():
    """测试 UIS API cycle=0 查询 30 天数据"""

    host = "10.103.115.8"
    port = 443
    username = "admin"
    password = "Admin@123."
    base_url = f"https://{host}:{port}/uis"
    test_vm_id = 14

    async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=30.0) as client:
        # 登录
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
            print(f"❌ 登录失败")
            return

        login_info = resp.json()
        if login_info.get('loginFailErrorCode'):
            print(f"❌ 登录失败: {login_info.get('loginFailMessage')}")
            return

        print("✅ 登录成功\n")

        # 测试 30 天查询
        print("=" * 80)
        print("测试: cycle=0 查询 30 天小时数据")
        print("=" * 80)

        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)

        start_time_str = start_time.strftime('%Y-%m-%d %H')
        end_time_str = end_time.strftime('%Y-%m-%d %H')

        params = {
            "domainId": test_vm_id,
            "cycle": 0,
            "startTime": start_time_str,
            "endTime": end_time_str,
            "type": 0  # CPU
        }

        print(f"查询时间范围: {start_time_str} ~ {end_time_str}")
        print(f"请求天数: 30 天")
        print(f"理论小时数: 30 * 24 = 720 小时\n")

        resp = await client.get(
            f"{base_url}/uis/report/cpuMemVm",
            params=params
        )

        if resp.status_code == 200:
            data = resp.json()

            if isinstance(data, list) and len(data) > 0:
                # 提取"平均值"数据
                avg_data = None
                for item in data:
                    if "平均" in item.get("title", ""):
                        avg_data = item.get("list", [])
                        break

                if avg_data:
                    actual_hours = len(avg_data)
                    print(f"✅ 实际返回: {actual_hours} 个小时数据点")

                    # 计算实际天数跨度
                    if len(avg_data) >= 2:
                        first_time = avg_data[0].get('name')
                        last_time = avg_data[-1].get('name')

                        print(f"\n最早时间: {first_time}")
                        print(f"最新时间: {last_time}")

                        # 计算时间差
                        try:
                            first_dt = datetime.strptime(first_time, '%Y-%m-%d %H')
                            last_dt = datetime.strptime(last_time, '%Y-%m-%d %H')
                            time_diff = last_dt - first_dt
                            days_span = time_diff.total_seconds() / 86400

                            print(f"实际跨度: {days_span:.2f} 天 ({time_diff.total_seconds() / 3600:.1f} 小时)")
                        except Exception as e:
                            print(f"⚠️  无法计算时间差: {e}")

                    print(f"\n数据采集率: {actual_hours / 720 * 100:.1f}% ({actual_hours}/720 小时)")

                    # 显示前 3 个和后 3 个数据点
                    print(f"\n前 3 个数据点:")
                    for point in avg_data[:3]:
                        print(f"  {point.get('name')}: rate={point.get('rate')}")

                    if len(avg_data) > 3:
                        print(f"\n后 3 个数据点:")
                        for point in avg_data[-3:]:
                            print(f"  {point.get('name')}: rate={point.get('rate')}")

                    # 结论
                    print("\n" + "=" * 80)
                    print("结论")
                    print("=" * 80)

                    if actual_hours < 720:
                        print(f"⚠️  UIS API cycle=0 对历史查询有限制")
                        print(f"   查询 30 天，但只返回了最近的 {actual_hours} 个小时数据")
                        print(f"   相当于 {actual_hours / 24:.1f} 天的数据")

                        # 推测限制
                        if actual_hours <= 30:
                            print(f"\n推测: UIS API cycle=0 最多返回 30 个小时数据点")
                        elif actual_hours <= 48:
                            print(f"\n推测: UIS API cycle=0 最多返回 48 个小时数据点")
                        elif actual_hours <= 72:
                            print(f"\n推测: UIS API cycle=0 最多返回 72 个小时数据点")

                        print(f"\n建议:")
                        print(f"   - 短期查询（1-2天）使用 cycle=0 获取小时级数据")
                        print(f"   - 长期查询（7天以上）使用 cycle=1 获取天级数据")
                    else:
                        print(f"✅ UIS API cycle=0 支持完整的 30 天小时数据查询")

                else:
                    print("❌ 未找到'平均值'数据")
            else:
                print("❌ 返回空数组或格式错误")
        else:
            print(f"❌ HTTP 错误: {resp.status_code}")


if __name__ == "__main__":
    asyncio.run(test_uis_30days())
