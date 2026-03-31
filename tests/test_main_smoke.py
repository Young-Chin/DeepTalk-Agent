from app import main as app_main
from app.main import build_app


def test_build_app_constructs_components(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("QWEN_ASR_BASE_URL", "http://localhost:8001")
    monkeypatch.setenv("FISH_TTS_BASE_URL", "http://localhost:8002")

    app = build_app()

    assert "state_machine" in app
    assert "bus" in app


def test_build_app_loads_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "GEMINI_API_KEY=from-dotenv",
                "QWEN_ASR_BASE_URL=http://localhost:8001",
                "FISH_TTS_BASE_URL=http://localhost:8002",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_ASR_BASE_URL", raising=False)
    monkeypatch.delenv("FISH_TTS_BASE_URL", raising=False)

    app = build_app()

    assert app["config"].gemini_api_key == "from-dotenv"


def test_build_app_passes_sample_rate_into_audio_components(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("QWEN_ASR_BASE_URL", "http://localhost:8001")
    monkeypatch.setenv("FISH_TTS_BASE_URL", "http://localhost:8002")
    monkeypatch.setenv("AUDIO_SAMPLE_RATE", "22050")

    app = build_app()

    assert app["audio_in"].sample_rate == 22050
    assert app["audio_out"].sample_rate == 22050


def test_main_returns_zero_on_keyboard_interrupt(monkeypatch):
    def _raise_interrupt():
        raise KeyboardInterrupt

    monkeypatch.setattr(app_main, "run", _raise_interrupt)

    assert app_main.main() == 0


def test_build_app_supports_mock_backend_mode(monkeypatch):
    monkeypatch.setenv("PODCAST_BACKEND", "mock")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_ASR_BASE_URL", raising=False)
    monkeypatch.delenv("FISH_TTS_BASE_URL", raising=False)

    app = build_app()

    assert app["config"].gemini_api_key == "mock"
    assert app["asr"].__class__.__name__ == "MockASRAdapter"
    assert app["agent"].__class__.__name__ == "MockAgentAdapter"
    assert app["tts"].__class__.__name__ == "MockTTSAdapter"


def test_build_app_enables_real_audio_output_modules(monkeypatch):
    monkeypatch.setenv("PODCAST_BACKEND", "mock")

    app = build_app()

    assert app["audio_out"]._sounddevice is not None
    assert app["audio_out"]._numpy is not None


def test_build_app_supports_local_qwen3_tts_backend(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("QWEN_ASR_BASE_URL", "http://localhost:8001")
    monkeypatch.delenv("FISH_TTS_BASE_URL", raising=False)
    monkeypatch.setenv("TTS_BACKEND", "mlx_qwen3")
    monkeypatch.setenv("MLX_TTS_MODEL", "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit")
    monkeypatch.setenv("MLX_TTS_LANGUAGE", "zh")

    app = build_app()

    assert app["tts"].__class__.__name__ == "MLXQwenTTSAdapter"
    assert app["tts"].model == "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit"
    assert app["tts"].lang_code == "zh"
