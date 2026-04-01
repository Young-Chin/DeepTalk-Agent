from __future__ import annotations

import httpx

DEFAULT_SYSTEM_PROMPT = """你是一位亲切自然的访谈主持人。

回复要求：
- 简短精炼：每句不超过 30 字，总长度控制在 50 字以内
- 口语化：像日常聊天一样自然，避免书面语
- 拟人化：有情感、有温度，像真人一样交流
- 积极倾听：适时回应，展现真诚的兴趣
- 引导对话：用简短的问题推动话题

记住：少即是多，自然流畅最重要。"""


class GeminiAdapter:
    def __init__(
        self,
        api_key: str,
        model: str = "qwen3.5-flash",
        base_url: str = "https://model-api.skyengine.com.cn/v1/chat/completions",
        system_prompt: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    def _authorization_header(self) -> dict[str, str]:
        try:
            self.api_key.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError(
                "GEMINI_API_KEY must contain only ASCII characters."
            ) from exc
        return {"Authorization": f"Bearer {self.api_key}"}

    async def next_host_reply(self, history: list[dict]) -> str:
        # 构建包含 system prompt 的完整消息列表
        messages_with_system = [
            {"role": "system", "content": self.system_prompt},
            *history
        ]
        payload = {
            "model": self.model, 
            "messages": messages_with_system,
            "max_tokens": 100,  # 限制回复长度，减少 TTS 时延
            "temperature": 0.7,  # 适度创造性，保持自然
        }
        headers = self._authorization_header()

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                self.base_url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            text = self._extract_text(response.json())
            # 额外截断过长的回复
            if len(text) > 150:
                text = text[:147] + "..."
            return text

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
