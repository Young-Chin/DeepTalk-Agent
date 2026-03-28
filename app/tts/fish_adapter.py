from __future__ import annotations

import base64
import binascii

import httpx


class FishTTSAdapter:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def synthesize(self, text: str) -> bytes:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.base_url}/synthesize",
                json={"text": text},
            )
            response.raise_for_status()
            return self._extract_audio_bytes(response)

    def _extract_audio_bytes(self, response: httpx.Response) -> bytes:
        content_type = response.headers.get("Content-Type", "").lower()
        if "application/json" not in content_type:
            return response.content

        payload = response.json()
        audio_field = self._find_audio_field(payload)
        if audio_field is None:
            raise ValueError("Unsupported Fish TTS response payload")

        try:
            return base64.b64decode(audio_field, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Malformed Fish TTS audio payload") from exc

    def _find_audio_field(self, payload: object) -> str | None:
        if isinstance(payload, dict):
            audio = payload.get("audio")
            if isinstance(audio, str):
                return audio

            data = payload.get("data")
            if isinstance(data, dict):
                nested_audio = data.get("audio")
                if isinstance(nested_audio, str):
                    return nested_audio

        return None
