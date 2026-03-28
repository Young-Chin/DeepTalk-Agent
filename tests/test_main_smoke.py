from app.main import build_app


def test_build_app_constructs_components(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("QWEN_ASR_BASE_URL", "http://localhost:8001")
    monkeypatch.setenv("FISH_TTS_BASE_URL", "http://localhost:8002")

    app = build_app()

    assert "state_machine" in app
    assert "bus" in app
