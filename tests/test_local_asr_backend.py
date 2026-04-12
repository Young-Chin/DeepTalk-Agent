from app.main import build_app


def test_build_app_supports_mlx_asr_backend(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("QWEN_ASR_BASE_URL", "http://localhost:8001")
    monkeypatch.setenv("FISH_TTS_BASE_URL", "http://localhost:8002")
    monkeypatch.setenv("ASR_BACKEND", "mlx")
    monkeypatch.setenv("MLX_ASR_MODEL", "mlx-community/Qwen3-ASR-0.6B-4bit")
    monkeypatch.setenv("MLX_ASR_LANGUAGE", "zh")

    app = build_app()

    assert app["asr"].__class__.__name__ == "MLXASRAdapter"
    assert app["asr"].model == "mlx-community/Qwen3-ASR-0.6B-4bit"
    assert app["asr"].language == "zh"
