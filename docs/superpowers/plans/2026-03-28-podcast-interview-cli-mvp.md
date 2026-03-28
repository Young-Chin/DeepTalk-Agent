# Podcast Interview CLI MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable CLI demo that supports microphone input, ASR→LLM→TTS turn-taking, and barge-in interruption (half-duplex) in Chinese.

**Architecture:** Use a single-process, event-driven pipeline with clear adapters for Qwen3-ASR, Gemini, and Fish Speech. A finite state machine orchestrates `LISTENING → TRANSCRIBING → THINKING → SPEAKING`, while an interrupt controller listens for user speech during playback and immediately stops TTS output.

**Tech Stack:** Python 3.11+, `pytest`, `sounddevice`, `numpy`, `webrtcvad`, `httpx`, standard library `asyncio`.

---

## File Structure

- `app/main.py`: CLI entrypoint and lifecycle bootstrap.
- `app/config.py`: environment-based configuration with validation.
- `app/bus.py`: typed event definitions + in-memory async event bus.
- `app/state_machine.py`: state transitions and side-effect orchestration.
- `app/audio/in_stream.py`: microphone capture + VAD speech windows.
- `app/audio/out_stream.py`: audio playback with immediate stop support.
- `app/asr/qwen_adapter.py`: Qwen3-ASR HTTP client adapter.
- `app/agent/gemini_adapter.py`: Gemini interviewer response adapter.
- `app/tts/fish_adapter.py`: Fish Speech HTTP streaming adapter.
- `app/memory/session_store.py`: in-memory conversation turns.
- `app/observability/logger.py`: structured logs + latency helpers.
- `tests/test_config.py`: config parsing and required env tests.
- `tests/test_bus.py`: event bus publish/subscribe tests.
- `tests/test_state_machine.py`: state transition + interrupt behavior tests.
- `tests/test_session_store.py`: memory behavior tests.
- `tests/test_adapters_contract.py`: adapter payload/response contract tests.
- `.env.example`: required runtime variables.
- `requirements.txt`: runtime and test dependencies.
- `README.md`: setup, run, and troubleshooting notes.

### Task 1: Bootstrap project skeleton and config guardrails

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `app/config.py`
- Create: `tests/test_config.py`
- Create: `app/__init__.py`

- [ ] **Step 1: Write the failing config tests**

```python
# tests/test_config.py
import os
import pytest

from app.config import AppConfig, ConfigError, load_config


def test_load_config_reads_required_values(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("QWEN_ASR_BASE_URL", "http://localhost:8001")
    monkeypatch.setenv("FISH_TTS_BASE_URL", "http://localhost:8002")

    cfg = load_config()
    assert isinstance(cfg, AppConfig)
    assert cfg.audio_sample_rate == 16000


def test_load_config_raises_when_required_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("QWEN_ASR_BASE_URL", "http://localhost:8001")
    monkeypatch.setenv("FISH_TTS_BASE_URL", "http://localhost:8002")

    with pytest.raises(ConfigError):
        load_config()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`  
Expected: FAIL with `ModuleNotFoundError` for `app.config`.

- [ ] **Step 3: Implement config module minimally**

```python
# app/config.py
from dataclasses import dataclass
import os


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class AppConfig:
    gemini_api_key: str
    qwen_asr_base_url: str
    fish_tts_base_url: str
    audio_sample_rate: int = 16000
    vad_start_ms: int = 120
    vad_interrupt_ms: int = 200
    turn_silence_ms: int = 600
    log_level: str = "INFO"


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"Missing required env: {name}")
    return value


def load_config() -> AppConfig:
    return AppConfig(
        gemini_api_key=_required("GEMINI_API_KEY"),
        qwen_asr_base_url=_required("QWEN_ASR_BASE_URL"),
        fish_tts_base_url=_required("FISH_TTS_BASE_URL"),
        audio_sample_rate=int(os.getenv("AUDIO_SAMPLE_RATE", "16000")),
        vad_start_ms=int(os.getenv("VAD_START_MS", "120")),
        vad_interrupt_ms=int(os.getenv("VAD_INTERRUPT_MS", "200")),
        turn_silence_ms=int(os.getenv("TURN_SILENCE_MS", "600")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`  
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .env.example app/__init__.py app/config.py tests/test_config.py
git commit -m "chore: bootstrap config and environment contract"
```

### Task 2: Build typed event bus and session memory core

**Files:**
- Create: `app/bus.py`
- Create: `app/memory/session_store.py`
- Create: `tests/test_bus.py`
- Create: `tests/test_session_store.py`

- [ ] **Step 1: Write failing bus and session store tests**

```python
# tests/test_bus.py
import asyncio
import pytest

from app.bus import EventBus, Event, EventType


@pytest.mark.asyncio
async def test_bus_delivers_events_in_order():
    bus = EventBus()
    await bus.publish(Event(type=EventType.USER_FINAL_TEXT, payload={"text": "你好"}))
    await bus.publish(Event(type=EventType.AGENT_TEXT_READY, payload={"text": "欢迎"}))
    items = [await bus.next_event(), await bus.next_event()]
    assert [x.type for x in items] == [EventType.USER_FINAL_TEXT, EventType.AGENT_TEXT_READY]
```

```python
# tests/test_session_store.py
from app.memory.session_store import SessionStore


def test_session_store_keeps_recent_turns():
    store = SessionStore(max_turns=2)
    store.add_user_turn("A")
    store.add_agent_turn("B", interrupted=False)
    store.add_user_turn("C")
    assert len(store.snapshot()) == 2
    assert store.snapshot()[-1]["content"] == "C"
```

- [ ] **Step 2: Run tests to verify failures**

Run: `pytest tests/test_bus.py tests/test_session_store.py -v`  
Expected: FAIL with missing modules.

- [ ] **Step 3: Implement minimal bus and memory**

```python
# app/bus.py
from dataclasses import dataclass
from enum import Enum
from typing import Any
import asyncio


class EventType(str, Enum):
    USER_FINAL_TEXT = "user_final_text"
    AGENT_TEXT_READY = "agent_text_ready"
    INTERRUPT = "interrupt"


@dataclass
class Event:
    type: EventType
    payload: dict[str, Any]


class EventBus:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[Event] = asyncio.Queue()

    async def publish(self, event: Event) -> None:
        await self._queue.put(event)

    async def next_event(self) -> Event:
        return await self._queue.get()
```

```python
# app/memory/session_store.py
from collections import deque


class SessionStore:
    def __init__(self, max_turns: int = 8) -> None:
        self._turns = deque(maxlen=max_turns)

    def add_user_turn(self, text: str) -> None:
        self._turns.append({"role": "user", "content": text})

    def add_agent_turn(self, text: str, interrupted: bool) -> None:
        self._turns.append({"role": "assistant", "content": text, "interrupted": interrupted})

    def snapshot(self) -> list[dict]:
        return list(self._turns)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_bus.py tests/test_session_store.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/bus.py app/memory/session_store.py tests/test_bus.py tests/test_session_store.py
git commit -m "feat: add event bus and in-memory session store"
```

### Task 3: Implement ASR/LLM/TTS adapter contracts with mocks-first tests

**Files:**
- Create: `app/asr/qwen_adapter.py`
- Create: `app/agent/gemini_adapter.py`
- Create: `app/tts/fish_adapter.py`
- Create: `tests/test_adapters_contract.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Write failing adapter contract tests**

```python
# tests/test_adapters_contract.py
import pytest
import httpx

from app.asr.qwen_adapter import QwenASRAdapter
from app.agent.gemini_adapter import GeminiAdapter
from app.tts.fish_adapter import FishTTSAdapter


@pytest.mark.asyncio
async def test_qwen_adapter_returns_final_text(httpx_mock):
    httpx_mock.add_response(json={"text": "你好世界"})
    adapter = QwenASRAdapter("http://localhost:8001")
    text = await adapter.transcribe_chunk(b"pcm")
    assert text == "你好世界"
```

- [ ] **Step 2: Run tests to verify failures**

Run: `pytest tests/test_adapters_contract.py -v`  
Expected: FAIL with missing adapter modules.

- [ ] **Step 3: Implement minimal adapter code**

```python
# app/asr/qwen_adapter.py
import httpx


class QwenASRAdapter:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def transcribe_chunk(self, pcm_bytes: bytes) -> str:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{self.base_url}/transcribe", content=pcm_bytes)
            resp.raise_for_status()
            return resp.json()["text"]
```

```python
# app/agent/gemini_adapter.py
import httpx


class GeminiAdapter:
    def __init__(self, api_key: str, model: str = "gemini-3.1-pro") -> None:
        self.api_key = api_key
        self.model = model

    async def next_host_reply(self, history: list[dict]) -> str:
        payload = {"model": self.model, "history": history}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post("https://generativelanguage.googleapis.com/v1/chat:completions", json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()["text"]
```

```python
# app/tts/fish_adapter.py
import httpx


class FishTTSAdapter:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def synthesize(self, text: str) -> bytes:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(f"{self.base_url}/synthesize", json={"text": text})
            resp.raise_for_status()
            return resp.content
```

- [ ] **Step 4: Add required deps and re-run tests**

Run:
- `printf '%s\n' "httpx>=0.27,<1.0" "pytest>=8.0,<9.0" "pytest-asyncio>=0.23,<1.0" "pytest-httpx>=0.30,<1.0" >> requirements.txt`
- `pytest tests/test_adapters_contract.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt app/asr/qwen_adapter.py app/agent/gemini_adapter.py app/tts/fish_adapter.py tests/test_adapters_contract.py
git commit -m "feat: add ASR LLM TTS adapters with contract tests"
```

### Task 4: Implement state machine with interruption behavior

**Files:**
- Create: `app/state_machine.py`
- Create: `tests/test_state_machine.py`
- Modify: `app/bus.py`
- Modify: `app/memory/session_store.py`

- [ ] **Step 1: Write failing state tests for normal turn + interrupt**

```python
# tests/test_state_machine.py
import pytest

from app.state_machine import ConversationStateMachine, State
from app.memory.session_store import SessionStore


def test_interrupt_during_speaking_switches_to_listening():
    memory = SessionStore()
    machine = ConversationStateMachine(memory=memory)
    machine.state = State.SPEAKING
    machine.on_interrupt()
    assert machine.state == State.LISTENING
```

- [ ] **Step 2: Run tests to verify failures**

Run: `pytest tests/test_state_machine.py -v`  
Expected: FAIL with missing module.

- [ ] **Step 3: Implement minimal state machine**

```python
# app/state_machine.py
from enum import Enum
from app.memory.session_store import SessionStore


class State(str, Enum):
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    SPEAKING = "speaking"


class ConversationStateMachine:
    def __init__(self, memory: SessionStore) -> None:
        self.memory = memory
        self.state = State.LISTENING
        self.current_agent_reply: str | None = None

    def on_user_final_text(self, text: str) -> None:
        self.memory.add_user_turn(text)
        self.state = State.THINKING

    def on_agent_reply_ready(self, text: str) -> None:
        self.current_agent_reply = text
        self.state = State.SPEAKING

    def on_playback_finished(self) -> None:
        if self.current_agent_reply:
            self.memory.add_agent_turn(self.current_agent_reply, interrupted=False)
        self.current_agent_reply = None
        self.state = State.LISTENING

    def on_interrupt(self) -> None:
        self.current_agent_reply = None
        self.state = State.LISTENING
```

- [ ] **Step 4: Run tests and add one regression assertion**

Run: `pytest tests/test_state_machine.py -v`  
Expected: PASS.

Then append and run:

```python
def test_playback_finished_persists_agent_turn():
    memory = SessionStore()
    machine = ConversationStateMachine(memory=memory)
    machine.on_agent_reply_ready("追问：你最难忘的一次采访是什么？")
    machine.on_playback_finished()
    assert memory.snapshot()[-1]["role"] == "assistant"
```

Run: `pytest tests/test_state_machine.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/state_machine.py tests/test_state_machine.py app/memory/session_store.py app/bus.py
git commit -m "feat: add conversation state machine with interruption transition"
```

### Task 5: Wire CLI runtime (microphone/listen, think, speak, interrupt)

**Files:**
- Create: `app/audio/in_stream.py`
- Create: `app/audio/out_stream.py`
- Create: `app/observability/logger.py`
- Create: `app/main.py`
- Modify: `requirements.txt`
- Modify: `README.md`

- [ ] **Step 1: Write failing smoke test for main loop bootstrap**

```python
# tests/test_main_smoke.py
from app.main import build_app


def test_build_app_constructs_components():
    app = build_app()
    assert "state_machine" in app
    assert "bus" in app
```

- [ ] **Step 2: Run smoke test to verify failure**

Run: `pytest tests/test_main_smoke.py -v`  
Expected: FAIL with missing `app.main`.

- [ ] **Step 3: Implement minimal runtime orchestration**

```python
# app/main.py
import asyncio
from app.config import load_config
from app.bus import EventBus
from app.memory.session_store import SessionStore
from app.state_machine import ConversationStateMachine
from app.asr.qwen_adapter import QwenASRAdapter
from app.agent.gemini_adapter import GeminiAdapter
from app.tts.fish_adapter import FishTTSAdapter


def build_app() -> dict:
    cfg = load_config()
    bus = EventBus()
    memory = SessionStore()
    machine = ConversationStateMachine(memory=memory)
    return {
        "config": cfg,
        "bus": bus,
        "state_machine": machine,
        "asr": QwenASRAdapter(cfg.qwen_asr_base_url),
        "agent": GeminiAdapter(cfg.gemini_api_key),
        "tts": FishTTSAdapter(cfg.fish_tts_base_url),
    }


async def run() -> None:
    app = build_app()
    print("DeepTalk Agent CLI started. Press Ctrl+C to exit.")
    while True:
        await asyncio.sleep(1)
        _ = app["state_machine"].state


if __name__ == "__main__":
    asyncio.run(run())
```

- [ ] **Step 4: Add audio and docs, then run targeted tests**

Run:
- `pytest tests/test_main_smoke.py tests/test_state_machine.py tests/test_config.py -v`

Expected: PASS.

Update `README.md` with:
- environment setup,
- dependency install command,
- `.env` setup,
- run command `python -m app.main`,
- known limits (half-duplex interrupt only).

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/audio/in_stream.py app/audio/out_stream.py app/observability/logger.py tests/test_main_smoke.py README.md requirements.txt
git commit -m "feat: wire runnable CLI loop and usage docs"
```

### Task 6: End-to-end dry-run and release-ready checks

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-03-28-podcast-interview-cli-design.md`

- [ ] **Step 1: Run full local test suite**

Run: `pytest -v`  
Expected: PASS across all tests.

- [ ] **Step 2: Run CLI startup sanity check**

Run: `python -m app.main`  
Expected: logs startup message and remains running without crash for 10+ seconds.

- [ ] **Step 3: Run manual chain verification checklist**

Use this exact checklist:
- Start app and speak one Chinese sentence into microphone.
- Observe ASR final text log line.
- Confirm one interviewer-style agent response text appears.
- Confirm TTS playback starts.
- During playback, speak again for >200ms.
- Confirm playback stops immediately and state returns to `LISTENING`.

- [ ] **Step 4: Document observed latencies and known issues**

Add section to `README.md`:
- measured `ASR final`, `LLM`, `TTS first-frame` timings,
- any timeout/retry events,
- next tuning priorities.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/superpowers/specs/2026-03-28-podcast-interview-cli-design.md
git commit -m "docs: add MVP verification results and tuning notes"
```

## Definition of Done

- CLI process starts successfully from `python -m app.main`.
- Core state machine transitions are covered by tests.
- Adapter contracts are test-covered with HTTP mocks.
- User can interrupt TTS playback by speaking (half-duplex behavior).
- README documents setup, run flow, and current limitations.
