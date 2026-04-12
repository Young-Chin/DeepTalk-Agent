"""MLX本地LLM适配器 - 使用mlx-vlm进行本地推理（支持多模态模型如Gemma 4）。"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.agent.gemini_adapter import DEFAULT_SYSTEM_PROMPT

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# 句子分割正则：中文句号/问号/感叹号，或英文句号+空格/结尾
_SENTENCE_SPLIT = re.compile(r'(?<=[。！？.!?])\s*')


class MLXLLMAdapter:
    """使用mlx-vlm的本地LLM适配器（支持Gemma 4等多模态模型）。"""

    def __init__(
        self,
        model: str = "mlx-community/gemma-4-e2b-it-4bit",
        max_tokens: int = 100,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> None:
        self.model_name = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self._model = None
        self._processor = None
        self._loaded = False

    def _load_model(self):
        """延迟加载模型。"""
        if self._loaded:
            return

        try:
            from mlx_vlm import load

            self._model, self._processor = load(self.model_name)
            self._loaded = True
        except Exception as exc:
            raise RuntimeError(f"Failed to load MLX LLM model {self.model_name}: {exc}") from exc

    def _format_messages(self, history: list[dict]) -> list[dict]:
        """将消息历史格式化为模型输入。"""
        messages = []

        # 添加系统提示
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        # 添加历史消息
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            messages.append({"role": role, "content": content})

        return messages

    async def next_host_reply(self, history: list[dict]) -> str:
        """生成完整的回复（非流式）。"""
        self._load_model()

        from mlx_vlm import generate
        from mlx_vlm.prompt_utils import apply_chat_template

        messages = self._format_messages(history)

        # 应用chat template
        prompt = apply_chat_template(
            self._processor,
            self._model.config,
            messages,
            add_generation_prompt=True,
        )

        # 在同步环境中运行生成
        import asyncio

        def _generate():
            return generate(
                self._model,
                self._processor,
                prompt,
                image=None,  # 纯文本模式，不使用图像
                max_tokens=self.max_tokens,
                temp=self.temperature,
                verbose=False,
            )

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _generate)

        # result 是 GenerationResult 对象，提取 text 属性
        text = result.text if hasattr(result, 'text') else str(result)

        # 限制长度
        if len(text) > 150:
            text = text[:147] + "..."

        return text.strip()

    async def next_host_reply_stream(
        self, history: list[dict]
    ) -> AsyncGenerator[str, None]:
        """流式生成回复，按句子yield。"""
        self._load_model()

        from mlx_vlm import stream_generate
        from mlx_vlm.prompt_utils import apply_chat_template

        messages = self._format_messages(history)

        # 应用chat template
        prompt = apply_chat_template(
            self._processor,
            self._model.config,
            messages,
            add_generation_prompt=True,
        )

        sentence_buffer = ""

        # 在同步环境中运行流式生成
        import asyncio

        def _stream_generate():
            return stream_generate(
                self._model,
                self._processor,
                prompt,
                image=None,  # 纯文本模式，不使用图像
                max_tokens=self.max_tokens,
                temp=self.temperature,
            )

        loop = asyncio.get_event_loop()
        generator = await loop.run_in_executor(None, _stream_generate)

        # 迭代生成结果
        while True:
            try:
                response = await loop.run_in_executor(None, lambda: next(generator, None))
                if response is None:
                    break

                # response 是 GenerationResult 对象
                text = response.text if hasattr(response, 'text') else str(response)
                if text:
                    sentence_buffer += text
                    sentences = _SENTENCE_SPLIT.split(sentence_buffer)

                    # 最后一个可能不完整，保留在buffer
                    if len(sentences) > 1:
                        for s in sentences[:-1]:
                            s = s.strip()
                            if s:
                                yield s
                        sentence_buffer = sentences[-1]

                # 检查是否生成完成
                if hasattr(response, 'finish_reason') and response.finish_reason is not None:
                    break

            except StopIteration:
                break

        # 输出剩余内容
        sentence_buffer = sentence_buffer.strip()
        if sentence_buffer:
            yield sentence_buffer
