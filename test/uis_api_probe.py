#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UIS 单脚本接口测试工具

目标：
- 只用一个脚本完成 UIS 接口探测
- 每个接口的请求与响应统一落在一个 JSON 文件中
- 必要参数通过命令行选项传入（如时间范围、周期、vm_id）
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests


DEFAULT_H3C_HOST = "https://10.103.125.116/uis/login"
DEFAULT_H3C_USERNAME = "admin"
DEFAULT_H3C_PASSWORD = "Admin@123."

REPORT_TYPES: Dict[str, Dict[str, Any]] = {
    "cpu": {"url": "/report/cpuMemVm", "type": 0, "name": "CPU利用率"},
    "memory": {"url": "/report/cpuMemVm", "type": 1, "name": "内存利用率"},
    "disk_read": {"url": "/report/diskVm", "type": 0, "name": "磁盘读速率"},
    "disk_write": {"url": "/report/diskVm", "type": 1, "name": "磁盘写速率"},
    "disk_usage": {"url": "/report/diskVm", "type": 3, "name": "磁盘利用率"},
    "io": {"url": "/report/ioVm", "type": 0, "name": "磁盘I/O吞吐量"},
    "net_total": {"url": "/report/netVm", "type": 0, "name": "网络总量"},
    "net_in": {"url": "/report/netVm", "type": 1, "name": "网络读流量"},
    "net_out": {"url": "/report/netVm", "type": 2, "name": "网络写流量"},
    "net_sp_in": {"url": "/report/netSpVm", "type": 0, "name": "网络读速率"},
    "net_sp_out": {"url": "/report/netSpVm", "type": 1, "name": "网络写速率"},
}


def normalize_host(raw: str) -> str:
    text = (raw or "").strip().strip("<>")
    if text.startswith("http://") or text.startswith("https://"):
        parsed = urlparse(text)
        if parsed.netloc:
            return parsed.netloc
    return text


class UISProbe:
    def __init__(self, host: str, username: str, password: str, verify_ssl: bool, timeout: int):
        self.host = normalize_host(host)
        self.base = f"https://{self.host}"
        self.username = username
        self.password = password
        self.timeout = timeout

        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update({"Content-Type": "application/json"})

        if not verify_ssl:
            requests.packages.urllib3.disable_warnings()  # type: ignore[attr-defined]

    def _request_once(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = self.base + path
        started = time.time()
        response = self.session.request(method=method, url=url, params=params, timeout=self.timeout)
        elapsed_ms = int((time.time() - started) * 1000)

        body: Any
        try:
            body = response.json()
        except Exception:
            body = response.text

        return {
            "request": {
                "method": method,
                "url": url,
                "path": path,
                "params": params or {},
            },
            "response": {
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
                "ok": 200 <= response.status_code < 300,
                "body": body,
            },
        }

    def request_with_fallback(self, method: str, paths: List[str], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        attempts: List[Dict[str, Any]] = []
        selected: Optional[Dict[str, Any]] = None

        for path in paths:
            result = self._request_once(method, path, params=params)
            attempts.append(result)
            body = result["response"]["body"]
            if result["response"]["ok"] and isinstance(body, (dict, list)):
                selected = result
                break

        if selected is None and attempts:
            selected = attempts[-1]

        return {
            "selected": selected,
            "attempts": attempts,
        }

    def login(self) -> Dict[str, Any]:
        params = {
            "encrypt": "false",
            "loginType": "authorCenter",
            "name": self.username,
            "password": self.password,
        }
        result = self._request_once("POST", "/uis/spring_check", params=params)

        body = result["response"]["body"]
        login_success = False
        login_message = None

        if isinstance(body, dict):
            code = body.get("loginFailErrorCode")
            login_success = (code == 0 or code is None)
            login_message = body.get("loginFailMessage")

        result["auth"] = {
            "login_success": login_success,
            "login_message": login_message,
        }
        return result


def build_common_resource_params(args: argparse.Namespace) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    if args.hp_id is not None:
        params["hpId"] = args.hp_id
    if args.cluster_id is not None:
        params["clusterId"] = args.cluster_id
    if args.host_id is not None:
        params["hostId"] = args.host_id
    if args.vm_id is not None:
        params["vmId"] = args.vm_id
    return params


def extract_vm_list(interface_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    selected = interface_result.get("selected") or {}
    response = selected.get("response") or {}
    body = response.get("body")
    if not isinstance(body, dict):
        return []

    entity = body.get("entity")
    if isinstance(entity, dict):
        data = entity.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]

    data = body.get("data")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]

    return []


def resolve_vm_id(args: argparse.Namespace, vm_summary_result: Dict[str, Any], legacy_vm_result: Dict[str, Any]) -> Optional[int]:
    if args.vm_id is not None:
        return args.vm_id

    for source in (vm_summary_result, legacy_vm_result):
        vm_list = extract_vm_list(source)
        if not vm_list:
            continue
        raw = vm_list[0].get("id")
        if isinstance(raw, int):
            return raw
        if isinstance(raw, float):
            return int(raw)

    return None


def write_output(output: str, data: Dict[str, Any]) -> Path:
    path = Path(output)

    if path.exists() and path.is_dir():
        path = path / f"uis_interfaces_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    elif not path.suffix:
        path.mkdir(parents=True, exist_ok=True)
        path = path / f"uis_interfaces_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    if path.parent:
        path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="UIS 单脚本接口测试工具")

    parser.add_argument("--host", default=DEFAULT_H3C_HOST, help="UIS地址，支持 host[:port] 或完整登录URL")
    parser.add_argument("--ip", help="兼容参数，优先于 --host")
    parser.add_argument("--username", default=DEFAULT_H3C_USERNAME, help="UIS 用户名")
    parser.add_argument("--password", default=DEFAULT_H3C_PASSWORD, help="UIS 密码")
    parser.add_argument("--verify-ssl", action="store_true", help="启用证书校验（默认关闭）")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP超时秒数")

    parser.add_argument("--hp-id", type=int, help="主机池ID")
    parser.add_argument("--cluster-id", type=int, help="集群ID")
    parser.add_argument("--host-id", type=int, help="主机ID")
    parser.add_argument("--vm-id", type=int, help="虚拟机ID（不传则自动从VM列表取第一条）")

    parser.add_argument("--start-time", default=datetime.now().strftime("%Y-%m-%d"), help="报表开始时间")
    parser.add_argument("--end-time", default=datetime.now().strftime("%Y-%m-%d"), help="报表结束时间")
    parser.add_argument("--cycle", type=int, default=1, choices=[0, 1, 2, 3, 4], help="报表统计周期")
    parser.add_argument("--metrics", nargs="+", choices=list(REPORT_TYPES.keys()), help="要测试的报表指标，默认全部")

    parser.add_argument("-o", "--output", default="tmp/uis_interfaces_result.json", help="输出JSON文件或目录")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    host = args.ip if args.ip else args.host

    probe = UISProbe(
        host=host,
        username=args.username,
        password=args.password,
        verify_ssl=args.verify_ssl,
        timeout=args.timeout,
    )

    result: Dict[str, Any] = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "host": host,
            "normalized_host": normalize_host(host),
            "verify_ssl": args.verify_ssl,
            "timeout": args.timeout,
            "time_range": {
                "start_time": args.start_time,
                "end_time": args.end_time,
                "cycle": args.cycle,
            },
        },
        "interfaces": {},
    }

    # 1. 登录
    login_result = probe.login()
    result["interfaces"]["login"] = login_result
    if not (login_result.get("auth") or {}).get("login_success"):
        result["meta"]["success"] = False
        result["meta"]["reason"] = "login_failed"
        out = write_output(args.output, result)
        result["meta"]["output_file"] = str(out)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    # 2. 资源接口
    common_params = build_common_resource_params(args)

    vm_summary = probe.request_with_fallback(
        "GET",
        ["/uis/vm/list/summary", "/uis/uis/vm/list/summary"],
        common_params,
    )
    result["interfaces"]["vm_summary"] = vm_summary

    legacy_vm = probe.request_with_fallback(
        "GET",
        ["/uis/uis/btnSeries/resourceDetail", "/uis/btnSeries/resourceDetail"],
        {"offset": 0, "limit": 1000},
    )
    result["interfaces"]["vm_list_legacy"] = legacy_vm

    cluster_summary = probe.request_with_fallback(
        "GET",
        ["/uis/cluster/clusterInfo/basic", "/uis/uis/cluster/clusterInfo/basic"],
        {k: v for k, v in common_params.items() if k in ["hpId", "clusterId"]},
    )
    result["interfaces"]["cluster_summary"] = cluster_summary

    host_summary = probe.request_with_fallback(
        "GET",
        ["/uis/host/summary", "/uis/uis/host/summary"],
        {k: v for k, v in common_params.items() if k in ["hpId", "clusterId", "hostId"]},
    )
    result["interfaces"]["host_summary"] = host_summary

    # 3. 报表接口
    vm_id = resolve_vm_id(args, vm_summary, legacy_vm)
    result["meta"]["resolved_vm_id"] = vm_id

    metrics = args.metrics or list(REPORT_TYPES.keys())
    result["interfaces"]["vm_reports"] = {}

    if vm_id is None:
        result["interfaces"]["vm_reports"] = {
            "skipped": True,
            "reason": "no_vm_id",
            "message": "未提供 --vm-id 且无法从 VM 列表推断第一条 VM ID",
        }
    else:
        for metric in metrics:
            config = REPORT_TYPES[metric]
            report_params = {
                "domainId": vm_id,
                "cycle": args.cycle,
                "startTime": args.start_time,
                "endTime": args.end_time,
                "type": config["type"],
            }
            report_result = probe.request_with_fallback(
                "GET",
                [
                    "/uis" + config["url"],
                    "/uis/uis" + config["url"],
                ],
                report_params,
            )
            result["interfaces"]["vm_reports"][metric] = report_result

    result["meta"]["success"] = True
    result["meta"]["finished_at"] = datetime.now().isoformat()

    out = write_output(args.output, result)
    result["meta"]["output_file"] = str(out)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
