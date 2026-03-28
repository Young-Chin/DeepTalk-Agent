from __future__ import annotations

import httpx


class QwenASRAdapter:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def transcribe_chunk(self, pcm_bytes: bytes) -> str:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}/transcribe",
                content=pcm_bytes,
            )
            response.raise_for_status()
            return response.json()["text"]
