import httpx
import pytest

from app.agent.gemini_adapter import GeminiAdapter
from app.asr.qwen_adapter import QwenASRAdapter
from app.tts.fish_adapter import FishTTSAdapter


@pytest.mark.asyncio
async def test_qwen_adapter_returns_final_text(httpx_mock):
    httpx_mock.add_response(json={"text": "你好世界"})

    adapter = QwenASRAdapter("http://localhost:8001")
    text = await adapter.transcribe_chunk(b"pcm")

    assert text == "你好世界"


@pytest.mark.asyncio
async def test_gemini_adapter_returns_host_reply(httpx_mock):
    httpx_mock.add_response(
        json={
            "choices": [
                {
                    "message": {
                        "content": "欢迎来到节目。"
                    }
                }
            ]
        }
    )

    adapter = GeminiAdapter(
        "secret-key",
        model="qwen3.5-flash",
        base_url="https://model-api.skyengine.com.cn/v1/chat/completions",
    )
    text = await adapter.next_host_reply([{"role": "user", "content": "你好"}])

    request = httpx_mock.get_requests()[0]
    assert request.headers["Authorization"] == "Bearer secret-key"
    assert request.url == "https://model-api.skyengine.com.cn/v1/chat/completions"
    assert request.read().decode("utf-8").find("qwen3.5-flash") != -1
    assert text == "欢迎来到节目。"


@pytest.mark.asyncio
async def test_gemini_adapter_rejects_non_ascii_api_key():
    adapter = GeminiAdapter("你的key")

    with pytest.raises(ValueError, match="ASCII"):
        await adapter.next_host_reply([{"role": "user", "content": "你好"}])


@pytest.mark.asyncio
async def test_gemini_adapter_accepts_top_level_text_payload(httpx_mock):
    httpx_mock.add_response(json={"text": "兼容旧响应"})

    adapter = GeminiAdapter("secret-key")

    text = await adapter.next_host_reply([{"role": "user", "content": "你好"}])

    assert text == "兼容旧响应"


@pytest.mark.asyncio
async def test_fish_tts_adapter_returns_audio_bytes(httpx_mock):
    httpx_mock.add_response(content=b"audio-bytes")

    adapter = FishTTSAdapter("http://localhost:8002")
    audio = await adapter.synthesize("欢迎收听")

    assert audio == b"audio-bytes"
