from __future__ import annotations

import io
import math
import struct
import wave


class MockTTSAdapter:
    def __init__(
        self,
        sample_rate: int = 16000,
        frame_count: int = 1600,
        frequency_hz: int = 880,
    ) -> None:
        self.sample_rate = sample_rate
        self.frame_count = frame_count
        self.frequency_hz = frequency_hz

    async def synthesize(self, text: str) -> bytes:
        del text
        frames = b"".join(
            struct.pack(
                "<h",
                int(
                    12000
                    * math.sin(
                        2 * math.pi * self.frequency_hz * index / self.sample_rate
                    )
                ),
            )
            for index in range(self.frame_count)
        )
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(frames)
        return buffer.getvalue()
