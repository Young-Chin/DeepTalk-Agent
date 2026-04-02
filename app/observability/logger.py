from __future__ import annotations

from contextlib import contextmanager
import logging
import time
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any


# 运行日志文件路径
RUN_LOG_DIR = Path(__file__).parent.parent.parent / "logs"


def configure_logging(level: str = "INFO", log_to_file: bool = True) -> None:
    """配置日志系统
    
    Args:
        level: 日志级别
        log_to_file: 是否写入文件（默认写入 logs/run.log）
    """
    # 创建日志目录
    if log_to_file:
        RUN_LOG_DIR.mkdir(exist_ok=True)
    
    # 设置根日志配置
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 清除现有 handler
    root_logger.handlers.clear()
    
    # 控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = "%(asctime)s %(levelname)s %(name)s %(message)s"
    console_formatter = logging.Formatter(console_format, datefmt="%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 文件 handler（详细日志）
    if log_to_file:
        log_file = RUN_LOG_DIR / "run.log"
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_format = "%(asctime)s.%(msecs)03d %(levelname)s %(name)s [%(filename)s:%(lineno)d] %(message)s"
        file_formatter = logging.Formatter(file_format, datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # 记录启动信息
        root_logger.info("=" * 80)
        root_logger.info("应用启动，日志文件：%s", log_file)
        root_logger.info("=" * 80)


def log_event(logger: logging.Logger, event_type: str, **kwargs):
    """记录关键事件到日志"""
    logger.info(f"[EVENT] {event_type}", extra=kwargs)


def log_error_details(logger: logging.Logger, component: str, error: Exception):
    """记录详细错误信息"""
    logger.error(
        f"[ERROR] {component} 失败",
        extra={
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
    )
    logger.debug(f"[DEBUG] {component} 堆栈跟踪", exc_info=True)


def timing_payload(
    *,
    component: str,
    operation: str,
    provider: str,
    elapsed_ms: float,
    status: str = "ok",
    **extra: Any,
) -> dict[str, Any]:
    payload = {
        "component": component,
        "operation": operation,
        "provider": provider,
        "elapsed_ms": int(round(elapsed_ms)),
        "status": status,
    }
    payload.update(extra)
    return payload


@contextmanager
def log_timing(
    logger: logging.Logger,
    *,
    component: str,
    operation: str,
    provider: str,
    level: int = logging.INFO,
    **extra: Any,
) -> Iterator[None]:
    start = time.perf_counter()
    status = "ok"
    try:
        yield
    except Exception as exc:
        status = "error"
        raise
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        payload = timing_payload(
            component=component,
            operation=operation,
            provider=provider,
            elapsed_ms=elapsed_ms,
            status=status,
            **extra,
        )
        logger.log(level, "timing", extra=payload)
