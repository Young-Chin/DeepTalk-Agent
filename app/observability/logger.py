from __future__ import annotations

from contextlib import contextmanager
import logging
import time
from collections.abc import Iterator
from typing import Any


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


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
    except Exception:
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
