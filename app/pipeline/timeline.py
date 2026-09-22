"""Audio-first media timeline builder, duration probing, padding, and subtitle allocation."""

import asyncio
import json
import logging
import math
import os
import re
import subprocess
from pathlib import Path

from app.domain.enums import JobStage
from app.domain.errors import PipelineExecutionError
from app.domain.lesson import LessonPlan, ScenePlan
from app.domain.timeline import (
    ResolvedSceneTiming,
    ResolvedTimeline,
    SubtitleCue,
)
from app.providers.speech.base import (
    SpeechProvider,
    SpeechProviderError,
    SpeechResult,
)
from app.storage.base import ArtifactStore

logger = logging.getLogger(__name__)


async def probe_duration(path: Path | str) -> float:
    """Measure the exact duration in seconds of an audio or video file using ffprobe.

    Executes without shell interpolation and strictly validates finite positive duration.
    """
    p = Path(path).resolve()
    if not p.exists() or not p.is_file() or p.stat().st_size == 0:
        raise SpeechProviderError(
            code="speech_invalid_audio",
            message=f"Audio file is missing, empty, or unreadable: {p.name}",
            retryable=False,
        )

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(p),
    ]

    def _run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

    proc = await asyncio.to_thread(_run)
    if proc.returncode != 0:
        logger.error("ffprobe failed on %s returncode=%d", p.name, proc.returncode)
        raise SpeechProviderError(
            code="speech_invalid_audio",
            message=f"Failed to probe audio duration for {p.name}",
            retryable=False,
        )

    raw_output = proc.stdout.strip()
    try:
        duration = float(raw_output)
    except (ValueError, TypeError):
        raise SpeechProviderError(
            code="speech_invalid_audio",
            message=f"ffprobe returned unparseable duration '{raw_output}'",
            retryable=False,
        )

    if not math.isfinite(duration) or duration <= 0:
        raise SpeechProviderError(
            code="speech_invalid_audio",
            message=f"ffprobe returned non-positive or non-finite duration: {duration}",
            retryable=False,
        )

    return duration


async def pad_audio(
    input_path: Path | str,
    output_path: Path | str,
    target_duration: float,
) -> float:
    """Pad audio to target_duration using FFmpeg apad filter in 48kHz mono PCM WAV.

    Validates that the resulting audio exists, is non-empty, and matches target duration.
    """
    in_p = Path(input_path).resolve()
    out_p = Path(output_path).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(in_p),
        "-af",
        "apad",
        "-t",
        f"{target_duration:.4f}",
        "-ar",
        "48000",
        "-ac",
        "1",
        str(out_p),
    ]

    def _run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

    proc = await asyncio.to_thread(_run)
    if proc.returncode != 0 or not out_p.exists() or out_p.stat().st_size == 0:
        logger.error("ffmpeg apad failed for %s returncode=%d", out_p.name, proc.returncode)
        raise SpeechProviderError(
            code="speech_invalid_audio",
            message=f"Failed to pad audio to {target_duration}s for {out_p.name}",
            retryable=False,
        )

    measured = await probe_duration(out_p)
    # Media tolerance: padded duration should be within 0.05s of target
    if abs(measured - target_duration) > 0.05:
        logger.error(
            "Padded duration mismatch target=%.4f measured=%.4f file=%s",
            target_duration,
            measured,
            out_p.name,
        )
        raise SpeechProviderError(
            code="speech_invalid_audio",
            message=f"Padded audio duration ({measured:.2f}s) diverged from target ({target_duration:.2f}s)",
            retryable=False,
        )

    return measured


def split_sentences_with_punctuation(text: str) -> list[str]:
    """Split narration text by punctuation into readable subtitle sentences."""
    # Split keeping delimiters: . ! ? ; :
    parts = re.split(r"([.!?;\:…]+)", text)
    sentences: list[str] = []
    i = 0
    while i < len(parts):
        chunk = parts[i].strip()
        punct = parts[i + 1].strip() if (i + 1 < len(parts)) else ""
        combined = f"{chunk}{punct}".strip()
        if combined:
            sentences.append(combined)
        i += 2

    # If no punctuation was matched, return the whole trimmed text
    if not sentences and text.strip():
        sentences = [text.strip()]

    return sentences


def generate_fallback_subtitle_cues(
    narration: str,
    scene_start: float,
    audio_duration: float,
) -> list[SubtitleCue]:
    """Allocate proportional subtitle cues across sentences within raw audio duration.

    Subtitles strictly end when speech finishes, never extending into padding silence.
    """
    sentences = split_sentences_with_punctuation(narration)
    if not sentences or audio_duration <= 0:
        return []

    if len(sentences) == 1:
        return [
            SubtitleCue(
                start_seconds=scene_start,
                end_seconds=scene_start + audio_duration,
                text=sentences[0],
            )
        ]

    total_weight = sum(max(len(s), 1) for s in sentences)
    cues: list[SubtitleCue] = []
    current_time = scene_start

    for idx, sentence in enumerate(sentences):
        weight = max(len(sentence), 1)
        if idx == len(sentences) - 1:
            seg_end = scene_start + audio_duration
        else:
            seg_duration = (weight / total_weight) * audio_duration
            seg_end = current_time + seg_duration

        # Ensure strict end > start
        if seg_end <= current_time:
            seg_end = current_time + 0.05

        cues.append(
            SubtitleCue(
                start_seconds=round(current_time, 4),
                end_seconds=round(seg_end, 4),
                text=sentence,
            )
        )
        current_time = seg_end

    return cues


def normalize_provider_cues(
    raw_cues: list[SubtitleCue],
    scene_start: float,
    raw_audio_duration: float,
    narration: str,
) -> list[SubtitleCue]:
    """Convert and validate scene-local provider timing cues to global scene coordinates.

    If provider timing is missing, corrupted, or out of bounds, falls back to proportional cues.
    """
    if not raw_cues:
        return generate_fallback_subtitle_cues(narration, scene_start, raw_audio_duration)

    normalized: list[SubtitleCue] = []
    scene_audio_end = scene_start + raw_audio_duration + 0.05

    for cue in raw_cues:
        g_start = round(scene_start + cue.start_seconds, 4)
        g_end = round(scene_start + cue.end_seconds, 4)

        if g_end <= g_start:
            # Bad metadata, fall back completely
            return generate_fallback_subtitle_cues(narration, scene_start, raw_audio_duration)

        if g_start < scene_start or g_end > scene_audio_end:
            # Out of bounds metadata, fall back
            return generate_fallback_subtitle_cues(narration, scene_start, raw_audio_duration)

        normalized.append(
            SubtitleCue(
                start_seconds=g_start,
                end_seconds=min(g_end, scene_start + raw_audio_duration),
                text=cue.text,
            )
        )

    return normalized if normalized else generate_fallback_subtitle_cues(narration, scene_start, raw_audio_duration)


class TimelineBuilder:
    """Builds a strictly continuous media timeline driven by measured audio durations."""

    def __init__(
        self,
        speech_provider: SpeechProvider,
        artifact_store: ArtifactStore,
    ):
        self.speech_provider = speech_provider
        self.artifact_store = artifact_store

    async def build(
        self,
        job_id: str,
        plan: LessonPlan,
    ) -> ResolvedTimeline:
        """Synthesize narration, pad audio, resolve scene coordinates, and persist timeline.json."""
        logger.info("Starting audio-first timeline build for job=%s scenes=%d", job_id, len(plan.scenes))

        timings: list[ResolvedSceneTiming] = []
        current_start = 0.0

        for scene in plan.scenes:
            try:
                # 1. Paths
                raw_filename = f"{scene.scene_id}.raw.mp3"
                padded_filename = f"{scene.scene_id}.padded.wav"
                raw_audio_path = self.artifact_store.get_path(job_id, "audio", raw_filename)
                padded_audio_path = self.artifact_store.get_path(job_id, "audio", padded_filename)

                # Ensure audio subfolder exists
                raw_audio_path.parent.mkdir(parents=True, exist_ok=True)

                # 2. Synthesize narration
                speech_res = await self.speech_provider.synthesize(
                    text=scene.narration,
                    output_path=raw_audio_path,
                    language=plan.language,
                )

                # 3. Probe measured raw audio duration
                raw_duration = await probe_duration(raw_audio_path)

                # 4. Compute render duration (+0.30s buffer, minimum 1.0s)
                render_duration = max(round(raw_duration + 0.30, 4), 1.0)

                # 5. Pad audio to render_duration
                await pad_audio(
                    input_path=raw_audio_path,
                    output_path=padded_audio_path,
                    target_duration=render_duration,
                )

                # 6. Resolve subtitles
                subtitles = normalize_provider_cues(
                    raw_cues=speech_res.subtitle_cues,
                    scene_start=current_start,
                    raw_audio_duration=raw_duration,
                    narration=scene.narration,
                )

                # 7. Form scene timing
                scene_end = round(current_start + render_duration, 4)
                timing = ResolvedSceneTiming(
                    scene_id=scene.scene_id,
                    raw_audio_path=str(raw_audio_path),
                    padded_audio_path=str(padded_audio_path),
                    audio_duration_seconds=raw_duration,
                    render_duration_seconds=render_duration,
                    start_seconds=current_start,
                    end_seconds=scene_end,
                    subtitle_cues=subtitles,
                )
                timings.append(timing)
                current_start = scene_end

            except SpeechProviderError as spe:
                logger.error("Audio step failed for scene=%s code=%s", scene.scene_id, spe.code)
                raise PipelineExecutionError(
                    code=spe.code,
                    message=spe.message,
                    stage=JobStage.AUDIO,
                    retryable=spe.retryable,
                ) from spe
            except Exception as exc:
                logger.error("Unexpected error in timeline audio for scene=%s type=%s", scene.scene_id, type(exc).__name__)
                raise PipelineExecutionError(
                    code="speech_provider_error",
                    message="An unexpected error occurred during audio processing.",
                    stage=JobStage.AUDIO,
                    retryable=False,
                ) from exc

        # 8. Create complete ResolvedTimeline
        total_duration = current_start
        timeline = ResolvedTimeline(
            scenes=timings,
            total_duration_seconds=total_duration,
        )

        # 9. Atomically persist timeline.json
        timeline_path = self.artifact_store.get_path(job_id, "timeline.json")
        tmp_timeline_path = self.artifact_store.get_path(
            job_id, f"timeline.tmp_{os.getpid()}_{id(timeline)}.json"
        )

        timeline_data = timeline.model_dump(mode="json")
        tmp_timeline_path.write_text(
            json.dumps(timeline_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp_timeline_path, timeline_path)

        logger.info(
            "Timeline successfully built and persisted for job=%s total_duration=%.2fs",
            job_id,
            total_duration,
        )
        return timeline
