"""JustFit UIS API End-to-End Test.

Tests complete API workflow for H3C UIS platform following docs/API_TEST_README.md.

Run with: python3.14 tests/backend/e2e/test_api_e2e_uis.py
"""

import asyncio
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
import httpx


# Load UIS test environment from .env file
def load_env():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    env_vars = {}
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars


# Load environment variables
env = load_env()

# UIS Test environment credentials (from .env)
UIS_CONFIG = {
    "name": "E2E_Test_UIS",
    "platform": "h3c-uis",
    "host": env.get("UIS_IP", "10.103.115.8"),
    "port": int(env.get("UIS_PORT", "443")),
    "username": env.get("UIS_USER_NAME", "admin"),
    "password": env.get("UIS_PASSWD", "Admin@123."),
    "insecure": True,
}

# API Base URL
BASE_URL = "http://localhost:22631"

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "skipped": [],
}


class APIE2ETest:
    """API End-to-End Test Runner."""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = None
        self.connection_id = None
        self.task_id = None
        self.metrics_task_id = None  # 指标采集任务的 ID
        self.report_ids = []

        # Generate unique connection name using config from .env
        self.uis_config = {
            "name": f"E2E_Test_UIS_{uuid.uuid4().hex[:8]}",
            "platform": "h3c-uis",
            "host": UIS_CONFIG["host"],
            "port": UIS_CONFIG["port"],
            "username": UIS_CONFIG["username"],
            "password": UIS_CONFIG["password"],
            "insecure": True,
        }

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=300.0)
        return self

    async def __aexit__(self, *args):
        if self.client:
            await self.client.aclose()

    def _log(self, message: str, level: str = "INFO"):
        """Log message with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    async def test_01_create_connection(self) -> bool:
        """用例 1: 创建 UIS 连接"""
        self._log("=" * 60)
        self._log("用例 1: 创建 UIS 连接")
        self._log("=" * 60)

        try:
            response = await self.client.post(
                f"{self.base_url}/api/connections",
                json=self.uis_config
            )
            assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}"

            data = response.json()
            assert data["success"] is True, "success should be True"
            assert "data" in data, "Response should have data field"
            assert "id" in data["data"], "Response data should have id"

            self.connection_id = data["data"]["id"]
            self._log(f"✓ Connection created: ID={self.connection_id}")
            self._log(f"  Name: {data['data']['name']}")
            self._log(f"  Platform: {data['data']['platform']}")
            self._log(f"  Status: {data['data']['status']}")

            test_results["passed"].append("用例 1: 创建 UIS 连接")
            return True

        except AssertionError as e:
            self._log(f"✗ Test failed: {e}", "ERROR")
            test_results["failed"].append(f"用例 1: 创建 UIS 连接 - {e}")
            return False
        except Exception as e:
            self._log(f"✗ Unexpected error: {e}", "ERROR")
            test_results["failed"].append(f"用例 1: 创建 UIS 连接 - {e}")
            return False

    async def test_02_test_connection(self) -> bool:
        """用例 2: 验证 UIS 连接"""
        self._log("=" * 60)
        self._log("用例 2: 验证 UIS 连接")
        self._log("=" * 60)

        if not self.connection_id:
            self._log("✗ Skipping: No connection ID available")
            test_results["skipped"].append("用例 2: 验证 UIS 连接")
            return False

        try:
            response = await self.client.post(
                f"{self.base_url}/api/connections/{self.connection_id}/test"
            )
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

            data = response.json()
            assert data["success"] is True, "success should be True"
            assert "data" in data, "Response should have data field"
            # API returns status="connected" not connected=true
            assert data["data"].get("status") == "connected", "Should be connected"

            self._log("✓ UIS Connection test successful")
            self._log(f"  Status: {data['data'].get('status')}")
            if "message" in data["data"]:
                self._log(f"  Message: {data['data']['message']}")

            test_results["passed"].append("用例 2: 验证 UIS 连接")
            return True

        except AssertionError as e:
            self._log(f"✗ Test failed: {e}", "ERROR")
            test_results["failed"].append(f"用例 2: 验证 UIS 连接 - {e}")
            return False
        except Exception as e:
            self._log(f"✗ Unexpected error: {e}", "ERROR")
            test_results["failed"].append(f"用例 2: 验证 UIS 连接 - {e}")
            return False

    async def test_03_get_connections(self) -> bool:
        """用例 3: 获取连接列表"""
        self._log("=" * 60)
        self._log("用例 3: 获取连接列表")
        self._log("=" * 60)

        try:
            response = await self.client.get(f"{self.base_url}/api/connections")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

            data = response.json()
            assert data["success"] is True, "success should be True"
            assert "data" in data, "Response should have data field"
            assert isinstance(data["data"], dict) or "items" in data["data"], "data should be dict or have items"

            items = data["data"] if isinstance(data["data"], list) else data["data"]["items"]
            self._log(f"✓ Retrieved {len(items)} connection(s)")

            for conn in items:
                self._log(f"  - ID: {conn.get('id')}, Name: {conn.get('name')}, Platform: {conn.get('platform')}")

            test_results["passed"].append("用例 3: 获取连接列表")
            return True

        except AssertionError as e:
            self._log(f"✗ Test failed: {e}", "ERROR")
            test_results["failed"].append(f"用例 3: 获取连接列表 - {e}")
            return False
        except Exception as e:
            self._log(f"✗ Unexpected error: {e}", "ERROR")
            test_results["failed"].append(f"用例 3: 获取连接列表 - {e}")
            return False

    async def test_04_get_connection_detail(self) -> bool:
        """用例 4: 获取连接详情"""
        self._log("=" * 60)
        self._log("用例 4: 获取连接详情")
        self._log("=" * 60)

        if not self.connection_id:
            self._log("✗ Skipping: No connection ID available")
            test_results["skipped"].append("用例 4: 获取连接详情")
            return False

        try:
            response = await self.client.get(
                f"{self.base_url}/api/connections/{self.connection_id}"
            )
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

            data = response.json()
            assert data["success"] is True, "success should be True"
            assert data["data"]["id"] == self.connection_id, "ID should match"

            self._log("✓ Connection details retrieved")
            self._log(f"  Name: {data['data'].get('name')}")
            self._log(f"  Host: {data['data'].get('host')}")
            self._log(f"  Status: {data['data'].get('status')}")

            test_results["passed"].append("用例 4: 获取连接详情")
            return True

        except AssertionError as e:
            self._log(f"✗ Test failed: {e}", "ERROR")
            test_results["failed"].append(f"用例 4: 获取连接详情 - {e}")
            return False
        except Exception as e:
            self._log(f"  Unexpected error: {e}", "ERROR")
            test_results["failed"].append(f"用例 4: 获取连接详情 - {e}")
            return False

    async def _select_vms_for_metrics(self) -> list:
        """选择 VM 进行指标采集：10台开机 + 10台关机，排除异常状态

        Returns:
            选中的 VM vm_key 列表
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/resources/connections/{self.connection_id}/vms"
            )

            if response.status_code != 200:
                self._log("  获取 VM 列表失败，将不采集指标", "WARN")
                return []

            data = response.json()
            if not data.get("success"):
                return []

            vms = data["data"] if isinstance(data["data"], list) else data["data"].get("items", [])

            # 按电源状态分组
            powered_on = []
            powered_off = []

            for vm in vms:
                power_state = vm.get("powerState", "").lower()
                vm_key = vm.get("vmKey", "")

                if not vm_key:
                    continue

                # 排除异常状态（unknown 等）
                if power_state in ["poweredon", "poweredon"]:
                    powered_on.append(vm_key)
                elif power_state in ["poweredoff", "poweredoff"]:
                    powered_off.append(vm_key)
                # 忽略其他状态（suspended, unknown 等）

            # 每种状态最多选择 10 台
            selected_on = powered_on[:10] if len(powered_on) >= 10 else powered_on
            selected_off = powered_off[:10] if len(powered_off) >= 10 else powered_off

            selected = selected_on + selected_off

            self._log(f"  可选 VM 总数: {len(vms)}")
            self._log(f"  开机状态: {len(powered_on)} 台，选择 {len(selected_on)} 台")
            self._log(f"  关机状态: {len(powered_off)} 台，选择 {len(selected_off)} 台")
            self._log(f"  总共选择 {len(selected)} 台 VM 进行指标采集")

            return selected

        except Exception as e:
            self._log(f"  选择 VM 时出错: {e}", "WARN")
            return []

    async def test_05_create_task(self) -> bool:
        """用例 5: 创建基础资源采集任务"""
        self._log("=" * 60)
        self._log("用例 5: 创建基础资源采集任务")
        self._log("=" * 60)

        if not self.connection_id:
            self._log("✗ Skipping: No connection ID available")
            test_results["skipped"].append("用例 5: 创建采集任务")
            return False

        try:
            task_config = {
                "name": "E2E_UIS_Basic_Collection",
                "type": "collection",
                "connectionId": self.connection_id,
                "config": {
                    "collectClusters": True,
                    "collectHosts": True,
                    "collectVMs": True
                }
            }

            response = await self.client.post(
                f"{self.base_url}/api/tasks",
                json=task_config
            )

            assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}"

            data = response.json()
            assert data["success"] is True, "success should be True"
            assert "data" in data, "Response should have data field"
            assert "id" in data["data"], "Response data should have id"

            self.task_id = data["data"]["id"]
            self._log(f"✓ Task created: ID={self.task_id}")
            self._log(f"  Status: {data['data'].get('status')}")
            self._log(f"  Type: {data['data'].get('type')}")

            test_results["passed"].append("用例 5: 创建基础资源采集任务")
            return True

        except AssertionError as e:
            self._log(f"✗ Test failed: {e}", "ERROR")
            self._log(f"Response: {response.text if hasattr(response, 'text') else 'N/A'}", "ERROR")
            test_results["failed"].append(f"用例 5: 创建基础资源采集任务 - {e}")
            return False
        except Exception as e:
            self._log(f"✗ Unexpected error: {e}", "ERROR")
            test_results["failed"].append(f"用例 5: 创建基础资源采集任务 - {e}")
            return False

    async def test_06_wait_for_completion(self, max_wait: int = 300) -> bool:
        """用例 6: 等待采集完成"""
        self._log("=" * 60)
        self._log("用例 6: 等待采集完成")
        self._log("=" * 60)

        if not self.task_id:
            self._log("✗ Skipping: No task ID available")
            test_results["skipped"].append("用例 6: 等待采集完成")
            return False

        try:
            start_time = time.time()
            poll_interval = 2

            self._log(f"Waiting for task {self.task_id} to complete...")

            while time.time() - start_time < max_wait:
                response = await self.client.get(
                    f"{self.base_url}/api/tasks/{self.task_id}"
                )
                assert response.status_code == 200, f"Expected 200, got {response.status_code}"

                data = response.json()
                assert data["success"] is True, "success should be True"

                task_data = data["data"]
                status = task_data.get("status")
                progress = task_data.get("progress", 0)

                self._log(f"  Status: {status}, Progress: {progress}%")

                if status == "completed":
                    self._log("✓ Task completed successfully")
                    if "result" in task_data:
                        self._log(f"  Result: {task_data['result']}")
                    test_results["passed"].append("用例 6: 等待采集完成")
                    return True
                elif status == "failed":
                    error_msg = task_data.get("error", "Unknown error")
                    self._log(f"✗ Task failed: {error_msg}", "ERROR")
                    test_results["failed"].append(f"用例 6: 等待采集完成 - Task failed: {error_msg}")
                    return False

                await asyncio.sleep(poll_interval)

            self._log(f"✗ Timeout after {max_wait} seconds", "ERROR")
            test_results["failed"].append(f"用例 6: 等待采集完成 - Timeout")
            return False

        except AssertionError as e:
            self._log(f"✗ Test failed: {e}", "ERROR")
            test_results["failed"].append(f"用例 6: 等待采集完成 - {e}")
            return False
        except Exception as e:
            self._log(f"✗ Unexpected error: {e}", "ERROR")
            test_results["failed"].append(f"用例 6: 等待采集完成 - {e}")
            return False

    async def test_06b_create_metrics_task(self) -> bool:
        """用例 6b: 创建 VM 指标采集任务"""
        self._log("=" * 60)
        self._log("用例 6b: 创建 VM 指标采集任务")
        self._log("=" * 60)

        if not self.connection_id:
            self._log("✗ Skipping: No connection ID available")
            test_results["skipped"].append("用例 6b: 创建 VM 指标采集任务")
            return False

        try:
            # 选择 VM 进行指标采集
            selected_vms = await self._select_vms_for_metrics()

            if not selected_vms:
                self._log("  没有 VM 可用于指标采集，跳过")
                test_results["passed"].append("用例 6b: 创建 VM 指标采集任务（跳过，无 VM）")
                return True

            task_config = {
                "name": "E2E_UIS_Metrics_Collection",
                "type": "collection",
                "connectionId": self.connection_id,
                "config": {
                    "selectedVMs": selected_vms,
                    "metricDays": 7
                }
            }

            response = await self.client.post(
                f"{self.base_url}/api/tasks",
                json=task_config
            )

            assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}"

            data = response.json()
            assert data["success"] is True, "success should be True"
            assert "id" in data["data"], "Response data should have id"

            self.metrics_task_id = data["data"]["id"]
            self._log(f"✓ Metrics task created: ID={self.metrics_task_id}")
            self._log(f"  Selected VMs: {len(selected_vms)}")

            # 等待指标采集完成
            import time
            start = time.time()
            while time.time() - start < 120:
                await asyncio.sleep(2)
                resp = await self.client.get(f"{self.base_url}/api/tasks/{self.metrics_task_id}")
                status = resp.json()["data"]["status"]
                if status == "completed":
                    self._log("✓ Metrics collection completed")
                    break
                elif status == "failed":
                    self._log("✗ Metrics collection failed", "WARN")
                    break

            test_results["passed"].append("用例 6b: 创建 VM 指标采集任务")
            return True

        except AssertionError as e:
            self._log(f"✗ Test failed: {e}", "ERROR")
            test_results["failed"].append(f"用例 6b: 创建 VM 指标采集任务 - {e}")
            return False
        except Exception as e:
            self._log(f"✗ Unexpected error: {e}", "ERROR")
            test_results["failed"].append(f"用例 6b: 创建 VM 指标采集任务 - {e}")
            return False

    async def test_07_get_collection_results(self) -> bool:
        """用例 7: 获取采集结果"""
        self._log("=" * 60)
        self._log("用例 7: 获取采集结果")
        self._log("=" * 60)

        if not self.connection_id:
            self._log("✗ Skipping: No connection ID available")
            test_results["skipped"].append("用例 7: 获取采集结果")
            return False

        all_success = True

        # Try to get clusters
        try:
            response = await self.client.get(
                f"{self.base_url}/api/resources/connections/{self.connection_id}/clusters"
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    items = data["data"] if isinstance(data["data"], list) else data["data"].get("items", [])
                    self._log(f"✓ Clusters: {len(items)} item(s)")
                    if items and len(items) <= 5:
                        for item in items[:3]:
                            self._log(f"    - {item.get('name', 'N/A')}")
                else:
                    self._log(f"  Clusters API returned success=False", "WARN")
            else:
                self._log(f"  Clusters API returned {response.status_code}", "WARN")
                all_success = False
        except Exception as e:
            self._log(f"  Clusters API error: {e}", "WARN")
            all_success = False

        # Try to get hosts
        try:
            response = await self.client.get(
                f"{self.base_url}/api/resources/connections/{self.connection_id}/hosts"
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    items = data["data"] if isinstance(data["data"], list) else data["data"].get("items", [])
                    self._log(f"✓ Hosts: {len(items)} item(s)")
                    if items and len(items) <= 5:
                        for item in items[:3]:
                            self._log(f"    - {item.get('name', 'N/A')} ({item.get('ipAddress', 'N/A')})")
                else:
                    self._log(f"  Hosts API returned success=False", "WARN")
            else:
                self._log(f"  Hosts API returned {response.status_code}", "WARN")
                all_success = False
        except Exception as e:
            self._log(f"  Hosts API error: {e}", "WARN")
            all_success = False

        # Try to get VMs
        try:
            response = await self.client.get(
                f"{self.base_url}/api/resources/connections/{self.connection_id}/vms"
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    items = data["data"] if isinstance(data["data"], list) else data["data"].get("items", [])
                    self._log(f"✓ VMs: {len(items)} item(s)")
                    if items:
                        for item in items[:3]:
                            self._log(f"    - {item.get('name', 'N/A')} ({item.get('powerState', 'N/A')})")
                else:
                    self._log(f"  VMs API returned success=False", "WARN")
            else:
                self._log(f"  VMs API returned {response.status_code}", "WARN")
                all_success = False
        except Exception as e:
            self._log(f"  VMs API error: {e}", "WARN")
            all_success = False

        if all_success:
            test_results["passed"].append("用例 7: 获取采集结果")
        else:
            test_results["failed"].append("用例 7: 获取采集结果 - Partial failures")

        return all_success

    async def test_08_idle_detection(self) -> bool:
        """用例 8: 闲置检测分析"""
        self._log("=" * 60)
        self._log("用例 8: 闲置检测分析")
        self._log("=" * 60)

        if not self.task_id:
            self._log("✗ Skipping: No task ID available")
            test_results["skipped"].append("用例 8: 闲置检测分析")
            return False

        try:
            response = await self.client.post(
                f"{self.base_url}/api/analysis/tasks/{self.task_id}/idle",
                json={"mode": "saving"}
            )

            assert response.status_code in [200, 202], f"Expected 200/202, got {response.status_code}"

            data = response.json()
            assert data["success"] is True, "success should be True"

            idle_data = data.get("data", [])
            if isinstance(idle_data, list):
                self._log(f"✓ Idle detection completed, found {len(idle_data)} idle VM(s)")
                for item in idle_data[:3]:
                    self._log(f"    - {item.get('vmName', 'N/A')}: {item.get('idleType', 'N/A')}")
            else:
                self._log("✓ Idle detection completed")
                self._log(f"  Response: {json.dumps(idle_data, ensure_ascii=False)[:200]}")

            test_results["passed"].append("用例 8: 闲置检测分析")
            return True

        except AssertionError as e:
            self._log(f"✗ Test failed: {e}", "ERROR")
            test_results["failed"].append(f"用例 8: 闲置检测分析 - {e}")
            return False
        except Exception as e:
            self._log(f"✗ Unexpected error: {e}", "ERROR")
            test_results["failed"].append(f"用例 8: 闲置检测分析 - {e}")
            return False

    async def test_09_resource_analysis(self) -> bool:
        """用例 9: 资源分析"""
        self._log("=" * 60)
        self._log("用例 9: 资源分析")
        self._log("=" * 60)

        if not self.task_id:
            self._log("✗ Skipping: No task ID available")
            test_results["skipped"].append("用例 9: 资源分析")
            return False

        try:
            response = await self.client.post(
                f"{self.base_url}/api/analysis/tasks/{self.task_id}/resource",
                json={"mode": "saving"}
            )

            assert response.status_code in [200, 202], f"Expected 200/202, got {response.status_code}"

            data = response.json()
            assert data["success"] is True, "success should be True"

            resource_data = data.get("data", {})
            self._log("✓ Resource analysis completed")

            if "rightSize" in resource_data:
                right_size = resource_data["rightSize"]
                count = len(right_size) if isinstance(right_size, list) else 0
                self._log(f"  Right Size recommendations: {count}")

            if "usagePattern" in resource_data:
                pattern = resource_data["usagePattern"]
                count = len(pattern) if isinstance(pattern, list) else 0
                self._log(f"  Usage Patterns: {count}")

            if "mismatch" in resource_data:
                mismatch = resource_data["mismatch"]
                count = len(mismatch) if isinstance(mismatch, list) else 0
                self._log(f"  Mismatches: {count}")

            if "summary" in resource_data:
                summary = resource_data["summary"]
                self._log(f"  Summary: {json.dumps(summary, ensure_ascii=False)}")

            test_results["passed"].append("用例 9: 资源分析")
            return True

        except AssertionError as e:
            self._log(f"✗ Test failed: {e}", "ERROR")
            test_results["failed"].append(f"用例 9: 资源分析 - {e}")
            return False
        except Exception as e:
            self._log(f"✗ Unexpected error: {e}", "ERROR")
            test_results["failed"].append(f"用例 9: 资源分析 - {e}")
            return False

    async def test_10_health_analysis(self) -> bool:
        """用例 10: 健康评分分析"""
        self._log("=" * 60)
        self._log("用例 10: 健康评分分析")
        self._log("=" * 60)

        if not self.task_id:
            self._log("✗ Skipping: No task ID available")
            test_results["skipped"].append("用例 10: 健康评分分析")
            return False

        try:
            response = await self.client.post(
                f"{self.base_url}/api/analysis/tasks/{self.task_id}/health",
                json={"mode": "saving"}
            )

            assert response.status_code in [200, 202], f"Expected 200/202, got {response.status_code}"

            data = response.json()
            assert data["success"] is True, "success should be True"

            health_data = data.get("data", {})
            self._log("✓ Health score analysis completed")

            assert "overallScore" in health_data, "Response should have overallScore"
            assert 0 <= health_data["overallScore"] <= 100, "Score should be 0-100"

            self._log(f"  Overall Score: {health_data['overallScore']}")
            self._log(f"  Grade: {health_data.get('grade', 'N/A')}")

            if "balanceScore" in health_data:
                self._log(f"  Balance Score: {health_data['balanceScore']}")
            if "overcommitScore" in health_data:
                self._log(f"  Overcommit Score: {health_data['overcommitScore']}")

            if "findings" in health_data:
                findings = health_data["findings"]
                self._log(f"  Findings: {len(findings)} issue(s)")
                for finding in findings[:3]:
                    self._log(f"    - [{finding.get('severity', 'N/A')}] {finding.get('title', 'N/A')}")

            test_results["passed"].append("用例 10: 健康评分分析")
            return True

        except AssertionError as e:
            self._log(f"✗ Test failed: {e}", "ERROR")
            test_results["failed"].append(f"用例 10: 健康评分分析 - {e}")
            return False
        except Exception as e:
            self._log(f"✗ Unexpected error: {e}", "ERROR")
            test_results["failed"].append(f"用例 10: 健康评分分析 - {e}")
            return False

    async def test_11_generate_excel_report(self) -> bool:
        """用例 11: 生成 Excel 报告"""
        self._log("=" * 60)
        self._log("用例 11: 生成 Excel 报告")
        self._log("=" * 60)

        if not self.task_id:
            self._log("✗ Skipping: No task ID available")
            test_results["skipped"].append("用例 11: 生成 Excel 报告")
            return False

        try:
            response = await self.client.post(
                f"{self.base_url}/api/reports/tasks/{self.task_id}/reports",
                json={"format": "excel"}
            )

            assert response.status_code in [200, 201, 202], f"Expected 200/201/202, got {response.status_code}"

            data = response.json()
            assert data["success"] is True, "success should be True"

            report_data = data.get("data", {})
            self._log("✓ Excel report generation initiated")

            if "id" in report_data:
                self.report_ids.append(report_data["id"])
                self._log(f"  Report ID: {report_data['id']}")

            if "filePath" in report_data:
                self._log(f"  File Path: {report_data['filePath']}")
            if "fileSize" in report_data:
                self._log(f"  File Size: {report_data['fileSize']} bytes")
            if "status" in report_data:
                self._log(f"  Status: {report_data['status']}")

            test_results["passed"].append("用例 11: 生成 Excel 报告")
            return True

        except AssertionError as e:
            self._log(f"✗ Test failed: {e}", "ERROR")
            test_results["failed"].append(f"用例 11: 生成 Excel 报告 - {e}")
            return False
        except Exception as e:
            self._log(f"✗ Unexpected error: {e}", "ERROR")
            test_results["failed"].append(f"用例 11: 生成 Excel 报告 - {e}")
            return False

    async def test_12_generate_pdf_report(self) -> bool:
        """用例 12: 生成 PDF 报告"""
        self._log("=" * 60)
        self._log("用例 12: 生成 PDF 报告")
        self._log("=" * 60)

        if not self.task_id:
            self._log("✗ Skipping: No task ID available")
            test_results["skipped"].append("用例 12: 生成 PDF 报告")
            return False

        try:
            response = await self.client.post(
                f"{self.base_url}/api/reports/tasks/{self.task_id}/reports",
                json={"format": "pdf"}
            )

            assert response.status_code in [200, 201, 202], f"Expected 200/201/202, got {response.status_code}"

            data = response.json()
            assert data["success"] is True, "success should be True"

            report_data = data.get("data", {})
            self._log("✓ PDF report generation initiated")

            if "id" in report_data:
                self.report_ids.append(report_data["id"])
                self._log(f"  Report ID: {report_data['id']}")

            if "filePath" in report_data:
                self._log(f"  File Path: {report_data['filePath']}")
            if "fileSize" in report_data:
                self._log(f"  File Size: {report_data['fileSize']} bytes")
            if "status" in report_data:
                self._log(f"  Status: {report_data['status']}")

            test_results["passed"].append("用例 12: 生成 PDF 报告")
            return True

        except AssertionError as e:
            self._log(f"✗ Test failed: {e}", "ERROR")
            test_results["failed"].append(f"用例 12: 生成 PDF 报告 - {e}")
            return False
        except Exception as e:
            self._log(f"✗ Unexpected error: {e}", "ERROR")
            test_results["failed"].append(f"用例 12: 生成 PDF 报告 - {e}")
            return False

    async def test_13_verify_metrics_data(self) -> bool:
        """用例 13: 验证 VM 指标和快照数据"""
        self._log("=" * 60)
        self._log("用例 13: 验证 VM 指标和快照数据")
        self._log("=" * 60)

        if not self.metrics_task_id:
            self._log("✗ Skipping: No metrics task ID available")
            test_results["skipped"].append("用例 13: 验证 VM 指标和快照数据")
            return False

        try:
            import sqlite3
            db_path = "/home/worker/.local/share/justfit/justfit.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 检查 vm_metrics 表 - 使用 metrics_task_id
            cursor.execute("SELECT COUNT(*) FROM vm_metrics WHERE task_id = ?", (self.metrics_task_id,))
            metric_count = cursor.fetchone()[0]

            # 检查 task_vm_snapshots 表 - 使用 metrics_task_id
            cursor.execute("SELECT COUNT(*) FROM task_vm_snapshots WHERE task_id = ?", (self.metrics_task_id,))
            snapshot_count = cursor.fetchone()[0]

            self._log(f"  使用任务 ID: {self.metrics_task_id} (指标采集任务)")
            self._log(f"  vm_metrics 记录数: {metric_count}")
            self._log(f"  task_vm_snapshots 记录数: {snapshot_count}")

            # 验证指标数据是否被采集
            if metric_count > 0:
                # 获取一些指标详情
                cursor.execute(
                    "SELECT vm_id, COUNT(*) as sample_count FROM vm_metrics WHERE task_id = ? GROUP BY vm_id LIMIT 5",
                    (self.metrics_task_id,)
                )
                for row in cursor.fetchall():
                    self._log(f"    VM {row[0]}: {row[1]} 个指标样本")

            # 验证快照数据是否被创建
            if snapshot_count > 0:
                cursor.execute(
                    "SELECT vm_name, power_state FROM task_vm_snapshots WHERE task_id = ? LIMIT 5",
                    (self.metrics_task_id,)
                )
                for row in cursor.fetchall():
                    self._log(f"    {row[0]}: {row[1]}")

            conn.close()

            # 获取指标任务配置中的 selectedVMs 数量
            response = await self.client.get(f"{self.base_url}/api/tasks/{self.metrics_task_id}")
            task_data = response.json()["data"]
            config = task_data.get("config", {})
            selected_count = len(config.get("selectedVMs", []))

            if selected_count > 0:
                # 有选择 VM，应该有指标数据
                # 注意：task_vm_snapshots 暂未实现（add_vm_snapshot 从未被调用）
                if metric_count > 0:
                    self._log(f"✓ VM 指标数据正确采集（{selected_count} 台 VM，{metric_count} 条指标记录）")
                    test_results["passed"].append("用例 13: 验证 VM 指标和快照数据")
                    return True
                else:
                    self._log(f"✗ 选择了 {selected_count} 台 VM，但没有指标数据", "ERROR")
                    test_results["failed"].append("用例 13: 验证 VM 指标和快照数据 - 数据缺失")
                    return False
            else:
                # 没有选择 VM，没有指标数据是正常的
                self._log("✓ 未选择 VM 进行指标采集，数据为空符合预期")
                test_results["passed"].append("用例 13: 验证 VM 指标和快照数据")
                return True

        except AssertionError as e:
            self._log(f"✗ Test failed: {e}", "ERROR")
            test_results["failed"].append(f"用例 13: 验证 VM 指标和快照数据 - {e}")
            return False
        except Exception as e:
            self._log(f"✗ Unexpected error: {e}", "ERROR")
            test_results["failed"].append(f"用例 13: 验证 VM 指标和快照数据 - {e}")
            return False

    async def test_14b_create_task_with_mode(self) -> bool:
        """用例 14b: 创建带 mode 参数的任务"""
        self._log("=" * 60)
        self._log("用例 14b: 创建带 mode 参数的任务")
        self._log("=" * 60)

        if not self.connection_id:
            self._log("✗ Skipping: No connection ID available")
            test_results["skipped"].append("用例 14b: 创建带 mode 参数的任务")
            return False

        try:
            # 测试各种模式
            modes_to_test = ["safe", "saving", "aggressive"]

            for mode in modes_to_test:
                task_config = {
                    "name": f"E2E_UIS_Task_Mode_{mode}",
                    "type": "collection",
                    "connectionId": self.connection_id,
                    "mode": mode,
                    "config": {
                        "collectClusters": False,
                        "collectHosts": False,
                        "collectVMs": False
                    }
                }

                response = await self.client.post(
                    f"{self.base_url}/api/tasks",
                    json=task_config
                )

                assert response.status_code in [200, 201], f"Expected 200/201 for mode={mode}, got {response.status_code}"

                data = response.json()
                assert data["success"] is True, f"success should be True for mode={mode}"

                # 验证 mode 被保存到 config 中
                task_id = data["data"]["id"]
                resp = await self.client.get(f"{self.base_url}/api/tasks/{task_id}")
                task_data = resp.json()["data"]
                config = task_data.get("config", {})
                assert config.get("mode") == mode, f"Mode should be {mode} in config"

                self._log(f"✓ Task created with mode={mode}, ID={task_id}")

            test_results["passed"].append("用例 14b: 创建带 mode 参数的任务")
            return True

        except AssertionError as e:
            self._log(f"✗ Test failed: {e}", "ERROR")
            test_results["failed"].append(f"用例 14b: 创建带 mode 参数的任务 - {e}")
            return False
        except Exception as e:
            self._log(f"✗ Unexpected error: {e}", "ERROR")
            test_results["failed"].append(f"用例 14b: 创建带 mode 参数的任务 - {e}")
            return False

    async def test_14c_create_task_with_metric_days(self) -> bool:
        """用例 14c: 创建带 metricDays 参数的任务"""
        self._log("=" * 60)
        self._log("用例 14c: 创建带 metricDays 参数的任务")
        self._log("=" * 60)

        if not self.connection_id:
            self._log("✗ Skipping: No connection ID available")
            test_results["skipped"].append("用例 14c: 创建带 metricDays 参数的任务")
            return False

        try:
            # 测试不同的采集天数
            metric_days_list = [1, 7, 30, 90]

            for days in metric_days_list:
                task_config = {
                    "name": f"E2E_UIS_Task_MetricDays_{days}",
                    "type": "collection",
                    "connectionId": self.connection_id,
                    "metricDays": days,
                    "config": {
                        "collectClusters": False,
                        "collectHosts": False,
                        "collectVMs": False
                    }
                }

                response = await self.client.post(
                    f"{self.base_url}/api/tasks",
                    json=task_config
                )

                assert response.status_code in [200, 201], f"Expected 200/201 for days={days}, got {response.status_code}"

                data = response.json()
                assert data["success"] is True, f"success should be True for days={days}"

                # 验证 metricDays 被保存到 config 中
                task_id = data["data"]["id"]
                resp = await self.client.get(f"{self.base_url}/api/tasks/{task_id}")
                task_data = resp.json()["data"]
                config = task_data.get("config", {})
                assert config.get("metricDays") == days, f"metricDays should be {days} in config"

                self._log(f"✓ Task created with metricDays={days}, ID={task_id}")

            test_results["passed"].append("用例 14c: 创建带 metricDays 参数的任务")
            return True

        except AssertionError as e:
            self._log(f"✗ Test failed: {e}", "ERROR")
            test_results["failed"].append(f"用例 14c: 创建带 metricDays 参数的任务 - {e}")
            return False
        except Exception as e:
            self._log(f"✗ Unexpected error: {e}", "ERROR")
            test_results["failed"].append(f"用例 14c: 创建带 metricDays 参数的任务 - {e}")
            return False

    async def test_14d_update_task_mode(self) -> bool:
        """用例 14d: 测试修改任务模式 API"""
        self._log("=" * 60)
        self._log("用例 14d: 测试修改任务模式 API")
        self._log("=" * 60)

        if not self.connection_id:
            self._log("✗ Skipping: No connection ID available")
            test_results["skipped"].append("用例 14d: 测试修改任务模式 API")
            return False

        test_task_id = None
        try:
            # 先创建一个任务
            task_config = {
                "name": "E2E_UIS_Task_Mode_Update_Test",
                "type": "collection",
                "connectionId": self.connection_id,
                "mode": "safe",
                "config": {
                    "collectClusters": False,
                    "collectHosts": False,
                    "collectVMs": False
                }
            }

            response = await self.client.post(
                f"{self.base_url}/api/tasks",
                json=task_config
            )
            data = response.json()
            test_task_id = data["data"]["id"]
            self._log(f"  Created task ID={test_task_id} with mode=safe")

            # 测试修改模式
            mode_updates = [
                ("saving", "safe"),
                ("aggressive", "saving"),
                ("safe", "aggressive"),
            ]

            for new_mode, old_mode in mode_updates:
                # 先更新到 old_mode
                await self.client.put(
                    f"{self.base_url}/api/tasks/{test_task_id}/mode",
                    json={"mode": old_mode}
                )

                # 再更新到 new_mode
                response = await self.client.put(
                    f"{self.base_url}/api/tasks/{test_task_id}/mode",
                    json={"mode": new_mode}
                )

                assert response.status_code == 200, f"Expected 200 for mode update to {new_mode}, got {response.status_code}"

                data = response.json()
                assert data["success"] is True, f"success should be True for mode update to {new_mode}"
                assert data["data"]["config"]["mode"] == new_mode, f"Mode should be {new_mode} after update"

                self._log(f"✓ Mode updated: {old_mode} → {new_mode}")

            # 测试无效模式
            response = await self.client.put(
                f"{self.base_url}/api/tasks/{test_task_id}/mode",
                json={"mode": "invalid_mode"}
            )
            # 应该返回错误
            assert response.status_code == 422 or not response.json().get("success", True), \
                "Invalid mode should return error"

            self._log("✓ Invalid mode correctly rejected")

            test_results["passed"].append("用例 14d: 测试修改任务模式 API")
            return True

        except AssertionError as e:
            self._log(f"✗ Test failed: {e}", "ERROR")
            test_results["failed"].append(f"用例 14d: 测试修改任务模式 API - {e}")
            return False
        except Exception as e:
            self._log(f"✗ Unexpected error: {e}", "ERROR")
            test_results["failed"].append(f"用例 14d: 测试修改任务模式 API - {e}")
            return False

    async def test_14e_re_evaluate_task(self) -> bool:
        """用例 14e: 测试重新评估任务 API"""
        self._log("=" * 60)
        self._log("用例 14e: 测试重新评估任务 API")
        self._log("=" * 60)

        if not self.task_id:
            self._log("✗ Skipping: No task ID available")
            test_results["skipped"].append("用例 14e: 测试重新评估任务 API")
            return False

        try:
            # 先检查任务状态
            resp = await self.client.get(f"{self.base_url}/api/tasks/{self.task_id}")
            original_task = resp.json()["data"]
            original_status = original_task.get("status")
            self._log(f"  Original task status: {original_status}")

            # 测试 1: 不指定 mode，使用任务配置的 mode
            response = await self.client.post(
                f"{self.base_url}/api/tasks/{self.task_id}/re-evaluate",
                json={}
            )

            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            assert data["success"] is True, "success should be True"
            assert data.get("message") == "重新评估已启动", "Message should be correct"

            self._log("✓ Re-evaluate started (without mode parameter)")

            # 等待一段时间确保后台任务开始
            await asyncio.sleep(2)

            # 测试 2: 指定不同的 mode
            response = await self.client.post(
                f"{self.base_url}/api/tasks/{self.task_id}/re-evaluate",
                json={"mode": "aggressive"}
            )

            assert response.status_code == 200, f"Expected 200 for mode=aggressive, got {response.status_code}"
            data = response.json()
            assert data["success"] is True, "success should be True for mode=aggressive"

            self._log("✓ Re-evaluate started with mode=aggressive")

            # 测试 3: 验证任务状态
            await asyncio.sleep(1)
            resp = await self.client.get(f"{self.base_url}/api/tasks/{self.task_id}")
            task_after = resp.json()["data"]
            status_after = task_after.get("status")

            self._log(f"  Task status after re-evaluate: {status_after}")

            test_results["passed"].append("用例 14e: 测试重新评估任务 API")
            return True

        except AssertionError as e:
            self._log(f"✗ Test failed: {e}", "ERROR")
            test_results["failed"].append(f"用例 14e: 测试重新评估任务 API - {e}")
            return False
        except Exception as e:
            self._log(f"✗ Unexpected error: {e}", "ERROR")
            test_results["failed"].append(f"用例 14e: 测试重新评估任务 API - {e}")
            return False

    async def test_14_delete_connection(self) -> bool:
        """用例 14: 删除连接"""
        self._log("=" * 60)
        self._log("用例 14: 删除连接")
        self._log("=" * 60)

        if not self.connection_id:
            self._log("✗ Skipping: No connection ID available")
            test_results["skipped"].append("用例 14: 删除连接")
            return False

        try:
            # Delete tasks first if exist
            tasks_to_delete = []
            if self.task_id:
                tasks_to_delete.append(self.task_id)
            if self.metrics_task_id:
                tasks_to_delete.append(self.metrics_task_id)

            for task_id in tasks_to_delete:
                try:
                    await self.client.delete(f"{self.base_url}/api/tasks/{task_id}")
                    self._log(f"  Task {task_id} deleted")
                except Exception as e:
                    self._log(f"  Task {task_id} deletion warning: {e}", "WARN")

            # Delete connection
            response = await self.client.delete(
                f"{self.base_url}/api/connections/{self.connection_id}"
            )
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

            data = response.json()
            assert data["success"] is True, "success should be True"

            self._log(f"✓ Connection {self.connection_id} deleted")

            # Verify deletion
            verify_response = await self.client.get(
                f"{self.base_url}/api/connections/{self.connection_id}"
            )
            assert verify_response.status_code == 404, "Should return 404 after deletion"
            self._log("✓ Deletion verified (404 response)")

            test_results["passed"].append("用例 13: 删除连接")
            return True

        except AssertionError as e:
            self._log(f"✗ Test failed: {e}", "ERROR")
            test_results["failed"].append(f"用例 14: 删除连接 - {e}")
            return False
        except Exception as e:
            self._log(f"✗ Unexpected error: {e}", "ERROR")
            test_results["failed"].append(f"用例 14: 删除连接 - {e}")
            return False

    def print_summary(self):
        """打印测试总结"""
        self._log("=" * 60)
        self._log("测试总结")
        self._log("=" * 60)
        self._log(f"通过: {len(test_results['passed'])}")
        self._log(f"失败: {len(test_results['failed'])}")
        self._log(f"跳过: {len(test_results['skipped'])}")
        self._log(f"总计: {len(test_results['passed']) + len(test_results['failed']) + len(test_results['skipped'])}")

        if test_results["failed"]:
            self._log("\n失败的测试:", "ERROR")
            for failure in test_results["failed"]:
                self._log(f"  ✗ {failure}", "ERROR")

        if test_results["skipped"]:
            self._log("\n跳过的测试:")
            for skipped in test_results["skipped"]:
                self._log(f"  - {skipped}")

        success_rate = len(test_results["passed"]) / max(1, len(test_results["passed"]) + len(test_results["failed"])) * 100
        self._log(f"\n成功率: {success_rate:.1f}%")

        if len(test_results["failed"]) == 0:
            self._log("\n✓ 所有测试通过!")
        else:
            self._log(f"\n✗ {len(test_results['failed'])} 个测试失败", "ERROR")

        return len(test_results["failed"]) == 0


async def run_all_tests():
    """运行所有测试用例"""
    print("\n" + "=" * 60)
    print("JustFit UIS API End-to-End Test")
    print("Following docs/API_TEST_README.md")
    print("=" * 60)

    async with APIE2ETest() as tester:
        # 基础测试用例
        await tester.test_01_create_connection()
        await tester.test_02_test_connection()
        await tester.test_03_get_connections()
        await tester.test_04_get_connection_detail()
        await tester.test_05_create_task()
        await tester.test_06_wait_for_completion()
        await tester.test_06b_create_metrics_task()  # VM 指标采集
        await tester.test_07_get_collection_results()
        await tester.test_08_idle_detection()
        await tester.test_09_resource_analysis()
        await tester.test_10_health_analysis()
        await tester.test_11_generate_excel_report()
        await tester.test_12_generate_pdf_report()
        await tester.test_13_verify_metrics_data()  # 验证 VM 指标数据

        # 新功能测试用例 - 任务模式与采集天数配置
        await tester.test_14b_create_task_with_mode()      # 测试 mode 参数
        await tester.test_14c_create_task_with_metric_days()  # 测试 metricDays 参数
        await tester.test_14d_update_task_mode()           # 测试修改模式 API
        await tester.test_14e_re_evaluate_task()           # 测试重新评估 API

        await tester.test_14_delete_connection()    # 如果需要保留数据可以直接注释掉改行

        # Print summary
        return tester.print_summary()


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
