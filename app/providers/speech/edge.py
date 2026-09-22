"""Edge-TTS speech synthesis provider with transient retry and atomic file write."""

import asyncio
import logging
import os
from pathlib import Path
import edge_tts

from app.domain.timeline import SubtitleCue
from app.providers.speech.base import (
    SpeechProvider,
    SpeechProviderError,
    SpeechResult,
)

logger = logging.getLogger(__name__)


class EdgeSpeechProvider(SpeechProvider):
    """Synthesizes scene narration using Microsoft Edge TTS (remote service)."""

    def __init__(
        self,
        voice_vi: str = "vi-VN-NamMinhNeural",
        voice_en: str = "en-US-GuyNeural",
        timeout: float = 30.0,
    ):
        self.voice_vi = voice_vi
        self.voice_en = voice_en
        self.timeout = timeout

    def _get_voice(self, language: str) -> str:
        lang = language.lower().strip()
        if lang == "vi":
            return self.voice_vi
        elif lang == "en":
            return self.voice_en
        else:
            raise SpeechProviderError(
                code="speech_provider_error",
                message=f"Unsupported speech language: {language}",
                retryable=False,
            )

    async def synthesize(
        self,
        text: str,
        output_path: Path,
        language: str,
    ) -> SpeechResult:
        """Synthesize scene narration into an MP3 file with optional timing metadata."""
        clean_text = text.strip()
        if not clean_text:
            raise SpeechProviderError(
                code="speech_invalid_audio",
                message="Cannot synthesize empty narration text.",
                retryable=False,
            )

        voice = self._get_voice(language)
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = output_path.with_name(f"{output_path.stem}.tmp_{os.getpid()}_{id(text)}.mp3")

        max_attempts = 2

        for attempt in range(1, max_attempts + 1):
            raw_cues: list[SubtitleCue] = []
            audio_bytes_written = 0

            try:
                # Clean up any leftover tmp file
                if tmp_path.exists():
                    tmp_path.unlink()

                communicate = edge_tts.Communicate(text=clean_text, voice=voice)

                async with asyncio.timeout(self.timeout):
                    with open(tmp_path, "wb") as f:
                        async for chunk in communicate.stream():
                            chunk_type = chunk.get("type")
                            if chunk_type == "audio":
                                data = chunk.get("data", b"")
                                if data:
                                    f.write(data)
                                    audio_bytes_written += len(data)
                            elif chunk_type == "SentenceBoundary":
                                offset_ticks = chunk.get("offset", 0)
                                duration_ticks = chunk.get("duration", 0)
                                sub_text = chunk.get("text", "").strip()
                                if sub_text and duration_ticks > 0:
                                    start_s = offset_ticks / 10_000_000.0
                                    end_s = start_s + (duration_ticks / 10_000_000.0)
                                    if end_s > start_s:
                                        try:
                                            cue = SubtitleCue(
                                                start_seconds=start_s,
                                                end_seconds=end_s,
                                                text=sub_text,
                                            )
                                            raw_cues.append(cue)
                                        except Exception:
                                            pass

                if audio_bytes_written == 0 or not tmp_path.exists() or tmp_path.stat().st_size == 0:
                    raise SpeechProviderError(
                        code="speech_empty_audio",
                        message="Speech synthesis yielded zero audio bytes.",
                        retryable=False,
                    )

                # Atomically replace to final destination
                os.replace(tmp_path, output_path)

                return SpeechResult(
                    path=str(output_path),
                    provider="edge",
                    subtitle_cues=raw_cues,
                )

            except Exception as exc:
                if tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except Exception:
                        pass

                if isinstance(exc, SpeechProviderError):
                    mapped = exc
                else:
                    err_str = str(exc).lower()
                    transient_types = (
                        TimeoutError,
                        asyncio.TimeoutError,
                        ConnectionError,
                        OSError,
                        edge_tts.exceptions.EdgeTTSException,
                    )
                    try:
                        import aiohttp
                        transient_types += (aiohttp.ClientError,)
                    except ImportError:
                        pass

                    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)) or "timeout" in err_str:
                        mapped = SpeechProviderError(
                            code="speech_timeout",
                            message="Edge TTS service request timed out.",
                            retryable=True,
                        )
                    elif isinstance(exc, transient_types) or "connection" in err_str or "reset" in err_str:
                        mapped = SpeechProviderError(
                            code="speech_provider_error",
                            message=f"Edge TTS service network glitch ({type(exc).__name__}).",
                            retryable=True,
                        )
                    else:
                        mapped = SpeechProviderError(
                            code="speech_provider_error",
                            message=f"Edge TTS service failed ({type(exc).__name__}).",
                            retryable=False,
                        )

                logger.error(
                    "Edge TTS error voice=%s language=%s exception_type=%s error_code=%s attempt=%d",
                    voice,
                    language,
                    type(exc).__name__,
                    mapped.code,
                    attempt,
                )

                if mapped.retryable and attempt < max_attempts:
                    await asyncio.sleep(0.5)
                    continue

                raise mapped from None

        raise SpeechProviderError(
            code="speech_provider_error",
            message="Edge TTS failed after retries.",
            retryable=False,
        )
