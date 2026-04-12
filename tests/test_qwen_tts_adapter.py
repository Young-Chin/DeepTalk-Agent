from __future__ import annotations

import io
import wave

import pytest

from app.tts.qwen_adapter import MLXQwenTTSAdapter


def _wav_bytes(sample_rate: int, frames: bytes) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(frames)
    return buffer.getvalue()


class FakeQwenTTSModel:
    def __init__(self, results):
        self.results = results
        self.calls: list[dict] = []
        self.sample_rate = 24000

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return self.results


class FakeGenerationResult:
    def __init__(self, audio):
        self.audio = audio


@pytest.mark.asyncio
async def test_qwen_tts_adapter_returns_joined_wav_bytes():
    model = FakeQwenTTSModel(
        [
            FakeGenerationResult([0.0, 0.25, -0.25]),
            FakeGenerationResult([0.5, -0.5]),
        ]
    )
    adapter = MLXQwenTTSAdapter(
        model="modelscope/Qwen3-TTS-12Hz-0.6B-Base-4bit",
        loaded_model=model,
        lang_code="zh",
    )

    audio = await adapter.synthesize("你好")

    assert audio.startswith(b"RIFF")
    with wave.open(io.BytesIO(audio), "rb") as wav_file:
        assert wav_file.getframerate() == 24000
        assert wav_file.readframes(wav_file.getnframes()) != b""
    assert model.calls[0]["text"] == "你好"
    assert model.calls[0]["lang_code"] == "zh"


@pytest.mark.asyncio
async def test_qwen_tts_adapter_rejects_empty_generation():
    model = FakeQwenTTSModel([])
    adapter = MLXQwenTTSAdapter(
        model="modelscope/Qwen3-TTS-12Hz-0.6B-Base-4bit",
        loaded_model=model,
    )

    with pytest.raises(ValueError, match="did not return audio"):
        await adapter.synthesize("你好")
