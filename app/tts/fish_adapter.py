from __future__ import annotations

import httpx


class FishTTSAdapter:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def synthesize(self, text: str) -> bytes:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.base_url}/synthesize",
                json={"text": text},
            )
            response.raise_for_status()
            return response.content
