# app/websocket_types.py
"""WebSocket 消息类型定义。"""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union
from pydantic import BaseModel, ConfigDict, Field


class WSMessageType(str, Enum):
    """WebSocket 消息类型。"""
    # 客户端 -> 服务端
    AUDIO_START = "audio_start"
    AUDIO_CHUNK = "audio_chunk"
    AUDIO_STOP = "audio_stop"
    INTERRUPT = "interrupt"

    # 服务端 -> 客户端
    STATE = "state"
    TRANSCRIPT = "transcript"
    REPLY_CHUNK = "reply_chunk"
    REPLY_DONE = "reply_done"
    AUDIO_OUT = "audio_out"
    AUDIO_DONE = "audio_done"
    ERROR = "error"


class ConversationState(str, Enum):
    """对话状态。"""
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"


class WSMessage(BaseModel):
    """WebSocket 消息基类，禁止额外字段。"""
    model_config = ConfigDict(extra="forbid")


# 客户端消息
class AudioStartMessage(WSMessage):
    type: Literal[WSMessageType.AUDIO_START] = WSMessageType.AUDIO_START


class AudioChunkMessage(WSMessage):
    type: Literal[WSMessageType.AUDIO_CHUNK] = WSMessageType.AUDIO_CHUNK
    data: str  # base64 编码的 PCM 音频


class AudioStopMessage(WSMessage):
    type: Literal[WSMessageType.AUDIO_STOP] = WSMessageType.AUDIO_STOP


class InterruptMessage(WSMessage):
    type: Literal[WSMessageType.INTERRUPT] = WSMessageType.INTERRUPT


# 服务端消息
class StateMessage(WSMessage):
    type: Literal[WSMessageType.STATE] = WSMessageType.STATE
    state: ConversationState


class TranscriptMessage(WSMessage):
    type: Literal[WSMessageType.TRANSCRIPT] = WSMessageType.TRANSCRIPT
    text: str
    # role 固定为 user，保持与设计文档一致
    role: Literal["user"] = "user"


class ReplyChunkMessage(WSMessage):
    type: Literal[WSMessageType.REPLY_CHUNK] = WSMessageType.REPLY_CHUNK
    text: str


class ReplyDoneMessage(WSMessage):
    type: Literal[WSMessageType.REPLY_DONE] = WSMessageType.REPLY_DONE
    text: str


class AudioOutMessage(WSMessage):
    type: Literal[WSMessageType.AUDIO_OUT] = WSMessageType.AUDIO_OUT
    data: str  # base64 编码的 PCM/WAV 音频


class AudioDoneMessage(WSMessage):
    type: Literal[WSMessageType.AUDIO_DONE] = WSMessageType.AUDIO_DONE


class ErrorMessage(WSMessage):
    type: Literal[WSMessageType.ERROR] = WSMessageType.ERROR
    message: str


# 联合类型 (使用 discriminator 优化反序列化)
ClientMessage = Annotated[
    Union[AudioStartMessage, AudioChunkMessage, AudioStopMessage, InterruptMessage],
    Field(discriminator="type")
]

ServerMessage = Annotated[
    Union[StateMessage, TranscriptMessage, ReplyChunkMessage, ReplyDoneMessage, AudioOutMessage, AudioDoneMessage, ErrorMessage],
    Field(discriminator="type")
]


__all__ = [
    "WSMessageType",
    "ConversationState",
    "WSMessage",
    "AudioStartMessage",
    "AudioChunkMessage",
    "AudioStopMessage",
    "InterruptMessage",
    "StateMessage",
    "TranscriptMessage",
    "ReplyChunkMessage",
    "ReplyDoneMessage",
    "AudioOutMessage",
    "AudioDoneMessage",
    "ErrorMessage",
    "ClientMessage",
    "ServerMessage",
]
