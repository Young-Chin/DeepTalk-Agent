from __future__ import annotations


class AudioOutput:
    """Minimal playback abstraction with immediate stop support."""

    def __init__(self) -> None:
        self.is_playing = False

    async def play(self, audio_bytes: bytes) -> None:
        self.is_playing = bool(audio_bytes)

    def stop(self) -> None:
        self.is_playing = False
