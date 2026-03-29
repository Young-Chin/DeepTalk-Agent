from __future__ import annotations

import httpx


class GeminiAdapter:
    def __init__(
        self,
        api_key: str,
        model: str = "qwen3.5-flash",
        base_url: str = "https://model-api.skyengine.com.cn/v1/chat/completions",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def _authorization_header(self) -> dict[str, str]:
        try:
            self.api_key.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError(
                "GEMINI_API_KEY must contain only ASCII characters."
            ) from exc
        return {"Authorization": f"Bearer {self.api_key}"}

    async def next_host_reply(self, history: list[dict]) -> str:
        payload = {"model": self.model, "messages": history}
        headers = self._authorization_header()

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                self.base_url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return self._extract_text(response.json())

    def _extract_text(self, payload: object) -> str:
        if isinstance(payload, dict):
            text = payload.get("text")
            if isinstance(text, str):
                return text
            choices = payload.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0]
                if isinstance(first, dict):
                    message = first.get("message")
                    if isinstance(message, dict):
                        content = message.get("content")
                        if isinstance(content, str):
                            return content
        raise ValueError("Unsupported LLM response payload")
