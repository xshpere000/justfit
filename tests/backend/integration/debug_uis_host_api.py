"""调试 UIS 主机 API，验证数据格式。

运行: PYTHONPATH=backend pytest tests/backend/integration/debug_uis_host_api.py -v -s
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


async def test_uis_host_api():
    """测试 UIS 主机相关 API"""

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

        # 测试获取主机信息
        print("\n" + "=" * 100)
        print("步骤 2: 获取主机信息")
        print("=" * 100)

        # 尝试不同的参数组合
        test_params = [
            {"params": {}, "desc": "不传任何参数"},
            {"params": {"hpId": 1, "clusterId": 1}, "desc": "传入 hpId 和 clusterId"},
            {"params": {"hostId": 1, "hpId": 1, "clusterId": 1}, "desc": "传入所有参数"},
        ]

        for params_config in test_params:
            print(f"\n测试: {params_config['desc']}")
            print(f"参数: {params_config['params']}")

            try:
                resp = await client.get(
                    f"{base_url}/uis/host/detail",
                    params=params_config["params"]
                )

                print(f"状态码: {resp.status_code}")

                if resp.status_code == 200:
                    data = resp.json()

                    if isinstance(data, dict) and data.get("data"):
                        result_data = data["data"]
                    else:
                        result_data = data if isinstance(data, list) else []

                    print(f"完整响应: {json.dumps(data, indent=2, ensure_ascii=False)[:1500]}...")
                    print(f"数据量: {len(result_data)}")

                    if result_data:
                        host = result_data[0]
                        print(f"主机名称: {host.get('name')}")
                        print(f"主机IP: {host.get('ip')}")
                        print(f"CPU 数量: {host.get('cpuCount')}")
                        print(f"CPU 频率: {host.get('cpuFrequence')} MHz")
                        print(f"内存: {host.get('memorySizeFormat')}")
                        print(f"磁盘: {host.get('diskSizeFormat')}")
                        print(f"VM 总数: {host.get('vmNum')}")
                        print(f"运行 VM: {host.get('vmRunCount')}")
                        print(f"关闭 VM: {host.get('vmShutoff')}")
                        print(f"集群 ID: {host.get('clusterId')}")
                        print(f"主机池 ID: {host.get('hostPoolId')}")

            except Exception as e:
                print(f"异常: {e}")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])
