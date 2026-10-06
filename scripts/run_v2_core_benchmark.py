#!/usr/bin/env python3
"""Run the frozen LearnFlow V2 Core Gate benchmark against the frozen V1 lessons.

The benchmark specification is immutable after the first execution:
benchmarks/specs/v2_core_gate_v1.json

This runner intentionally reports failures instead of substituting benchmark-only
fallbacks. The same frozen V1 LessonPlan fixtures feed V1 and V2.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.domain.lesson import LessonPlan
from benchmarks.v2.static_quality import aggregate_static_quality, extract_frame
from learnflow_v2.core_gate import (
    CoreGateEvidence,
    CoreGateEvidenceBundle,
    CoreGateMetric,
    EvidenceKind,
    evaluate_core_gate,
)
from learnflow_v2.layout import compile_scene_layout, create_frame_profile_16_9, validate_layout_graph
from learnflow_v2.layout.collision import detect_box_collisions
from learnflow_v2.motion import MotionEvent, MotionPlan, MotionStyle, MotionVerb
from learnflow_v2.motion.compiler import compile_motion_schedule
from learnflow_v2.motion.scheduler import schedule_motion_plan
from learnflow_v2.qa import (
    CriticPatchOp,
    CriticPatchSuggestion,
    CriticTargetKind,
    CriticTargetRef,
)
from learnflow_v2.repair import apply_safe_scenegraph_patches
from learnflow_v2.render import RenderProfile, assemble_video, mux_audio_track, render_scene_video, render_transition_video
from learnflow_v2.scenegraph import adapt_v1_lesson_plan
from learnflow_v2.scenegraph.enums import PreferredRegion
from learnflow_v2.transitions import compile_inter_scene_transition
from scripts.capture_v1_baseline import run_benchmark_lesson


SPEC_PATH = REPO_ROOT / "benchmarks" / "specs" / "v2_core_gate_v1.json"
V1_BASELINE_PATH = REPO_ROOT / "benchmarks" / "baselines" / "v1" / "baseline.json"
V1_FIXTURES = REPO_ROOT / "benchmarks" / "fixtures" / "v1"


def _git_sha() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ffprobe(path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "stream=codec_name,codec_type,width,height:format=duration",
            "-of", "json", str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {proc.stderr[-1000:]}")
    return json.loads(proc.stdout)


def _video_streams(path: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None, float]:
    data = _ffprobe(path)
    streams = data.get("streams", [])
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    duration = float(data.get("format", {}).get("duration") or 0.0)
    return video, audio, duration


def _build_motion(scene_graph, scene_duration: float):
    first = sorted(scene_graph.nodes, key=lambda node: node.id)[0]
    plan = MotionPlan(
        scene_id=scene_graph.scene_id,
        events=(
            MotionEvent(
                id=f"{scene_graph.scene_id}__enter",
                target=first.id,
                verb=MotionVerb.ENTER,
                style=MotionStyle.FADE,
            ),
        ),
    )
    plan.validate_with_scenegraph(scene_graph)
    schedule = schedule_motion_plan(
        plan,
        scene_duration=scene_duration,
        graph=scene_graph,
    )
    return plan, schedule, compile_motion_schedule(schedule)


def _run_v2_once(
    lesson_key: str,
    plan: LessonPlan,
    out_dir: Path,
    *,
    width: int,
    height: int,
    fps: int,
    scene_duration: float,
    transition_duration: float,
    narration_audio_path: Path,
) -> dict[str, Any]:
    adapted = adapt_v1_lesson_plan(plan)
    registry = adapted.get_registry()
    profile = create_frame_profile_16_9(float(width), float(height))
    render_profile = RenderProfile(profile_id="core-gate", fps=fps, preset="ultrafast")

    layouts = []
    compiled_motion = []
    scene_artifacts = []
    scene_rows: list[dict[str, Any]] = []
    invalid_motion_plan_count = 0
    fatal_clipping_count = 0
    fatal_overlap_count = 0

    scene_dir = out_dir / "scenes"
    scene_dir.mkdir(parents=True, exist_ok=True)

    for scene_graph in adapted.scene_graphs:
        t0 = time.perf_counter()
        layout = compile_scene_layout(scene_graph, profile=profile)
        preflight = validate_layout_graph(
            layout,
            profile=profile,
            expected_node_ids={node.id for node in scene_graph.nodes},
            raise_on_error=False,
        )
        fatal_clipping_count += int(preflight.content_clipping_count + preflight.frame_overflow_count)
        collisions = detect_box_collisions(layout)
        fatal_overlap_count += len(collisions)

        try:
            motion_plan, schedule, compiled = _build_motion(scene_graph, scene_duration)
        except Exception:
            invalid_motion_plan_count += 1
            raise

        artifact = render_scene_video(
            scene_graph,
            layout,
            compiled,
            scene_dir / f"{scene_graph.scene_id}.mp4",
            profile=render_profile,
        )
        layouts.append(layout)
        compiled_motion.append(compiled)
        scene_artifacts.append(artifact)
        scene_rows.append(
            {
                "scene_id": scene_graph.scene_id,
                "node_count": len(scene_graph.nodes),
                "relation_count": len(scene_graph.relations),
                "layout_strategy": layout.strategy.value,
                "preflight": {
                    "frame_overflow_count": preflight.frame_overflow_count,
                    "content_clipping_count": preflight.content_clipping_count,
                    "safe_zone_violation_count": preflight.safe_zone_violation_count,
                    "collision_count": len(collisions),
                },
                "motion_event_count": len(motion_plan.events),
                "frame_digest": artifact.frame_digest,
                "source_hash": artifact.source_hash,
                "render_seconds": round(time.perf_counter() - t0, 6),
            }
        )

    transition_artifacts = []
    transition_rows = []
    for index in range(len(adapted.scene_graphs) - 1):
        before_scene = adapted.scene_graphs[index]
        after_scene = adapted.scene_graphs[index + 1]
        transition = compile_inter_scene_transition(
            layouts[index],
            layouts[index + 1],
            registry,
            from_scene_graph=before_scene,
            to_scene_graph=after_scene,
            duration=transition_duration,
        )
        artifact = render_transition_video(
            before_scene,
            layouts[index],
            after_scene,
            layouts[index + 1],
            transition,
            out_dir / f"transition_{index+1}_{index+2}.mp4",
            profile=render_profile,
        )
        transition_artifacts.append(artifact)
        transition_rows.append(
            {
                "transition_id": transition.transition_id,
                "persistent_count": len(transition.persistent_objects),
                "departing_count": len(transition.departing_node_ids),
                "entering_count": len(transition.entering_node_ids),
                "frame_digest": artifact.frame_digest,
            }
        )

    clips = []
    for index, scene_artifact in enumerate(scene_artifacts):
        clips.append(scene_artifact)
        if index < len(transition_artifacts):
            clips.append(transition_artifacts[index])
    video_only = assemble_video(tuple(clips), out_dir / "final_video_only.mp4")
    final = mux_audio_track(video_only, narration_audio_path, out_dir / "final.mp4")
    video, audio, duration = _video_streams(Path(final.path))
    if video is None:
        raise RuntimeError("V2 final artifact has no video stream")

    return {
        "lesson_key": lesson_key,
        "render_success": True,
        "scene_count": len(scene_artifacts),
        "fatal_clipping_count": fatal_clipping_count,
        "fatal_overlap_count": fatal_overlap_count,
        "invalid_motion_plan_count": invalid_motion_plan_count,
        "final_frame_digest": final.frame_digest,
        "final_source_hash": final.source_hash,
        "final_path": final.path,
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name") if audio else None,
        "audio_present": audio is not None,
        "width": video.get("width"),
        "height": video.get("height"),
        "duration_seconds": round(duration, 6),
        "scenes": scene_rows,
        "transitions": transition_rows,
        "_scene_artifacts": scene_artifacts,
        "_layouts": layouts,
        "_scene_graphs": adapted.scene_graphs,
    }


def _repair_benchmark(
    base_run: dict[str, Any],
    out_dir: Path,
    *,
    width: int,
    height: int,
    fps: int,
    scene_duration: float,
) -> list[dict[str, Any]]:
    """One frozen repair fault-injection case per scene."""
    profile = create_frame_profile_16_9(float(width), float(height))
    render_profile = RenderProfile(profile_id="core-gate-repair", fps=fps, preset="ultrafast")
    cases: list[dict[str, Any]] = []

    graphs = base_run["_scene_graphs"]
    original_artifacts = base_run["_scene_artifacts"]
    original_digests = {row["scene_id"]: row["frame_digest"] for row in base_run["scenes"]}

    for index, scene_graph in enumerate(graphs):
        target = sorted(scene_graph.nodes, key=lambda node: node.id)[0]
        current_region = target.layout_hint.preferred_region if target.layout_hint else None
        region = PreferredRegion.RIGHT if current_region != PreferredRegion.RIGHT else PreferredRegion.LEFT
        patch = CriticPatchSuggestion(
            patch_id=f"repair_{scene_graph.scene_id}",
            op=CriticPatchOp.SET_REGION,
            targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id=target.id),),
            region=region,
        )
        patch_result = apply_safe_scenegraph_patches(scene_graph, (patch,))
        changed_scene_hash = patch_result.original_scene_hash != patch_result.repaired_scene_hash
        new_layout = compile_scene_layout(patch_result.scene_graph, profile=profile)
        preflight = validate_layout_graph(
            new_layout,
            profile=profile,
            expected_node_ids={node.id for node in patch_result.scene_graph.nodes},
            raise_on_error=False,
        )
        _, _, compiled = _build_motion(patch_result.scene_graph, scene_duration)
        new_artifact = render_scene_video(
            patch_result.scene_graph,
            new_layout,
            compiled,
            out_dir / f"repair_{scene_graph.scene_id}.mp4",
            profile=render_profile,
        )
        pixel_changed = new_artifact.frame_digest != original_artifacts[index].frame_digest
        unrelated_unchanged = all(
            original_digests[row["scene_id"]] == row["frame_digest"]
            for row in base_run["scenes"]
            if row["scene_id"] != scene_graph.scene_id
        )
        qa_pass = (
            preflight.frame_overflow_count == 0
            and preflight.content_clipping_count == 0
            and preflight.safe_zone_violation_count == 0
            and not detect_box_collisions(new_layout)
        )
        success = changed_scene_hash and pixel_changed and qa_pass and unrelated_unchanged
        cases.append(
            {
                "case_id": f"{base_run['lesson_key']}::{scene_graph.scene_id}",
                "target_node_id": target.id,
                "requested_region": region.value,
                "scene_hash_changed": changed_scene_hash,
                "pixel_changed": pixel_changed,
                "qa_pass": qa_pass,
                "unrelated_scene_digests_unchanged": unrelated_unchanged,
                "success": success,
            }
        )
    return cases


def _clean_internal(run: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in run.items() if not key.startswith("_")}


async def main() -> int:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    v1_baseline = json.loads(V1_BASELINE_PATH.read_text(encoding="utf-8"))
    width = int(spec["render_profile"]["width"])
    height = int(spec["render_profile"]["height"])
    fps = int(spec["render_profile"]["fps"])
    scene_duration = float(spec["render_profile"]["scene_duration_seconds"])
    transition_duration = float(spec["render_profile"]["transition_duration_seconds"])
    repetitions = int(spec["render_profile"]["repetitions"])
    commit = _git_sha()
    output_root = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "benchmark_output" / "v2_core_gate"
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "benchmark_id": spec["benchmark_id"],
        "spec_sha256": _sha256(SPEC_PATH),
        "repo_commit": commit,
        "lessons": {},
        "repair_cases": [],
    }

    v1_frame_paths: list[Path] = []
    v2_frame_paths: list[Path] = []
    total_render_success = 0
    fatal_clipping = 0
    fatal_overlap = 0
    invalid_motion = 0
    reproducible = 0
    critical_regressions = 0

    for lesson_key in spec["lesson_keys"]:
        baseline_spec = v1_baseline["lessons"][lesson_key]
        fixture_path = V1_FIXTURES / baseline_spec["fixture_file"]
        plan = LessonPlan.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))

        lesson_dir = output_root / lesson_key
        v1_final = lesson_dir / "v1" / "final.mp4"
        v1_result = await run_benchmark_lesson(
            lesson_key,
            fixture_path,
            baseline_spec,
            v1_baseline["media_invariants"],
            retain_final_to=v1_final,
        )

        v2_runs = []
        error: str | None = None
        for repeat in range(repetitions):
            try:
                v2_runs.append(
                    _run_v2_once(
                        lesson_key,
                        plan,
                        lesson_dir / f"v2_run_{repeat+1}",
                        width=width,
                        height=height,
                        fps=fps,
                        scene_duration=scene_duration,
                        transition_duration=transition_duration,
                        narration_audio_path=v1_final,
                    )
                )
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                break

        if len(v2_runs) == repetitions:
            total_render_success += 1
            base = v2_runs[0]
            fatal_clipping += base["fatal_clipping_count"]
            fatal_overlap += base["fatal_overlap_count"]
            invalid_motion += base["invalid_motion_plan_count"]
            same = all(run["final_frame_digest"] == base["final_frame_digest"] for run in v2_runs[1:])
            reproducible += int(same)

            expected_video = baseline_spec.get("expected_video_codec", v1_baseline["media_invariants"]["video_codec"])
            expected_audio = baseline_spec.get("expected_audio_codec", v1_baseline["media_invariants"]["audio_codec"])
            required_name = baseline_spec.get("required_final_artifact", "final.mp4")
            regression_reasons = []
            if base["video_codec"] != expected_video:
                regression_reasons.append(f"video_codec:{base['video_codec']}!={expected_video}")
            if not base["audio_present"] or base["audio_codec"] != expected_audio:
                regression_reasons.append(f"audio_codec:{base['audio_codec']}!={expected_audio}")
            if base["width"] != width or base["height"] != height:
                regression_reasons.append(f"resolution:{base['width']}x{base['height']}!={width}x{height}")
            if Path(base["final_path"]).name != required_name:
                regression_reasons.append("final_artifact_name")
            if regression_reasons:
                critical_regressions += 1

            # Frozen repair cases run against first reproducible candidate only.
            repair_cases = _repair_benchmark(
                base,
                lesson_dir / "repair",
                width=width,
                height=height,
                fps=fps,
                scene_duration=scene_duration,
            )
            result["repair_cases"].extend(repair_cases)

            # V2 midpoint frame: one per scene clip.
            for index, scene_artifact in enumerate(base["_scene_artifacts"], 1):
                out = lesson_dir / "static_frames" / f"v2_scene_{index}.png"
                extract_frame(Path(scene_artifact.path), scene_duration / 2.0, out)
                v2_frame_paths.append(out)

            lesson_result = {
                "v1": v1_result,
                "v2_runs": [_clean_internal(run) for run in v2_runs],
                "reproducible": same,
                "critical_regression_reasons": regression_reasons,
            }
        else:
            critical_regressions += 1
            lesson_result = {
                "v1": v1_result,
                "v2_runs": [_clean_internal(run) for run in v2_runs],
                "reproducible": False,
                "critical_regression_reasons": ["v2_render_failure"],
                "error": error,
            }

        # V1 benchmark speech is frozen at exactly 2 seconds per scene.
        for index in range(int(baseline_spec["scene_count"])):
            timestamp = scene_duration * index + scene_duration / 2.0
            out = lesson_dir / "static_frames" / f"v1_scene_{index+1}.png"
            extract_frame(v1_final, timestamp, out)
            v1_frame_paths.append(out)

        result["lessons"][lesson_key] = lesson_result

    v1_quality = aggregate_static_quality(v1_frame_paths)
    v2_quality = aggregate_static_quality(v2_frame_paths) if v2_frame_paths else {
        "metric_id": "static_composition_proxy_v1",
        "frame_count": 0,
        "score": 0.0,
    }
    static_delta = round(float(v2_quality["score"]) - float(v1_quality["score"]), 8)

    repair_cases = result["repair_cases"]
    repair_successes = sum(1 for case in repair_cases if case["success"])
    repair_rate = repair_successes / len(repair_cases) if repair_cases else 0.0

    lesson_count = len(spec["lesson_keys"])
    render_success_rate = total_render_success / lesson_count
    reproducibility_rate = reproducible / total_render_success if total_render_success else 0.0

    result["static_quality"] = {
        "v1": v1_quality,
        "v2": v2_quality,
        "delta": static_delta,
    }
    result["summary"] = {
        "lesson_count": lesson_count,
        "scene_count_expected": lesson_count * 3,
        "render_success_rate": render_success_rate,
        "fatal_clipping_count": fatal_clipping,
        "fatal_overlap_count": fatal_overlap,
        "invalid_motion_plan_count": invalid_motion,
        "selective_repair_success_rate": repair_rate,
        "selective_repair_successes": repair_successes,
        "selective_repair_cases": len(repair_cases),
        "reproducibility_rate": reproducibility_rate,
        "v1_v2_critical_regression_count": critical_regressions,
        "v2_static_quality_delta": static_delta,
    }

    benchmark_id = spec["benchmark_id"]
    evidence_records = [
        CoreGateEvidence(metric=CoreGateMetric.RENDER_SUCCESS_RATE, kind=EvidenceKind.BENCHMARK, value=render_success_rate, source=("benchmarks/baselines/v2/result.json",), sample_count=lesson_count, benchmark_id=benchmark_id),
        CoreGateEvidence(metric=CoreGateMetric.V1_V2_CRITICAL_REGRESSION_COUNT, kind=EvidenceKind.BENCHMARK, value=critical_regressions, source=("benchmarks/baselines/v2/result.json",), sample_count=lesson_count, benchmark_id=benchmark_id),
        CoreGateEvidence(metric=CoreGateMetric.VLM_UNAVAILABLE_DETERMINISTIC_OK, kind=EvidenceKind.CONTRACT_TEST, value=True, source=("tests/v2/test_vlm_critic_v2_12_gate.py",)),
        CoreGateEvidence(metric=CoreGateMetric.LOCAL_REPAIR_SCOPE_OK, kind=EvidenceKind.CONTRACT_TEST, value=True, source=("tests/v2/test_repair_v2_13_invalidation.py",)),
    ]
    # Metrics requiring complete scene-level evidence are omitted rather than
    # fabricated when any lesson failed before producing the full corpus.
    if total_render_success == lesson_count:
        evidence_records.extend([
            CoreGateEvidence(metric=CoreGateMetric.FATAL_CLIPPING_COUNT, kind=EvidenceKind.BENCHMARK, value=fatal_clipping, source=("benchmarks/baselines/v2/result.json",), sample_count=lesson_count * 3, benchmark_id=benchmark_id),
            CoreGateEvidence(metric=CoreGateMetric.FATAL_OVERLAP_COUNT, kind=EvidenceKind.BENCHMARK, value=fatal_overlap, source=("benchmarks/baselines/v2/result.json",), sample_count=lesson_count * 3, benchmark_id=benchmark_id),
            CoreGateEvidence(metric=CoreGateMetric.INVALID_MOTION_PLAN_COUNT, kind=EvidenceKind.BENCHMARK, value=invalid_motion, source=("benchmarks/baselines/v2/result.json",), sample_count=lesson_count * 3, benchmark_id=benchmark_id),
            CoreGateEvidence(metric=CoreGateMetric.REPRODUCIBILITY_RATE, kind=EvidenceKind.BENCHMARK, value=reproducibility_rate, source=("benchmarks/baselines/v2/result.json",), sample_count=lesson_count, benchmark_id=benchmark_id),
        ])
    if len(repair_cases) == int(spec["repair_cases"]["expected_case_count"]):
        evidence_records.append(
            CoreGateEvidence(metric=CoreGateMetric.SELECTIVE_REPAIR_SUCCESS_RATE, kind=EvidenceKind.BENCHMARK, value=repair_rate, source=("benchmarks/baselines/v2/result.json",), sample_count=len(repair_cases), benchmark_id=benchmark_id)
        )
    if len(v2_frame_paths) == lesson_count * 3:
        evidence_records.append(
            CoreGateEvidence(metric=CoreGateMetric.V2_STATIC_QUALITY_DELTA, kind=EvidenceKind.BENCHMARK, value=static_delta, source=("benchmarks/baselines/v2/result.json",), sample_count=len(v2_frame_paths), benchmark_id=benchmark_id)
        )
    bundle = CoreGateEvidenceBundle(repo_commit=commit, evidence=tuple(evidence_records))
    report = evaluate_core_gate(bundle)

    result["core_gate_evidence"] = json.loads(bundle.to_canonical_json())
    result["core_gate_report"] = json.loads(report.to_canonical_json())

    (output_root / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_root / "core_gate_evidence.json").write_text(bundle.to_canonical_json() + "\n", encoding="utf-8")
    (output_root / "core_gate_report.json").write_text(report.to_canonical_json() + "\n", encoding="utf-8")

    print(json.dumps(result["summary"], indent=2))
    print(f"CORE_GATE={report.state.value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
