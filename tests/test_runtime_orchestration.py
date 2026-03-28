import pytest

from app.bus import Event, EventType
from app.main import build_app, handle_event
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

    async def play(self, audio_bytes: bytes) -> None:
        self.played.append(audio_bytes)

    def stop(self) -> None:
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
