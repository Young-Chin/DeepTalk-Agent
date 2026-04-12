from __future__ import annotations

from enum import Enum

from app.memory.session_store import SessionStore


class State(str, Enum):
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    SPEAKING = "speaking"


class ConversationStateMachine:
    def __init__(self, memory: SessionStore) -> None:
        self.memory = memory
        self.state = State.LISTENING
        self.current_agent_reply: str | None = None

    def on_user_final_text(self, text: str) -> None:
        self.memory.add_user_turn(text)
        self.state = State.THINKING

    def on_agent_reply_ready(self, text: str) -> None:
        self.current_agent_reply = text
        self.state = State.SPEAKING

    def on_playback_finished(self) -> None:
        if self.current_agent_reply:
            self.memory.add_agent_turn(self.current_agent_reply, interrupted=False)
        self.current_agent_reply = None
        self.state = State.LISTENING

    def on_interrupt(self) -> None:
        self.current_agent_reply = None
        self.state = State.LISTENING
