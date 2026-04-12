import pytest

from app.asr.mlx_adapter import MLXASRAdapter, _MLXTranscriber


class FakeMLXTranscriber:
    """Mock transcriber for testing, supports both sync and streaming."""
    def __init__(self, result):
        self.result = result
        self.calls: list[tuple[bytes, str | None]] = []

    def transcribe(self, audio_bytes: bytes, language: str | None = None):
        self.calls.append((audio_bytes, language))
        return self.result

    def transcribe_stream(self, audio_bytes: bytes, language: str | None = None):
        """Mock streaming - yields (text, is_final) tuples."""
        self.calls.append((audio_bytes, language))
        # 对于简单测试，直接 yield 结果
        if isinstance(self.result, str):
            yield self.result, True
        elif isinstance(self.result, list):
            # 对于 segment 列表，一次性 yield 拼接结果
            text = "".join(item.get("text", "") for item in self.result if isinstance(item, dict))
            if text:
                yield text, True
            else:
                # 触发 unsupported payload 错误
                raise ValueError("Unsupported MLX ASR response payload")
        else:
            yield self.result, True


@pytest.mark.asyncio
async def test_mlx_adapter_returns_string_result():
    transcriber = FakeMLXTranscriber("你好世界")
    adapter = MLXASRAdapter(transcriber=transcriber, language="zh")

    text = await adapter.transcribe_chunk(b"pcm")

    assert text == "你好世界"


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
