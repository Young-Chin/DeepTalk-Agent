import pytest

from app.bus import Event, EventType
from app.main import (
    build_app,
    consume_next_event,
    handle_event,
    pump_microphone_once,
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


class FakeTTS:
    def __init__(self, audio: bytes) -> None:
        self.audio = audio
        self.calls: list[str] = []

    async def synthesize(self, text: str) -> bytes:
        self.calls.append(text)
        return self.audio


class FakeAudioOut:
    def __init__(self) -> None:
        self.played: list[bytes] = []
        self.stop_calls = 0
        self.is_playing = False

    async def play(self, audio_bytes: bytes) -> None:
        self.played.append(audio_bytes)
        self.is_playing = True

    def stop(self) -> None:
        self.stop_calls += 1
        self.is_playing = False


class FakeASR:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[bytes] = []

    async def transcribe_chunk(self, pcm_bytes: bytes) -> str:
        self.calls.append(pcm_bytes)
        return self.text


class FakeMicrophone:
    def __init__(self) -> None:
        self.start_calls = 0
        self.stop_calls = 0

    def start_device_capture(self) -> None:
        self.start_calls += 1

    def stop_device_capture(self) -> None:
        self.stop_calls += 1


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
    assert event.payload == {"text": "采访开始"}


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
    assert event.payload == {"text": "合并后的语句"}


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
    app = _build_test_app(monkeypatch)
    fake_tts = FakeTTS(b"audio")
    fake_audio = FakeAudioOut()
    app["tts"] = fake_tts
    app["audio_out"] = fake_audio
    app["audio_in"].push_frame(b"interrupting-frame")

    await handle_event(
        app,
        Event(type=EventType.AGENT_TEXT_READY, payload={"text": "继续聊聊"}),
    )

    assert fake_tts.calls == ["继续聊聊"]
    assert fake_audio.played == [b"audio"]
    assert fake_audio.stop_calls == 1
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
