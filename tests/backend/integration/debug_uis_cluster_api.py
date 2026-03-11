"""调试 UIS 集群 API，验证数据格式。

运行: PYTHONPATH=backend pytest tests/backend/integration/debug_uis_cluster_api.py -v -s
"""

import asyncio
import json
from dotenv import load_dotenv

import httpx

# 直接读取环境变量
def get_env(key, default=""):
    with open('/home/worker/pengxin/TEMP/justfit/.env', 'r') as f:
        for line in f:
            if line.startswith(key + '='):
                return line.strip().split('=', 1)[1]
    return default


async def test_uis_cluster_api():
    """测试 UIS 集群相关 API"""

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

        # 测试获取主机池列表
        print("\n" + "=" * 100)
        print("步骤 2: 获取主机池和集群列表")
        print("=" * 100)

        api_endpoints = [
            {"name": "获取集群列表", "url": "/uis/cluster/getClusterList"},
            {"name": "获取主机池列表", "url": "/uis/cluster/getHostPoolList"},
            {"name": "获取集群资源列表", "url": "/uis/resource/getClusterList"},
            {"name": "获取所有资源", "url": "/uis/resource/all"},
            {"name": "获取集群详情", "url": "/uis/cluster/detail"},
            {"name": "获取主机池", "url": "/uis/hostPool/list"},
            {"name": "获取资源池", "url": "/uis/resourcePool/list"},
            # 尝试使用 report 相关的 API
            {"name": "获取资源详情（已知可用）", "url": "/uis/btnSeries/resourceDetail"},
        ]

        for endpoint in api_endpoints:
            print(f"\n测试: {endpoint['name']}")
            print(f"URL: {endpoint['url']}")

            try:
                resp = await client.get(f"{base_url}{endpoint['url']}")
                print(f"状态码: {resp.status_code}")

                if resp.status_code == 200:
                    data = resp.json()
                    print(f"响应类型: success={data.get('success')}")

                    if data.get('success'):
                        result_data = data.get('data', [])
                        print(f"数据量: {len(result_data)}")

                        if result_data:
                            print(f"第一个元素: {json.dumps(result_data[0], indent=2, ensure_ascii=False)[:500]}...")
                    else:
                        print(f"错误消息: {data.get('message', '未知错误')}")
                else:
                    print(f"错误响应: {resp.text[:200]}")

            except Exception as e:
                print(f"异常: {e}")

        # 如果找到了主机池或集群，尝试获取详细信息
        print("\n" + "=" * 100)
        print("步骤 3: 获取集群详细信息（测试不传参数）")
        print("=" * 100)

        # 尝试不同的参数组合
        test_params = [
            {"params": {}, "desc": "不传任何参数"},
            {"params": {"hpId": "", "clusterId": ""}, "desc": "传入空字符串"},
            {"params": {"hpId": 1, "clusterId": 1}, "desc": "传入具体 ID"},
        ]

        for params_config in test_params:
            print(f"\n测试: {params_config['desc']}")
            print(f"参数: {params_config['params']}")

            try:
                resp = await client.get(
                    f"{base_url}/uis/cluster/clusterInfo/detail",
                    params=params_config["params"]
                )

                print(f"状态码: {resp.status_code}")

                if resp.status_code == 200:
                    data = resp.json()
                    print(f"完整响应: {json.dumps(data, indent=2, ensure_ascii=False)[:1000]}")

                    # 尝试直接从响应中获取数据
                    if isinstance(data, list):
                        result_data = data
                    elif isinstance(data, dict):
                        if data.get('success'):
                            result_data = data.get('data', [])
                        else:
                            result_data = data.get('data', [])
                            if not result_data:
                                print(f"错误或空数据")
                                continue
                    else:
                        print(f"未知响应类型: {type(data)}")
                        continue

                    print(f"数据量: {len(result_data)}")

                    if result_data:
                        cluster = result_data[0]
                        print(f"集群名称: {cluster.get('name')}")
                        print(f"主机数量: {cluster.get('hostNum')}")
                        print(f"CPU 核心数: {cluster.get('cpu')}")
                        print(f"内存: {cluster.get('memory')}")
                        print(f"存储: {cluster.get('storage')}")
                        print(f"VM 总数: {cluster.get('vmTotal')}")
                        print(f"运行 VM: {cluster.get('vmRun')}")
                        print(f"关闭 VM: {cluster.get('vmShutoff')}")

            except Exception as e:
                print(f"异常: {e}")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])
