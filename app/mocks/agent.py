from __future__ import annotations


DEFAULT_SYSTEM_PROMPT = """你是一位亲切自然的访谈主持人。

回复要求：
- 简短精炼：每句不超过 30 字，总长度控制在 50 字以内
- 口语化：像日常聊天一样自然，避免书面语
- 拟人化：有情感、有温度，像真人一样交流
- 积极倾听：适时回应，展现真诚的兴趣
- 引导对话：用简短的问题推动话题

记住：少即是多，自然流畅最重要。"""


class MockAgentAdapter:
    def __init__(
        self, 
        default_prompt: str = "Tell me a little about yourself.",
        system_prompt: str | None = None,
    ) -> None:
        self.default_prompt = default_prompt
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    async def next_host_reply(self, history: list[dict]) -> str:
        full = []
        async for chunk in self.next_host_reply_stream(history):
            full.append(chunk)
        return "".join(full)

    async def next_host_reply_stream(self, history: list[dict]):
        """流式返回 mock 回复，按句子 yield。"""
        reply = await self._build_reply(history)
        # 简单按标点分割
        import re
        parts = re.split(r'(?<=[。！？.!?])\s*', reply)
        for p in parts:
            p = p.strip()
            if p:
                yield p

    async def _build_reply(self, history: list[dict]) -> str:
        last_user_message = self._last_user_message(history)
        if last_user_message is None:
            return f"Host: {self.default_prompt}"
        
        context_summary = self._summarize_context(history)
        if context_summary:
            return f"Host: [{context_summary}] 关于{last_user_message}，能详细说说吗？"
        return f"Host: 关于{last_user_message}，能详细说说吗？"

    def _last_user_message(self, history: list[dict]) -> str | None:
        for message in reversed(history):
            if message.get("role") != "user":
                continue
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
        return None
    
    def _summarize_context(self, history: list[dict]) -> str | None:
        """从对话历史中提取上下文信息，用于生成更连贯的回复。"""
        # 简单实现：返回最近一次 AI 回复的前 20 个字符作为上下文提示
        for message in reversed(history[:-1]):  # 排除最后一条（当前用户的消息）
            if message.get("role") == "assistant":
                content = message.get("content", "")
                if isinstance(content, str) and len(content) > 20:
                    return content[:20] + "..."
        return None
