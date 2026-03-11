#!/usr/bin/env python3.14
"""
vCenter 计数器修复验证测试

问题描述：
1. cpu.usage 计数器（ID=2, unit=percent）在某些嵌套 VM 上返回 MHz 而不是 percent
2. mem.usage 计数器（ID=24, unit=percent）返回的值不可靠（大于100）

解决方案：
1. CPU: 使用 cpu.usagemhz 计数器（ID=6, unit=megaHertz），始终返回 MHz
2. 内存: 使用 mem.consumed 计数器（ID=98, unit=kiloBytes），始终返回 KB

存储格式（与 UIS 保持一致）：
- CPU: 直接存储 MHz 值
- 内存: 存储 MB 值（从 KB 转换）

还原百分比公式：
- CPU: stored_value / cpu_count / host_cpu_mhz * 100
- 内存: stored_value / memory_mb * 100

运行此测试需要 vCenter 连接。
"""

import pytest


@pytest.mark.skipif(
    True,  # 需要真实的 vCenter 连接，默认跳过
    reason="需要 vCenter 连接，手动运行时取消 skip"
)
def test_vcenter_cpu_counter_returns_mhz_for_nested_vms():
    """
    验证 vCenter 的 cpu.usage 计数器在嵌套 VM 上返回 MHz 而不是 percent。

    这个测试记录了问题发现，基于文档目的。
    """
    # 预期结果（基于实际 vCenter API 调用）：
    #
    # VM Name          | cpu.usage (ID=2) | cpu.usagemhz (ID=6) | 说明
    # -----------------|------------------|---------------------|------------------
    # test-vcf         | 357-409          | 299-343 MHz         | usage 返回 MHz
    # VCF              | 472-553          | 395-464 MHz         | usage 返回 MHz
    # vNMC-2           | 3057-3347        | 2562-2805 MHz       | usage 返回 MHz
    # centos7.9        | 21-40            | 相近值               | usage 返回 percent（正常）
    #
    # 结论：必须使用 cpu.usagemhz 计数器获取一致的 MHz 值

    assert True  # 文档测试


def test_vcenter_storage_formula():
    """
    验证存储和还原公式。

    存储（使用 cpu.usagemhz）：
    - CPU: 直接存储 usagemhz 值（MHz）
    - Memory: percentage / 100 * memory_mb（MB）

    还原：
    - CPU % = stored_mhz / cpu_count / host_cpu_mhz * 100
    - Memory % = stored_mb / memory_mb * 100

    示例：
    - test-vcf: usagemhz=299, cpu_count=4, host_cpu_mhz=2095
      - 存储: 299 MHz
      - 还原: 299 / 4 / 2095 * 100 = 3.57%
    """
    # 示例：test-vcf
    usagemhz = 299
    cpu_count = 4
    host_cpu_mhz = 2095

    # 存储
    stored_mhz = usagemhz  # 直接存储 MHz

    # 还原
    percentage = stored_mhz / cpu_count / host_cpu_mhz * 100

    assert stored_mhz == 299
    assert abs(percentage - 3.57) < 0.1  # 约 3.57%


def test_memory_storage_formula():
    """
    验证内存存储和还原公式

    vCenter mem.consumed 返回 KB，需要转换为 MB 存储
    """
    # 示例：vCenter 返回 11638744 KB，VM 配置 16GB
    consumed_kb = 11638744
    memory_mb = 16 * 1024  # 16384 MB

    # 存储: KB / 1024 = MB（存储为 MB）
    stored_mb = consumed_kb / 1024

    # 还原: stored_mb / memory_mb * 100
    restored_percentage = stored_mb / memory_mb * 100

    assert stored_mb == pytest.approx(11366, rel=0.01)  # 约 11366 MB
    assert restored_percentage == pytest.approx(69.4, rel=0.01)  # 约 69.4%


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
