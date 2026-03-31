from __future__ import annotations

import asyncio
import importlib
import logging
import os

from app.bus import Event, EventBus, EventType
from app.agent.gemini_adapter import GeminiAdapter
from app.asr.qwen_adapter import QwenASRAdapter
from app.audio.in_stream import MicrophoneInput
from app.audio.out_stream import AudioOutput
from app.config import AppConfig, _load_dotenv, load_config
from app.memory.session_store import SessionStore
from app.observability.logger import configure_logging, log_timing
from app.state_machine import ConversationStateMachine, State
from app.tts.fish_adapter import FishTTSAdapter

LOGGER = logging.getLogger("podcast.runtime")


def _build_mock_config() -> AppConfig:
    return AppConfig(
        gemini_api_key="mock",
        qwen_asr_base_url="mock://asr",
        fish_tts_base_url="mock://tts",
        audio_sample_rate=int(os.getenv("AUDIO_SAMPLE_RATE", "16000")),
        vad_start_ms=int(os.getenv("VAD_START_MS", "120")),
        vad_interrupt_ms=int(os.getenv("VAD_INTERRUPT_MS", "200")),
        turn_silence_ms=int(os.getenv("TURN_SILENCE_MS", "600")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


def build_app() -> dict:
    backend = os.getenv("PODCAST_BACKEND", "").strip().lower()
    if backend == "mock":
        config = _build_mock_config()
    else:
        _load_dotenv()
        config = load_config()
    bus = EventBus()
    memory = SessionStore()
    state_machine = ConversationStateMachine(memory=memory)
    try:
        sounddevice_module = importlib.import_module("sounddevice")
        numpy_module = importlib.import_module("numpy")
    except ModuleNotFoundError:
        sounddevice_module = None
        numpy_module = None
    if backend == "mock":
        from app.mocks import MockASRAdapter, MockAgentAdapter, MockTTSAdapter

        asr = MockASRAdapter()
        agent = MockAgentAdapter()
        tts = MockTTSAdapter(sample_rate=config.audio_sample_rate)
    else:
        asr = QwenASRAdapter(config.qwen_asr_base_url)
        agent = GeminiAdapter(config.gemini_api_key)
        tts = FishTTSAdapter(config.fish_tts_base_url)

    return {
        "config": config,
        "bus": bus,
        "state_machine": state_machine,
        "memory": memory,
        "audio_in": MicrophoneInput(sample_rate=config.audio_sample_rate),
        "audio_out": AudioOutput(
            sample_rate=config.audio_sample_rate,
            sounddevice_module=sounddevice_module,
            numpy_module=numpy_module,
        ),
        "asr": asr,
        "agent": agent,
        "tts": tts,
    }


def _recover_to_listening(app: dict, component: str, exc: Exception) -> None:
    LOGGER.exception("%s failure; recovering to listening: %s", component, exc)
    app["state_machine"].on_interrupt()


async def _check_for_interrupt(app: dict) -> bool:
    """Check pending frames for interrupt speech. Returns True if interrupted."""
    interrupt_threshold_s = app["config"].vad_interrupt_ms / 1000.0
    consecutive_speech = 0.0

    while app["audio_in"].has_pending_frame():
        frame = await app["audio_in"].read_frame()
        if app["audio_in"].is_speech_frame(frame):
            consecutive_speech += 0.1
            if consecutive_speech >= interrupt_threshold_s:
                LOGGER.info(
                    "interrupt: detected %dms of continuous speech",
                    int(consecutive_speech * 1000),
                )
                return True
        else:
            consecutive_speech = 0.0

    return False


async def _wait_for_playback_done(app: dict) -> bool:
    """Wait until audio playback finishes or is interrupted by speech.

    Runs a parallel VAD monitor during playback. When continuous speech
    exceeds the configured interrupt threshold, stops playback and returns
    immediately.
    
    Returns True if interrupted by speech, False if playback finished naturally.
    """
    interrupted_flag = {"value": False}
    
    async def _monitor_interrupt() -> None:
        while True:
            if app["audio_in"].has_pending_frame():
                interrupted = await _check_for_interrupt(app)
                if interrupted:
                    app["audio_out"].stop()
                    interrupted_flag["value"] = True
                    return
            await asyncio.sleep(0.1)

    monitor_task = asyncio.create_task(_monitor_interrupt())
    playback_task = asyncio.create_task(app["audio_out"].wait())

    done, pending = await asyncio.wait(
        [monitor_task, playback_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    # Cancel whichever task is still pending
    for task in pending:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    return interrupted_flag["value"]


async def handle_event(app: dict, event: Event) -> None:
    machine: ConversationStateMachine = app["state_machine"]

    if event.type == EventType.USER_FINAL_TEXT:
        text = event.payload["text"]
        print(f"User: {text}")
        machine.on_user_final_text(text)
        try:
            with log_timing(
                LOGGER,
                component="llm",
                operation="next_host_reply",
                provider="gemini",
            ):
                reply = await app["agent"].next_host_reply(app["memory"].snapshot())
        except Exception as exc:
            _recover_to_listening(app, "llm", exc)
            return
        await handle_event(
            app,
            Event(type=EventType.AGENT_TEXT_READY, payload={"text": reply}),
        )
        return

    if event.type == EventType.AGENT_TEXT_READY:
        text = event.payload["text"]
        print(f"Host: {text}")
        machine.on_agent_reply_ready(text)
        try:
            with log_timing(
                LOGGER,
                component="tts",
                operation="synthesize",
                provider="fish",
            ):
                audio_bytes = await app["tts"].synthesize(text)
            await app["audio_out"].play(audio_bytes)
        except Exception as exc:
            _recover_to_listening(app, "tts", exc)
            return

        interrupted = await _wait_for_playback_done(app)
        if interrupted:
            app["state_machine"].on_interrupt()
        else:
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
    first_frame = await app["audio_in"].read_frame()
    if not app["audio_in"].is_speech_frame(first_frame):
        return
    pending_frames = app["audio_in"].drain_pending_frames()
    if pending_frames:
        chunk = b"".join([first_frame, *pending_frames])
    else:
        chunk = await app["audio_in"].collect_utterance(
            app["config"].turn_silence_ms,
            initial_frame=first_frame,
        )
    try:
        with log_timing(
            LOGGER,
            component="asr",
            operation="transcribe_chunk",
            provider="qwen",
        ):
            text = await app["asr"].transcribe_chunk(chunk)
    except Exception as exc:
        _recover_to_listening(app, "asr", exc)
        return
    await app["bus"].publish(
        Event(type=EventType.USER_FINAL_TEXT, payload={"text": text}),
    )


def start_audio_input(app: dict) -> None:
    app["audio_in"].start_device_capture()


def stop_audio_input(app: dict) -> None:
    app["audio_in"].stop_device_capture()


async def run() -> None:
    app = build_app()
    configure_logging(app["config"].log_level)
    print("DeepTalk Agent CLI started. Press Ctrl+C to exit.")
    try:
        start_audio_input(app)
    except RuntimeError as exc:
        LOGGER.warning("audio input unavailable: %s", exc)

    try:
        while True:
            await pump_microphone_once(app)
            await consume_next_event(app)
    finally:
        stop_audio_input(app)


def main() -> int:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
