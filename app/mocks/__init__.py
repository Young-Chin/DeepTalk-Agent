"""Deterministic local mock backends for end-to-end CLI exercises."""

from app.mocks.agent import MockAgentAdapter
from app.mocks.asr import MockASRAdapter
from app.mocks.tts import MockTTSAdapter

__all__ = ["MockASRAdapter", "MockAgentAdapter", "MockTTSAdapter"]
