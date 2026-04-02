import pytest

from app.config import AppConfig, ConfigError, load_config


def test_load_config_reads_required_values(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("QWEN_ASR_BASE_URL", "http://localhost:8001")
    monkeypatch.setenv("FISH_TTS_BASE_URL", "http://localhost:8002")

    cfg = load_config()

    assert isinstance(cfg, AppConfig)
    assert cfg.audio_sample_rate == 16000
    assert cfg.gemini_api_key == "k"
    assert cfg.llm_model == "qwen3.5-flash"


def test_load_config_raises_when_required_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("QWEN_ASR_BASE_URL", "http://localhost:8001")
    monkeypatch.setenv("FISH_TTS_BASE_URL", "http://localhost:8002")

    with pytest.raises(ConfigError):
        load_config()


def test_load_config_allows_mlx_asr_without_remote_qwen_url(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.delenv("QWEN_ASR_BASE_URL", raising=False)
    monkeypatch.setenv("ASR_BACKEND", "mlx")
    monkeypatch.setenv("MLX_ASR_MODEL", "mlx-community/Qwen3-ASR-0.6B-4bit")
    monkeypatch.setenv("FISH_TTS_BASE_URL", "http://localhost:8002")

    cfg = load_config()

    assert cfg.asr_backend == "mlx"
    assert cfg.qwen_asr_base_url is None


def test_load_config_rejects_non_ascii_gemini_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "你的key")
    monkeypatch.setenv("QWEN_ASR_BASE_URL", "http://localhost:8001")
    monkeypatch.setenv("FISH_TTS_BASE_URL", "http://localhost:8002")

    with pytest.raises(ConfigError, match="GEMINI_API_KEY must contain only ASCII"):
        load_config()


def test_load_config_allows_mlx_qwen3_tts_without_remote_fish_url(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("QWEN_ASR_BASE_URL", "http://localhost:8001")
    monkeypatch.delenv("FISH_TTS_BASE_URL", raising=False)
    monkeypatch.setenv("TTS_BACKEND", "mlx_qwen3")
    monkeypatch.setenv("MLX_TTS_MODEL_TYPE", "qwen3")
    monkeypatch.setenv("MLX_TTS_QWEN3_MODEL", "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit")
    monkeypatch.setenv("MLX_TTS_LANGUAGE", "zh")

    cfg = load_config()

    assert cfg.tts_backend == "mlx_qwen3"
    assert cfg.fish_tts_base_url is None


def test_load_config_reads_custom_llm_endpoint(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("QWEN_ASR_BASE_URL", "http://localhost:8001")
    monkeypatch.setenv("FISH_TTS_BASE_URL", "http://localhost:8002")
    monkeypatch.setenv("LLM_BASE_URL", "https://model-api.skyengine.com.cn/v1/chat/completions")
    monkeypatch.setenv("LLM_MODEL", "qwen3.5-flash")

    cfg = load_config()

    assert cfg.llm_base_url == "https://model-api.skyengine.com.cn/v1/chat/completions"
    assert cfg.llm_model == "qwen3.5-flash"
