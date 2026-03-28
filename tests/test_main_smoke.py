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
