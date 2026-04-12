import base64

import pytest

from app.tts.fish_adapter import FishTTSAdapter


@pytest.mark.asyncio
async def test_fish_tts_adapter_returns_raw_audio_bytes(httpx_mock):
    httpx_mock.add_response(content=b"audio-bytes")

    adapter = FishTTSAdapter("http://localhost:8002")
    audio = await adapter.synthesize("welcome")

    assert audio == b"audio-bytes"


@pytest.mark.asyncio
async def test_fish_tts_adapter_decodes_top_level_base64_audio(httpx_mock):
    encoded_audio = base64.b64encode(b"audio-bytes").decode("ascii")
    httpx_mock.add_response(
        json={"audio": encoded_audio},
        headers={"Content-Type": "application/json"},
    )

    adapter = FishTTSAdapter("http://localhost:8002")
    audio = await adapter.synthesize("welcome")

    assert audio == b"audio-bytes"


@pytest.mark.asyncio
async def test_fish_tts_adapter_decodes_nested_base64_audio(httpx_mock):
    encoded_audio = base64.b64encode(b"nested-audio").decode("ascii")
    httpx_mock.add_response(
        json={"data": {"audio": encoded_audio}},
        headers={"Content-Type": "application/json"},
    )

    adapter = FishTTSAdapter("http://localhost:8002")
    audio = await adapter.synthesize("welcome")

    assert audio == b"nested-audio"


@pytest.mark.asyncio
async def test_fish_tts_adapter_rejects_unsupported_json_payload(httpx_mock):
    httpx_mock.add_response(
        json={"unexpected": "payload"},
        headers={"Content-Type": "application/json"},
    )

    adapter = FishTTSAdapter("http://localhost:8002")

    with pytest.raises(ValueError, match="Unsupported Fish TTS response payload"):
        await adapter.synthesize("welcome")


@pytest.mark.asyncio
async def test_fish_tts_adapter_rejects_malformed_base64_audio(httpx_mock):
    httpx_mock.add_response(
        json={"audio": "%%%not-base64%%%"},
        headers={"Content-Type": "application/json"},
    )

    adapter = FishTTSAdapter("http://localhost:8002")

    with pytest.raises(ValueError, match="Malformed Fish TTS audio payload"):
        await adapter.synthesize("welcome")
