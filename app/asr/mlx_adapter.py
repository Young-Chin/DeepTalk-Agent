from __future__ import annotations

import asyncio
import io
import tempfile
import wave
from pathlib import Path


class _MLXTranscriber:
    def __init__(self, model: str) -> None:
        self.model = model
        self._loaded_model = None

    def _model_instance(self):
        if self._loaded_model is None:
            try:
                from mlx_audio.stt.utils import load_model
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "mlx-audio is required for ASR_BACKEND=mlx. Install it with: python3 -m pip install mlx-audio"
                ) from exc
            self._loaded_model = load_model(self.model)
        return self._loaded_model

    def transcribe(self, audio_bytes: bytes, language: str | None = None):
        model = self._model_instance()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        try:
            with wave.open(str(temp_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(audio_bytes)
            return model.generate(str(temp_path), language=language, verbose=False)
        finally:
            temp_path.unlink(missing_ok=True)


class MLXASRAdapter:
    def __init__(
        self,
        model: str = "modelscope/Qwen3-ASR-0.6B-4bit",
        *,
        language: str | None = "zh",
        transcriber=None,
    ) -> None:
        self.model = model
        self.language = language
        self._transcriber = transcriber or _MLXTranscriber(model)

    async def transcribe_chunk(self, pcm_bytes: bytes) -> str:
        result = await asyncio.to_thread(
            self._transcriber.transcribe,
            pcm_bytes,
            self.language,
        )
        return self._extract_text(result)

    def _extract_text(self, payload: object) -> str:
        if isinstance(payload, str):
            return payload

        text = getattr(payload, "text", None)
        if isinstance(text, str):
            return text

        if isinstance(payload, list):
            segments: list[str] = []
            for item in payload:
                if not isinstance(item, dict):
                    raise ValueError("Unsupported MLX ASR response payload")
                segment_text = item.get("text")
                if not isinstance(segment_text, str):
                    raise ValueError("Unsupported MLX ASR response payload")
                segments.append(segment_text)
            return "".join(segments)

        raise ValueError("Unsupported MLX ASR response payload")
