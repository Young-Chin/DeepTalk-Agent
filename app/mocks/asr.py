from __future__ import annotations


class MockASRAdapter:
    def __init__(self, fallback_text: str = "mock transcript") -> None:
        self.fallback_text = fallback_text

    async def transcribe_chunk(self, pcm_bytes: bytes) -> str:
        full = []
        async for chunk in self.transcribe_stream(pcm_bytes):
            full.append(chunk)
        return "".join(full)

    async def transcribe_stream(self, pcm_bytes: bytes):
        text = await self._decode(pcm_bytes)
        yield text

    async def _decode(self, pcm_bytes: bytes) -> str:
        try:
            text = pcm_bytes.decode("utf-8").strip()
        except UnicodeDecodeError:
            return self.fallback_text
        return text or self.fallback_text
