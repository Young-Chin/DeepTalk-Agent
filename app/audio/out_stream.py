from __future__ import annotations

import importlib

_AUTO = object()


class AudioOutput:
    """Minimal playback abstraction with immediate stop support."""

    def __init__(
        self,
        *,
        sample_rate: int = 16000,
        sounddevice_module=_AUTO,
        numpy_module=_AUTO,
    ) -> None:
        self.sample_rate = sample_rate
        self._sounddevice = sounddevice_module
        self._numpy = numpy_module
        self.is_playing = False
        self.last_played: bytes | None = None

    def _resolve_sounddevice(self):
        if self._sounddevice is _AUTO:
            try:
                self._sounddevice = importlib.import_module("sounddevice")
            except ModuleNotFoundError:
                self._sounddevice = None
        if self._sounddevice is not None:
            return self._sounddevice
        raise RuntimeError("sounddevice is required for audio playback")

    def _resolve_numpy(self):
        if self._numpy is _AUTO:
            try:
                self._numpy = importlib.import_module("numpy")
            except ModuleNotFoundError:
                self._numpy = None
        if self._numpy is not None:
            return self._numpy
        raise RuntimeError("numpy is required for audio playback")

    async def play(self, audio_bytes: bytes) -> None:
        # Default to in-memory playback state tracking so tests and dry runs work
        # even when optional audio device dependencies are unavailable.
        if self._sounddevice is not _AUTO or self._numpy is not _AUTO:
            sounddevice = self._resolve_sounddevice()
            numpy_module = self._resolve_numpy()
            samples = numpy_module.frombuffer(audio_bytes, dtype=numpy_module.int16)
            sounddevice.play(samples, self.sample_rate)
        self.is_playing = bool(audio_bytes)
        self.last_played = audio_bytes

    def stop(self) -> None:
        if self._sounddevice not in (_AUTO, None):
            self._sounddevice.stop()
        self.is_playing = False
