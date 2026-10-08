"""Production media integration for live LearnFlow V2D evaluation.

This module intentionally sits above frozen Core V2. It consumes accepted typed
lesson artifacts, drives existing public motion/transition/render facades, and
adds narration/audio/subtitles plus a fail-closed production output gate.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Callable, Protocol, Sequence

from learnflow_v2.concepts import ConceptRegistry
from learnflow_v2.layout import LayoutGraph, compile_scene_layout
from learnflow_v2.motion import (
    MotionEvent,
    MotionPlan,
    MotionStyle,
    MotionTrigger,
    MotionVerb,
    compile_motion_schedule,
    create_narration_beat_map_fallback,
    resolve_motion_plan_timing,
    schedule_motion_plan,
)
from learnflow_v2.render import (
    RenderArtifactKind,
    RenderInvalidInputError,
    RenderProfile,
    RenderedArtifact,
    SubtitleRenderCue,
    assemble_video,
    burn_subtitles,
    mux_audio_track,
    render_transition_video,
)
from learnflow_v2.transitions import (
    MINIMAL_TRANSITION_CAPABILITIES,
    compile_inter_scene_transition,
)

from .models import LessonPipelineResult


SCENE_TAIL_PAD_SECONDS = 0.20
TRANSITION_DURATION_SECONDS = 0.45
MIN_TARGET_DURATION_RATIO = 0.55
MAX_TARGET_DURATION_RATIO = 1.45


class ProductionOutputGateError(RuntimeError):
    """Raised when a live lesson renders but is not production-usable."""


@dataclass(frozen=True)
class SynthesizedNarration:
    path: Path
    duration_seconds: float
    subtitle_cues: tuple[SubtitleRenderCue, ...]
    provider: str


class NarrationSynthesizer(Protocol):
    def __call__(
        self,
        text: str,
        output_path: Path,
        language: str,
    ) -> SynthesizedNarration: ...


@dataclass(frozen=True)
class ProductionMediaResult:
    final_video: RenderedArtifact
    report: dict[str, Any]


def _run(cmd: list[str], *, label: str) -> subprocess.CompletedProcess[str]:
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise ProductionOutputGateError(f"{label} failed to start: {exc}") from exc
    if proc.returncode != 0:
        raise ProductionOutputGateError(
            f"{label} failed: {proc.stderr[-2000:]}"
        )
    return proc


def probe_media_duration(path: str | Path) -> float:
    target = Path(path)
    if not target.is_file() or target.stat().st_size <= 0:
        raise ProductionOutputGateError(f"media file missing: {target}")
    proc = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(target),
        ],
        label="ffprobe duration",
    )
    try:
        value = float(proc.stdout.strip())
    except ValueError as exc:
        raise ProductionOutputGateError(
            f"ffprobe returned invalid duration for {target}"
        ) from exc
    if value <= 0.0:
        raise ProductionOutputGateError(
            f"ffprobe returned non-positive duration for {target}: {value}"
        )
    return value


def _probe_stream_types(path: str | Path) -> set[str]:
    proc = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "json",
            str(Path(path)),
        ],
        label="ffprobe streams",
    )
    payload = json.loads(proc.stdout or "{}")
    return {
        str(item.get("codec_type"))
        for item in payload.get("streams") or ()
        if item.get("codec_type")
    }


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_capability(raw: str, *, action: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProductionOutputGateError(
            f"{action} returned invalid JSON"
        ) from exc
    if not isinstance(payload, dict) or not payload.get("success"):
        error = payload.get("error") if isinstance(payload, dict) else {}
        raise ProductionOutputGateError(
            f"{action} failed: {(error or {}).get('code', 'UNKNOWN')} "
            f"{(error or {}).get('message', '')}".strip()
        )
    return payload


def _scene_segments(result: LessonPipelineResult, scene) -> tuple[Any, ...]:
    by_id = {segment.segment_id: segment for segment in result.lesson_script.segments}
    return tuple(by_id[segment_id] for segment_id in scene.script_segment_ids)


def _build_motion_plan(
    graph,
    layout: LayoutGraph,
    *,
    phrase_count: int,
) -> tuple[MotionPlan, tuple[dict[str, Any], ...]]:
    events: list[MotionEvent] = []
    beat_defs: list[dict[str, Any]] = []
    nodes = list(graph.nodes)
    routed_relations = {edge.edge_id for edge in layout.routed_edges}

    node_limit = min(len(nodes), 16)
    styles = (MotionStyle.FADE, MotionStyle.SLIDE, MotionStyle.REVEAL)
    planned: list[tuple[str, MotionVerb, MotionStyle]] = []
    for index, node in enumerate(nodes[:node_limit]):
        planned.append((node.id, MotionVerb.ENTER, styles[index % len(styles)]))

    for relation in graph.relations:
        if relation.id in routed_relations and len(planned) < 24:
            planned.append(
                (relation.id, MotionVerb.RELATION, MotionStyle.DRAW_EDGE)
            )

    if nodes and len(planned) < 24:
        planned.append(
            (nodes[0].id, MotionVerb.EMPHASIZE, MotionStyle.PULSE)
        )

    total = len(planned)
    for index, (target, verb, style) in enumerate(planned):
        beat_id = f"motion_beat_{index:02d}"
        phrase_index = 0
        if phrase_count > 1 and total > 1:
            phrase_index = round(index * (phrase_count - 1) / (total - 1))
        event = MotionEvent(
            id=f"motion_event_{index:02d}",
            target=target,
            verb=verb,
            style=style,
            trigger=MotionTrigger(beat=beat_id),
        )
        events.append(event)
        beat_defs.append(
            {
                "id": beat_id,
                "name": beat_id,
                "phrase_index": int(phrase_index),
            }
        )

    return MotionPlan(scene_id=graph.scene_id, events=tuple(events)), tuple(beat_defs)


def _concat_audio_sequence(
    entries: Sequence[tuple[str, Path | float]],
    output_path: Path,
) -> float:
    if not entries:
        raise ProductionOutputGateError("audio assembly requires at least one entry")

    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    durations: list[float] = []
    for kind, value in entries:
        if kind == "file":
            path = Path(value)
            cmd.extend(["-i", str(path)])
            durations.append(probe_media_duration(path))
        elif kind == "silence":
            duration = float(value)
            if duration <= 1e-4:
                continue
            cmd.extend(
                [
                    "-f",
                    "lavfi",
                    "-t",
                    f"{duration:.6f}",
                    "-i",
                    "anullsrc=channel_layout=stereo:sample_rate=44100",
                ]
            )
            durations.append(duration)
        else:
            raise ProductionOutputGateError(f"unknown audio entry kind: {kind}")

    if not durations:
        raise ProductionOutputGateError("audio assembly resolved to zero entries")

    chains = [
        f"[{index}:a]aresample=44100,aformat=channel_layouts=stereo[a{index}]"
        for index in range(len(durations))
    ]
    concat = "".join(f"[a{index}]" for index in range(len(durations)))
    chains.append(f"{concat}concat=n={len(durations)}:v=0:a=1[outa]")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd.extend(
        [
            "-filter_complex",
            ";".join(chains),
            "-map",
            "[outa]",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(output_path),
        ]
    )
    _run(cmd, label="lesson audio concat")
    return probe_media_duration(output_path)


def _refresh_artifact_manifest(root: Path, final_video: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "artifact_manifest.json":
            continue
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha256_file(path),
            }
        )
    _atomic_json(
        root / "artifact_manifest.json",
        {
            "schema_version": "lesson-pipeline-artifact-manifest-v2",
            "artifacts": rows,
            "final_video": str(final_video),
        },
    )


def build_production_media(
    result: LessonPipelineResult,
    *,
    create: Callable[..., str],
    run: Callable[..., str],
    render: Callable[..., str],
    repo_root: str | Path,
    synthesize_narration: NarrationSynthesizer,
) -> ProductionMediaResult:
    """Build narration-aware production media from accepted typed lesson artifacts."""

    root = Path(result.artifact_root)
    repo_root = Path(repo_root).resolve()
    root.mkdir(parents=True, exist_ok=True)

    preview = root / "final.mp4"
    if preview.is_file():
        preview_target = root / "core_preview.mp4"
        if preview_target.exists():
            preview_target.unlink()
        preview.replace(preview_target)

    audio_dir = root / "audio"
    layout_dir = root / "layouts"
    motion_dir = root / "motion"
    transition_dir = root / "transitions"
    scene_dir = root / "scenes"
    verification_dir = root / "verification"
    for directory in (
        audio_dir,
        layout_dir,
        motion_dir,
        transition_dir,
        scene_dir,
        verification_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    profile = RenderProfile(
        profile_id="live-v2d-production",
        fps=30,
        crf=18,
        preset="medium",
    )
    registry = ConceptRegistry.from_schema(result.concept_registry)

    scene_artifacts: list[RenderedArtifact] = []
    scene_layouts: list[LayoutGraph] = []
    scene_audio: list[SynthesizedNarration] = []
    scene_subtitles: list[tuple[SubtitleRenderCue, ...]] = []
    scene_motion_counts: list[int] = []
    scene_reports: list[dict[str, Any]] = []

    for index, (scene, graph) in enumerate(
        zip(result.storyboard.scenes, result.scenegraphs, strict=True),
        start=1,
    ):
        segments = _scene_segments(result, scene)
        spoken_text = " ".join(segment.spoken_text.strip() for segment in segments)
        phrase_hints = tuple(segment.spoken_text for segment in segments)
        subtitle_texts = tuple(segment.subtitle_text for segment in segments)
        language = segments[0].spoken_language if segments else result.learning_brief.language

        narration_path = audio_dir / f"{index:03d}.mp3"
        narration = synthesize_narration(
            spoken_text,
            narration_path,
            language,
        )
        if not narration.path.is_file() or narration.duration_seconds <= 0.0:
            raise ProductionOutputGateError(
                f"scene {scene.scene_id} narration synthesis produced no usable audio"
            )

        scene_duration = max(
            1.0,
            narration.duration_seconds + SCENE_TAIL_PAD_SECONDS,
        )
        layout = compile_scene_layout(graph)
        plan, beat_definitions = _build_motion_plan(
            graph,
            layout,
            phrase_count=max(1, len(phrase_hints)),
        )
        if not plan.events:
            raise ProductionOutputGateError(
                f"scene {scene.scene_id} has no production motion events"
            )
        beat_map = create_narration_beat_map_fallback(
            scene_id=graph.scene_id,
            narration_text=spoken_text,
            total_duration=scene_duration,
            phrase_hints=phrase_hints,
            beat_definitions=beat_definitions,
        )
        resolved = resolve_motion_plan_timing(plan, beat_map)
        schedule = schedule_motion_plan(
            plan,
            scene_duration,
            resolved_timing=resolved,
            graph=graph,
        )
        compiled = compile_motion_schedule(schedule)

        _atomic_json(
            layout_dir / f"{index:03d}.json",
            layout.model_dump(mode="json"),
        )
        _atomic_json(
            motion_dir / f"{index:03d}.plan.json",
            plan.model_dump(mode="json"),
        )
        _atomic_json(
            motion_dir / f"{index:03d}.beats.json",
            beat_map.model_dump(mode="json"),
        )
        _atomic_json(
            motion_dir / f"{index:03d}.resolved.json",
            resolved.model_dump(mode="json"),
        )
        _atomic_json(
            motion_dir / f"{index:03d}.schedule.json",
            schedule.model_dump(mode="json"),
        )
        _atomic_json(
            motion_dir / f"{index:03d}.compiled.json",
            compiled.model_dump(mode="json"),
        )

        created = _parse_capability(
            create(
                {
                    "scene_graph": graph.model_dump(mode="json"),
                    "motion_plan": plan.model_dump(mode="json"),
                    "resolved_timing": resolved.model_dump(mode="json"),
                    "scene_duration": scene_duration,
                }
            ),
            action="learnflow_create",
        )
        run_id = str(created["run_id"])
        compiled_response = _parse_capability(
            run({"run_id": run_id}),
            action="learnflow_run",
        )
        if not compiled_response.get("layout_feasible"):
            raise ProductionOutputGateError(
                f"scene {scene.scene_id} production layout is infeasible"
            )
        rendered = _parse_capability(
            render({"run_id": run_id}),
            action="learnflow_render",
        )

        reported = Path(str(rendered["output"]))
        source_path = reported if reported.is_absolute() else repo_root / reported
        if not source_path.is_file():
            raise ProductionOutputGateError(
                f"scene {scene.scene_id} render output missing: {source_path}"
            )
        local_scene = scene_dir / f"{index:03d}.mp4"
        shutil.copy2(source_path, local_scene)
        artifact = RenderedArtifact(
            artifact_id=str(rendered["artifact_id"]),
            kind=RenderArtifactKind.SCENE,
            path=str(local_scene),
            duration=float(rendered["duration"]),
            width=int(rendered["width"]),
            height=int(rendered["height"]),
            fps=int(rendered["fps"]),
            frame_count=int(rendered["frame_count"]),
            frame_digest=str(rendered["frame_digest"]),
            source_hash=str(rendered["source_hash"]),
        )

        # Edge TTS SentenceBoundary events are useful provenance, but providers
        # may emit overlapping sentence intervals. Frozen Core intentionally
        # rejects overlapping subtitle cues, so learner-visible subtitles are
        # derived from the accepted ScriptSegment boundaries and measured audio
        # duration via the deterministic beat map. Persist raw provider cues for
        # audit rather than silently trusting them as presentation timing.
        _atomic_json(
            audio_dir / f"{index:03d}.provider_cues.json",
            [
                cue.model_dump(mode="json")
                for cue in narration.subtitle_cues
            ],
        )
        # Isolated one-shot paid V2 evaluation: use provider sentence timing,
        # not one giant ScriptSegment caption per scene. Fail closed on unsafe
        # text or geometry; the frozen Core and other routes remain unchanged.
        paid_caption_policy = (
            os.environ.get("LEARNFLOW_PAID_PILOT_MODEL") == "openai/gpt-6-luna"
            and os.environ.get("GITHUB_REF")
            == "refs/heads/chatgpt/live-v2d-gpt6-luna-paid-pilot"
        )
        cues: list[SubtitleRenderCue] = []
        if paid_caption_policy:
            from lesson_pipeline.subtitle_policy import (
                check_safe_subtitle_band,
                normalize_tts_subtitles,
            )
            check_safe_subtitle_band(layout)
            try:
                pages = normalize_tts_subtitles(
                    narration.subtitle_cues,
                    audio_duration=narration.duration_seconds,
                    scene_duration=artifact.duration,
                )
            except ValueError as exc:
                raise ProductionOutputGateError(
                    f"unsafe timed subtitle cues for {scene.scene_id}: {exc}"
                ) from exc
            cues.extend(
                SubtitleRenderCue(
                    start_seconds=page.start_seconds,
                    end_seconds=page.end_seconds,
                    text=page.text,
                )
                for page in pages
            )
        else:
            for phrase_index, phrase in enumerate(beat_map.phrases):
                text = (
                    subtitle_texts[phrase_index]
                    if phrase_index < len(subtitle_texts)
                    else phrase.text
                )
                end = min(float(phrase.end), artifact.duration)
                start = min(float(phrase.start), max(0.0, end - 1e-3))
                if end > start + 1e-4:
                    cues.append(
                        SubtitleRenderCue(
                            start_seconds=start,
                            end_seconds=end,
                            text=text,
                        )
                    )

        scene_artifacts.append(artifact)
        scene_layouts.append(layout)
        scene_audio.append(narration)
        scene_subtitles.append(tuple(cues))
        scene_motion_counts.append(len(compiled.events))
        scene_reports.append(
            {
                "scene_id": scene.scene_id,
                "capability_run_id": run_id,
                "narration_provider": narration.provider,
                "audio_duration_seconds": narration.duration_seconds,
                "render_duration_seconds": artifact.duration,
                "motion_event_count": len(compiled.events),
                "subtitle_cue_count": len(cues),
                "provider_subtitle_cue_count": len(narration.subtitle_cues),
                "subtitle_timing_source": (
                    "tts_sentence_short_pages_v1" if paid_caption_policy
                    else "deterministic_script_segments"
                ),
                "layout_intent": graph.layout_intent.type.value,
            }
        )

    transitions: list[RenderedArtifact] = []
    transition_plans: list[Any] = []
    for index in range(len(result.scenegraphs) - 1):
        plan = compile_inter_scene_transition(
            scene_layouts[index],
            scene_layouts[index + 1],
            registry,
            from_scene_graph=result.scenegraphs[index],
            to_scene_graph=result.scenegraphs[index + 1],
            duration=TRANSITION_DURATION_SECONDS,
        )
        transition_path = transition_dir / f"{index + 1:03d}.mp4"
        fallback_used = False
        try:
            artifact = render_transition_video(
                result.scenegraphs[index],
                scene_layouts[index],
                result.scenegraphs[index + 1],
                scene_layouts[index + 1],
                plan,
                transition_path,
                profile=profile,
            )
        except RenderInvalidInputError as exc:
            message = str(exc)
            if "does not fit solved LayoutGraph box" not in message:
                raise
            # Persistent MOVE interpolates between endpoint boxes. A text node can
            # fit both accepted endpoint layouts yet become unreadable at an
            # intermediate rect. Do not weaken Core text-fit validation. Recompile
            # only this transition against the official FADE-only capability set.
            plan = compile_inter_scene_transition(
                scene_layouts[index],
                scene_layouts[index + 1],
                registry,
                from_scene_graph=result.scenegraphs[index],
                to_scene_graph=result.scenegraphs[index + 1],
                duration=TRANSITION_DURATION_SECONDS,
                capabilities=MINIMAL_TRANSITION_CAPABILITIES,
            )
            fallback_used = True
            artifact = render_transition_video(
                result.scenegraphs[index],
                scene_layouts[index],
                result.scenegraphs[index + 1],
                scene_layouts[index + 1],
                plan,
                transition_path,
                profile=profile,
            )
        transition_payload = plan.model_dump(mode="json")
        transition_payload["production_render_fallback"] = (
            "FADE_FOR_INTERPOLATION_TEXT_FIT" if fallback_used else None
        )
        _atomic_json(
            transition_dir / f"{index + 1:03d}.json",
            transition_payload,
        )
        transitions.append(artifact)
        transition_plans.append(plan)

    ordered_video: list[RenderedArtifact] = []
    for index, scene_artifact in enumerate(scene_artifacts):
        ordered_video.append(scene_artifact)
        if index < len(transitions):
            ordered_video.append(transitions[index])

    video_only = assemble_video(ordered_video, root / "final.video.mp4")

    audio_entries: list[tuple[str, Path | float]] = []
    global_cues: list[SubtitleRenderCue] = []
    video_cursor = 0.0
    for index, (artifact, narration, cues) in enumerate(
        zip(scene_artifacts, scene_audio, scene_subtitles, strict=True)
    ):
        audio_entries.append(("file", narration.path))
        tail = max(0.0, artifact.duration - narration.duration_seconds)
        if tail > 1e-4:
            audio_entries.append(("silence", tail))
        for cue in cues:
            global_cues.append(
                SubtitleRenderCue(
                    start_seconds=video_cursor + cue.start_seconds,
                    end_seconds=min(
                        video_cursor + cue.end_seconds,
                        video_cursor + artifact.duration,
                    ),
                    text=cue.text,
                )
            )
        video_cursor += artifact.duration
        if index < len(transitions):
            audio_entries.append(("silence", transitions[index].duration))
            video_cursor += transitions[index].duration

    lesson_audio_path = audio_dir / "lesson.m4a"
    assembled_audio_duration = _concat_audio_sequence(
        audio_entries,
        lesson_audio_path,
    )
    av_artifact = mux_audio_track(
        video_only,
        lesson_audio_path,
        root / "final.av.mp4",
    )
    # The frozen implementation buffers the entire decoded RGB stream in RAM
    # solely for SHA-256 (many GiB at 1080p/30fps). In this isolated GPT-6
    # Luna experiment use a bounded reader while retaining exact SHA-256,
    # frozen cue validation, and subtitle burn-in behavior.
    paid_streaming_digest = (
        os.environ.get("LEARNFLOW_PAID_PILOT_MODEL") == "openai/gpt-6-luna"
        and os.environ.get("GITHUB_REF")
        == "refs/heads/chatgpt/live-v2d-gpt6-luna-paid-pilot"
    )
    if paid_streaming_digest:
        from lesson_pipeline.subtitle_render_adapter import burn_short_subtitles

        final_artifact = burn_short_subtitles(
            av_artifact,
            global_cues,
            root / "final.mp4",
        )
    else:
        final_artifact = burn_subtitles(
            av_artifact,
            global_cues,
            root / "final.mp4",
        )

    stream_types = _probe_stream_types(final_artifact.path)
    target_duration = result.learning_brief.target_duration_minutes * 60.0
    duration_ratio = final_artifact.duration / target_duration
    spoken_words = sum(
        len(segment.spoken_text.split())
        for segment in result.lesson_script.segments
    )
    target_words = target_duration / 60.0 * 145.0

    checks = {
        "video_stream_present": "video" in stream_types,
        "audio_stream_present": "audio" in stream_types,
        "duration_near_target": (
            MIN_TARGET_DURATION_RATIO
            <= duration_ratio
            <= MAX_TARGET_DURATION_RATIO
        ),
        "not_smoke_length": final_artifact.duration >= max(30.0, target_duration * 0.5),
        "motion_every_scene": all(count > 0 for count in scene_motion_counts),
        "transition_coverage": len(transitions) == max(0, len(scene_artifacts) - 1),
        "subtitle_coverage": len(global_cues) >= len(result.lesson_script.segments),
        "subtitle_short_pages": (
            not paid_streaming_digest or (
                len(global_cues) > len(result.lesson_script.segments)
                and all(len(cue.text) <= 72 and len(cue.text.split()) <= 12 for cue in global_cues)
            )
        ),
        "audio_timeline_covers_video": (
            abs(assembled_audio_duration - final_artifact.duration) <= 0.35
        ),
    }
    passed = all(checks.values())
    report = {
        "schema_version": "production-live-v2d-gate-v1",
        "passed": passed,
        "checks": checks,
        "target_duration_seconds": target_duration,
        "final_duration_seconds": final_artifact.duration,
        "duration_ratio": duration_ratio,
        "spoken_word_count": spoken_words,
        "target_word_count_at_145_wpm": target_words,
        "stream_types": sorted(stream_types),
        "scene_count": len(scene_artifacts),
        "transition_count": len(transitions),
        "transition_fade_fallback_count": sum(
            1
            for plan in transition_plans
            if any(
                item.fallback_reason == "BACKEND_UNSUPPORTED_MOVE"
                for item in plan.persistent_objects
            )
        ),
        "persistent_transition_count": sum(
            len(plan.persistent_objects) for plan in transition_plans
        ),
        "motion_event_count": sum(scene_motion_counts),
        "subtitle_cue_count": len(global_cues),
        "tts_request_count": len(scene_audio),
        "assembled_audio_duration_seconds": assembled_audio_duration,
        "scene_reports": scene_reports,
        "final_video": str(final_artifact.path),
    }
    _atomic_json(verification_dir / "production_output_gate.json", report)

    render_manifest_path = root / "render_manifest.json"
    if render_manifest_path.is_file():
        current = json.loads(render_manifest_path.read_text(encoding="utf-8"))
    else:
        current = {"run_id": result.run_id}
    current["final_video"] = final_artifact.model_dump(mode="json")
    current["production_media"] = report
    _atomic_json(render_manifest_path, current)
    _refresh_artifact_manifest(root, Path(final_artifact.path))

    if not passed:
        failed = [name for name, ok in checks.items() if not ok]
        raise ProductionOutputGateError(
            "production live V2D output gate failed: " + ", ".join(failed)
        )

    return ProductionMediaResult(
        final_video=final_artifact,
        report=report,
    )
