from __future__ import annotations

import asyncio

from app.agent.gemini_adapter import GeminiAdapter
from app.asr.qwen_adapter import QwenASRAdapter
from app.audio.in_stream import MicrophoneInput
from app.audio.out_stream import AudioOutput
from app.bus import EventBus
from app.config import _load_dotenv, load_config
from app.memory.session_store import SessionStore
from app.observability.logger import configure_logging
from app.state_machine import ConversationStateMachine
from app.tts.fish_adapter import FishTTSAdapter


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


async def run() -> None:
    app = build_app()
    configure_logging(app["config"].log_level)
    print("DeepTalk Agent CLI started. Press Ctrl+C to exit.")

    while True:
        await asyncio.sleep(1)
        _ = app["state_machine"].state


if __name__ == "__main__":
    asyncio.run(run())
