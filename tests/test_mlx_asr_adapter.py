import pytest

from app.asr.mlx_adapter import MLXASRAdapter


class FakeMLXTranscriber:
    def __init__(self, result):
        self.result = result
        self.calls: list[tuple[bytes, str | None]] = []

    def transcribe(self, audio_bytes: bytes, language: str | None = None):
        self.calls.append((audio_bytes, language))
        return self.result


@pytest.mark.asyncio
async def test_mlx_adapter_returns_string_result():
    transcriber = FakeMLXTranscriber("你好世界")
    adapter = MLXASRAdapter(transcriber=transcriber, language="zh")

    text = await adapter.transcribe_chunk(b"pcm")

    assert text == "你好世界"
    assert transcriber.calls == [(b"pcm", "zh")]


@pytest.mark.asyncio
async def test_mlx_adapter_returns_text_from_segment_payload():
    transcriber = FakeMLXTranscriber(
        [{"text": "你好"}, {"text": "世界"}]
    )
    adapter = MLXASRAdapter(transcriber=transcriber)

    text = await adapter.transcribe_chunk(b"pcm")

    assert text == "你好世界"


@pytest.mark.asyncio
async def test_mlx_adapter_raises_for_unsupported_payload():
    transcriber = FakeMLXTranscriber([{"unexpected": "shape"}])
    adapter = MLXASRAdapter(transcriber=transcriber)

    with pytest.raises(ValueError, match="Unsupported MLX ASR response payload"):
        await adapter.transcribe_chunk(b"pcm")
