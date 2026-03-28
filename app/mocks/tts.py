from __future__ import annotations

import io
import wave


class MockTTSAdapter:
    def __init__(self, sample_rate: int = 16000, frame_count: int = 2) -> None:
        self.sample_rate = sample_rate
        self.frame_count = frame_count

    async def synthesize(self, text: str) -> bytes:
        del text
        frames = b"\x00\x00" * self.frame_count
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(frames)
        return buffer.getvalue()
