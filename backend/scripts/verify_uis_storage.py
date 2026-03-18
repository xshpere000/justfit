"""验证 H3C UIS 连接器的存储数据采集."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.connectors.uis import UISConnector


async def main():
    connector = UISConnector(
        host="10.103.115.8",
        port=443,
        username="admin",
        password="Admin@123.",
        insecure=True,
    )

    try:
        # 1. 验证集群存储
        print("=" * 60)
        print("集群存储信息")
        print("=" * 60)
        clusters = await connector.get_clusters()
        if not clusters:
            print("[WARN] 未获取到集群数据")
        for c in clusters:
            total_gb = c.total_storage / (1024**3) if c.total_storage else 0
            used_gb = c.used_storage / (1024**3) if c.used_storage else 0
            print(f"  集群: {c.name}")
            print(f"    总存储: {total_gb:.2f} GB")
            print(f"    已用存储: {used_gb:.2f} GB")
            print(f"    total_storage(raw): {c.total_storage}")
            print(f"    used_storage(raw): {c.used_storage}")
            print()

        # 2. 验证 VM 磁盘使用量
        print("=" * 60)
        print("VM 磁盘使用量（前 5 台）")
        print("=" * 60)
        vms = await connector.get_vms()
        if not vms:
            print("[WARN] 未获取到 VM 数据")
        for vm in vms[:5]:
            disk_gb = vm.disk_usage_bytes / (1024**3) if vm.disk_usage_bytes else 0
            print(f"  VM: {vm.name}")
            print(f"    磁盘使用: {disk_gb:.2f} GB")
            print(f"    disk_usage_bytes(raw): {vm.disk_usage_bytes}")
            print()

        # 3. 汇总
        print("=" * 60)
        print("汇总")
        print("=" * 60)
        print(f"  集群数: {len(clusters)}")
        print(f"  VM 总数: {len(vms)}")
        has_storage = any(c.total_storage and c.total_storage > 0 for c in clusters)
        has_disk = any(vm.disk_usage_bytes and vm.disk_usage_bytes > 0 for vm in vms)
        print(f"  集群存储有值: {'YES' if has_storage else 'NO'}")
        print(f"  VM 磁盘有值: {'YES' if has_disk else 'NO'}")

    finally:
        await connector.close()


if __name__ == "__main__":
    asyncio.run(main())
