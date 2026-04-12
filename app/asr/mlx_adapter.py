from __future__ import annotations

import asyncio
import tempfile
import wave
from pathlib import Path
import numpy as np


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
        """非流式识别：完整音频一次性识别。"""
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

    def _transcribe_stream_sync(self, audio_bytes: bytes, language: str | None = None):
        """同步流式识别内部方法，返回列表便于线程传递。"""
        model = self._model_instance()

        # 转换为 numpy array（Qwen3-ASR streaming 需要）
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        # 检查模型是否支持 stream 参数
        import inspect
        sig = inspect.signature(model.generate)
        supports_stream = "stream" in sig.parameters

        results = []
        if supports_stream:
            # 使用原生 streaming 模式
            for chunk in model.generate(audio_np, language=language, stream=True, verbose=False):
                # chunk 是 StreamingResult 对象
                if hasattr(chunk, "text"):
                    results.append((chunk.text, getattr(chunk, "is_final", False)))
                else:
                    results.append((str(chunk), False))
        else:
            # 不支持 streaming，退化为一次性输出
            result = model.generate(audio_np, language=language, verbose=False)
            text = self._extract_text(result)
            if text:
                results.append((text, True))

        return results

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


class MLXASRAdapter:
    def __init__(
        self,
        model: str = "mlx-community/Qwen3-ASR-0.6B-4bit",
        *,
        language: str | None = "zh",
        transcriber=None,
    ) -> None:
        self.model = model
        self.language = language
        self._transcriber = transcriber or _MLXTranscriber(model)

    async def transcribe_chunk(self, pcm_bytes: bytes) -> str:
        """非流式识别：返回完整识别文本。"""
        full_text = []
        async for chunk_text, _ in self.transcribe_stream(pcm_bytes):
            if chunk_text:  # 跳过空字符串
                full_text.append(chunk_text)
        return "".join(full_text)

    async def transcribe_stream(self, pcm_bytes: bytes):
        """流式 ASR：逐步返回识别文本。

        适用于边录音边识别的场景，可以减少首字延迟。

        Yields:
            tuple[str, bool]: (文本片段, 是否为最终结果)
        """
        # 检查是否是 mock transcriber（有 transcribe_stream 方法）
        if hasattr(self._transcriber, 'transcribe_stream'):
            # 直接调用 mock 的同步生成器
            for chunk, is_final in self._transcriber.transcribe_stream(pcm_bytes, self.language):
                yield chunk, is_final
        else:
            # 真实模型：在线程中执行整个流式识别
            results = await asyncio.to_thread(
                self._transcriber._transcribe_stream_sync,
                pcm_bytes,
                self.language,
            )
            for chunk, is_final in results:
                yield chunk, is_final
