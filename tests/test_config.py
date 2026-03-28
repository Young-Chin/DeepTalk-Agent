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


def test_load_config_raises_when_required_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("QWEN_ASR_BASE_URL", "http://localhost:8001")
    monkeypatch.setenv("FISH_TTS_BASE_URL", "http://localhost:8002")

    with pytest.raises(ConfigError):
        load_config()
