from __future__ import annotations

import asyncio
import io
import logging
import wave

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
        model: str = "modelscope/VibeVoice-Realtime-0.5B-4bit",
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

    def _generate_results(self, text: str):
        # 根据模型类型调整参数
        is_kokoro = "kokoro" in self.model.lower()
        is_vibevoice = "vibevoice" in self.model.lower()
        
        LOGGER.info("TTS 生成参数：model=%s, lang=%s, voice=%s", 
                   self.model.split('/')[-1], self.lang_code, self.voice)
        
        kwargs = {
            "text": text,
            "verbose": False,
        }
        
        if is_kokoro:
            # Kokoro 特定参数
            kwargs.update({
                "lang": self.lang_code,  # Kokoro 使用 lang 而不是 lang_code
                "speed": self.speed,
            })
            LOGGER.debug("使用 Kokoro 模式")
        elif is_vibevoice:
            # VibeVoice 特定参数
            kwargs.update({
                "lang_code": self.lang_code,
                "speed": self.speed,
            })
            if self.voice:
                kwargs["voice"] = self.voice
            LOGGER.debug("使用 VibeVoice 模式")
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
