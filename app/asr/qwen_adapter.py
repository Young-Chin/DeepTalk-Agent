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
            return self._extract_text(response.json())

    def _extract_text(self, payload: object) -> str:
        if isinstance(payload, dict):
            text = payload.get("text")
            if isinstance(text, str):
                return text

            result = payload.get("result")
            if isinstance(result, dict):
                nested_text = result.get("text")
                if isinstance(nested_text, str):
                    return nested_text

        raise ValueError("Unsupported ASR response payload")
