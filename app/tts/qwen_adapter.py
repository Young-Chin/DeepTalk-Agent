from __future__ import annotations

import asyncio
import io
import logging
import wave
from typing import AsyncGenerator

import numpy as np

LOGGER = logging.getLogger("podcast.tts.mlx")


class _MLXQwenTTSModel:
    def __init__(self, model: str) -> None:
        self.model = model
        self._loaded_model = None

    def _model_instance(self):
        if self._loaded_model is None:
            try:
                from mlx_audio.tts.utils import load_model
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "mlx-audio is required for TTS_BACKEND=mlx_qwen3. Install it with: python3 -m pip install mlx-audio"
                ) from exc
            LOGGER.info("Loading TTS model: %s", self.model)
            self._loaded_model = load_model(self.model)
            LOGGER.info("TTS model loaded successfully")
        return self._loaded_model

    def generate(self, **kwargs):
        model = self._model_instance()
        return model.generate(**kwargs)

    @property
    def sample_rate(self) -> int:
        model = self._model_instance()
        return int(getattr(model, "sample_rate", 24000))


class MLXQwenTTSAdapter:
    def __init__(
        self,
        model: str = "mlx-community/Kokoro-82M-bf16",
        *,
        lang_code: str = "zh",
        voice: str | None = None,
        speed: float = 1.0,
        loaded_model=None,
    ) -> None:
        self.model = model
        self.lang_code = lang_code
        self.voice = voice
        self.speed = speed
        self._model = loaded_model or _MLXQwenTTSModel(model)

    async def synthesize(self, text: str) -> bytes:
        LOGGER.info("="*60)
        LOGGER.info("开始 TTS 合成")
        LOGGER.info("  文本长度：%d 字符", len(text))
        LOGGER.info("  模型：%s", self.model.split('/')[-1])
        LOGGER.info("  语言：%s", self.lang_code)
        LOGGER.info("  语速：%f", self.speed)

        try:
            results = await asyncio.to_thread(
                self._generate_results,
                text,
            )
            audio_bytes = self._encode_wav(results)
            LOGGER.info("TTS 合成完成")
            LOGGER.info("  音频大小：%.1f KB", len(audio_bytes) / 1024)
            LOGGER.info("="*60)
            return audio_bytes
        except Exception as e:
            LOGGER.error("TTS 合成失败：%s", str(e))
            LOGGER.error("  错误类型：%s", type(e).__name__)
            LOGGER.debug("堆栈跟踪:", exc_info=True)
            raise

    async def synthesize_stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """流式合成音频，边生成边返回音频块。

        对于 Kokoro：按标点符号分割成句子，逐句合成
        对于 Qwen3-TTS：使用 stream=True 模式

        Yields:
            bytes: WAV 格式的音频块（包含完整的 WAV header）
        """
        LOGGER.info("="*60)
        LOGGER.info("开始流式 TTS 合成")
        LOGGER.info("  文本长度：%d 字符", len(text))
        LOGGER.info("  模型：%s", self.model.split('/')[-1])

        is_kokoro = "kokoro" in self.model.lower()

        try:
            # 使用线程执行同步生成，但通过队列实现流式返回
            queue: asyncio.Queue = asyncio.Queue()
            exception_holder = {"error": None}

            def _generate_and_queue():
                try:
                    if is_kokoro:
                        # Kokoro: 使用 split_pattern 按标点分割
                        kwargs = {
                            "text": text,
                            "lang_code": "z" if self.lang_code == "zh" else "a",
                            "speed": self.speed,
                            "split_pattern": r'[。，！？；：\n]+',  # 按中文标点分割
                            "verbose": False,
                        }
                        if self.voice:
                            kwargs["voice"] = self.voice
                    else:
                        # Qwen3-TTS: 使用 stream=True
                        kwargs = {
                            "text": text,
                            "lang_code": self.lang_code,
                            "voice": self.voice,
                            "speed": self.speed,
                            "stream": True,
                            "streaming_interval": 2.0,  # 每 2 秒输出一个 chunk
                            "verbose": False,
                        }

                    generator = self._model.generate(**kwargs)
                    chunk_idx = 0

                    for result in generator:
                        audio = getattr(result, "audio", None)
                        if audio is not None:
                            chunk_idx += 1
                            # 将音频块编码为 WAV 格式
                            chunk_bytes = self._encode_audio_chunk(audio)
                            # 通过队列发送到异步生成器
                            loop.call_soon_threadsafe(queue.put_nowait, (chunk_idx, chunk_bytes))
                            LOGGER.debug("流式 TTS chunk %d: %.2fs 音频", chunk_idx, len(audio) / self._model.sample_rate)

                    # 发送结束信号
                    loop.call_soon_threadsafe(queue.put_nowait, (None, None))

                except Exception as e:
                    exception_holder["error"] = e
                    loop.call_soon_threadsafe(queue.put_nowait, (None, None))

            loop = asyncio.get_running_loop()
            # 在线程池中执行生成
            thread = asyncio.to_thread(_generate_and_queue)
            task = asyncio.create_task(thread)

            # 从队列中读取并 yield
            while True:
                chunk_idx, chunk_bytes = await queue.get()
                if chunk_idx is None:
                    break
                yield chunk_bytes

            # 检查是否有异常
            if exception_holder["error"]:
                raise exception_holder["error"]

            LOGGER.info("流式 TTS 合成完成")
            LOGGER.info("="*60)

        except Exception as e:
            LOGGER.error("流式 TTS 合成失败：%s", str(e))
            LOGGER.error("  错误类型：%s", type(e).__name__)
            raise

    def _encode_audio_chunk(self, audio: np.ndarray) -> bytes:
        """将单个音频块编码为 WAV 格式。"""
        waveform = np.asarray(audio, dtype=np.float32)
        clipped = np.clip(waveform, -1.0, 1.0)
        pcm = (clipped * 32767.0).astype(np.int16).tobytes()

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self._model.sample_rate)
            wav_file.writeframes(pcm)
        return buffer.getvalue()

    def _generate_results(self, text: str):
        # 根据模型类型调整参数
        is_kokoro = "kokoro" in self.model.lower()

        LOGGER.info("TTS 生成参数：model=%s, lang=%s, voice=%s",
                   self.model.split('/')[-1], self.lang_code, self.voice)

        kwargs = {
            "text": text,
            "verbose": False,
        }

        if is_kokoro:
            # Kokoro 特定参数
            # 语言代码映射: zh -> z (中文), en -> a (英文)
            lang_code = "z" if self.lang_code == "zh" else "a"
            kwargs.update({
                "lang_code": lang_code,
                "speed": self.speed,
            })
            if self.voice:
                kwargs["voice"] = self.voice
            LOGGER.debug("使用 Kokoro 模式，语言代码=%s", lang_code)
        else:
            # Qwen3 TTS 默认参数
            kwargs.update({
                "lang_code": self.lang_code,
                "voice": self.voice,
                "speed": self.speed,
            })
            LOGGER.debug("使用 Qwen3 TTS 模式")

        generator = self._model.generate(**kwargs)
        return list(generator)

    def _encode_wav(self, results: list[object]) -> bytes:
        if not results:
            raise ValueError("TTS did not return audio")

        chunks: list[np.ndarray] = []
        for result in results:
            audio = getattr(result, "audio", None)
            if audio is None:
                raise ValueError("TTS did not return audio")
            chunks.append(np.asarray(audio, dtype=np.float32))

        waveform = np.concatenate(chunks, axis=0)
        clipped = np.clip(waveform, -1.0, 1.0)
        pcm = (clipped * 32767.0).astype(np.int16).tobytes()

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self._model.sample_rate)
            wav_file.writeframes(pcm)
        return buffer.getvalue()
