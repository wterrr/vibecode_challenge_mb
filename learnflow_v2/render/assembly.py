"""Deterministic V2 scene assembly using typed transition artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Sequence

from learnflow_v2.render.errors import RenderAssemblyError, RenderInvalidInputError
from learnflow_v2.render.schema import RenderedScene, RenderedVideo


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _transition(plan: Any) -> tuple[str, str, str, float, str]:
    for field in ("transition_id", "from_scene", "to_scene", "duration"):
        if not hasattr(plan, field):
            raise RenderInvalidInputError("transition plan does not satisfy InterSceneTransitionPlan contract")
    tid, left, right = str(plan.transition_id).strip(), str(plan.from_scene).strip(), str(plan.to_scene).strip()
    duration = plan.duration
    if not tid or not left or not right:
        raise RenderInvalidInputError("transition identifiers cannot be blank")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or float(duration) <= 0:
        raise RenderInvalidInputError("transition duration must be positive")
    operations: list[str] = []
    for item in getattr(plan, "persistent_objects", ()):
        raw = getattr(item, "effective_operation", None)
        value = getattr(raw, "value", raw)
        if value is not None:
            operations.append(str(value))
    # Reference Pillow/FFmpeg backend supports whole-frame FADE. Unsupported
    # persistent-object operations degrade deterministically instead of failing.
    effective = "FADE" if not operations or all(op == "FADE" for op in operations) else "FADE_RUNTIME_FALLBACK"
    return tid, left, right, float(duration), effective


def assemble_rendered_scenes(
    *,
    video_id: str,
    scenes: Sequence[RenderedScene],
    transition_plans: Sequence[Any],
    output_path: Path,
) -> RenderedVideo:
    if not isinstance(video_id, str) or not video_id.strip():
        raise RenderInvalidInputError("video_id must be non-empty")
    scenes = tuple(RenderedScene.model_validate(s.model_dump(mode="json")) for s in scenes)
    transitions = tuple(transition_plans)
    if not scenes:
        raise RenderInvalidInputError("assembly requires at least one scene")
    if len(transitions) != max(0, len(scenes) - 1):
        raise RenderInvalidInputError("assembly requires one transition per adjacent scene pair")
    if len({s.scene_id for s in scenes}) != len(scenes):
        raise RenderInvalidInputError("assembled scene IDs must be unique")
    if len({(s.width, s.height, s.fps) for s in scenes}) != 1:
        raise RenderInvalidInputError("all scenes must share width/height/fps")
    if len({s.has_audio for s in scenes}) != 1:
        raise RenderInvalidInputError("all scenes must either all have audio or all omit audio")
    for scene in scenes:
        p = Path(scene.output_path)
        if not p.is_file() or p.stat().st_size <= 0:
            raise RenderInvalidInputError(f"rendered scene file is missing: {scene.output_path}")

    specs: list[tuple[str, str, str, float, str]] = []
    for index, plan in enumerate(transitions):
        spec = _transition(plan)
        expected = (scenes[index].scene_id, scenes[index + 1].scene_id)
        if (spec[1], spec[2]) != expected:
            raise RenderInvalidInputError(f"transition '{spec[0]}' endpoints do not match adjacent scenes {expected}")
        limit = min(scenes[index].rendered_duration, scenes[index + 1].rendered_duration) - 1 / scenes[index].fps
        if spec[3] >= limit:
            raise RenderInvalidInputError(f"transition '{spec[0]}' duration is too long")
        specs.append(spec)

    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() != ".mp4":
        raise RenderInvalidInputError("assembly output must be .mp4")
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RenderAssemblyError("ffmpeg/ffprobe are required")

    diagnostics: list[str] = []
    if len(scenes) == 1:
        shutil.copyfile(scenes[0].output_path, output)
        expected_duration = scenes[0].rendered_duration
    else:
        cmd = ["ffmpeg", "-y", "-loglevel", "error"]
        for scene in scenes:
            cmd += ["-i", scene.output_path]
        filters: list[str] = []
        current_v = "0:v"
        current_a = "0:a" if scenes[0].has_audio else None
        expected_duration = scenes[0].rendered_duration
        for index, spec in enumerate(specs, start=1):
            tid, _left, _right, duration, effective = spec
            offset = expected_duration - duration
            out_v = f"v{index}"
            filters.append(
                f"[{current_v}][{index}:v]xfade=transition=fade:duration={duration:.6f}:offset={offset:.6f}[{out_v}]"
            )
            current_v = out_v
            if current_a is not None:
                out_a = f"a{index}"
                filters.append(f"[{current_a}][{index}:a]acrossfade=d={duration:.6f}:c1=tri:c2=tri[{out_a}]")
                current_a = out_a
            expected_duration += scenes[index].rendered_duration - duration
            if effective != "FADE":
                diagnostics.append(f"{tid}:BACKEND_RUNTIME_FALLBACK:{effective}->FADE")
        cmd += ["-filter_complex", ";".join(filters), "-map", f"[{current_v}]"]
        if current_a is not None:
            cmd += ["-map", f"[{current_a}]", "-c:a", "aac", "-b:a", "96k"]
        cmd += [
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-r", str(scenes[0].fps), "-threads", "1", "-map_metadata", "-1",
            "-fflags", "+bitexact", "-flags:v", "+bitexact", str(output),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=180)
        if proc.returncode != 0 or not output.is_file() or output.stat().st_size <= 0:
            raise RenderAssemblyError(f"ffmpeg assembly failed: {proc.stderr[-500:]}")

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration", "-of", "json", str(output)],
        capture_output=True, text=True, check=False, timeout=30,
    )
    if probe.returncode != 0:
        raise RenderAssemblyError("ffprobe failed on assembled video")
    data = json.loads(probe.stdout)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if video is None:
        raise RenderAssemblyError("assembled video has no video stream")
    duration = float(data.get("format", {}).get("duration", 0.0))
    if abs(duration - expected_duration) > max(0.12, 2 / scenes[0].fps):
        raise RenderAssemblyError(f"assembled duration mismatch: expected={expected_duration:.6f}, got={duration:.6f}")
    return RenderedVideo(
        video_id=video_id.strip(),
        output_path=str(output),
        scene_ids=tuple(s.scene_id for s in scenes),
        transition_ids=tuple(s[0] for s in specs),
        duration=round(duration, 6),
        width=int(video.get("width", 0)),
        height=int(video.get("height", 0)),
        fps=scenes[0].fps,
        file_size_bytes=output.stat().st_size,
        video_sha256=_sha256(output),
        diagnostics=tuple(diagnostics),
    )
