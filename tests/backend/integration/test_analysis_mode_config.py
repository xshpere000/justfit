"""评估模式配置集成测试.

测试评估模式的配置保存、字段名转换、以及分析器正确使用配置。
"""

import pytest
import json
from app.analyzers.modes import AnalysisModes
from app.services.analysis import AnalysisService
from app.routers.task import camel_to_snake, convert_config_keys_to_snake


class TestFieldNameConversion:
    """测试字段名转换功能."""

    def test_camel_to_snake_basic(self):
        """测试基本的 camelCase 到 snake_case 转换."""
        test_cases = {
            "cpuBufferPercent": "cpu_buffer_percent",
            "memoryBufferPercent": "memory_buffer_percent",
            "usagePattern": "usage_pattern",
            "minConfidence": "min_confidence",
            "highUsageThreshold": "high_usage_threshold",
            "lowUsageThreshold": "low_usage_threshold",
            "cpuThreshold": "cpu_threshold",
            "cvThreshold": "cv_threshold",
            "peakValleyRatio": "peak_valley_ratio",
            "cpuLowThreshold": "cpu_low_threshold",
            "cpuHighThreshold": "cpu_high_threshold",
            "overcommitThreshold": "overcommit_threshold",
            "hotspotThreshold": "hotspot_threshold",
            "balanceThreshold": "balance_threshold",
        }

        for camel, expected in test_cases.items():
            result = camel_to_snake(camel)
            assert result == expected, f"{camel} -> {result}, expected: {expected}"

    def test_convert_config_keys_to_snake_flat(self):
        """测试扁平配置的转换."""
        config = {
            "cpuBufferPercent": 20.0,
            "memoryBufferPercent": 20.0,
            "minConfidence": 60.0,
        }

        result = convert_config_keys_to_snake(config)

        assert result == {
            "cpu_buffer_percent": 20.0,
            "memory_buffer_percent": 20.0,
            "min_confidence": 60.0,
        }

    def test_convert_config_keys_to_snake_nested(self):
        """测试嵌套配置的转换."""
        config = {
            "resource": {
                "rightsize": {
                    "cpuBufferPercent": 20.0,
                    "highUsageThreshold": 90.0,
                },
                "usagePattern": {
                    "cvThreshold": 0.4,
                    "peakValleyRatio": 2.5,
                },
            }
        }

        result = convert_config_keys_to_snake(config)

        assert result == {
            "resource": {
                "rightsize": {
                    "cpu_buffer_percent": 20.0,
                    "high_usage_threshold": 90.0,
                },
                "usage_pattern": {
                    "cv_threshold": 0.4,
                    "peak_valley_ratio": 2.5,
                },
            }
        }

    def test_usage_pattern_special_case(self):
        """测试 usagePattern 的特殊转换."""
        config = {"usagePattern": {"cvThreshold": 0.4}}
        result = convert_config_keys_to_snake(config)

        # usagePattern 应该转换为 usage_pattern
        assert "usage_pattern" in result
        assert result["usage_pattern"]["cv_threshold"] == 0.4


class TestAnalysisModeStructure:
    """测试评估模式配置结构."""

    def test_modes_structure(self):
        """测试 modes.py 中的配置结构使用 snake_case."""
        modes = ["safe", "saving", "aggressive"]

        for mode in modes:
            config = AnalysisModes.get_mode(mode)

            # 验证 resource 结构使用 snake_case
            assert "resource" in config
            assert "rightsize" in config["resource"]
            assert "usage_pattern" in config["resource"]
            assert "mismatch" in config["resource"]

            # 验证 rightsize 字段使用 snake_case
            rightsize = config["resource"]["rightsize"]
            assert "cpu_buffer_percent" in rightsize
            assert "memory_buffer_percent" in rightsize
            assert "high_usage_threshold" in rightsize
            assert "low_usage_threshold" in rightsize
            assert "min_confidence" in rightsize

            # 验证 usage_pattern 字段使用 snake_case
            usage_pattern = config["resource"]["usage_pattern"]
            assert "cv_threshold" in usage_pattern
            assert "peak_valley_ratio" in usage_pattern

    def test_idle_config_structure(self):
        """测试闲置检测配置结构."""
        config = AnalysisModes.get_mode("saving")

        assert "idle" in config
        idle = config["idle"]

        # 验证字段使用 snake_case
        assert "days" in idle
        assert "cpu_threshold" in idle
        assert "memory_threshold" in idle
        assert "min_confidence" in idle

    def test_health_config_structure(self):
        """测试健康评分配置结构."""
        config = AnalysisModes.get_mode("saving")

        assert "health" in config
        health = config["health"]

        # 验证字段使用 snake_case
        assert "overcommit_threshold" in health
        assert "hotspot_threshold" in health
        assert "balance_threshold" in health


class TestConfigMerge:
    """测试配置合并功能."""

    def test_merge_mode_config_basic(self):
        """测试基本的配置合并."""
        base_mode = "saving"
        custom_config = {
            "idle": {
                "cpu_threshold": 15.0,  # 覆盖默认的 10.0
                "min_confidence": 80.0,  # 覆盖默认的 60.0
            }
        }

        merged = AnalysisService.merge_mode_config(base_mode, custom_config)

        # 验证自定义配置已合并
        assert merged["idle"]["cpu_threshold"] == 15.0
        assert merged["idle"]["min_confidence"] == 80.0

        # 验证未覆盖的字段保持原值
        assert merged["idle"]["memory_threshold"] == 20.0  # saving 模式的默认值
        assert merged["idle"]["days"] == 30  # saving 模式的默认值

    def test_merge_mode_config_with_snake_case(self):
        """测试使用 snake_case 的配置合并（模拟转换后的前端配置）."""
        base_mode = "saving"
        # 这是前端配置经过 convert_config_keys_to_snake 转换后的结果
        custom_config = {
            "resource": {
                "rightsize": {
                    "cpu_buffer_percent": 30.0,  # 覆盖默认的 20.0
                    "min_confidence": 80.0,  # 覆盖默认的 60.0
                },
                "usage_pattern": {
                    "cv_threshold": 0.3,  # 覆盖默认的 0.4
                }
            }
        }

        merged = AnalysisService.merge_mode_config(base_mode, custom_config)

        # 验证自定义配置已合并
        assert merged["resource"]["rightsize"]["cpu_buffer_percent"] == 30.0
        assert merged["resource"]["rightsize"]["min_confidence"] == 80.0
        assert merged["resource"]["usage_pattern"]["cv_threshold"] == 0.3

        # 验证未覆盖的字段保持原值
        assert merged["resource"]["rightsize"]["memory_buffer_percent"] == 20.0  # 默认值
        assert merged["resource"]["usage_pattern"]["peak_valley_ratio"] == 2.5  # 默认值

    def test_merge_mode_config_deep_merge(self):
        """测试深度合并."""
        base_mode = "saving"
        custom_config = {
            "resource": {
                "rightsize": {
                    "cpu_buffer_percent": 30.0,
                    # 只覆盖部分字段
                }
            }
        }

        merged = AnalysisService.merge_mode_config(base_mode, custom_config)

        # 验证被覆盖的字段
        assert merged["resource"]["rightsize"]["cpu_buffer_percent"] == 30.0

        # 验证其他字段保持原值
        assert merged["resource"]["rightsize"]["memory_buffer_percent"] == 20.0
        assert merged["resource"]["rightsize"]["high_usage_threshold"] == 90.0


class TestFrontendToBackendFlow:
    """测试前端到后端的配置流程."""

    def test_full_config_flow(self):
        """测试完整的配置流程：前端 -> 字段转换 -> 合并 -> 分析器使用."""
        # 1. 模拟前端发送的配置（camelCase）
        frontend_config = {
            "cpuBufferPercent": 30.0,
            "memoryBufferPercent": 25.0,
            "minConfidence": 80.0,
        }

        # 2. 字段名转换
        converted_config = convert_config_keys_to_snake(frontend_config)
        assert converted_config == {
            "cpu_buffer_percent": 30.0,
            "memory_buffer_percent": 25.0,
            "min_confidence": 80.0,
        }

        # 3. 与基础模式合并
        base_mode = "saving"
        custom_config = {"resource": {"rightsize": converted_config}}
        merged = AnalysisService.merge_mode_config(base_mode, custom_config)

        # 4. 验证合并后的配置可以被分析器使用
        rightsize_config = merged["resource"]["rightsize"]
        assert rightsize_config["cpu_buffer_percent"] == 30.0
        assert rightsize_config["memory_buffer_percent"] == 25.0
        assert rightsize_config["min_confidence"] == 80.0
        # 其他字段来自基础模式
        assert rightsize_config["high_usage_threshold"] == 90.0
        assert rightsize_config["low_usage_threshold"] == 30.0

    def test_multiple_analysis_types_config(self):
        """测试多个分析类型的配置."""
        # 模拟前端发送的完整配置
        frontend_full_config = {
            "idle": {
                "cpuThreshold": 15.0,
                "minConfidence": 70.0,
            },
            "resource": {
                "rightsize": {
                    "cpuBufferPercent": 30.0,
                    "days": 14,
                },
                "usagePattern": {
                    "cvThreshold": 0.3,
                }
            },
            "health": {
                "overcommitThreshold": 1.8,
            }
        }

        # 转换每个分析类型的配置
        idle_converted = convert_config_keys_to_snake(frontend_full_config["idle"])
        resource_converted = convert_config_keys_to_snake(frontend_full_config["resource"])
        health_converted = convert_config_keys_to_snake(frontend_full_config["health"])

        # 验证转换结果
        assert idle_converted == {
            "cpu_threshold": 15.0,
            "min_confidence": 70.0,
        }

        assert resource_converted["rightsize"] == {
            "cpu_buffer_percent": 30.0,
            "days": 14,
        }
        assert resource_converted["usage_pattern"] == {
            "cv_threshold": 0.3,
        }

        assert health_converted == {
            "overcommit_threshold": 1.8,
        }
