"""Analysis Modes - Preset configurations for different analysis modes."""

from typing import Dict, Any, List


class AnalysisModes:
    """Analysis mode preset configurations."""

    MODES = {
        "safe": {
            "description": "安全模式 - 保守阈值，适合生产环境",
            "zombie": {
                "days": 30,
                "cpu_threshold": 5.0,
                "memory_threshold": 10.0,
                "disk_io_threshold": 5.0,
                "network_threshold": 5.0,
                "min_confidence": 80.0,
            },
            "rightsize": {
                "days": 14,
                "cpu_buffer_percent": 30.0,
                "memory_buffer_percent": 30.0,
                "high_usage_threshold": 85.0,
                "low_usage_threshold": 15.0,
                "min_confidence": 70.0,
            },
            "tidal": {
                "days": 30,
                "peak_threshold": 80.0,
                "valley_threshold": 30.0,
                "min_stability": 70.0,
            },
            "health": {
                "overcommit_threshold": 120.0,
                "hotspot_threshold": 85.0,
                "balance_threshold": 0.5,
            },
        },
        "saving": {
            "description": "节省模式 - 平衡阈值，推荐默认",
            "zombie": {
                "days": 14,
                "cpu_threshold": 10.0,
                "memory_threshold": 20.0,
                "disk_io_threshold": 5.0,
                "network_threshold": 5.0,
                "min_confidence": 60.0,
            },
            "rightsize": {
                "days": 7,
                "cpu_buffer_percent": 20.0,
                "memory_buffer_percent": 20.0,
                "high_usage_threshold": 90.0,
                "low_usage_threshold": 30.0,
                "min_confidence": 60.0,
            },
            "tidal": {
                "days": 14,
                "peak_threshold": 75.0,
                "valley_threshold": 35.0,
                "min_stability": 50.0,
            },
            "health": {
                "overcommit_threshold": 150.0,
                "hotspot_threshold": 90.0,
                "balance_threshold": 0.6,
            },
        },
        "aggressive": {
            "description": "激进模式 - 最大化发现问题",
            "zombie": {
                "days": 7,
                "cpu_threshold": 15.0,
                "memory_threshold": 25.0,
                "disk_io_threshold": 10.0,
                "network_threshold": 10.0,
                "min_confidence": 50.0,
            },
            "rightsize": {
                "days": 7,
                "cpu_buffer_percent": 10.0,
                "memory_buffer_percent": 10.0,
                "high_usage_threshold": 95.0,
                "low_usage_threshold": 40.0,
                "min_confidence": 50.0,
            },
            "tidal": {
                "days": 7,
                "peak_threshold": 70.0,
                "valley_threshold": 40.0,
                "min_stability": 30.0,
            },
            "health": {
                "overcommit_threshold": 200.0,
                "hotspot_threshold": 95.0,
                "balance_threshold": 0.7,
            },
        },
        "custom": {
            "description": "自定义模式 - 用户自定义配置",
            "zombie": {},
            "rightsize": {},
            "tidal": {},
            "health": {},
        },
    }

    @classmethod
    def get_mode(cls, mode_name: str) -> Dict[str, Any]:
        """Get mode configuration.

        Args:
            mode_name: Mode name (safe, saving, aggressive, custom)

        Returns:
            Mode configuration dict
        """
        return cls.MODES.get(mode_name, cls.MODES["custom"])

    @classmethod
    def list_modes(cls) -> Dict[str, Dict]:
        """List all available modes.

        Returns:
            Dict of mode configurations
        """
        return {
            "safe": cls.MODES["safe"],
            "saving": cls.MODES["saving"],
            "aggressive": cls.MODES["aggressive"],
            "custom": cls.MODES["custom"],
        }

    @classmethod
    def get_mode_names(cls) -> List[str]:
        """Get list of mode names.

        Returns:
            List of mode names
        """
        return ["safe", "saving", "aggressive", "custom"]

    @classmethod
    def update_custom_mode(
        cls,
        analysis_type: str,
        config: Dict[str, Any],
    ) -> None:
        """Update custom mode configuration.

        Args:
            analysis_type: Analysis type (zombie, rightsize, tidal, health)
            config: New configuration
        """
        if analysis_type in cls.MODES["custom"]:
            cls.MODES["custom"][analysis_type] = config
