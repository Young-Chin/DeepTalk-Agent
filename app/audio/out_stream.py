from __future__ import annotations


class AudioOutput:
    """Minimal playback abstraction with immediate stop support."""

    def __init__(self) -> None:
        self.is_playing = False
        self.last_played: bytes | None = None

    async def play(self, audio_bytes: bytes) -> None:
        self.is_playing = bool(audio_bytes)
        self.last_played = audio_bytes

    def stop(self) -> None:
        self.is_playing = False
