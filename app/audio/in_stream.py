from __future__ import annotations

from collections.abc import AsyncIterator
import asyncio
import importlib
from typing import Iterable


class MicrophoneInput:
    """Queue-backed microphone abstraction for orchestration and tests."""

    def __init__(
        self,
        frames: Iterable[bytes] | None = None,
        *,
        sample_rate: int = 16000,
        channels: int = 1,
        dtype: str = "int16",
        sounddevice_module=None,
    ) -> None:
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self._sounddevice = sounddevice_module
        self._stream = None
        for frame in frames or []:
            self.push_frame(frame)

    def push_frame(self, frame: bytes) -> None:
        self._queue.put_nowait(frame)

    def has_pending_frame(self) -> bool:
        return not self._queue.empty()

    def _resolve_sounddevice(self):
        if self._sounddevice is not None:
            return self._sounddevice
        try:
            self._sounddevice = importlib.import_module("sounddevice")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "sounddevice is required for real microphone capture"
            ) from exc
        return self._sounddevice

    def start_device_capture(self) -> None:
        sounddevice = self._resolve_sounddevice()

        def _callback(indata, frames, time_info, status) -> None:
            del frames, time_info, status
            self.push_frame(bytes(indata))

        self._stream = sounddevice.RawInputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            callback=_callback,
        )
        self._stream.start()

    def stop_device_capture(self) -> None:
        if self._stream is None:
            return
        self._stream.stop()
        self._stream.close()
        self._stream = None

    async def read_frame(self) -> bytes:
        return await self._queue.get()

    async def frames(self) -> AsyncIterator[bytes]:
        while True:
            yield await self.read_frame()
