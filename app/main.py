from __future__ import annotations

import asyncio
import io
import importlib
import logging
import os
import select
import sys
import termios
import time
import tty
import wave
from collections.abc import Callable
from pathlib import Path

from app.bus import Event, EventBus, EventType
from app.agent.gemini_adapter import GeminiAdapter
from app.asr.mlx_adapter import MLXASRAdapter
from app.asr.qwen_adapter import QwenASRAdapter
from app.audio.in_stream import MicrophoneInput
from app.audio.out_stream import AudioOutput
from app.config import AppConfig, _load_dotenv, load_config
from app.memory.session_store import SessionStore
from app.observability.logger import configure_logging, log_timing
from app.state_machine import ConversationStateMachine, State
from app.tts.fish_adapter import FishTTSAdapter
from app.tts.qwen_adapter import MLXQwenTTSAdapter

LOGGER = logging.getLogger("podcast.runtime")


def _build_mock_config() -> AppConfig:
    return AppConfig(
        gemini_api_key="mock",
        llm_base_url="mock://llm",
        llm_model="mock-llm",
        llm_system_prompt=None,
        qwen_asr_base_url="mock://asr",
        fish_tts_base_url="mock://tts",
        asr_backend="mock",
        tts_backend="mock",
        mlx_tts_model_type="qwen3",
        mlx_tts_vibevoice_model="modelscope/VibeVoice-Realtime-0.5B-4bit",
        mlx_tts_kokoro_model="modelscope/Kokoro-82M-4bit",
        mlx_tts_qwen3_model="modelscope/Qwen3-TTS-12Hz-0.6B-Base-4bit",
        audio_sample_rate=int(os.getenv("AUDIO_SAMPLE_RATE", "16000")),
        vad_start_ms=int(os.getenv("VAD_START_MS", "120")),
        vad_interrupt_ms=int(os.getenv("VAD_INTERRUPT_MS", "200")),
        turn_silence_ms=int(os.getenv("TURN_SILENCE_MS", "1500")),
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
        # 根据配置选择 TTS 模型
        model_map = {
            "vibevoice": config.mlx_tts_vibevoice_model,
            "kokoro": config.mlx_tts_kokoro_model,
            "qwen3": config.mlx_tts_qwen3_model,
        }
        selected_model = model_map.get(config.mlx_tts_model_type, config.mlx_tts_vibevoice_model)
        LOGGER.info("DEBUG: config.mlx_tts_model_type=%s, available models=%s", config.mlx_tts_model_type, list(model_map.keys()))
        LOGGER.info("使用 TTS 模型：%s (%s)", config.mlx_tts_model_type, selected_model.split('/')[-1])
        return (
            MLXQwenTTSAdapter(
                model=selected_model,
                lang_code=config.mlx_tts_language,
                voice=config.mlx_tts_voice,
                speed=config.mlx_tts_speed,
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
    
    # 尽早初始化日志系统
    configure_logging(config.log_level)
    
    bus = EventBus()
    memory = SessionStore()
    state_machine = ConversationStateMachine(memory=memory)
    try:
        sounddevice_module = importlib.import_module("sounddevice")
        numpy_module = importlib.import_module("numpy")
    except (ModuleNotFoundError, OSError):
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
            system_prompt=config.llm_system_prompt,
        )
        tts, tts_provider = _build_tts(config, backend)

    app_dict = {
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

    _preload_models(app_dict)

    return app_dict


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


def _print_turn_latency(turn_started_at: float | None, printer: Callable[[str], None] = print) -> None:
    if turn_started_at is None:
        return
    elapsed_ms = int(round((time.perf_counter() - turn_started_at) * 1000))
    printer(f"Turn latency: {elapsed_ms} ms")


def _preload_models(app: dict, printer=None) -> None:
    """Warm up lazy-loaded MLX models on startup."""
    if printer is None:
        printer = print
    config = app["config"]
    if app["asr_provider"] == "mlx":
        try:
            app["asr"]._transcriber._model_instance()
            printer(f"ASR model preloaded: {config.mlx_asr_model}")
        except Exception as exc:
            printer(f"Warning: ASR model preload skipped: {exc}")
    if app["tts_provider"] == "mlx_qwen3":
        try:
            app["tts"]._model._model_instance()
            model_map = {
                "vibevoice": config.mlx_tts_vibevoice_model,
                "kokoro": config.mlx_tts_kokoro_model,
                "qwen3": config.mlx_tts_qwen3_model,
            }
            selected_model = model_map.get(config.mlx_tts_model_type, config.mlx_tts_qwen3_model)
            printer(f"TTS model preloaded: {selected_model}")
        except Exception as exc:
            printer(f"Warning: TTS model preload skipped: {exc}")


def _describe_asr_model(app: dict) -> str:
    config: AppConfig = app["config"]
    if app["asr_provider"] == "mlx":
        return config.mlx_asr_model
    if app["asr_provider"] == "mock":
        return "mock"
    return config.qwen_asr_base_url or "unconfigured"


def _describe_tts_model(app: dict) -> str:
    config: AppConfig = app["config"]
    if app["tts_provider"] == "mlx_qwen3":
        model_map = {
            "vibevoice": config.mlx_tts_vibevoice_model,
            "kokoro": config.mlx_tts_kokoro_model,
            "qwen3": config.mlx_tts_qwen3_model,
        }
        return model_map.get(config.mlx_tts_model_type, config.mlx_tts_qwen3_model)
    if app["tts_provider"] == "mock":
        return "mock"
    return config.fish_tts_base_url or "unconfigured"


def _load_demo_audio_bytes(path: str) -> bytes:
    audio_path = Path(path)
    raw = audio_path.read_bytes()
    if raw.startswith(b"RIFF") and b"WAVE" in raw[:16]:
        with wave.open(io.BytesIO(raw), "rb") as wav_file:
            return wav_file.readframes(wav_file.getnframes())
    return raw


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
        
        # 记录 LLM 回复完成时间点
        llm_done_at = time.perf_counter()
        LOGGER.info(
            "LLM 回复完成，准备 TTS 合成",
            extra={"latency_ms": int((llm_done_at - turn_started_at) * 1000) if turn_started_at else 0},
        )
        
        await handle_event(
            app,
            Event(
                type=EventType.AGENT_TEXT_READY,
                payload={"text": reply, "turn_started_at": turn_started_at, "llm_done_at": llm_done_at},
            ),
        )
        return

    if event.type == EventType.AGENT_TEXT_READY:
        text = event.payload["text"]
        turn_started_at = event.payload.get("turn_started_at")
        llm_done_at = event.payload.get("llm_done_at")
        print(f"Host: {text}")
        
        # 测量打印到 TTS 合成的延迟
        print_after = time.perf_counter()
        if llm_done_at:
            print_to_tts_start_ms = int((print_after - llm_done_at) * 1000)
            LOGGER.info(f"打印后等待 TTS 合成：{print_to_tts_start_ms}ms")
        
        machine.on_agent_reply_ready(text)
        try:
            tts_start = time.perf_counter()
            
            # 优化：TTS 合成和播放准备并行执行
            # 创建 TTS 合成任务
            tts_task = asyncio.create_task(app["tts"].synthesize(text))
            
            # 等待 TTS 完成
            with log_timing(
                LOGGER,
                component="tts",
                operation="synthesize",
                provider=app["tts_provider"],
            ):
                audio_bytes = await tts_task
            
            tts_end = time.perf_counter()
            tts_duration_ms = int((tts_end - tts_start) * 1000)
            LOGGER.info(f"TTS 合成总耗时：{tts_duration_ms}ms")
            
            # 测量 TTS 合成后到播放开始的延迟
            play_start = time.perf_counter()
            tts_to_play_ms = int((play_start - tts_end) * 1000)
            LOGGER.info(f"TTS 合成完成到播放开始：{tts_to_play_ms}ms")
            
            await app["audio_out"].play(audio_bytes)
        except Exception as exc:
            _recover_to_listening(app, "tts", exc)
            return

        interrupted = await _wait_for_playback_done(app)
        if interrupted:
            app["state_machine"].on_interrupt()
            _print_turn_latency(turn_started_at)
        else:
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
    printer(f"LLM model: {app['config'].llm_model}")
    printer(f"ASR model: {_describe_asr_model(app)}")
    printer(f"TTS model: {_describe_tts_model(app)}")
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


async def run_text_demo(
    app: dict,
    text: str,
    *,
    printer: Callable[[str], None] = print,
) -> None:
    printer("Text demo mode")
    printer(f"LLM model: {app['config'].llm_model}")
    printer(f"TTS backend: {app['tts_provider']}")
    printer(f"TTS model: {_describe_tts_model(app)}")
    await handle_event(
        app,
        Event(
            type=EventType.USER_FINAL_TEXT,
            payload={"text": text, "turn_started_at": time.perf_counter()},
        ),
    )


async def run_audio_demo(
    app: dict,
    audio_bytes: bytes,
    *,
    printer: Callable[[str], None] = print,
) -> None:
    printer("Audio demo mode")
    printer(f"ASR backend: {app['asr_provider']}")
    printer(f"LLM model: {app['config'].llm_model}")
    printer(f"TTS backend: {app['tts_provider']}")
    printer(f"ASR model: {_describe_asr_model(app)}")
    printer(f"TTS model: {_describe_tts_model(app)}")

    turn_started_at = time.perf_counter()
    with log_timing(
        LOGGER,
        component="asr",
        operation="transcribe_chunk",
        provider=app["asr_provider"],
    ):
        text = await app["asr"].transcribe_chunk(audio_bytes)
    await handle_event(
        app,
        Event(
            type=EventType.USER_FINAL_TEXT,
            payload={"text": text, "turn_started_at": turn_started_at},
        ),
    )


def start_audio_input(app: dict) -> None:
    app["audio_in"].start_device_capture()


def stop_audio_input(app: dict) -> None:
    app["audio_in"].stop_device_capture()


def _frame_energy(frame: bytes) -> float:
    """Calculate average absolute sample energy (0-32767 scale)."""
    import struct

    if not frame:
        return 0.0
    sample_count = len(frame) // 2
    if sample_count == 0:
        return 0.0
    samples = struct.unpack("<" + "h" * sample_count, frame[: sample_count * 2])
    return sum(abs(s) for s in samples) / sample_count


def _render_volume_meter(frame: bytes) -> None:
    """Draw a simple volume meter in-place on the terminal."""
    energy = _frame_energy(frame)
    bars = int(min(energy / 800, 30))
    bar_str = ("\u2588" * bars) + ("\u2591" * (30 - bars))
    sys.stdout.write(f"\rRecording... [{bar_str}] {energy:.0f}  ")
    sys.stdout.flush()


class _TerminalKeyReader:
    """Non-blocking single-key reader for push-to-talk in terminal."""

    def __init__(self) -> None:
        self._old_settings: list | None = None

    def __enter__(self) -> "_TerminalKeyReader":
        if not sys.stdin.isatty():
            raise RuntimeError("Push-to-talk requires a terminal")
        self._old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        return self

    def __exit__(self, *args: object) -> None:
        if self._old_settings is not None:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old_settings)

    def wait_for_key(self) -> None:
        """Block until any key is pressed."""
        select.select([sys.stdin], [], [])
        sys.stdin.read(1)


async def _run_push_to_talk(app: dict) -> None:
    """Push-to-talk loop: press any key to start recording, press again to stop."""
    print("Push-to-talk mode: press any key to toggle recording")
    key_reader = _TerminalKeyReader()

    with key_reader:
        while True:
            print("\n[\u23f8] Press any key to start recording...", end="", flush=True)
            key_reader.wait_for_key()

            print("\n[\u23fa] Recording... Press any key to stop")
            app["audio_in"].drain_pending_frames()
            start_audio_input(app)
            print("[", end="", flush=True)

            stop_recording = asyncio.Event()
            loop = asyncio.get_running_loop()

            def _wait_for_key() -> None:
                select.select([sys.stdin], [], [])
                sys.stdin.read(1)
                loop.call_soon_threadsafe(stop_recording.set)

            key_task = loop.run_in_executor(None, _wait_for_key)

            try:
                while not stop_recording.is_set():
                    try:
                        frame = app["audio_in"]._queue.get_nowait()
                        app["audio_in"].push_frame(frame)
                        _render_volume_meter(frame)
                    except asyncio.QueueEmpty:
                        pass
                    try:
                        await asyncio.wait_for(stop_recording.wait(), timeout=0.05)
                    except asyncio.TimeoutError:
                        continue
            finally:
                stop_audio_input(app)
                stop_recording.set()
                sys.stdout.write("\r" + " " * 64 + "\r")
                sys.stdout.flush()

            print("[\u23f9] Stopped. Transcribing...")
            pending = app["audio_in"].drain_pending_frames()
            if not pending:
                print("[No audio captured]")
                continue

            chunk = b"".join(pending)
            turn_started_at = time.perf_counter()
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
                continue

            await app["bus"].publish(
                Event(
                    type=EventType.USER_FINAL_TEXT,
                    payload={"text": text, "turn_started_at": turn_started_at},
                ),
            )
            await consume_next_event(app)


async def run() -> None:
    app = build_app()
    print("DeepTalk Agent CLI started. Press Ctrl+C to exit.")
    if os.getenv("PODCAST_SELF_TEST", "").strip().lower() in {"1", "true", "yes", "on"}:
        await run_self_test(app)
        return
    text_demo = os.getenv("PODCAST_TEXT_DEMO", "").strip()
    if text_demo:
        await run_text_demo(app, text_demo)
        return
    audio_demo_path = os.getenv("PODCAST_DEMO_AUDIO", "").strip()
    if audio_demo_path:
        await run_audio_demo(app, _load_demo_audio_bytes(audio_demo_path))
        return

    ptt = os.getenv("PODCAST_PTT", "").strip().lower()
    if ptt in {"1", "true", "yes", "on"}:
        await _run_push_to_talk(app)
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
