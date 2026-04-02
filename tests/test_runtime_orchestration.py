import pytest
from unittest.mock import patch

from app.bus import Event, EventType
from app.audio.out_stream import AudioOutput
from app.main import (
    build_app,
    consume_next_event,
    handle_event,
    pump_microphone_once,
    run_audio_demo,
    run_text_demo,
    run_self_test,
    start_audio_input,
    stop_audio_input,
)
from app.state_machine import State


class FakeAgent:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls: list[list[dict]] = []

    async def next_host_reply(self, history: list[dict]) -> str:
        self.calls.append(history)
        return self.reply


class FailingAgent:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls: list[list[dict]] = []

    async def next_host_reply(self, history: list[dict]) -> str:
        self.calls.append(history)
        raise self.error


class FakeTTS:
    def __init__(self, audio: bytes) -> None:
        self.audio = audio
        self.calls: list[str] = []

    async def synthesize(self, text: str) -> bytes:
        self.calls.append(text)
        return self.audio


class FailingTTS:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls: list[str] = []

    async def synthesize(self, text: str) -> bytes:
        self.calls.append(text)
        raise self.error


class FakeAudioOut:
    def __init__(self, wait_event=None) -> None:
        self.played: list[bytes] = []
        self.stop_calls = 0
        self.is_playing = False
        self._wait_event = wait_event
        self.last_played: bytes | None = None
        self.playback_mode = "real"
        self.playback_invoked = False

    async def play(self, audio_bytes: bytes) -> None:
        self.played.append(audio_bytes)
        self.is_playing = True
        self.last_played = audio_bytes
        self.playback_invoked = True

    async def wait(self) -> None:
        """Block until playback completes (or test event is set)."""
        if self._wait_event is not None:
            await self._wait_event.wait()
        self.is_playing = False

    def stop(self) -> None:
        self.stop_calls += 1
        self.is_playing = False

    def describe_output_target(self) -> str:
        return "Fake Speaker"


class FakeASR:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[bytes] = []

    async def transcribe_chunk(self, pcm_bytes: bytes) -> str:
        self.calls.append(pcm_bytes)
        return self.text


class FailingASR:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls: list[bytes] = []

    async def transcribe_chunk(self, pcm_bytes: bytes) -> str:
        self.calls.append(pcm_bytes)
        raise self.error


class FakeMicrophone:
    def __init__(self) -> None:
        self.start_calls = 0
        self.stop_calls = 0

    def start_device_capture(self) -> None:
        self.start_calls += 1

    def stop_device_capture(self) -> None:
        self.stop_calls += 1

    def describe_input_target(self) -> str:
        return "Fake Microphone"


class FailingAudioOut(FakeAudioOut):
    def __init__(self, error: Exception) -> None:
        super().__init__()
        self.error = error

    async def play(self, audio_bytes: bytes) -> None:
        raise self.error


def _build_test_app(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("QWEN_ASR_BASE_URL", "http://localhost:8001")
    monkeypatch.setenv("FISH_TTS_BASE_URL", "http://localhost:8002")
    return build_app()


@pytest.mark.asyncio
async def test_handle_user_final_text_drives_agent_tts_and_memory(monkeypatch):
    app = _build_test_app(monkeypatch)
    fake_agent = FakeAgent("欢迎来到节目")
    fake_tts = FakeTTS(b"audio")
    fake_audio = FakeAudioOut()
    app["agent"] = fake_agent
    app["tts"] = fake_tts
    app["audio_out"] = fake_audio

    await handle_event(
        app,
        Event(type=EventType.USER_FINAL_TEXT, payload={"text": "你好"}),
    )

    assert fake_agent.calls[0][-1]["content"] == "你好"
    assert fake_tts.calls == ["欢迎来到节目"]
    assert fake_audio.played == [b"audio"]
    assert app["state_machine"].state == State.LISTENING
    assert app["memory"].snapshot()[-1]["content"] == "欢迎来到节目"


@pytest.mark.asyncio
async def test_handle_interrupt_stops_audio_and_resets_state(monkeypatch):
    app = _build_test_app(monkeypatch)
    fake_audio = FakeAudioOut()
    app["audio_out"] = fake_audio
    app["state_machine"].on_agent_reply_ready("先说到这里")

    await handle_event(app, Event(type=EventType.INTERRUPT, payload={}))

    assert fake_audio.stop_calls == 1
    assert app["state_machine"].state == State.LISTENING


@pytest.mark.asyncio
async def test_consume_next_event_reads_from_bus_and_processes_it(monkeypatch):
    app = _build_test_app(monkeypatch)
    fake_agent = FakeAgent("欢迎来到节目")
    fake_tts = FakeTTS(b"audio")
    fake_audio = FakeAudioOut()
    app["agent"] = fake_agent
    app["tts"] = fake_tts
    app["audio_out"] = fake_audio

    await app["bus"].publish(
        Event(type=EventType.USER_FINAL_TEXT, payload={"text": "你好"}),
    )

    await consume_next_event(app)

    assert fake_agent.calls[0][-1]["content"] == "你好"
    assert fake_audio.played == [b"audio"]
    assert app["state_machine"].state == State.LISTENING


@pytest.mark.asyncio
async def test_pump_microphone_once_transcribes_and_publishes_user_text(monkeypatch):
    app = _build_test_app(monkeypatch)
    fake_asr = FakeASR("采访开始")
    app["asr"] = fake_asr
    app["audio_in"].push_frame(b"pcm-frame")

    await pump_microphone_once(app)
    event = await app["bus"].next_event()

    assert fake_asr.calls == [b"pcm-frame"]
    assert event.type == EventType.USER_FINAL_TEXT
    assert event.payload["text"] == "采访开始"
    assert isinstance(event.payload["turn_started_at"], float)


@pytest.mark.asyncio
async def test_pump_microphone_once_batches_pending_speech_frames(monkeypatch):
    app = _build_test_app(monkeypatch)
    fake_asr = FakeASR("合并后的语句")
    app["asr"] = fake_asr
    app["audio_in"].push_frame(b"frame-a")
    app["audio_in"].push_frame(b"frame-b")
    app["audio_in"].push_frame(b"frame-c")

    await pump_microphone_once(app)
    event = await app["bus"].next_event()

    assert fake_asr.calls == [b"frame-aframe-bframe-c"]
    assert event.payload["text"] == "合并后的语句"
    assert isinstance(event.payload["turn_started_at"], float)


@pytest.mark.asyncio
async def test_pump_microphone_once_skips_non_speech_frames(monkeypatch):
    app = _build_test_app(monkeypatch)
    fake_asr = FakeASR("不会被调用")
    app["asr"] = fake_asr
    app["audio_in"].push_frame(b"")

    await pump_microphone_once(app)

    assert fake_asr.calls == []


@pytest.mark.asyncio
async def test_agent_reply_is_interrupted_when_new_audio_arrives(monkeypatch):
    import asyncio as _asyncio

    app = _build_test_app(monkeypatch)
    fake_tts = FakeTTS(b"audio")
    app["tts"] = fake_tts

    # Use an event to make FakeAudioOut.wait() block until the monitor
    # has detected speech and called stop().
    playback_done = _asyncio.Event()
    fake_audio = FakeAudioOut(wait_event=playback_done)
    app["audio_out"] = fake_audio

    # Pre-fill speech frames in the audio input queue so the VAD monitor
    # detects speech and triggers an interrupt during playback.
    for _ in range(20):
        app["audio_in"].push_frame(b"\x08\x03" * 240)  # high-energy PCM16 samples

    # Ensure the playback event only fires AFTER stop() is called.
    original_stop = fake_audio.stop
    def _stop_and_set():
        original_stop()
        playback_done.set()
    fake_audio.stop = _stop_and_set

    await handle_event(
        app,
        Event(type=EventType.AGENT_TEXT_READY, payload={"text": "继续聊聊"}),
    )

    assert fake_tts.calls == ["继续聊聊"]
    assert fake_audio.played == [b"audio"]
    assert fake_audio.stop_calls == 1
    assert app["state_machine"].state == State.LISTENING
    assert app["memory"].snapshot() == []


@pytest.mark.asyncio
async def test_handle_user_final_text_recovers_to_listening_when_agent_fails(
    monkeypatch,
):
    app = _build_test_app(monkeypatch)
    app["agent"] = FailingAgent(RuntimeError("llm unavailable"))

    await handle_event(
        app,
        Event(type=EventType.USER_FINAL_TEXT, payload={"text": "你好"}),
    )

    assert app["state_machine"].state == State.LISTENING
    assert app["state_machine"].current_agent_reply is None
    assert app["memory"].snapshot() == [{"role": "user", "content": "你好"}]


@pytest.mark.asyncio
async def test_handle_agent_text_ready_recovers_without_persisting_reply_when_tts_fails(
    monkeypatch,
):
    app = _build_test_app(monkeypatch)
    app["tts"] = FailingTTS(RuntimeError("tts unavailable"))
    app["audio_out"] = FakeAudioOut()

    await handle_event(
        app,
        Event(type=EventType.AGENT_TEXT_READY, payload={"text": "继续聊聊"}),
    )

    assert app["state_machine"].state == State.LISTENING
    assert app["state_machine"].current_agent_reply is None
    assert app["memory"].snapshot() == []
    assert app["audio_out"].played == []


@pytest.mark.asyncio
async def test_pump_microphone_once_recovers_to_listening_when_asr_fails(monkeypatch):
    app = _build_test_app(monkeypatch)
    fake_asr = FailingASR(RuntimeError("asr unavailable"))
    app["asr"] = fake_asr
    app["audio_in"].push_frame(b"pcm-frame")

    await pump_microphone_once(app)

    assert fake_asr.calls == [b"pcm-frame"]
    assert app["state_machine"].state == State.LISTENING
    assert app["memory"].snapshot() == []


def test_start_audio_input_starts_device_capture():
    app = {"audio_in": FakeMicrophone()}

    start_audio_input(app)

    assert app["audio_in"].start_calls == 1


def test_stop_audio_input_stops_device_capture():
    app = {"audio_in": FakeMicrophone()}

    stop_audio_input(app)

    assert app["audio_in"].stop_calls == 1


@pytest.mark.asyncio
async def test_handle_event_prints_transcript_and_agent_reply(monkeypatch, capsys):
    app = _build_test_app(monkeypatch)
    app["agent"] = FakeAgent("欢迎来到节目")
    app["tts"] = FakeTTS(b"audio")
    app["audio_out"] = FakeAudioOut()

    await handle_event(
        app,
        Event(type=EventType.USER_FINAL_TEXT, payload={"text": "你好"}),
    )

    output = capsys.readouterr().out
    assert "User: 你好" in output
    assert "Host: 欢迎来到节目" in output


@pytest.mark.asyncio
async def test_handle_event_prints_turn_latency_when_turn_start_is_present(
    monkeypatch, capsys
):
    app = _build_test_app(monkeypatch)
    app["agent"] = FakeAgent("欢迎来到节目")
    app["tts"] = FakeTTS(b"audio")
    app["audio_out"] = FakeAudioOut()

    with patch("app.main.time.perf_counter", return_value=100.123):
        await handle_event(
            app,
            Event(
                type=EventType.USER_FINAL_TEXT,
                payload={"text": "你好", "turn_started_at": 100.0},
            ),
        )

    output = capsys.readouterr().out
    assert "Turn latency: 123 ms" in output


@pytest.mark.asyncio
async def test_run_self_test_reports_devices_and_pipeline_status(monkeypatch):
    app = _build_test_app(monkeypatch)
    app["audio_in"].push_frame(b"pcm-frame")
    app["asr"] = FakeASR("你好，世界")
    app["tts"] = FakeTTS(b"audio")
    app["audio_out"] = FakeAudioOut()
    app["audio_in"].start_device_capture = lambda: None
    app["audio_in"].stop_device_capture = lambda: None
    app["audio_in"].describe_input_target = lambda: "Fake Microphone"
    app["audio_in"].is_speech_frame = lambda frame: True
    app["audio_out"].describe_output_target = lambda: "Fake Speaker"
    lines: list[str] = []

    await run_self_test(app, printer=lines.append, speech_timeout_s=0.01)

    assert "ASR backend: mlx" in lines
    assert "TTS backend: mlx_qwen3" in lines
    assert "LLM model: qwen3.5-flash" in lines
    assert "ASR model: mlx-community/Qwen3-ASR-0.6B-4bit" in lines
    assert "TTS model: mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit" in lines
    assert "Input device: Fake Microphone" in lines
    assert "Output device: Fake Speaker" in lines
    assert "Playback mode: real" in lines
    assert "Speech frame detected: yes" in lines
    assert "ASR text: 你好，世界" in lines
    assert "TTS audio bytes: 5" in lines
    assert "Playback invoked: yes" in lines


@pytest.mark.asyncio
async def test_run_self_test_reports_memory_fallback_without_false_playback_success(
    monkeypatch,
):
    app = _build_test_app(monkeypatch)
    app["audio_in"].start_device_capture = lambda: None
    app["audio_in"].stop_device_capture = lambda: None
    app["audio_in"].describe_input_target = lambda: "Fake Microphone"
    app["audio_out"] = AudioOutput(sounddevice_module=None, numpy_module=None)
    app["tts"] = FakeTTS(b"audio")
    lines: list[str] = []

    await run_self_test(app, printer=lines.append, speech_timeout_s=0.01)

    assert "Playback mode: memory" in lines
    assert "Playback invoked: no" in lines


@pytest.mark.asyncio
async def test_run_self_test_reports_playback_failure_instead_of_crashing(monkeypatch):
    app = _build_test_app(monkeypatch)
    app["audio_in"].start_device_capture = lambda: None
    app["audio_in"].stop_device_capture = lambda: None
    app["audio_in"].describe_input_target = lambda: "Fake Microphone"
    app["audio_out"] = FailingAudioOut(RuntimeError("speaker unavailable"))
    app["tts"] = FakeTTS(b"audio")
    lines: list[str] = []

    await run_self_test(app, printer=lines.append, speech_timeout_s=0.01)

    assert "Playback invoked: unavailable (speaker unavailable)" in lines


@pytest.mark.asyncio
async def test_run_text_demo_drives_llm_tts_and_playback(monkeypatch):
    app = _build_test_app(monkeypatch)
    app["agent"] = FakeAgent("欢迎来到节目")
    app["tts"] = FakeTTS(b"audio")
    app["audio_out"] = FakeAudioOut()
    lines: list[str] = []

    await run_text_demo(app, "请先自我介绍一下", printer=lines.append)

    assert "Text demo mode" in lines
    assert "LLM model: qwen3.5-flash" in lines
    assert "TTS backend: mlx_qwen3" in lines
    assert app["audio_out"].played == [b"audio"]
    assert app["memory"].snapshot()[-1]["content"] == "欢迎来到节目"


@pytest.mark.asyncio
async def test_run_audio_demo_drives_asr_llm_tts_and_playback(monkeypatch):
    app = _build_test_app(monkeypatch)
    app["asr"] = FakeASR("这是脚本化转写")
    app["agent"] = FakeAgent("欢迎来到节目")
    app["tts"] = FakeTTS(b"audio")
    app["audio_out"] = FakeAudioOut()
    lines: list[str] = []

    await run_audio_demo(app, b"pcm-frame", printer=lines.append)

    assert "Audio demo mode" in lines
    assert "ASR backend: mlx" in lines
    assert "LLM model: qwen3.5-flash" in lines
    assert "TTS backend: mlx_qwen3" in lines
    assert app["audio_out"].played == [b"audio"]
    assert app["memory"].snapshot()[0]["content"] == "这是脚本化转写"
