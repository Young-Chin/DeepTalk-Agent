from __future__ import annotations

from collections.abc import AsyncIterator
import asyncio
from typing import Iterable


class MicrophoneInput:
    """Queue-backed microphone abstraction for orchestration and tests."""

    def __init__(self, frames: Iterable[bytes] | None = None) -> None:
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()
        for frame in frames or []:
            self.push_frame(frame)

    def push_frame(self, frame: bytes) -> None:
        self._queue.put_nowait(frame)

    async def read_frame(self) -> bytes:
        return await self._queue.get()

    async def frames(self) -> AsyncIterator[bytes]:
        while True:
            yield await self.read_frame()
