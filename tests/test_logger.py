import logging
from unittest.mock import patch

import pytest

from app.observability.logger import log_timing, timing_payload


def test_timing_payload_rounds_elapsed_ms_to_int():
    payload = timing_payload(
        component="asr",
        operation="transcribe",
        provider="qwen",
        elapsed_ms=12.7,
    )

    assert payload == {
        "component": "asr",
        "operation": "transcribe",
        "provider": "qwen",
        "elapsed_ms": 13,
        "status": "ok",
    }


def test_log_timing_emits_structured_payload_on_success(caplog):
    logger = logging.getLogger("podcast.test")

    with patch(
        "app.observability.logger.time.perf_counter",
        side_effect=[10.0, 10.0254],
    ):
        with caplog.at_level(logging.INFO, logger="podcast.test"):
            with log_timing(
                logger,
                component="llm",
                operation="generate_outline",
                provider="gemini",
            ):
                pass

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.msg == "timing"
    assert record.component == "llm"
    assert record.operation == "generate_outline"
    assert record.provider == "gemini"
    assert record.status == "ok"
    assert record.elapsed_ms == 25


def test_log_timing_emits_error_payload_and_reraises(caplog):
    logger = logging.getLogger("podcast.test")

    with patch(
        "app.observability.logger.time.perf_counter",
        side_effect=[5.0, 5.0101],
    ):
        with caplog.at_level(logging.INFO, logger="podcast.test"):
            with pytest.raises(RuntimeError, match="boom"):
                with log_timing(
                    logger,
                    component="tts",
                    operation="synthesize",
                    provider="fish",
                ):
                    raise RuntimeError("boom")

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.msg == "timing"
    assert record.component == "tts"
    assert record.operation == "synthesize"
    assert record.provider == "fish"
    assert record.status == "error"
    assert record.elapsed_ms == 10
