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
        timeout_seconds: float = 180.0,
    ):
        self.fps = fps
        self.font_path = font_path
        self.timeout_seconds = timeout_seconds

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

        # 3. Build FFmpeg command
        # Subtitle filter escaping for FFmpeg: escape colons and backslashes
        escaped_srt_path = str(srt_file.resolve()).replace("\\", "/").replace(":", "\\:")
        
        # Subtitle style: bottom-center, readable white text, subtle dark outline
        force_style = (
            f"Fontname=DejaVu Sans,Fontsize=22,PrimaryColour=&H00FFFFFF&,"
            f"OutlineColour=&H00000000&,Outline=2,Shadow=0,MarginV=36,Alignment=2"
        )
        sub_filter = f"subtitles='{escaped_srt_path}':force_style='{force_style}'"

        # If srt file has no cues, avoid applying empty subtitle filter which might warn or fail
        has_subtitles = bool(srt_content.strip())
        video_filters = sub_filter if has_subtitles else "null"

        cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(visual_concat_list.resolve()),
            "-f", "concat",
            "-safe", "0",
            "-i", str(audio_concat_list.resolve()),
            "-vf", video_filters,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(self.fps),
            "-c:a", "aac",
            "-ar", "48000",
            "-ac", "2",
            "-movflags", "+faststart",
            "-shortest",
            str(output_path.resolve()),
        ]

        def _run_ffmpeg() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=self.timeout_seconds,
            )

        try:
            proc = await asyncio.to_thread(_run_ffmpeg)
        except subprocess.TimeoutExpired as exc:
            logger.error(
                "Assembly timed out after %.1fs job_id=%s timeout=%s",
                self.timeout_seconds,
                job_id,
                exc,
            )
            raise PipelineExecutionError(
                code="assembly_failed",
                message="Video assembly timed out.",
                stage=JobStage.ASSEMBLING,
                retryable=False,
            ) from exc
        except Exception as exc:
            logger.error(
                "Assembly process error job_id=%s exc_type=%s",
                job_id,
                type(exc).__name__,
            )
            raise PipelineExecutionError(
                code="assembly_failed",
                message="The final video could not be assembled.",
                stage=JobStage.ASSEMBLING,
                retryable=False,
            ) from exc

        if proc.returncode != 0:
            logger.error(
                "FFmpeg assembly failed for job_id=%s returncode=%d",
                job_id,
                proc.returncode,
            )
            raise PipelineExecutionError(
                code="assembly_failed",
                message="The final video could not be assembled.",
                stage=JobStage.ASSEMBLING,
                retryable=False,
            )

        # Validate candidate output file
        if not output_path.exists() or not output_path.is_file() or output_path.stat().st_size == 0:
            logger.error(
                "Assembly finished but output file is missing or empty: %s",
                output_path,
            )
            raise PipelineExecutionError(
                code="assembly_failed",
                message="The final video could not be assembled.",
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
