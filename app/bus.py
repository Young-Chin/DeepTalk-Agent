from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any


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
