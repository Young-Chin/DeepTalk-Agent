from __future__ import annotations

from collections import deque


class SessionStore:
    """管理对话历史的存储类。
    
    自动维护固定长度的对话历史，确保上下文不会无限增长。
    每次对话都会累积历史记录，作为 LLM 的 context。
    """
    
    def __init__(self, max_turns: int = 10) -> None:
        """初始化会话存储。
        
        Args:
            max_turns: 最大保留的对话轮数（默认 10 轮）。超过此数量的早期对话会被自动丢弃。
        """
        self._turns = deque(maxlen=max_turns)

    def add_user_turn(self, text: str) -> None:
        """添加用户发言到对话历史。
        
        Args:
            text: 用户的发言内容
        """
        self._turns.append({"role": "user", "content": text})

    def add_agent_turn(self, text: str, interrupted: bool = False) -> None:
        """添加 AI 回复到对话历史。
        
        Args:
            text: AI 的回复内容
            interrupted: 是否被用户打断（用于调试和统计）
        """
        self._turns.append(
            {"role": "assistant", "content": text, "interrupted": interrupted}
        )

    def snapshot(self) -> list[dict]:
        """获取当前对话历史的快照。
        
        Returns:
            包含所有对话历史的列表，每个元素是一个包含 role 和 content 的字典。
            这个快照可以直接传递给 LLM API 作为 context。
        """
        return list(self._turns)
    
    def clear(self) -> None:
        """清空对话历史。"""
        self._turns.clear()
    
    def turn_count(self) -> int:
        """获取当前对话轮数。
        
        Returns:
            当前已记录的对话消息数量
        """
        return len(self._turns)
