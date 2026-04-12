# app/websocket_handler.py
"""WebSocket 连接处理器。"""
from __future__ import annotations

import asyncio
import base64
import logging
from typing import TYPE_CHECKING, Any

from fastapi import WebSocket, WebSocketDisconnect

from app.websocket_types import (
    AudioChunkMessage,
    AudioDoneMessage,
    AudioOutMessage,
    AudioStartMessage,
    AudioStopMessage,
    ClientMessage,
    ConversationState,
    ErrorMessage,
    InterruptMessage,
    ReplyChunkMessage,
    ReplyDoneMessage,
    StateMessage,
    TranscriptMessage,
    WSMessage,
    WSMessageType,
)

if TYPE_CHECKING:
    from app.state_machine import ConversationStateMachine
    from app.memory.session_store import SessionStore

LOGGER = logging.getLogger("podcast.websocket")


class WebSocketSession:
    """管理单个 WebSocket 会话。"""

    def __init__(
        self,
        websocket: WebSocket,
        state_machine: "ConversationStateMachine",
        memory: "SessionStore",
        asr: Any,  # ASR adapter with transcribe_chunk method
        agent: Any,  # Agent adapter with next_host_reply/next_host_reply_stream methods
        tts: Any,  # TTS adapter with synthesize method
        audio_out: Any,  # Audio output handler
        audio_sample_rate: int = 16000,
    ) -> None:
        self.websocket = websocket
        self.state_machine = state_machine
        self.memory = memory
        self.asr = asr
        self.agent = agent
        self.tts = tts
        self.audio_out = audio_out
        self.audio_sample_rate = audio_sample_rate

        self._audio_chunks: list[bytes] = []
        self._is_recording = False
        self._is_interrupted = False

    async def run(self) -> None:
        """主循环：处理 WebSocket 消息。"""
        try:
            await self.websocket.accept()
        except Exception as e:
            LOGGER.warning("Failed to accept WebSocket: %s", e)
            return

        try:
            await self._send_state(ConversationState.LISTENING)
        except Exception as e:
            LOGGER.warning("Failed to send initial state: %s", e)
            return

        try:
            while True:
                try:
                    data = await self.websocket.receive_json()
                    await self._handle_message(data)
                except WebSocketDisconnect:
                    LOGGER.info("WebSocket disconnected")
                    return
        except Exception as e:
            LOGGER.exception("WebSocket error: %s", e)
            # 只有在 WebSocket 还连接时才尝试发送错误
            try:
                await self._send_error(str(e))
            except Exception:
                pass

    async def _handle_message(self, data: dict) -> None:
        """处理单条消息。"""
        msg_type = data.get("type")

        if msg_type == WSMessageType.AUDIO_START:
            await self._on_audio_start()
        elif msg_type == WSMessageType.AUDIO_CHUNK:
            await self._on_audio_chunk(data.get("data", ""))
        elif msg_type == WSMessageType.AUDIO_STOP:
            await self._on_audio_stop()
        elif msg_type == WSMessageType.INTERRUPT:
            await self._on_interrupt()
        else:
            LOGGER.warning("Unknown message type: %s", msg_type)

    async def _on_audio_start(self) -> None:
        """开始录音。"""
        self._audio_chunks = []
        self._is_recording = True
        self._is_interrupted = False
        LOGGER.debug("Recording started")

    async def _on_audio_chunk(self, data_b64: str) -> None:
        """接收音频块。"""
        if not self._is_recording:
            return
        try:
            chunk = base64.b64decode(data_b64)
            self._audio_chunks.append(chunk)
        except Exception as e:
            LOGGER.warning("Failed to decode audio chunk: %s", e)

    async def _on_audio_stop(self) -> None:
        """停止录音，开始处理。"""
        if not self._audio_chunks:
            await self._send_state(ConversationState.LISTENING)
            return

        self._is_recording = False
        audio_bytes = b"".join(self._audio_chunks)
        self._audio_chunks = []

        # ASR
        await self._send_state(ConversationState.TRANSCRIBING)
        try:
            text = await self.asr.transcribe_chunk(audio_bytes)
        except Exception as e:
            LOGGER.exception("ASR failed: %s", e)
            await self._send_error(f"ASR failed: {e}")
            await self._send_state(ConversationState.LISTENING)
            return

        # 修复：检查 None
        if not text or not text.strip():
            await self._send_state(ConversationState.LISTENING)
            return

        await self._send(TranscriptMessage(text=text))
        self.state_machine.on_user_final_text(text)

        # LLM + TTS
        await self._process_llm_tts(text)

    async def _process_llm_tts(self, user_text: str) -> None:
        """处理 LLM 和 TTS 流程。"""
        await self._send_state(ConversationState.THINKING)

        full_reply_parts: list[str] = []

        try:
            # 流式 LLM
            if hasattr(self.agent, "next_host_reply_stream"):
                async for sentence in self.agent.next_host_reply_stream(
                    self.memory.snapshot()
                ):
                    full_reply_parts.append(sentence)
                    await self._send(ReplyChunkMessage(text=sentence))

                    # 立即 TTS 并发送
                    await self._synthesize_and_send(sentence)

                    if self._is_interrupted:
                        break
            else:
                # 非流式回退
                reply = await self.agent.next_host_reply(self.memory.snapshot())
                full_reply_parts.append(reply)
                await self._send(ReplyChunkMessage(text=reply))
                await self._synthesize_and_send(reply)

        except Exception as e:
            LOGGER.exception("LLM/TTS failed: %s", e)
            await self._send_error(f"Processing failed: {e}")
            await self._send_state(ConversationState.LISTENING)
            return

        full_reply = "".join(full_reply_parts)
        await self._send(ReplyDoneMessage(text=full_reply))
        self.state_machine.on_agent_reply_ready(full_reply)
        self.memory.add_agent_turn(full_reply, interrupted=self._is_interrupted)

        await self._send(AudioDoneMessage())
        await self._send_state(ConversationState.LISTENING)

    async def _synthesize_and_send(self, text: str) -> None:
        """合成 TTS 并发送音频。"""
        try:
            audio_bytes = await self.tts.synthesize(text)
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            await self._send(AudioOutMessage(data=audio_b64))
        except Exception as e:
            LOGGER.warning("TTS failed for sentence: %s", e)

    async def _on_interrupt(self) -> None:
        """处理打断。"""
        self._is_interrupted = True
        self.state_machine.on_interrupt()
        self._audio_chunks = []
        await self._send_state(ConversationState.LISTENING)

    async def _send_state(self, state: ConversationState) -> None:
        """发送状态更新。"""
        await self._send(StateMessage(state=state))

    async def _send_error(self, message: str) -> None:
        """发送错误消息。"""
        await self._send(ErrorMessage(message=message))

    async def _send(self, msg: "WSMessage") -> None:
        """发送消息。"""
        try:
            await self.websocket.send_json(msg.model_dump())
        except Exception as e:
            LOGGER.warning("Failed to send message: %s", e)
