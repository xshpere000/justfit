"""验证 vCenter 存储数据采集脚本."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.connectors.vcenter import VCenterConnector

HOST = "10.103.116.116"
PORT = 443
USERNAME = "administrator@vsphere.local"
PASSWORD = "Admin@123."


async def main():
    connector = VCenterConnector(
        host=HOST, port=PORT, username=USERNAME,
        password=PASSWORD, insecure=True, timeout=30,
    )
    try:
        # 1. 集群存储信息
        print("=" * 60)
        print("集群存储信息")
        print("=" * 60)
        clusters = await connector.get_clusters()
        for c in clusters:
            total_gb = c.total_storage / (1024**3)
            used_gb = c.used_storage / (1024**3)
            pct = (used_gb / total_gb * 100) if total_gb > 0 else 0
            print(f"  {c.name}: 总存储={total_gb:.1f} GB, "
                  f"已用={used_gb:.1f} GB ({pct:.1f}%)")

        # 2. VM 磁盘使用量（前 5 台）
        print()
        print("=" * 60)
        print("VM 磁盘使用量（前 5 台）")
        print("=" * 60)
        vms = await connector.get_vms()
        for vm in vms[:5]:
            disk_gb = vm.disk_usage_bytes / (1024**3)
            print(f"  {vm.name}: 磁盘使用={disk_gb:.2f} GB, "
                  f"状态={vm.power_state}")

        # 3. 汇总
        print()
        print("=" * 60)
        print("汇总")
        print("=" * 60)
        total_vms = len(vms)
        vms_with_disk = sum(1 for v in vms if v.disk_usage_bytes > 0)
        print(f"  总 VM 数: {total_vms}")
        print(f"  有磁盘数据的 VM: {vms_with_disk}/{total_vms}")
    finally:
        await connector.close()


if __name__ == "__main__":
    asyncio.run(main())
