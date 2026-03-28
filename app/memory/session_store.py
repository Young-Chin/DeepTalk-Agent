from __future__ import annotations

from collections import deque


class SessionStore:
    def __init__(self, max_turns: int = 8) -> None:
        self._turns = deque(maxlen=max_turns)

    def add_user_turn(self, text: str) -> None:
        self._turns.append({"role": "user", "content": text})

    def add_agent_turn(self, text: str, interrupted: bool) -> None:
        self._turns.append(
            {"role": "assistant", "content": text, "interrupted": interrupted}
        )

    def snapshot(self) -> list[dict]:
        return list(self._turns)
