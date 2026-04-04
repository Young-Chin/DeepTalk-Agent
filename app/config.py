from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class AppConfig:
    gemini_api_key: str
    qwen_asr_base_url: str | None
    fish_tts_base_url: str | None
    llm_base_url: str = "https://model-api.skyengine.com.cn/v1/chat/completions"
    llm_model: str = "qwen3.5-flash"
    llm_system_prompt: str | None = None  # 可选的自定义 system prompt
    asr_backend: str = "mlx"
    mlx_asr_model: str = "mlx-community/whisper-small-asr-4bit"
    mlx_asr_language: str = "zh"
    tts_backend: str = "mlx_qwen3"
    # TTS 模型选择：vibevoice / kokoro / qwen3
    mlx_tts_model_type: str = "kokoro"
    mlx_tts_vibevoice_model: str = "mlx-community/VibeVoice-Realtime-0.5B-4bit"
    mlx_tts_kokoro_model: str = "mlx-community/Kokoro-82M-bf16"
    mlx_tts_qwen3_model: str = "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit"
    mlx_tts_language: str = "zh"
    mlx_tts_voice: str | None = None
    mlx_tts_speed: float = 1.0  # TTS 语速控制
    audio_sample_rate: int = 16000
    vad_start_ms: int = 120
    vad_interrupt_ms: int = 200
    turn_silence_ms: int = 1500
    log_level: str = "INFO"


def _required(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        raise ConfigError(f"Missing required env: {name}")
    return value


def _require_ascii(name: str, value: str) -> str:
    try:
        value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ConfigError(
            f"{name} must contain only ASCII characters. Check whether your shell environment is overriding .env with placeholder text."
        ) from exc
    return value


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"Invalid int for {name}: {raw}") from exc


def _optional(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


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
    asr_backend = os.getenv("ASR_BACKEND", "mlx").strip().lower() or "mlx"
    tts_backend = os.getenv("TTS_BACKEND", "mlx_qwen3").strip().lower() or "mlx_qwen3"
    qwen_asr_base_url = _optional("QWEN_ASR_BASE_URL")
    fish_tts_base_url = _optional("FISH_TTS_BASE_URL")
    if asr_backend == "qwen" and qwen_asr_base_url is None:
        raise ConfigError("Missing required env: QWEN_ASR_BASE_URL")
    if tts_backend == "fish" and fish_tts_base_url is None:
        raise ConfigError("Missing required env: FISH_TTS_BASE_URL")
    
    # TTS 模型类型选择
    mlx_tts_model_type = os.getenv("MLX_TTS_MODEL_TYPE", "kokoro").strip().lower()
    if mlx_tts_model_type not in {"vibevoice", "kokoro", "qwen3"}:
        mlx_tts_model_type = "kokoro"
    
    return AppConfig(
        gemini_api_key=_require_ascii("GEMINI_API_KEY", _required("GEMINI_API_KEY")),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://model-api.skyengine.com.cn/v1/chat/completions"),
        llm_model=os.getenv("LLM_MODEL", "qwen3.5-flash"),
        llm_system_prompt=_optional("LLM_SYSTEM_PROMPT"),  # 可选的自定义 system prompt
        qwen_asr_base_url=qwen_asr_base_url,
        fish_tts_base_url=fish_tts_base_url,
        asr_backend=asr_backend,
        mlx_asr_model=os.getenv("MLX_ASR_MODEL", "mlx-community/whisper-small-asr-4bit"),
        mlx_asr_language=os.getenv("MLX_ASR_LANGUAGE", "zh"),
        tts_backend=tts_backend,
        mlx_tts_model_type=mlx_tts_model_type,  # vibevoice / kokoro / qwen3
        mlx_tts_vibevoice_model=os.getenv("MLX_TTS_VIBEVOICE_MODEL", "mlx-community/VibeVoice-Realtime-0.5B-4bit"),
        mlx_tts_kokoro_model=os.getenv("MLX_TTS_KOKORO_MODEL", "mlx-community/Kokoro-82M-bf16"),
        mlx_tts_qwen3_model=os.getenv("MLX_TTS_QWEN3_MODEL", "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit"),
        mlx_tts_language=os.getenv("MLX_TTS_LANGUAGE", "zh"),
        mlx_tts_voice=_optional("MLX_TTS_VOICE"),
        mlx_tts_speed=float(os.getenv("MLX_TTS_SPEED", "1.0")),  # TTS 语速控制
        audio_sample_rate=_int("AUDIO_SAMPLE_RATE", 16000),
        vad_start_ms=_int("VAD_START_MS", 120),
        vad_interrupt_ms=_int("VAD_INTERRUPT_MS", 200),
        turn_silence_ms=_int("TURN_SILENCE_MS", 600),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


__all__ = ["AppConfig", "ConfigError", "load_config", "_load_dotenv"]
