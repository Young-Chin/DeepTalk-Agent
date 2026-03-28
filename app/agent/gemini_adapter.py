from __future__ import annotations

import httpx


class GeminiAdapter:
    def __init__(self, api_key: str, model: str = "gemini-3.1-pro") -> None:
        self.api_key = api_key
        self.model = model

    async def next_host_reply(self, history: list[dict]) -> str:
        payload = {"model": self.model, "history": history}
        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://generativelanguage.googleapis.com/v1/chat:completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()["text"]
