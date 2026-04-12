from __future__ import annotations

import asyncio
import io
import importlib
import logging
import queue
import threading
import wave
from typing import AsyncGenerator

_AUTO = object()
LOGGER = logging.getLogger("podcast.audio.output")


def _get_logger():
    return LOGGER


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
        self.playback_invoked = False

    def _resolve_sounddevice(self):
        if self._sounddevice is _AUTO:
            try:
                self._sounddevice = importlib.import_module("sounddevice")
            except (ModuleNotFoundError, OSError):
                self._sounddevice = None
        return self._sounddevice

    def _resolve_numpy(self):
        if self._numpy is _AUTO:
            try:
                self._numpy = importlib.import_module("numpy")
            except ModuleNotFoundError:
                self._numpy = None
        return self._numpy

    @property
    def playback_mode(self) -> str:
        if self._resolve_sounddevice() is not None and self._resolve_numpy() is not None:
            return "real"
        return "memory"

    def describe_output_target(self) -> str:
        sounddevice = self._resolve_sounddevice()
        if sounddevice is None:
            return "memory-fallback (sounddevice unavailable)"
        try:
            default_device = getattr(sounddevice, "default").device
            output_index = default_device[1] if isinstance(default_device, (list, tuple)) else default_device
            device = sounddevice.query_devices(output_index, "output")
        except Exception:
            return "default output unavailable"
        if isinstance(device, dict):
            return str(device.get("name", "default output"))
        return str(getattr(device, "name", "default output"))

    def _decode_audio_bytes(self, audio_bytes: bytes) -> tuple[bytes, int]:
        if audio_bytes.startswith(b"RIFF") and b"WAVE" in audio_bytes[:16]:
            with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
                return wav_file.readframes(wav_file.getnframes()), wav_file.getframerate()
        return audio_bytes, self.sample_rate

    async def play(self, audio_bytes: bytes) -> None:
        self.last_played = audio_bytes
        self.playback_invoked = False
        sounddevice = self._resolve_sounddevice()
        numpy_module = self._resolve_numpy()
        if sounddevice is None or numpy_module is None:
            self.is_playing = False
            return
        decoded_bytes, sample_rate = self._decode_audio_bytes(audio_bytes)
        samples = numpy_module.frombuffer(decoded_bytes, dtype=numpy_module.int16)
        # 确保采样率正确，使用音频数据自身的采样率
        sounddevice.play(samples, sample_rate)
        LOGGER.debug(f"Playing audio: {len(samples)} samples @ {sample_rate}Hz")
        self.playback_invoked = bool(audio_bytes)
        self.is_playing = bool(audio_bytes)

    async def wait(self) -> None:
        """Wait for playback to complete (blocking)."""
        sounddevice = self._resolve_sounddevice()
        # sounddevice.wait() is a blocking call; run it in executor
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, sounddevice.wait)
        self.is_playing = False

    def stop(self) -> None:
        sounddevice = self._resolve_sounddevice()
        if sounddevice is not None:
            sounddevice.stop()
        self.is_playing = False
        # Signal streaming to stop
        if hasattr(self, '_stream_stop_event'):
            self._stream_stop_event.set()

    async def play_stream(
        self,
        audio_generator: AsyncGenerator[bytes, None],
        sample_rate: int = 24000,
    ) -> None:
        """流式播放音频块。

        接收一个异步音频块生成器，边接收边播放。
        支持中途打断（通过 stop() 方法）。

        Args:
            audio_generator: 异步生成器，yield WAV 格式的音频块
            sample_rate: 音频采样率（默认 24000，TTS 模型的输出采样率）
        """
        sounddevice = self._resolve_sounddevice()
        numpy_module = self._resolve_numpy()

        if sounddevice is None or numpy_module is None:
            self.is_playing = False
            # 仍然消费生成器，但不播放
            async for _ in audio_generator:
                pass
            return

        self.is_playing = True
        self.playback_invoked = True
        self._stream_stop_event = threading.Event()

        # 使用线程安全队列传递音频数据
        audio_queue: queue.Queue = queue.Queue()
        # 使用特殊标记表示结束
        SENTINEL = object()

        # 当前播放位置和数据
        playback_state = {
            "buffer": numpy_module.zeros(0, dtype=numpy_module.int16),
            "position": 0,
            "done": False,
        }

        def audio_callback(outdata, frames, time_info, status):
            """sounddevice 回调函数，从队列中获取音频数据并播放。"""
            del time_info, status

            if self._stream_stop_event.is_set() or playback_state["done"]:
                outdata.fill(0)
                return

            # 尝试从队列获取新数据
            try:
                while len(playback_state["buffer"]) - playback_state["position"] < frames:
                    chunk = audio_queue.get_nowait()
                    if chunk is SENTINEL:
                        playback_state["done"] = True
                        break
                    playback_state["buffer"] = numpy_module.concatenate([
                        playback_state["buffer"][playback_state["position"]:],
                        chunk
                    ])
                    playback_state["position"] = 0
            except queue.Empty:
                pass

            # 填充输出缓冲区
            available = len(playback_state["buffer"]) - playback_state["position"]
            if available >= frames:
                outdata[:, 0] = playback_state["buffer"][playback_state["position"]:playback_state["position"] + frames]
                playback_state["position"] += frames
            elif available > 0:
                # 数据不足，填充剩余部分为零
                outdata[:available, 0] = playback_state["buffer"][playback_state["position"]:playback_state["position"] + available]
                outdata[available:, 0] = 0
                playback_state["position"] = len(playback_state["buffer"])
            else:
                outdata.fill(0)

        async def feed_audio():
            """从异步生成器读取音频并放入队列。"""
            try:
                async for chunk_bytes in audio_generator:
                    if self._stream_stop_event.is_set():
                        break
                    decoded_bytes, chunk_sr = self._decode_audio_bytes(chunk_bytes)
                    if chunk_sr != sample_rate:
                        # 采样率不匹配，跳过或重采样（简化处理：跳过）
                        LOGGER.warning("采样率不匹配: %d vs %d", chunk_sr, sample_rate)
                        continue
                    samples = numpy_module.frombuffer(decoded_bytes, dtype=numpy_module.int16)
                    audio_queue.put(samples)
            except Exception as e:
                LOGGER.error("音频流生成错误: %s", e)
            finally:
                audio_queue.put(SENTINEL)

        # 启动流式播放
        try:
            stream = sounddevice.OutputStream(
                samplerate=sample_rate,
                channels=1,
                dtype=numpy_module.int16,
                callback=audio_callback,
                blocksize=4096,  # 约 170ms @ 24kHz
            )
            stream.start()

            # 启动音频生产者任务
            feed_task = asyncio.create_task(feed_audio())

            # 等待播放完成或停止信号
            while not playback_state["done"] and not self._stream_stop_event.is_set():
                await asyncio.sleep(0.05)

            # 等待音频队列消费完成
            if not self._stream_stop_event.is_set():
                # 等待缓冲区播放完
                remaining = len(playback_state["buffer"]) - playback_state["position"]
                wait_time = remaining / sample_rate + 0.1
                await asyncio.sleep(wait_time)

            feed_task.cancel()
            try:
                await feed_task
            except asyncio.CancelledError:
                pass

        finally:
            if 'stream' in dir():
                stream.stop()
                stream.close()
            self.is_playing = False
