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
        "audio_in": MicrophoneInput(sample_rate=config.audio_sample_rate),
        "audio_out": AudioOutput(sample_rate=config.audio_sample_rate),
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
        if app["audio_in"].has_pending_frame():
            await app["audio_in"].read_frame()
            await handle_event(app, Event(type=EventType.INTERRUPT, payload={}))
            return
        machine.on_playback_finished()
        return

    if event.type == EventType.INTERRUPT:
        app["audio_out"].stop()
        machine.on_interrupt()
        return

    raise ValueError(f"Unsupported event type: {event.type}")


async def consume_next_event(app: dict) -> None:
    event = await app["bus"].next_event()
    await handle_event(app, event)


async def pump_microphone_once(app: dict) -> None:
    frame = await app["audio_in"].read_frame()
    with log_timing(
        LOGGER,
        component="asr",
        operation="transcribe_chunk",
        provider="qwen",
    ):
        text = await app["asr"].transcribe_chunk(frame)
    await app["bus"].publish(
        Event(type=EventType.USER_FINAL_TEXT, payload={"text": text}),
    )


def start_audio_input(app: dict) -> None:
    app["audio_in"].start_device_capture()


async def run() -> None:
    app = build_app()
    configure_logging(app["config"].log_level)
    print("DeepTalk Agent CLI started. Press Ctrl+C to exit.")
    try:
        start_audio_input(app)
    except RuntimeError as exc:
        LOGGER.warning("audio input unavailable: %s", exc)

    while True:
        await pump_microphone_once(app)
        await consume_next_event(app)


if __name__ == "__main__":
    asyncio.run(run())
