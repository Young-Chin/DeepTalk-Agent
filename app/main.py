from __future__ import annotations

import asyncio
import importlib
import logging
import os
import time
from collections.abc import Callable

from app.bus import Event, EventBus, EventType
from app.agent.gemini_adapter import GeminiAdapter
from app.asr.mlx_adapter import MLXASRAdapter
from app.asr.qwen_adapter import QwenASRAdapter
from app.audio.in_stream import MicrophoneInput
from app.audio.out_stream import AudioOutput
from app.config import AppConfig, _load_dotenv, load_config
from app.memory.session_store import SessionStore
from app.observability.logger import configure_logging, log_timing
from app.state_machine import ConversationStateMachine
from app.tts.fish_adapter import FishTTSAdapter
from app.tts.qwen_adapter import MLXQwenTTSAdapter

LOGGER = logging.getLogger("podcast.runtime")


def _build_mock_config() -> AppConfig:
    return AppConfig(
        gemini_api_key="mock",
        llm_base_url="mock://llm",
        llm_model="mock-llm",
        qwen_asr_base_url="mock://asr",
        fish_tts_base_url="mock://tts",
        asr_backend="mock",
        tts_backend="mock",
        audio_sample_rate=int(os.getenv("AUDIO_SAMPLE_RATE", "16000")),
        vad_start_ms=int(os.getenv("VAD_START_MS", "120")),
        vad_interrupt_ms=int(os.getenv("VAD_INTERRUPT_MS", "200")),
        turn_silence_ms=int(os.getenv("TURN_SILENCE_MS", "600")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


def _build_asr(config: AppConfig, backend: str):
    if backend == "mock":
        from app.mocks import MockASRAdapter

        return MockASRAdapter(), "mock"
    if config.asr_backend == "mlx":
        return (
            MLXASRAdapter(
                model=config.mlx_asr_model,
                language=config.mlx_asr_language,
            ),
            "mlx",
        )
    if config.qwen_asr_base_url is None:
        raise RuntimeError("QWEN_ASR_BASE_URL is required for ASR_BACKEND=qwen")
    return QwenASRAdapter(config.qwen_asr_base_url), "qwen"


def _build_tts(config: AppConfig, backend: str):
    if backend == "mock":
        from app.mocks import MockTTSAdapter

        return MockTTSAdapter(sample_rate=config.audio_sample_rate), "mock"
    if config.tts_backend == "mlx_qwen3":
        return (
            MLXQwenTTSAdapter(
                model=config.mlx_tts_model,
                lang_code=config.mlx_tts_language,
                voice=config.mlx_tts_voice,
            ),
            "mlx_qwen3",
        )
    if config.fish_tts_base_url is None:
        raise RuntimeError("FISH_TTS_BASE_URL is required for TTS_BACKEND=fish")
    return FishTTSAdapter(config.fish_tts_base_url), "fish"


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
        from app.mocks import MockAgentAdapter

        asr, asr_provider = _build_asr(config, backend)
        agent = MockAgentAdapter()
        tts, tts_provider = _build_tts(config, backend)
    else:
        asr, asr_provider = _build_asr(config, backend)
        agent = GeminiAdapter(
            config.gemini_api_key,
            model=config.llm_model,
            base_url=config.llm_base_url,
        )
        tts, tts_provider = _build_tts(config, backend)

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
        "asr_provider": asr_provider,
        "tts_provider": tts_provider,
        "llm_provider": config.llm_model,
        "asr": asr,
        "agent": agent,
        "tts": tts,
    }


def _recover_to_listening(app: dict, component: str, exc: Exception) -> None:
    LOGGER.exception("%s failure; recovering to listening: %s", component, exc)
    app["state_machine"].on_interrupt()


def _print_turn_latency(turn_started_at: float | None, printer: Callable[[str], None] = print) -> None:
    if turn_started_at is None:
        return
    elapsed_ms = int(round((time.perf_counter() - turn_started_at) * 1000))
    printer(f"Turn latency: {elapsed_ms} ms")


async def handle_event(app: dict, event: Event) -> None:
    machine: ConversationStateMachine = app["state_machine"]

    if event.type == EventType.USER_FINAL_TEXT:
        text = event.payload["text"]
        turn_started_at = event.payload.get("turn_started_at")
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
            Event(
                type=EventType.AGENT_TEXT_READY,
                payload={"text": reply, "turn_started_at": turn_started_at},
            ),
        )
        return

    if event.type == EventType.AGENT_TEXT_READY:
        text = event.payload["text"]
        turn_started_at = event.payload.get("turn_started_at")
        print(f"Host: {text}")
        machine.on_agent_reply_ready(text)
        try:
            with log_timing(
                LOGGER,
                component="tts",
                operation="synthesize",
                provider=app["tts_provider"],
            ):
                audio_bytes = await app["tts"].synthesize(text)
            await app["audio_out"].play(audio_bytes)
        except Exception as exc:
            _recover_to_listening(app, "tts", exc)
            return
        if app["audio_in"].has_pending_frame():
            await app["audio_in"].read_frame()
            await handle_event(app, Event(type=EventType.INTERRUPT, payload={}))
            _print_turn_latency(turn_started_at)
            return
        machine.on_playback_finished()
        _print_turn_latency(turn_started_at)
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
    turn_started_at = time.perf_counter()
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
            provider=app["asr_provider"],
        ):
            text = await app["asr"].transcribe_chunk(chunk)
    except Exception as exc:
        _recover_to_listening(app, "asr", exc)
        return
    await app["bus"].publish(
        Event(
            type=EventType.USER_FINAL_TEXT,
            payload={"text": text, "turn_started_at": turn_started_at},
        ),
    )


async def run_self_test(
    app: dict,
    *,
    printer: Callable[[str], None] = print,
    speech_timeout_s: float = 3.0,
) -> None:
    printer("Self-test mode")
    printer(f"ASR backend: {app['asr_provider']}")
    printer(f"TTS backend: {app['tts_provider']}")
    printer(f"Input device: {app['audio_in'].describe_input_target()}")
    printer(f"Output device: {app['audio_out'].describe_output_target()}")
    printer(f"Playback mode: {app['audio_out'].playback_mode}")

    transcript: str | None = None
    started_audio = False
    try:
        start_audio_input(app)
        started_audio = True
        try:
            frame = await asyncio.wait_for(app["audio_in"].read_frame(), timeout=speech_timeout_s)
        except asyncio.TimeoutError:
            printer("Speech frame detected: no")
        else:
            if app["audio_in"].is_speech_frame(frame):
                printer("Speech frame detected: yes")
                try:
                    transcript = await app["asr"].transcribe_chunk(frame)
                except Exception as exc:
                    printer(f"ASR text: unavailable ({exc})")
                else:
                    printer(f"ASR text: {transcript}")
            else:
                printer("Speech frame detected: no")
    except RuntimeError as exc:
        printer(f"Speech frame detected: unavailable ({exc})")
    finally:
        if started_audio:
            stop_audio_input(app)

    tts_text = transcript or "self test"
    try:
        audio_bytes = await app["tts"].synthesize(tts_text)
    except Exception as exc:
        printer(f"TTS audio bytes: unavailable ({exc})")
        return
    printer(f"TTS audio bytes: {len(audio_bytes)}")
    try:
        await app["audio_out"].play(audio_bytes)
    except Exception as exc:
        printer(f"Playback invoked: unavailable ({exc})")
        return
    printer(
        f"Playback invoked: {'yes' if getattr(app['audio_out'], 'playback_invoked', False) else 'no'}"
    )


def start_audio_input(app: dict) -> None:
    app["audio_in"].start_device_capture()


def stop_audio_input(app: dict) -> None:
    app["audio_in"].stop_device_capture()


async def run() -> None:
    app = build_app()
    configure_logging(app["config"].log_level)
    print("DeepTalk Agent CLI started. Press Ctrl+C to exit.")
    if os.getenv("PODCAST_SELF_TEST", "").strip().lower() in {"1", "true", "yes", "on"}:
        await run_self_test(app)
        return
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
