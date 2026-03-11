#!/usr/bin/env python3.14
"""测试任务创建时 selectedVMs 参数的处理"""

import sys
sys.path.insert(0, '/home/worker/pengxin/TEMP/justfit/backend')

def test_selected_vms_handling():
    """模拟任务创建时的参数处理"""

    # 模拟 API 请求数据
    data = {
        "name": "VCF-测试",
        "type": "collection",
        "connectionId": 1,
        "mode": "saving",
        "metricDays": 30,
        "selectedVMs": ["conn1:uuid:564d784a-fbe8-7d9c-1b7c-e89321f4388b"]
    }

    # 模拟 task.py 中的处理逻辑
    task_name = data.get("name", "New Task")
    task_type = data.get("type", "collection")
    connection_id = data.get("connectionId")
    mode = data.get("mode", "saving")
    metric_days = data.get("metricDays")

    # 将 mode、metricDays、baseMode 和 selectedVMs 合并到 config 中
    config = data.get("config") or {}
    if mode:
        config["mode"] = mode
    if metric_days:
        config["metricDays"] = metric_days
    # 保存 baseMode 用于 custom 模式
    base_mode = data.get("baseMode")
    if base_mode:
        config["baseMode"] = base_mode
    # 保存 selectedVMs 列表
    selected_vms = data.get("selectedVMs")

    print(f"selected_vms: {selected_vms}")
    print(f"selected_vms is not None: {selected_vms is not None}")

    if selected_vms is not None:
        config["selectedVMs"] = selected_vms
        config["selectedVMCount"] = len(selected_vms)
        print(f"✓ selectedVMs 已添加到 config")
        print(f"✓ config: {config}")
    else:
        print(f"✗ selectedVMs 为 None，未添加到 config")

if __name__ == "__main__":
    test_selected_vms_handling()
