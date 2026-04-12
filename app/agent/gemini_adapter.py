from __future__ import annotations

import httpx
import re

DEFAULT_SYSTEM_PROMPT = """你是一位亲切自然的访谈主持人。

回复要求：
- 简短精炼：每句不超过 30 字，总长度控制在 50 字以内
- 口语化：像日常聊天一样自然，避免书面语
- 拟人化：有情感、有温度，像真人一样交流
- 积极倾听：适时回应，展现真诚的兴趣
- 引导对话：用简短的问题推动话题

记住：少即是多，自然流畅最重要。"""

# 句子分割正则：中文句号/问号/感叹号，或英文句号+空格/结尾
_SENTENCE_SPLIT = re.compile(r'(?<=[。！？.!?])\s*')


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
        full_text = []
        async for chunk in self.next_host_reply_stream(history):
            full_text.append(chunk)
        result = "".join(full_text)
        if len(result) > 150:
            result = result[:147] + "..."
        return result

    async def next_host_reply_stream(self, history: list[dict]):
        """流式返回 LLM 回复，按句子 yield。"""
        messages_with_system = [
            {"role": "system", "content": self.system_prompt},
            *history
        ]
        payload = {
            "model": self.model,
            "messages": messages_with_system,
            "max_tokens": 100,
            "temperature": 0.7,
            "stream": True,
        }
        headers = self._authorization_header()

        sentence_buffer = ""
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                self.base_url,
                json=payload,
                headers=headers,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or line.strip() == "data: [DONE]":
                        continue
                    if not line.startswith("data: "):
                        continue
                    text = self._extract_stream_text(line)
                    if text:
                        sentence_buffer += text
                        sentences = _SENTENCE_SPLIT.split(sentence_buffer)
                        # 最后一个可能不完整，保留在 buffer
                        if len(sentences) > 1:
                            for s in sentences[:-1]:
                                s = s.strip()
                                if s:
                                    yield s
                            sentence_buffer = sentences[-1]
                # 输出剩余内容
                sentence_buffer = sentence_buffer.strip()
                if sentence_buffer:
                    yield sentence_buffer

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

    def _extract_stream_text(self, line: str) -> str:
        """从 SSE data: 行提取增量文本。"""
        import json
        try:
            data = json.loads(line[6:])  # strip "data: "
            choices = data.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                return delta.get("content", "")
        except (json.JSONDecodeError, KeyError, IndexError):
            pass
        return ""
