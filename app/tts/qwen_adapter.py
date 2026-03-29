from __future__ import annotations

import asyncio
import io
import wave

import numpy as np


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
            self._loaded_model = load_model(self.model)
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
        model: str = "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit",
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
        results = await asyncio.to_thread(
            self._generate_results,
            text,
        )
        return self._encode_wav(results)

    def _generate_results(self, text: str):
        return list(
            self._model.generate(
                text=text,
                voice=self.voice,
                speed=self.speed,
                lang_code=self.lang_code,
                verbose=False,
                stream=False,
            )
        )

    def _encode_wav(self, results: list[object]) -> bytes:
        if not results:
            raise ValueError("Qwen3 TTS did not return audio")

        chunks: list[np.ndarray] = []
        for result in results:
            audio = getattr(result, "audio", None)
            if audio is None:
                raise ValueError("Qwen3 TTS did not return audio")
            chunks.append(np.asarray(audio, dtype=np.float32))

        waveform = np.concatenate(chunks, axis=0)
        clipped = np.clip(waveform, -1.0, 1.0)
        pcm = (clipped * 32767.0).astype(np.int16).tobytes()

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(int(getattr(self._model, "sample_rate", 24000)))
            wav_file.writeframes(pcm)
        return buffer.getvalue()
