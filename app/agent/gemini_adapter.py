from __future__ import annotations

import httpx


class GeminiAdapter:
    def __init__(self, api_key: str, model: str = "gemini-3.1-pro") -> None:
        self.api_key = api_key
        self.model = model

    def _authorization_header(self) -> dict[str, str]:
        try:
            self.api_key.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError(
                "GEMINI_API_KEY must contain only ASCII characters."
            ) from exc
        return {"Authorization": f"Bearer {self.api_key}"}

    async def next_host_reply(self, history: list[dict]) -> str:
        payload = {"model": self.model, "history": history}
        headers = self._authorization_header()

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://generativelanguage.googleapis.com/v1/chat:completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()["text"]
