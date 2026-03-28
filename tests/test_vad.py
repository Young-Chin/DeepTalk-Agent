from __future__ import annotations

import struct

from app.audio.in_stream import MicrophoneInput


class FakeVAD:
    def __init__(self, result: bool) -> None:
        self.result = result
        self.calls: list[tuple[bytes, int]] = []

    def is_speech(self, frame: bytes, sample_rate: int) -> bool:
        self.calls.append((frame, sample_rate))
        return self.result


def _pcm16(samples: list[int]) -> bytes:
    return struct.pack("<" + "h" * len(samples), *samples)


def test_is_speech_frame_uses_webrtcvad_when_available():
    vad = FakeVAD(True)
    microphone = MicrophoneInput(sample_rate=16000, vad=vad)
    frame = _pcm16([500] * 480)

    assert microphone.is_speech_frame(frame) is True
    assert vad.calls == [(frame, 16000)]


def test_is_speech_frame_falls_back_to_energy_threshold_without_vad():
    microphone = MicrophoneInput(sample_rate=16000, vad=None, energy_threshold=200)
    speech_frame = _pcm16([500] * 480)
    silence_frame = _pcm16([0] * 480)

    assert microphone.is_speech_frame(speech_frame) is True
    assert microphone.is_speech_frame(silence_frame) is False


def test_is_speech_frame_rejects_empty_frames():
    microphone = MicrophoneInput(sample_rate=16000, vad=None)

    assert microphone.is_speech_frame(b"") is False
