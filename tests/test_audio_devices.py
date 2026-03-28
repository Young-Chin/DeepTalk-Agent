from __future__ import annotations

import asyncio
import io
import struct
import threading
import types
import wave

import pytest

from app.audio.in_stream import MicrophoneInput
from app.audio.out_stream import AudioOutput


class FakeRawInputStream:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.started = False
        self.stopped = False
        self.closed = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def close(self) -> None:
        self.closed = True


class FakeSoundDeviceInputModule:
    def __init__(self) -> None:
        self.streams: list[FakeRawInputStream] = []

    def RawInputStream(self, **kwargs):
        stream = FakeRawInputStream(**kwargs)
        self.streams.append(stream)
        return stream


class FakeSoundDeviceOutputModule:
    def __init__(self) -> None:
        self.play_calls: list[tuple[object, int]] = []
        self.stop_calls = 0

    def play(self, samples, samplerate: int) -> None:
        self.play_calls.append((samples, samplerate))

    def stop(self) -> None:
        self.stop_calls += 1


class FakeNumpyModule:
    int16 = "int16"

    @staticmethod
    def frombuffer(payload: bytes, dtype=None):
        assert dtype == "int16"
        return {"payload": payload, "dtype": dtype}


def _wav_bytes(sample_rate: int, frames: bytes) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(frames)
    return buffer.getvalue()


def test_microphone_input_start_device_capture_uses_sounddevice_callback():
    sounddevice = FakeSoundDeviceInputModule()
    microphone = MicrophoneInput(sounddevice_module=sounddevice)

    microphone.start_device_capture()

    stream = sounddevice.streams[0]
    assert stream.started is True
    stream.kwargs["callback"](b"pcm-frame", 1, None, None)
    assert microphone.has_pending_frame() is True


def test_microphone_input_stop_device_capture_stops_and_closes_stream():
    sounddevice = FakeSoundDeviceInputModule()
    microphone = MicrophoneInput(sounddevice_module=sounddevice)
    microphone.start_device_capture()

    microphone.stop_device_capture()

    stream = sounddevice.streams[0]
    assert stream.stopped is True
    assert stream.closed is True


def test_microphone_input_start_device_capture_requires_sounddevice():
    microphone = MicrophoneInput(sounddevice_module=None)

    with pytest.raises(RuntimeError, match="sounddevice"):
        microphone.start_device_capture()


@pytest.mark.asyncio
async def test_audio_output_play_uses_sounddevice_and_numpy():
    sounddevice = FakeSoundDeviceOutputModule()
    numpy_module = FakeNumpyModule()
    output = AudioOutput(
        sounddevice_module=sounddevice,
        numpy_module=numpy_module,
    )

    await output.play(b"\x01\x00\x02\x00")

    samples, samplerate = sounddevice.play_calls[0]
    assert samples == {"payload": b"\x01\x00\x02\x00", "dtype": "int16"}
    assert samplerate == 16000
    assert output.is_playing is True
    assert output.last_played == b"\x01\x00\x02\x00"


def test_audio_output_stop_calls_sounddevice_stop():
    sounddevice = FakeSoundDeviceOutputModule()
    output = AudioOutput(sounddevice_module=sounddevice, numpy_module=FakeNumpyModule())

    output.stop()

    assert sounddevice.stop_calls == 1
    assert output.is_playing is False


@pytest.mark.asyncio
async def test_audio_output_play_requires_optional_dependencies():
    output = AudioOutput(sounddevice_module=None, numpy_module=None)

    with pytest.raises(RuntimeError, match="sounddevice"):
        await output.play(b"audio")


@pytest.mark.asyncio
async def test_audio_output_play_decodes_wav_and_uses_embedded_sample_rate():
    sounddevice = FakeSoundDeviceOutputModule()
    numpy_module = FakeNumpyModule()
    output = AudioOutput(
        sample_rate=16000,
        sounddevice_module=sounddevice,
        numpy_module=numpy_module,
    )

    await output.play(_wav_bytes(22050, b"\x01\x00\x02\x00"))

    samples, samplerate = sounddevice.play_calls[0]
    assert samples == {"payload": b"\x01\x00\x02\x00", "dtype": "int16"}
    assert samplerate == 22050


class _ThreadedRawInputStream:
    """Fake RawInputStream that fires the callback from a background thread."""

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self._callback = kwargs.get("callback")
        self.started = False
        self.stopped = False
        self.closed = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self.started = True

        def _run() -> None:
            if self._callback is not None:
                self._callback(self.kwargs["_frame"], None, None, None)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.stopped = True

    def close(self) -> None:
        self.closed = True


class _ThreadedSoundDeviceModule:
    def __init__(self, frame: bytes) -> None:
        self._frame = frame
        self.streams: list[_ThreadedRawInputStream] = []

    def RawInputStream(self, **kwargs):
        kwargs["_frame"] = self._frame
        stream = _ThreadedRawInputStream(**kwargs)
        self.streams.append(stream)
        return stream


@pytest.mark.asyncio
async def test_device_capture_delivers_speech_frame_from_background_thread():
    """The sounddevice callback fires in an OS thread; frames must reach the
    asyncio queue via call_soon_threadsafe so that read_frame() wakes up."""
    speech_frame = struct.pack("<" + "h" * 480, *([500] * 480))
    sounddevice = _ThreadedSoundDeviceModule(speech_frame)
    microphone = MicrophoneInput(
        sounddevice_module=sounddevice,
        vad=None,
        energy_threshold=250,
    )

    microphone.start_device_capture()

    received = await asyncio.wait_for(microphone.read_frame(), timeout=1.0)
    assert received == speech_frame

