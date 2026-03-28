from __future__ import annotations

import asyncio
import logging

from app.bus import Event, EventBus, EventType
from app.agent.gemini_adapter import GeminiAdapter
from app.asr.qwen_adapter import QwenASRAdapter
from app.audio.in_stream import MicrophoneInput
from app.audio.out_stream import AudioOutput
from app.config import _load_dotenv, load_config
from app.memory.session_store import SessionStore
from app.observability.logger import configure_logging, log_timing
from app.state_machine import ConversationStateMachine
from app.tts.fish_adapter import FishTTSAdapter

LOGGER = logging.getLogger("podcast.runtime")


def build_app() -> dict:
    _load_dotenv()
    config = load_config()
    bus = EventBus()
    memory = SessionStore()
    state_machine = ConversationStateMachine(memory=memory)

    return {
        "config": config,
        "bus": bus,
        "state_machine": state_machine,
        "memory": memory,
        "audio_in": MicrophoneInput(),
        "audio_out": AudioOutput(),
        "asr": QwenASRAdapter(config.qwen_asr_base_url),
        "agent": GeminiAdapter(config.gemini_api_key),
        "tts": FishTTSAdapter(config.fish_tts_base_url),
    }


async def handle_event(app: dict, event: Event) -> None:
    machine: ConversationStateMachine = app["state_machine"]

    if event.type == EventType.USER_FINAL_TEXT:
        text = event.payload["text"]
        machine.on_user_final_text(text)
        with log_timing(
            LOGGER,
            component="llm",
            operation="next_host_reply",
            provider="gemini",
        ):
            reply = await app["agent"].next_host_reply(app["memory"].snapshot())
        await handle_event(
            app,
            Event(type=EventType.AGENT_TEXT_READY, payload={"text": reply}),
        )
        return

    if event.type == EventType.AGENT_TEXT_READY:
        text = event.payload["text"]
        machine.on_agent_reply_ready(text)
        with log_timing(
            LOGGER,
            component="tts",
            operation="synthesize",
            provider="fish",
        ):
            audio_bytes = await app["tts"].synthesize(text)
        await app["audio_out"].play(audio_bytes)
        machine.on_playback_finished()
        return

    if event.type == EventType.INTERRUPT:
        app["audio_out"].stop()
        machine.on_interrupt()
        return

    raise ValueError(f"Unsupported event type: {event.type}")


async def run() -> None:
    app = build_app()
    configure_logging(app["config"].log_level)
    print("DeepTalk Agent CLI started. Press Ctrl+C to exit.")

    while True:
        await asyncio.sleep(1)
        _ = app["state_machine"].state


if __name__ == "__main__":
    asyncio.run(run())
