"""Quality Gate verifying that candidate video artifacts satisfy production media contracts."""

import asyncio
import json
import logging
import math
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.domain.lesson import LessonPlan
from app.domain.timeline import ResolvedTimeline

logger = logging.getLogger(__name__)


class QualityCheck(BaseModel):
    """Result of an individual validation check."""

    name: str
    passed: bool
    details: str


class QualityReport(BaseModel):
    """Aggregated validation report for a candidate video artifact."""

    passed: bool
    checks: list[QualityCheck]
    metadata: dict[str, Any]


class QualityGate:
    """Verifies candidate video artifacts with ffprobe metadata checks and schema revalidation."""

    def __init__(
        self,
        expected_width: int = 1280,
        expected_height: int = 720,
        min_size_bytes: int = 50_000,
        timeout_seconds: float = 30.0,
    ):
        self.expected_width = expected_width
        self.expected_height = expected_height
        self.min_size_bytes = min_size_bytes
        self.timeout_seconds = timeout_seconds

    async def validate(
        self,
        candidate_path: Path,
        timeline: ResolvedTimeline,
        plan: LessonPlan,
    ) -> QualityReport:
        """Execute all quality gate checks on candidate video against timeline and lesson plan."""
        checks: list[QualityCheck] = []
        candidate = Path(candidate_path).resolve()

        # 1. Existence check
        exists = candidate.exists()
        checks.append(
            QualityCheck(
                name="file_exists",
                passed=exists,
                details=f"File exists: {exists} ({candidate.name})",
            )
        )
        if not exists:
            return QualityReport(passed=False, checks=checks, metadata={})

        # 2. Regular file check
        is_file = candidate.is_file()
        checks.append(
            QualityCheck(
                name="regular_file",
                passed=is_file,
                details=f"Is regular file: {is_file}",
            )
        )
        if not is_file:
            return QualityReport(passed=False, checks=checks, metadata={})

        # 3. File size check
        size_bytes = candidate.stat().st_size
        size_passed = size_bytes >= self.min_size_bytes
        checks.append(
            QualityCheck(
                name="minimum_size",
                passed=size_passed,
                details=f"File size {size_bytes} bytes (min: {self.min_size_bytes} bytes)",
            )
        )
        if not size_passed:
            return QualityReport(passed=False, checks=checks, metadata={})

        # 4. Probe with ffprobe
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(candidate),
        ]

        def _run_ffprobe() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=self.timeout_seconds,
            )

        try:
            proc = await asyncio.to_thread(_run_ffprobe)
            ffprobe_ok = proc.returncode == 0
            raw_stdout = proc.stdout
        except Exception as exc:
            logger.error("Quality gate ffprobe exception: %s", type(exc).__name__)
            ffprobe_ok = False
            raw_stdout = ""

        checks.append(
            QualityCheck(
                name="ffprobe_execution",
                passed=ffprobe_ok,
                details=f"ffprobe returncode {proc.returncode if ffprobe_ok else 'failed'}",
            )
        )
        if not ffprobe_ok:
            return QualityReport(passed=False, checks=checks, metadata={})

        # Parse JSON
        try:
            probe_data = json.loads(raw_stdout)
        except Exception:
            checks.append(
                QualityCheck(
                    name="ffprobe_json_parse",
                    passed=False,
                    details="ffprobe stdout could not be parsed as valid JSON",
                )
            )
            return QualityReport(passed=False, checks=checks, metadata={})

        streams = probe_data.get("streams", [])
        fmt = probe_data.get("format", {})

        # Find streams by codec_type (never assume stream index order)
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        # 5. Video stream exists
        checks.append(
            QualityCheck(
                name="video_stream_exists",
                passed=video_stream is not None,
                details="Video stream found" if video_stream else "No video stream in container",
            )
        )

        # 6. Audio stream exists
        checks.append(
            QualityCheck(
                name="audio_stream_exists",
                passed=audio_stream is not None,
                details="Audio stream found" if audio_stream else "No audio stream in container",
            )
        )

        if not video_stream or not audio_stream:
            return QualityReport(passed=False, checks=checks, metadata={})

        # 7. Codec names
        video_codec = video_stream.get("codec_name", "")
        audio_codec = audio_stream.get("codec_name", "")
        codecs_ok = bool(video_codec) and bool(audio_codec)
        checks.append(
            QualityCheck(
                name="codec_names_present",
                passed=codecs_ok,
                details=f"Video codec: {video_codec}, Audio codec: {audio_codec}",
            )
        )

        # 8. Resolution check
        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        resolution_ok = width == self.expected_width and height == self.expected_height
        checks.append(
            QualityCheck(
                name="resolution_match",
                passed=resolution_ok,
                details=f"Resolution {width}x{height} (expected {self.expected_width}x{self.expected_height})",
            )
        )

        # 9. Duration check & tolerance
        raw_dur = fmt.get("duration") or video_stream.get("duration") or 0.0
        try:
            actual_duration = float(raw_dur)
        except (ValueError, TypeError):
            actual_duration = 0.0

        finite_duration = math.isfinite(actual_duration) and actual_duration > 1.0
        checks.append(
            QualityCheck(
                name="duration_finite_positive",
                passed=finite_duration,
                details=f"Measured duration: {actual_duration:.2f}s",
            )
        )

        expected_duration = timeline.total_duration_seconds
        tolerance = max(0.75, expected_duration * 0.03)
        duration_diff = abs(actual_duration - expected_duration)
        duration_close = duration_diff <= tolerance
        checks.append(
            QualityCheck(
                name="duration_within_tolerance",
                passed=duration_close,
                details=(
                    f"Actual: {actual_duration:.2f}s, Timeline: {expected_duration:.2f}s, "
                    f"Diff: {duration_diff:.2f}s (Tolerance: {tolerance:.2f}s)"
                ),
            )
        )

        # 10. LessonPlan schema revalidation
        try:
            LessonPlan.model_validate(plan.model_dump())
            plan_valid = True
            plan_details = f"LessonPlan schema valid ({len(plan.scenes)} scenes)"
        except Exception as exc:
            plan_valid = False
            plan_details = f"LessonPlan revalidation failed: {type(exc).__name__}"

        checks.append(
            QualityCheck(
                name="lesson_plan_schema_valid",
                passed=plan_valid,
                details=plan_details,
            )
        )

        all_passed = all(c.passed for c in checks)

        metadata = {}
        if all_passed:
            metadata = {
                "filename": "final.mp4",
                "size_bytes": size_bytes,
                "duration_seconds": round(actual_duration, 2),
                "width": width,
                "height": height,
                "video_codec": str(video_codec),
                "audio_codec": str(audio_codec),
            }

        return QualityReport(
            passed=all_passed,
            checks=checks,
            metadata=metadata,
        )
