import pytest

from app.asr.qwen_adapter import QwenASRAdapter


@pytest.mark.asyncio
async def test_qwen_adapter_returns_top_level_text(httpx_mock):
    httpx_mock.add_response(json={"text": "hello world"})

    adapter = QwenASRAdapter("http://localhost:8001")

    text = await adapter.transcribe_chunk(b"pcm")

    assert text == "hello world"


@pytest.mark.asyncio
async def test_qwen_adapter_returns_nested_result_text(httpx_mock):
    httpx_mock.add_response(json={"result": {"text": "nested hello"}})

    adapter = QwenASRAdapter("http://localhost:8001")

    text = await adapter.transcribe_chunk(b"pcm")

    assert text == "nested hello"


@pytest.mark.asyncio
async def test_qwen_adapter_raises_for_unsupported_payload(httpx_mock):
    httpx_mock.add_response(json={"unexpected": "shape"})

    adapter = QwenASRAdapter("http://localhost:8001")

    with pytest.raises(ValueError, match="Unsupported ASR response payload"):
        await adapter.transcribe_chunk(b"pcm")
