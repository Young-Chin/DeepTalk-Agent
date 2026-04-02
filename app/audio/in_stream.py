from __future__ import annotations

from collections.abc import AsyncIterator
import asyncio
import importlib
import struct
from typing import Iterable

_AUTO = object()


class MicrophoneInput:
    """Queue-backed microphone abstraction for orchestration and tests."""

    def __init__(
        self,
        frames: Iterable[bytes] | None = None,
        *,
        sample_rate: int = 16000,
        channels: int = 1,
        dtype: str = "int16",
        vad=_AUTO,
        energy_threshold: int = 500,
        sounddevice_module=_AUTO,
    ) -> None:
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.energy_threshold = energy_threshold
        self._sounddevice = sounddevice_module
        self._vad = vad
        self._stream = None
        for frame in frames or []:
            self.push_frame(frame)

    def push_frame(self, frame: bytes) -> None:
        self._queue.put_nowait(frame)

    def has_pending_frame(self) -> bool:
        return not self._queue.empty()

    def _resolve_sounddevice(self):
        if self._sounddevice is _AUTO:
            try:
                self._sounddevice = importlib.import_module("sounddevice")
            except (ModuleNotFoundError, OSError) as exc:
                raise RuntimeError(
                    "sounddevice is required for real microphone capture"
                ) from exc
        if self._sounddevice is not None:
            return self._sounddevice
        raise RuntimeError("sounddevice is required for real microphone capture")

    def _resolve_vad(self):
        if self._vad is _AUTO:
            try:
                webrtcvad = importlib.import_module("webrtcvad")
            except ModuleNotFoundError:
                self._vad = None
                return None
            self._vad = webrtcvad.Vad(0)
        if self._vad is not None:
            return self._vad
        return None

    def _frame_energy(self, frame: bytes) -> float:
        if not frame:
            return 0.0
        sample_width = 2
        sample_count = len(frame) // sample_width
        if sample_count == 0:
            return 0.0
        samples = struct.unpack("<" + "h" * sample_count, frame[: sample_count * 2])
        return sum(abs(sample) for sample in samples) / sample_count

    def is_speech_frame(self, frame: bytes) -> bool:
        if not frame:
            return False
        vad = self._resolve_vad()
        if vad is not None:
            try:
                return bool(vad.is_speech(frame, self.sample_rate))
            except Exception:
                return self._frame_energy(frame) >= self.energy_threshold
        return self._frame_energy(frame) >= self.energy_threshold

    def start_device_capture(self) -> None:
        sounddevice = self._resolve_sounddevice()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        put_frame = self._queue.put_nowait

        def _callback(indata, frames, time_info, status) -> None:
            del frames, time_info, status
            frame = bytes(indata)
            if self.is_speech_frame(frame):
                if loop is not None:
                    loop.call_soon_threadsafe(put_frame, frame)
                else:
                    put_frame(frame)

        self._stream = sounddevice.RawInputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            callback=_callback,
        )
        self._stream.start()

    def describe_input_target(self) -> str:
        try:
            sounddevice = self._resolve_sounddevice()
        except RuntimeError:
            return "unavailable (sounddevice unavailable)"
        try:
            default_device = getattr(sounddevice, "default").device
            input_index = default_device[0] if isinstance(default_device, (list, tuple)) else default_device
            device = sounddevice.query_devices(input_index, "input")
        except Exception:
            return "default input unavailable"
        if isinstance(device, dict):
            return str(device.get("name", "default input"))
        return str(getattr(device, "name", "default input"))

    def stop_device_capture(self) -> None:
        if self._stream is None:
            return
        self._stream.stop()
        self._stream.close()
        self._stream = None

    async def read_frame(self) -> bytes:
        return await self._queue.get()

    def drain_pending_frames(self) -> list[bytes]:
        frames: list[bytes] = []
        while not self._queue.empty():
            frames.append(self._queue.get_nowait())
        return frames

    async def collect_utterance(
        self,
        silence_timeout_ms: int,
        *,
        initial_frame: bytes | None = None,
    ) -> bytes:
        frames = [initial_frame] if initial_frame is not None else [await self.read_frame()]
        timeout_s = silence_timeout_ms / 1000

        while True:
            pending = self.drain_pending_frames()
            if pending:
                frames.extend(pending)
                continue
            try:
                frame = await asyncio.wait_for(self.read_frame(), timeout=timeout_s)
            except asyncio.TimeoutError:
                break
            frames.append(frame)

        return b"".join(frames)

    async def frames(self) -> AsyncIterator[bytes]:
        while True:
            yield await self.read_frame()
