"""Provider-aware speech-to-text adapter.

The host environment does not ship an STT provider (no ``openai``/whisper, no
API key). Rather than fabricating transcripts, the transcriber reports its
capability honestly. Providers are probed at call time so adding one later is
a zero-code deploy:

- ``openai-whisper``: available when ``openai`` is importable and a key is set.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


class SpeechToTextError(RuntimeError):
    pass


class SpeechTranscriber:
    PROVIDERS = ("openai-whisper",)

    @classmethod
    def available_providers(cls) -> list[str]:
        providers: list[str] = []
        try:
            import openai  # noqa: F401

            if os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY"):
                providers.append("openai-whisper")
        except ImportError:
            pass
        return providers

    @classmethod
    def is_configured(cls) -> bool:
        return bool(cls.available_providers())

    @classmethod
    async def transcribe(cls, audio_path: str) -> str:
        """Transcribe an audio file to text.

        Raises ``SpeechToTextError`` when no provider is configured. The caller
        converts this into a graceful ``processing_status='failed'`` result
        rather than failing the whole request.
        """
        providers = cls.available_providers()
        for provider in providers:
            try:
                if provider == "openai-whisper":
                    return await cls._transcribe_openai(audio_path)
            except Exception as exc:  # pragma: no cover - provider-specific
                logger.warning("Speech transcription via %s failed: %s", provider, exc)
        raise SpeechToTextError(
            "Speech-to-text is not configured on this deployment. "
            "No provider is available (install ``openai`` + set OPENAI_API_KEY). "
            "The recording was preserved but not transcribed."
        )

    @staticmethod
    async def _transcribe_openai(audio_path: str) -> str:  # pragma: no cover
        import openai

        key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
        client = openai.AsyncOpenAI(api_key=key)
        with open(audio_path, "rb") as f:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
            )
        return transcript.text or ""