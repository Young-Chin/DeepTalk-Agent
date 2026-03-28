from __future__ import annotations

import io
import wave

import pytest

from app.mocks import MockAgentAdapter, MockASRAdapter, MockTTSAdapter


def _read_wav(audio_bytes: bytes) -> tuple[int, bytes]:
    with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
        return wav_file.getframerate(), wav_file.readframes(wav_file.getnframes())


@pytest.mark.asyncio
async def test_mock_asr_adapter_decodes_utf8_payload():
    adapter = MockASRAdapter()

    text = await adapter.transcribe_chunk("hello world".encode("utf-8"))

    assert text == "hello world"


@pytest.mark.asyncio
async def test_mock_asr_adapter_returns_fallback_for_non_utf8_payload():
    adapter = MockASRAdapter(fallback_text="mock transcript")

    text = await adapter.transcribe_chunk(b"\xff\xfe")

    assert text == "mock transcript"


@pytest.mark.asyncio
async def test_mock_agent_adapter_uses_last_user_message():
    adapter = MockAgentAdapter()

    reply = await adapter.next_host_reply(
        [
            {"role": "system", "content": "host"},
            {"role": "user", "content": "Tell me about testing"},
        ]
    )

    assert reply == "Host: Tell me more about Tell me about testing."


@pytest.mark.asyncio
async def test_mock_agent_adapter_handles_missing_user_history():
    adapter = MockAgentAdapter()

    reply = await adapter.next_host_reply([{"role": "assistant", "content": "intro"}])

    assert reply == "Host: Tell me a little about yourself."


@pytest.mark.asyncio
async def test_mock_tts_adapter_returns_small_wav_payload():
    adapter = MockTTSAdapter()

    audio = await adapter.synthesize("short line")

    sample_rate, frames = _read_wav(audio)
    assert audio.startswith(b"RIFF")
    assert sample_rate == 16000
    assert frames != b"\x00\x00\x00\x00"
