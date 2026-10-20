"""Video assembly engine concatenating visual scenes, audio, and burning subtitles."""

import asyncio
import logging
import math
import subprocess
from pathlib import Path

from app.domain.enums import JobStage
from app.domain.errors import PipelineExecutionError
from app.domain.timeline import ResolvedTimeline, SubtitleCue

logger = logging.getLogger(__name__)


def assembly_timeout_budget(duration_seconds: float) -> float:
    """Bound costly 720p subtitle burn-in on a shared production CPU.

    The previous hard-coded 180s is insufficient for 90s+ 720p videos,
    especially when libass subtitles require a second H264 encoding pass.
    """
    if not math.isfinite(duration_seconds) or duration_seconds <= 0:
        raise ValueError("Invalid total video duration")
    return float(max(180, min(900, int(duration_seconds * 7 + 90))))


def format_srt_timestamp(seconds: float) -> str:
    """Format float seconds to SRT time format: HH:MM:SS,mmm."""
    clamped = max(0.0, float(seconds))
    if not math.isfinite(clamped):
        clamped = 0.0

    total_millis = int(round(clamped * 1000))
    hours = total_millis // 3_600_000
    remainder = total_millis % 3_600_000
    minutes = remainder // 60_000
    remainder %= 60_000
    secs = remainder // 1000
    millis = remainder % 1000

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def build_srt_content(timeline: ResolvedTimeline) -> str:
    """Compile subtitle cues from all timeline scenes in chronological order into valid SRT format."""
    all_cues: list[SubtitleCue] = []
    for scene in timeline.scenes:
        if scene.subtitle_cues:
            all_cues.extend(scene.subtitle_cues)

    # Sort strictly by start time
    all_cues.sort(key=lambda c: (c.start_seconds, c.end_seconds))

    blocks: list[str] = []
    index = 1
    for cue in all_cues:
        start_sec = max(0.0, cue.start_seconds)
        end_sec = max(start_sec + 0.05, cue.end_seconds)
        text = cue.text.strip()
        if not text:
            continue

        start_ts = format_srt_timestamp(start_sec)
        end_ts = format_srt_timestamp(end_sec)
        blocks.append(f"{index}\n{start_ts} --> {end_ts}\n{text}\n")
        index += 1

    return "\n".join(blocks)


class VideoAssembler:
    """Assembles scene visual MP4s and padded audio files into a final pending MP4 with burned subtitles."""

    def __init__(
        self,
        fps: int = 24,
        font_path: str = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        timeout_seconds: float | None = None,
        subtitle_force_style: str | None = None,
    ):
        self.fps = fps
        self.font_path = font_path
        # An explicit timeout is respected for tests or deployment tuning.
        # None means a bounded budget based on actual narration length.
        self.timeout_seconds = timeout_seconds
        # V3-19 opt-in override; None preserves the existing V2 font/size EXACTLY.
        self.subtitle_force_style = subtitle_force_style

    async def assemble(
        self,
        job_id: str,
        scene_video_paths: list[Path],
        timeline: ResolvedTimeline,
        output_path: Path,
        subtitles_path: Path | None = None,
    ) -> Path:
        """Concatenate scene visuals, concatenate padded audio, burn subtitles, and produce final.pending.mp4.

        Writes strictly to output_path (which must be final.pending.mp4, never final.mp4).
        """
        if not scene_video_paths:
            raise PipelineExecutionError(
                code="assembly_failed",
                message="Cannot assemble video: scene video list is empty.",
                stage=JobStage.ASSEMBLING,
                retryable=False,
            )

        if len(scene_video_paths) != len(timeline.scenes):
            raise PipelineExecutionError(
                code="assembly_failed",
                message=f"Scene video count ({len(scene_video_paths)}) does not match timeline ({len(timeline.scenes)}).",
                stage=JobStage.ASSEMBLING,
                retryable=False,
            )

        logger.info(
            "Starting video assembly for job=%s scenes=%d fps=%d target=%s",
            job_id,
            len(scene_video_paths),
            self.fps,
            output_path.name,
        )

        job_dir = output_path.parent
        job_dir.mkdir(parents=True, exist_ok=True)

        # 1. Generate subtitles.srt
        srt_file = subtitles_path or (job_dir / "subtitles.srt")
        srt_content = build_srt_content(timeline)
        srt_file.write_text(srt_content, encoding="utf-8")

        # 2. Prepare concat lists for FFmpeg concat demuxer
        visual_concat_list = job_dir / "visual_concat.txt"
        audio_concat_list = job_dir / "audio_concat.txt"

        visual_lines = [f"file '{p.resolve()}'" for p in scene_video_paths]
        visual_concat_list.write_text("\n".join(visual_lines) + "\n", encoding="utf-8")

        audio_paths = [Path(scene.padded_audio_path).resolve() for scene in timeline.scenes]
        audio_lines = [f"file '{p}'" for p in audio_paths]
        audio_concat_list.write_text("\n".join(audio_lines) + "\n", encoding="utf-8")

        timeout_budget = (self.timeout_seconds if self.timeout_seconds is not None
                          else assembly_timeout_budget(timeline.total_duration_seconds))

        # 3. Build FFmpeg command
        # Subtitle filter escaping for FFmpeg: escape colons and backslashes
        escaped_srt_path = str(srt_file.resolve()).replace("\\", "/").replace(":", "\\:")
        
        # Subtitle style: bottom-center, readable white text, subtle dark outline
        force_style = (
            f"Fontname=DejaVu Sans,Fontsize=22,PrimaryColour=&H00FFFFFF&,"
            f"OutlineColour=&H00000000&,Outline=2,Shadow=0,MarginV=36,Alignment=2"
        )
        if self.subtitle_force_style is not None:
            if not self.subtitle_force_style or any(c in self.subtitle_force_style for c in ("'", "\\", "\n", "\r")):
                raise PipelineExecutionError(
                    code="assembly_failed",message="Invalid subtitle style",
                    stage=JobStage.ASSEMBLING,retryable=False)
            force_style=self.subtitle_force_style
        sub_filter = f"subtitles='{escaped_srt_path}':force_style='{force_style}'"

        # If srt file has no cues, avoid applying empty subtitle filter which might warn or fail
        has_subtitles = bool(srt_content.strip())
        video_filters = sub_filter if has_subtitles else "null"

        cmd = [
            "ffmpeg",
            "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(visual_concat_list.resolve()),
            "-f", "concat",
            "-safe", "0",
            "-i", str(audio_concat_list.resolve()),
            # Single bounded filter graph and encoder; the previous implicit
            # x264 "medium" preset could exceed 180 seconds on small hosts.
            "-filter_threads", "2",
            "-vf", video_filters,
            "-c:v", "libx264",
            "-preset", "ultrafast", "-crf", "23",
            "-threads", "2",
            "-pix_fmt", "yuv420p",
            "-r", str(self.fps),
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "48000",
            "-ac", "2",
            "-movflags", "+faststart",
            "-shortest",
            str(output_path.resolve()),
        ]

        def _run_ffmpeg() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=timeout_budget,
            )

        try:
            logger.info(
                "Starting bounded FFmpeg assembly job=%s duration=%.2fs "
                "scenes=%d subtitles=%s budget=%.0fs",
                job_id, timeline.total_duration_seconds, len(scene_video_paths),
                has_subtitles, timeout_budget,
            )
            proc = await asyncio.to_thread(_run_ffmpeg)
        except subprocess.TimeoutExpired:
            output_path.unlink(missing_ok=True)
            logger.error("FFmpeg assembly timed out job=%s budget=%.0fs duration=%.2fs",
                         job_id, timeout_budget, timeline.total_duration_seconds)
            raise PipelineExecutionError(
                code="assembly_timeout",
                message="Video assembly exceeded its bounded time budget.",
                stage=JobStage.ASSEMBLING,
                retryable=False,
            ) from None
        except FileNotFoundError:
            output_path.unlink(missing_ok=True)
            logger.error("FFmpeg assembly executable missing job=%s", job_id)
            raise PipelineExecutionError(
                code="assembly_ffmpeg_missing",
                message="Video assembly requires FFmpeg.",
                stage=JobStage.ASSEMBLING,
                retryable=False,
            ) from None
        except Exception as exc:
            output_path.unlink(missing_ok=True)
            logger.error("Assembly subprocess exception job=%s type=%s",
                         job_id, type(exc).__name__)
            raise PipelineExecutionError(
                code="assembly_failed",
                message="The final video could not be assembled.",
                stage=JobStage.ASSEMBLING,
                retryable=False,
            ) from None

        if proc.returncode != 0:
            output_path.unlink(missing_ok=True)
            # Never include stderr, file paths, narration, or private data in
            # a user-visible error or public logs.
            logger.error("FFmpeg assembly failed job=%s returncode=%d", job_id, proc.returncode)
            raise PipelineExecutionError(
                code="assembly_ffmpeg_failed",
                message="FFmpeg could not combine the rendered scenes and audio.",
                stage=JobStage.ASSEMBLING,
                retryable=False,
            )

        # Validate candidate output file
        if not output_path.is_file() or output_path.stat().st_size == 0:
            output_path.unlink(missing_ok=True)
            logger.error("Assembly produced missing/empty final candidate job=%s", job_id)
            raise PipelineExecutionError(
                code="assembly_empty_output",
                message="FFmpeg produced an empty final video.",
                stage=JobStage.ASSEMBLING,
                retryable=False,
            )

        logger.info(
            "Video assembly succeeded for job=%s file=%s size=%d bytes",
            job_id,
            output_path.name,
            output_path.stat().st_size,
        )
        return output_path
