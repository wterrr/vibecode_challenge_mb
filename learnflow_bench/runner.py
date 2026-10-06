"""Executable LearnFlowBench tracks.

Core ablation uses the exact frozen V1 LessonPlan fixtures for V1/V2A/V2B/V2C.
V2D uses the accepted typed full-pipeline fixture replay. The two tracks are
reported separately and never treated as an apples-to-apples quality ranking.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

from app.domain.lesson import LessonPlan
from benchmarks.v2.static_quality import aggregate_static_quality, extract_frame
from learnflow_v2.layout import compile_scene_layout, create_frame_profile_16_9, validate_layout_graph
from learnflow_v2.layout.collision import detect_box_collisions
from learnflow_v2.motion.compiler import CompiledMotionArtifact
from learnflow_v2.render import (
    RenderProfile,
    SubtitleRenderCue,
    assemble_video,
    burn_subtitles,
    mux_audio_track,
    render_scene_video,
    render_transition_video,
)
from learnflow_v2.scenegraph import adapt_v1_lesson_plan
from learnflow_v2.transitions import compile_inter_scene_transition
from lesson_pipeline import CapabilityCoreGateway, STAGE_ORDER, run_lesson_pipeline
from scripts.capture_v1_baseline import run_benchmark_lesson
from scripts.run_v2_core_benchmark import (
    _build_motion,
    _repair_benchmark,
    _scene_qa_report,
    _video_streams,
)
from scripts.verify_lesson_pipeline import _load_plugin, build_fixture_runner

from .corpus import CORE_ABLATION_PATH, core_fixture_sha256, corpus_sha256, load_corpus
from .models import (
    BenchmarkCandidateId,
    BenchmarkCandidateResult,
    BenchmarkMetricCategory,
    BenchmarkObservation,
    BenchmarkReport,
    MeasurementState,
)

ROOT = Path(__file__).resolve().parents[1]
V1_BASELINE_PATH = ROOT / "benchmarks" / "baselines" / "v1" / "baseline.json"
V1_FIXTURE_DIR = ROOT / "benchmarks" / "fixtures" / "v1"


def _sha256_bytes(parts: list[bytes]) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return digest.hexdigest()


def _source_commit() -> str:
    value = os.environ.get("BENCHMARK_SOURCE_COMMIT", "").strip().lower()
    if not value:
        import subprocess
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        value = proc.stdout.strip().lower()
    if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise RuntimeError("benchmark source commit must be a 40-character git SHA")
    return value


def full_system_fixture_sha256() -> str:
    paths = [
        ROOT / "scripts" / "verify_lesson_pipeline.py",
        ROOT / "scripts" / "verify_script_agent.py",
        ROOT / "scripts" / "verify_visual_director.py",
    ]
    return _sha256_bytes([path.read_bytes() for path in paths])


def _obs(
    metric_id: str,
    category: BenchmarkMetricCategory,
    *,
    value: float | int | bool | str | None = None,
    unit: str | None = None,
    sample_count: int | None = None,
    evidence: tuple[str, ...] = (),
    state: MeasurementState = MeasurementState.MEASURED,
    notes: str = "",
) -> BenchmarkObservation:
    return BenchmarkObservation(
        metric_id=metric_id,
        category=category,
        state=state,
        value=value,
        unit=unit,
        sample_count=sample_count,
        evidence=evidence,
        notes=notes,
    )


def _unmeasured(metric_id: str, category: BenchmarkMetricCategory, notes: str) -> BenchmarkObservation:
    return _obs(
        metric_id,
        category,
        state=MeasurementState.UNMEASURED,
        value=None,
        evidence=(),
        notes=notes,
    )


def _not_applicable(metric_id: str, category: BenchmarkMetricCategory, notes: str) -> BenchmarkObservation:
    return _obs(
        metric_id,
        category,
        state=MeasurementState.NOT_APPLICABLE,
        value=None,
        evidence=(),
        notes=notes,
    )


def _candidate_static_frames(
    artifacts: list[Any],
    *,
    scene_duration: float,
    output_dir: Path,
    prefix: str,
) -> list[Path]:
    frames: list[Path] = []
    for index, artifact in enumerate(artifacts, 1):
        path = output_dir / f"{prefix}_{index:02d}.png"
        extract_frame(Path(artifact.path), scene_duration / 2.0, path)
        frames.append(path)
    return frames


def _subtitle_cues(plan: LessonPlan, scene_duration: float, transition_duration: float) -> tuple[SubtitleRenderCue, ...]:
    cues: list[SubtitleRenderCue] = []
    cursor = 0.0
    for scene_index, scene in enumerate(plan.scenes):
        cues.append(
            SubtitleRenderCue(
                start_seconds=cursor,
                end_seconds=cursor + scene_duration,
                text=(scene.narration[:40] if scene.narration else "Lesson narration"),
            )
        )
        cursor += scene_duration
        if scene_index < len(plan.scenes) - 1:
            cursor += transition_duration
    return tuple(cues)


def _run_v2_candidate(
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
    motion_enabled: bool,
    transitions_enabled: bool,
    qa_enabled: bool,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    adapted = adapt_v1_lesson_plan(plan)
    registry = adapted.get_registry()
    frame_profile = create_frame_profile_16_9(float(width), float(height))
    render_profile = RenderProfile(profile_id=f"learnflowbench-{lesson_key}", fps=fps, preset="ultrafast")
    out_dir.mkdir(parents=True, exist_ok=True)
    scene_dir = out_dir / "scenes"
    scene_dir.mkdir(parents=True, exist_ok=True)

    layouts: list[Any] = []
    scene_artifacts: list[Any] = []
    fatal_clipping = 0
    fatal_overlap = 0
    invalid_motion = 0
    qa_passes = 0
    motion_events = 0
    scene_rows: list[dict[str, Any]] = []

    for graph in adapted.scene_graphs:
        layout = compile_scene_layout(graph, profile=frame_profile)
        preflight = validate_layout_graph(
            layout,
            profile=frame_profile,
            expected_node_ids={node.id for node in graph.nodes},
            raise_on_error=False,
        )
        fatal_clipping += int(preflight.content_clipping_count + preflight.frame_overflow_count)
        fatal_overlap += len(detect_box_collisions(layout))

        if motion_enabled:
            try:
                motion_plan, _schedule, compiled = _build_motion(graph, scene_duration)
            except Exception:
                invalid_motion += 1
                raise
            motion_events += len(motion_plan.events)
        else:
            compiled = CompiledMotionArtifact(
                scene_id=graph.scene_id,
                scene_duration=scene_duration,
                events=(),
                tracks=(),
            )

        artifact = render_scene_video(
            graph,
            layout,
            compiled,
            scene_dir / f"{graph.scene_id}.mp4",
            profile=render_profile,
        )
        if qa_enabled:
            qa_report = _scene_qa_report(graph, layout, compiled, artifact, frame_profile)
            qa_passes += int(qa_report.passed)
            if not qa_report.passed:
                raise RuntimeError(
                    f"LearnFlowBench deterministic QA failed for {lesson_key}/{graph.scene_id}: "
                    f"{[issue.code.value for issue in qa_report.issues]}"
                )
        layouts.append(layout)
        scene_artifacts.append(artifact)
        scene_rows.append(
            {
                "scene_id": graph.scene_id,
                "frame_digest": artifact.frame_digest,
                "source_hash": artifact.source_hash,
                "preflight": {
                    "frame_overflow_count": preflight.frame_overflow_count,
                    "content_clipping_count": preflight.content_clipping_count,
                    "safe_zone_violation_count": preflight.safe_zone_violation_count,
                    "collision_count": len(detect_box_collisions(layout)),
                },
            }
        )

    transition_artifacts: list[Any] = []
    if transitions_enabled:
        for index in range(len(adapted.scene_graphs) - 1):
            transition = compile_inter_scene_transition(
                layouts[index],
                layouts[index + 1],
                registry,
                from_scene_graph=adapted.scene_graphs[index],
                to_scene_graph=adapted.scene_graphs[index + 1],
                duration=transition_duration,
            )
            transition_artifacts.append(
                render_transition_video(
                    adapted.scene_graphs[index],
                    layouts[index],
                    adapted.scene_graphs[index + 1],
                    layouts[index + 1],
                    transition,
                    out_dir / f"transition_{index+1}_{index+2}.mp4",
                    profile=render_profile,
                )
            )

    clips: list[Any] = []
    for index, scene_artifact in enumerate(scene_artifacts):
        clips.append(scene_artifact)
        if index < len(transition_artifacts):
            clips.append(transition_artifacts[index])

    video_only = assemble_video(tuple(clips), out_dir / "final_video_only.mp4")
    with_audio = mux_audio_track(video_only, narration_audio_path, out_dir / "final_with_audio.mp4")
    final = burn_subtitles(
        with_audio,
        _subtitle_cues(
            plan,
            scene_duration,
            transition_duration if transitions_enabled else 0.0,
        ),
        out_dir / "final.mp4",
    )
    video, audio, duration = _video_streams(Path(final.path))
    if video is None or audio is None:
        raise RuntimeError("LearnFlowBench candidate final artifact requires video + audio")

    return {
        "lesson_key": lesson_key,
        "render_success": True,
        "scene_count": len(scene_artifacts),
        "fatal_clipping_count": fatal_clipping,
        "fatal_overlap_count": fatal_overlap,
        "invalid_motion_plan_count": invalid_motion,
        "qa_pass_count": qa_passes,
        "motion_event_count": motion_events,
        "transition_count": len(transition_artifacts),
        "duration_seconds": duration,
        "render_wall_seconds": time.perf_counter() - t0,
        "final_path": final.path,
        "scenes": scene_rows,
        "_scene_artifacts": scene_artifacts,
        "_layouts": layouts,
        "_scene_graphs": adapted.scene_graphs,
    }


async def run_core_ablation(output_root: Path) -> tuple[BenchmarkCandidateResult, ...]:
    config = json.loads(CORE_ABLATION_PATH.read_text(encoding="utf-8"))
    baseline = json.loads(V1_BASELINE_PATH.read_text(encoding="utf-8"))
    profile = config["render_profile"]
    width = int(profile["width"])
    height = int(profile["height"])
    fps = int(profile["fps"])
    scene_duration = float(profile["scene_duration_seconds"])
    transition_duration = float(profile["transition_duration_seconds"])
    fixture_hash = core_fixture_sha256()

    rows: dict[str, list[dict[str, Any]]] = {"v1": [], "v2a": [], "v2b": [], "v2c": []}
    frame_paths: dict[str, list[Path]] = {"v1": [], "v2a": [], "v2b": [], "v2c": []}
    repair_cases: list[dict[str, Any]] = []

    for lesson_key in config["legacy_v1_fixture_ids"]:
        spec = baseline["lessons"][lesson_key]
        fixture_path = V1_FIXTURE_DIR / spec["fixture_file"]
        plan = LessonPlan.model_validate_json(fixture_path.read_text(encoding="utf-8"))
        lesson_dir = output_root / lesson_key

        v1_final = lesson_dir / "v1" / "final.mp4"
        v1 = await run_benchmark_lesson(
            lesson_key,
            fixture_path,
            spec,
            baseline["media_invariants"],
            retain_final_to=v1_final,
            retain_scenes_to=lesson_dir / "v1" / "scenes",
        )
        rows["v1"].append(v1)
        for index, scene_path in enumerate(v1["retained_scene_paths"], 1):
            out = lesson_dir / "frames" / f"v1_{index:02d}.png"
            extract_frame(Path(scene_path), scene_duration / 2.0, out)
            frame_paths["v1"].append(out)

        for candidate_id, motion_enabled, transitions_enabled, qa_enabled in (
            ("v2a", False, False, False),
            ("v2b", True, True, False),
            ("v2c", True, True, True),
        ):
            candidate = _run_v2_candidate(
                lesson_key,
                plan,
                lesson_dir / candidate_id,
                width=width,
                height=height,
                fps=fps,
                scene_duration=scene_duration,
                transition_duration=transition_duration,
                narration_audio_path=v1_final,
                motion_enabled=motion_enabled,
                transitions_enabled=transitions_enabled,
                qa_enabled=qa_enabled,
            )
            rows[candidate_id].append(candidate)
            frame_paths[candidate_id].extend(
                _candidate_static_frames(
                    candidate["_scene_artifacts"],
                    scene_duration=scene_duration,
                    output_dir=lesson_dir / "frames",
                    prefix=candidate_id,
                )
            )
            if candidate_id == "v2c":
                repair_cases.extend(
                    _repair_benchmark(
                        candidate,
                        lesson_dir / "v2c" / "repair",
                        width=width,
                        height=height,
                        fps=fps,
                        scene_duration=scene_duration,
                    )
                )

    results: list[BenchmarkCandidateResult] = []
    for candidate_id in ("v1", "v2a", "v2b", "v2c"):
        candidate_rows = rows[candidate_id]
        sample_count = len(candidate_rows)
        static = aggregate_static_quality(frame_paths[candidate_id])
        render_seconds = sum(float(row.get("total_render_seconds", row.get("render_wall_seconds", 0.0))) for row in candidate_rows)
        observations = [
            _obs(
                "render_success_rate",
                BenchmarkMetricCategory.STRUCTURAL,
                value=sum(int(bool(row.get("render_success"))) for row in candidate_rows) / sample_count,
                unit="ratio",
                sample_count=sample_count,
                evidence=("benchmark_output/learnflowbench/report.json",),
            ),
            _obs(
                "static_composition_proxy_v1",
                BenchmarkMetricCategory.VISUAL,
                value=float(static["score"]),
                unit="score_0_100",
                sample_count=int(static["frame_count"]),
                evidence=("benchmark_output/learnflowbench/report.json",),
                notes="Narrow deterministic frame-composition proxy; not a human aesthetic score.",
            ),
            _obs(
                "render_wall_seconds",
                BenchmarkMetricCategory.COST,
                value=round(render_seconds, 6),
                unit="seconds",
                sample_count=sample_count,
                evidence=("benchmark_output/learnflowbench/report.json",),
            ),
            _unmeasured(
                "teachquiz_learning_outcome",
                BenchmarkMetricCategory.LEARNING_OUTCOME,
                "No learner/judge evaluation is executed in the network-free core ablation.",
            ),
        ]

        if candidate_id == "v1":
            observations.extend(
                [
                    _not_applicable(
                        "motion_event_count",
                        BenchmarkMetricCategory.TEMPORAL,
                        "V1 is the frozen legacy renderer baseline, not a V2 Motion Grammar candidate.",
                    ),
                    _not_applicable(
                        "selective_repair_success_rate",
                        BenchmarkMetricCategory.STRUCTURAL,
                        "V1 has no V2 selective repair layer.",
                    ),
                ]
            )
        else:
            observations.extend(
                [
                    _obs(
                        "fatal_clipping_count",
                        BenchmarkMetricCategory.STRUCTURAL,
                        value=sum(int(row["fatal_clipping_count"]) for row in candidate_rows),
                        unit="count",
                        sample_count=sum(int(row["scene_count"]) for row in candidate_rows),
                        evidence=("benchmark_output/learnflowbench/report.json",),
                    ),
                    _obs(
                        "fatal_overlap_count",
                        BenchmarkMetricCategory.STRUCTURAL,
                        value=sum(int(row["fatal_overlap_count"]) for row in candidate_rows),
                        unit="count",
                        sample_count=sum(int(row["scene_count"]) for row in candidate_rows),
                        evidence=("benchmark_output/learnflowbench/report.json",),
                    ),
                    _obs(
                        "motion_event_count",
                        BenchmarkMetricCategory.TEMPORAL,
                        value=sum(int(row["motion_event_count"]) for row in candidate_rows),
                        unit="count",
                        sample_count=sum(int(row["scene_count"]) for row in candidate_rows),
                        evidence=("benchmark_output/learnflowbench/report.json",),
                    ),
                    _obs(
                        "transition_count",
                        BenchmarkMetricCategory.TEMPORAL,
                        value=sum(int(row["transition_count"]) for row in candidate_rows),
                        unit="count",
                        sample_count=sample_count,
                        evidence=("benchmark_output/learnflowbench/report.json",),
                    ),
                ]
            )
            if candidate_id == "v2c":
                repair_success = sum(int(bool(case["success"])) for case in repair_cases)
                observations.extend(
                    [
                        _obs(
                            "deterministic_qa_pass_rate",
                            BenchmarkMetricCategory.STRUCTURAL,
                            value=sum(int(row["qa_pass_count"]) for row in candidate_rows)
                            / sum(int(row["scene_count"]) for row in candidate_rows),
                            unit="ratio",
                            sample_count=sum(int(row["scene_count"]) for row in candidate_rows),
                            evidence=("benchmark_output/learnflowbench/report.json",),
                        ),
                        _obs(
                            "selective_repair_success_rate",
                            BenchmarkMetricCategory.STRUCTURAL,
                            value=repair_success / len(repair_cases),
                            unit="ratio",
                            sample_count=len(repair_cases),
                            evidence=("benchmark_output/learnflowbench/report.json",),
                            notes="Measured on frozen deterministic fault-injection repair cases.",
                        ),
                    ]
                )
            else:
                observations.append(
                    _not_applicable(
                        "selective_repair_success_rate",
                        BenchmarkMetricCategory.STRUCTURAL,
                        "Repair is not enabled for this candidate milestone.",
                    )
                )

        results.append(
            BenchmarkCandidateResult(
                candidate_id=BenchmarkCandidateId(candidate_id),
                execution_mode="frozen_core_ablation",
                fixture_set_sha256=fixture_hash,
                observations=tuple(observations),
            )
        )

    raw_path = output_root / "core_ablation_raw.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    clean_rows = {
        key: [
            {k: v for k, v in row.items() if not k.startswith("_")}
            for row in candidate_rows
        ]
        for key, candidate_rows in rows.items()
    }
    raw_path.write_text(
        json.dumps({"rows": clean_rows, "repair_cases": repair_cases}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return tuple(results)


def _coverage_rate(expected: set[str], actual: set[str]) -> float:
    return len(expected & actual) / len(expected) if expected else 1.0


def run_v2d_fixture(output_root: Path) -> BenchmarkCandidateResult:
    plugin = _load_plugin()
    brief, runner = build_fixture_runner()
    runtime_root = output_root / "v2d"
    gateway = CapabilityCoreGateway(
        create=plugin.handle_create,
        run=plugin.handle_run,
        render=plugin.handle_render,
        repo_root=ROOT,
        duration_resolver=lambda _scene, _script: 0.2,
    )
    t0 = time.perf_counter()
    result = run_lesson_pipeline(
        brief,
        runner=runner,
        core_gateway=gateway,
        runtime_root=runtime_root,
    )
    wall = time.perf_counter() - t0

    expected_objectives = {item.objective_id for item in result.pedagogy_plan.learning_objectives}
    script_objectives = {
        objective_id
        for segment in result.lesson_script.segments
        for objective_id in segment.objective_ids
    }
    selected_claims = {
        claim_id
        for item in (
            *result.pedagogy_plan.worked_examples,
            *result.pedagogy_plan.analogies,
            *result.pedagogy_plan.misconceptions,
        )
        for claim_id in item.claim_ids
    }
    script_claims = {
        claim_id
        for segment in result.lesson_script.segments
        for claim_id in segment.claim_ids
    }

    observations = (
        _obs(
            "render_success_rate",
            BenchmarkMetricCategory.STRUCTURAL,
            value=1.0,
            unit="ratio",
            sample_count=1,
            evidence=("benchmark_output/learnflowbench/report.json",),
            notes="Fixture-replay full typed pipeline, not a live-provider quality run.",
        ),
        _obs(
            "typed_stage_count",
            BenchmarkMetricCategory.STRUCTURAL,
            value=len(STAGE_ORDER),
            unit="count",
            sample_count=1,
            evidence=("benchmark_output/learnflowbench/report.json",),
        ),
        _obs(
            "objective_coverage_rate",
            BenchmarkMetricCategory.PEDAGOGY,
            value=_coverage_rate(expected_objectives, script_objectives),
            unit="ratio",
            sample_count=len(expected_objectives),
            evidence=("benchmark_output/learnflowbench/report.json",),
        ),
        _obs(
            "selected_claim_preservation_rate",
            BenchmarkMetricCategory.SEMANTIC,
            value=_coverage_rate(selected_claims, script_claims),
            unit="ratio",
            sample_count=len(selected_claims),
            evidence=("benchmark_output/learnflowbench/report.json",),
        ),
        _obs(
            "pipeline_wall_seconds",
            BenchmarkMetricCategory.COST,
            value=round(wall, 6),
            unit="seconds",
            sample_count=1,
            evidence=("benchmark_output/learnflowbench/report.json",),
            notes="Fixture runner has no representative provider latency or token usage.",
        ),
        _unmeasured(
            "llm_input_tokens",
            BenchmarkMetricCategory.COST,
            "Fixture replay intentionally makes no representative live-provider token measurement.",
        ),
        _unmeasured(
            "llm_output_tokens",
            BenchmarkMetricCategory.COST,
            "Fixture replay intentionally makes no representative live-provider token measurement.",
        ),
        _unmeasured(
            "provider_cost_usd",
            BenchmarkMetricCategory.COST,
            "Requires a governed live-provider benchmark run.",
        ),
        _unmeasured(
            "teachquiz_learning_outcome",
            BenchmarkMetricCategory.LEARNING_OUTCOME,
            "Requires a fixed quiz/judge protocol run on the frozen topic corpus.",
        ),
        _unmeasured(
            "human_visual_quality",
            BenchmarkMetricCategory.VISUAL,
            "No human or fixed external visual-quality panel is executed in CI.",
        ),
    )
    return BenchmarkCandidateResult(
        candidate_id=BenchmarkCandidateId.V2D,
        execution_mode="typed_fixture_replay",
        fixture_set_sha256=full_system_fixture_sha256(),
        observations=observations,
    )


async def run_learnflow_bench(output_root: str | Path) -> BenchmarkReport:
    output = Path(output_root)
    output.mkdir(parents=True, exist_ok=True)
    corpus = load_corpus()
    core_results = await run_core_ablation(output / "core_ablation")
    v2d = run_v2d_fixture(output / "full_system")
    report = BenchmarkReport(
        benchmark_id="learnflowbench-v1",
        source_commit=_source_commit(),
        corpus_sha256=corpus_sha256(),
        core_fixture_sha256=core_fixture_sha256(),
        corpus_topic_count=len(corpus.topics),
        core_ablation_topic_count=len(json.loads(CORE_ABLATION_PATH.read_text(encoding="utf-8"))["legacy_v1_fixture_ids"]),
        full_system_fixture_count=1,
        results=(*core_results, v2d),
        benchmark_execution_passed=True,
        sota_claim_allowed=False,
        limitations=(
            "The frozen 100-topic corpus is defined but CI does not generate 100 live-provider lessons.",
            "Core V1/V2A/V2B/V2C comparison uses the same three frozen V1 LessonPlan fixtures.",
            "V2D is fixture replay for integration evidence; it is not comparable to the core ablation quality scores.",
            "TeachQuiz-style learning outcome remains UNMEASURED until a fixed quiz/judge protocol is executed.",
            "Live LLM/VLM token counts and USD cost remain UNMEASURED in fixture replay.",
            "The deterministic static-composition proxy is not a human aesthetic score.",
        ),
    )
    (output / "report.json").write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report
