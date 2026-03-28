import pytest

from app.audio.in_stream import MicrophoneInput
from app.audio.out_stream import AudioOutput


@pytest.mark.asyncio
async def test_microphone_input_returns_injected_frames_in_order():
    microphone = MicrophoneInput(frames=[b"a", b"b"])

    assert await microphone.read_frame() == b"a"
    assert await microphone.read_frame() == b"b"


@pytest.mark.asyncio
async def test_microphone_input_collects_utterance_until_silence_timeout():
    microphone = MicrophoneInput(frames=[b"a", b"b", b"c"])

    chunk = await microphone.collect_utterance(silence_timeout_ms=1)

    assert chunk == b"abc"


@pytest.mark.asyncio
async def test_audio_output_tracks_playback_and_last_payload():
    output = AudioOutput()

    await output.play(b"voice")

    assert output.is_playing is True
    assert output.last_played == b"voice"


def test_audio_output_stop_resets_playback_state():
    output = AudioOutput()
    output.is_playing = True
    output.last_played = b"voice"

    output.stop()

    assert output.is_playing is False
    assert output.last_played == b"voice"
