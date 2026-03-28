from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class AppConfig:
    gemini_api_key: str
    qwen_asr_base_url: str
    fish_tts_base_url: str
    audio_sample_rate: int = 16000
    vad_start_ms: int = 120
    vad_interrupt_ms: int = 200
    turn_silence_ms: int = 600
    log_level: str = "INFO"


def _required(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        raise ConfigError(f"Missing required env: {name}")
    return value


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"Invalid int for {name}: {raw}") from exc


def _load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def load_config() -> AppConfig:
    return AppConfig(
        gemini_api_key=_required("GEMINI_API_KEY"),
        qwen_asr_base_url=_required("QWEN_ASR_BASE_URL"),
        fish_tts_base_url=_required("FISH_TTS_BASE_URL"),
        audio_sample_rate=_int("AUDIO_SAMPLE_RATE", 16000),
        vad_start_ms=_int("VAD_START_MS", 120),
        vad_interrupt_ms=_int("VAD_INTERRUPT_MS", 200),
        turn_silence_ms=_int("TURN_SILENCE_MS", 600),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


__all__ = ["AppConfig", "ConfigError", "load_config", "_load_dotenv"]
