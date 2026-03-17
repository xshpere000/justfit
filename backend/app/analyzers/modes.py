"""Analysis Modes - Preset configurations for different analysis modes."""

from typing import Dict, Any, List
import copy


class AnalysisModes:
    """Analysis mode preset configurations."""

    MODES = {
        "safe": {
            "description": "安全模式 - 保守阈值，适合生产环境",
            "idle": {
                "days": 30,
                "cpu_threshold": 5.0,
                "memory_threshold": 10.0,
                "min_confidence": 80.0,
            },
            "resource": {
                "rightsize": {
                    "days": 30,
                    "cpu_buffer_percent": 30.0,
                    "memory_buffer_percent": 30.0,
                    "min_confidence": 70.0,
                },
                "usage_pattern": {
                    "cv_threshold": 0.3,
                    "peak_valley_ratio": 2.0,
                },
            },
            "health": {
                "overcommit_threshold": 1.2,
                "hotspot_threshold": 5.0,
                "balance_threshold": 0.5,
            },
        },
        "saving": {
            "description": "节省模式 - 平衡阈值，推荐默认",
            "idle": {
                "days": 14,
                "cpu_threshold": 10.0,
                "memory_threshold": 20.0,
                "min_confidence": 60.0,
            },
            "resource": {
                "rightsize": {
                    "days": 14,
                    "cpu_buffer_percent": 20.0,
                    "memory_buffer_percent": 20.0,
                    "min_confidence": 60.0,
                },
                "usage_pattern": {
                    "cv_threshold": 0.4,
                    "peak_valley_ratio": 2.5,
                },
            },
            "health": {
                "overcommit_threshold": 1.5,
                "hotspot_threshold": 7.0,
                "balance_threshold": 0.6,
            },
        },
        "aggressive": {
            "description": "激进模式 - 最大化发现问题",
            "idle": {
                "days": 7,
                "cpu_threshold": 15.0,
                "memory_threshold": 25.0,
                "min_confidence": 50.0,
            },
            "resource": {
                "rightsize": {
                    "days": 7,
                    "cpu_buffer_percent": 10.0,
                    "memory_buffer_percent": 10.0,
                    "min_confidence": 50.0,
                },
                "usage_pattern": {
                    "cv_threshold": 0.5,
                    "peak_valley_ratio": 3.0,
                },
            },
            "health": {
                "overcommit_threshold": 2.0,
                "hotspot_threshold": 10.0,
                "balance_threshold": 0.7,
            },
        },
        "custom": {
            "description": "自定义模式 - 用户自定义配置",
            "idle": {},
            "resource": {
                "rightsize": {},
                "usage_pattern": {},
            },
            "health": {},
        },
    }

    @classmethod
    def get_mode(cls, mode_name: str) -> Dict[str, Any]:
        """Get mode configuration.

        Args:
            mode_name: Mode name (safe, saving, aggressive, custom)

        Returns:
            Mode configuration dict (deep copy to prevent mutation)
        """
        return copy.deepcopy(cls.MODES.get(mode_name, cls.MODES["custom"]))

    @classmethod
    def list_modes(cls) -> Dict[str, Dict]:
        """List all available modes.

        Returns:
            Dict of mode configurations (deep copies to prevent mutation)
        """
        return {
            "safe": copy.deepcopy(cls.MODES["safe"]),
            "saving": copy.deepcopy(cls.MODES["saving"]),
            "aggressive": copy.deepcopy(cls.MODES["aggressive"]),
            "custom": copy.deepcopy(cls.MODES["custom"]),
        }

    @classmethod
    def get_mode_names(cls) -> List[str]:
        """Get list of mode names.

        Returns:
            List of mode names
        """
        return ["safe", "saving", "aggressive", "custom"]
