"""Structured Logging Configuration."""

import logging
import logging.handlers
import sys
from pathlib import Path

import structlog

from app.config import settings


def setup_logging(level: int = logging.INFO) -> None:
    """Configure structured logging with console and file output."""

    # 确保日志目录存在
    log_dir = settings.DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "justfit.log"

    # 配置标准 logging root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除已有的 handlers
    root_logger.handlers.clear()

    # 格式化器
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. 控制台处理器 (带颜色)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 2. 文件处理器 (自动轮询)
    # 每个文件最大 10MB，保留 5 个备份
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 3. 设置 SQLAlchemy 相关 logger 级别为 WARNING，避免大量 SQL 日志
    # 这样可以屏蔽正常的 SQL 查询日志，只保留错误和警告
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)

    # 配置 structlog
    is_debug = settings.DEBUG

    # 创建共享的处理器
    def add_logger(logger, method_name, event_dict):
        """将 structlog 日志转发到标准 logging"""
        logger_name = event_dict.pop("logger_name", "app")
        level = event_dict.pop("level", "info").upper()
        msg = event_dict.pop("event", "")
        event_dict.pop("level_no", None)  # 移除 level_no

        # 构建日志消息
        extra = []
        for key, value in event_dict.items():
            if key not in {"logger_name", "timestamp", "asctime"}:
                extra.append(f"{key}={value}")

        if extra:
            full_msg = f"{msg} | " + " | ".join(extra)
        else:
            full_msg = msg

        # 获取标准 logger 并记录
        stdlib_logger = logging.getLogger(logger_name)
        log_level = getattr(logging, level, logging.INFO)
        stdlib_logger.log(log_level, full_msg)
        return event_dict

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            add_logger,
            # 生产环境用 JSON，开发环境用可读格式
            structlog.processors.JSONRenderer() if not is_debug else structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 记录日志文件位置
    logging.info(f"日志文件: {log_file}")
    logging.info(f"日志级别: {logging.getLevelName(level)}")
    logging.info(f"调试模式: {is_debug}")


def get_log_file_path() -> Path:
    """获取日志文件路径."""
    return settings.DATA_DIR / "logs" / "justfit.log"
