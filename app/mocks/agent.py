from __future__ import annotations


class MockAgentAdapter:
    def __init__(self, default_prompt: str = "Tell me a little about yourself.") -> None:
        self.default_prompt = default_prompt

    async def next_host_reply(self, history: list[dict]) -> str:
        last_user_message = self._last_user_message(history)
        if last_user_message is None:
            return f"Host: {self.default_prompt}"
        return f"Host: Tell me more about {last_user_message}."

    def _last_user_message(self, history: list[dict]) -> str | None:
        for message in reversed(history):
            if message.get("role") != "user":
                continue
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
        return None
