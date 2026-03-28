from __future__ import annotations

from collections.abc import AsyncIterator


class MicrophoneInput:
    """Placeholder microphone stream for the MVP bootstrap stage."""

    async def frames(self) -> AsyncIterator[bytes]:
        if False:  # pragma: no cover
            yield b""
