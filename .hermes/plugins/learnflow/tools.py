"""Bounded capability handlers for Hermes LearnFlow Capability Plugin.

The plugin is an orchestration adapter only. It consumes public LearnFlow Core V2
contracts and never imports renderer internals or accepts arbitrary output paths.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_RUNTIME_ROOT = _REPO_ROOT / ".hermes_runtime" / "learnflow-plugin" / "runs"
_RUN_ID_RE = re.compile(r"^[0-9a-f]{16}$")
_MAX_INPUT_BYTES = 128 * 1024
_MAX_NODES = 64
_MAX_RELATIONS = 128
_MIN_DURATION = 0.1
_MAX_DURATION = 30.0

# Explicitly reject geometry/executable-rendering vocabulary before Pydantic validation.
# This is a control-plane boundary check, not a replacement for Core schema validation.
_FORBIDDEN_KEYS = frozenset(
    {
        "x",
        "y",
        "pixel_x",
        "pixel_y",
        "pixel_width",
        "pixel_height",
        "font_size",
        "font_size_px",
        "absolute_font_size",
        "ffmpeg_expression",
        "renderer_code",
        "render_code",
        "python_code",
        "output_path",
        "render_profile",
        "fps",
        "crf",
        "preset",
    }
)


def _json_response(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _ok(**payload: Any) -> str:
    return _json_response({"success": True, **payload})


def _fail(code: str, message: str, **payload: Any) -> str:
    return _json_response({"success": False, "error": {"code": code, "message": message}, **payload})


def _runtime_root() -> Path:
    raw = os.environ.get("LEARNFLOW_PLUGIN_RUNTIME_ROOT")
    root = Path(raw).expanduser() if raw else _DEFAULT_RUNTIME_ROOT
    return root.resolve()


def _ensure_repo_importable() -> None:
    repo = str(_REPO_ROOT)
    if repo not in sys.path:
        sys.path.insert(0, repo)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _validate_run_id(raw: Any) -> str:
    run_id = str(raw or "").strip()
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("run_id must be exactly 16 lowercase hexadecimal characters")
    return run_id


def _run_dir(run_id: str) -> Path:
    run_id = _validate_run_id(run_id)
    root = _runtime_root()
    candidate = (root / run_id).resolve()
    if candidate.parent != root:
        raise ValueError("run_id escapes the LearnFlow Capability Plugin runtime root")
    return candidate


def _atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(_canonical_bytes(value))
    os.replace(tmp, path)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _forbidden_key_paths(value: Any, prefix: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{prefix}.{key_text}"
            if key_text.lower() in _FORBIDDEN_KEYS:
                hits.append(child_path)
            hits.extend(_forbidden_key_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(_forbidden_key_paths(child, f"{prefix}[{index}]"))
    return hits


def _normalize_duration(raw: Any) -> float:
    if raw is None:
        return 1.0
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError("scene_duration must be a number")
    duration = float(raw)
    if not (_MIN_DURATION <= duration <= _MAX_DURATION):
        raise ValueError(
            f"scene_duration must be between {_MIN_DURATION} and {_MAX_DURATION} seconds"
        )
    return duration


def _load_created_run(run_id: str) -> tuple[Path, dict[str, Any]]:
    run_dir = _run_dir(run_id)
    input_path = run_dir / "input.json"
    if not input_path.is_file():
        raise FileNotFoundError(f"unknown LearnFlow Capability Plugin run_id '{run_id}'")
    payload = _read_json(input_path)
    if not isinstance(payload, dict):
        raise ValueError("stored LearnFlow Capability Plugin input is invalid")
    return run_dir, payload


def _public_core_types():
    _ensure_repo_importable()
    from learnflow_v2.layout import LayoutGraph, compile_scene_layout
    from learnflow_v2.motion import (
        CompiledMotionArtifact,
        MotionPlan,
        compile_motion_schedule,
        schedule_motion_plan,
    )
    from learnflow_v2.render import RenderProfile, RenderedArtifact, render_scene_video
    from learnflow_v2.scenegraph import SceneGraph

    return {
        "SceneGraph": SceneGraph,
        "LayoutGraph": LayoutGraph,
        "MotionPlan": MotionPlan,
        "CompiledMotionArtifact": CompiledMotionArtifact,
        "RenderProfile": RenderProfile,
        "RenderedArtifact": RenderedArtifact,
        "compile_scene_layout": compile_scene_layout,
        "schedule_motion_plan": schedule_motion_plan,
        "compile_motion_schedule": compile_motion_schedule,
        "render_scene_video": render_scene_video,
    }


def handle_create(args: dict[str, Any], **_kwargs: Any) -> str:
    """Validate semantic input and materialize a deterministic controlled run."""
    try:
        if not isinstance(args, dict):
            return _fail("LEARNFLOW_PLUGIN_INVALID_ARGUMENTS", "arguments must be an object")
        unexpected = sorted(set(args) - {"scene_graph", "motion_plan", "scene_duration"})
        if unexpected:
            return _fail("LEARNFLOW_PLUGIN_UNEXPECTED_ARGUMENT", f"unexpected argument(s): {unexpected}")

        scene_payload = args.get("scene_graph")
        if not isinstance(scene_payload, dict):
            return _fail("LEARNFLOW_PLUGIN_INVALID_SCENEGRAPH", "scene_graph must be an object")

        raw_size = len(_canonical_bytes(args))
        if raw_size > _MAX_INPUT_BYTES:
            return _fail(
                "LEARNFLOW_PLUGIN_INPUT_TOO_LARGE",
                f"input exceeds {_MAX_INPUT_BYTES} bytes",
                input_bytes=raw_size,
            )

        forbidden = _forbidden_key_paths(args)
        if forbidden:
            return _fail(
                "LEARNFLOW_PLUGIN_BOUNDARY_VIOLATION",
                "agent input contains geometry, renderer, codec, or output-path controls",
                forbidden_paths=forbidden,
            )

        duration = _normalize_duration(args.get("scene_duration"))
        core = _public_core_types()
        SceneGraph = core["SceneGraph"]
        MotionPlan = core["MotionPlan"]

        scene_graph = SceneGraph.model_validate(scene_payload)
        if len(scene_graph.nodes) > _MAX_NODES:
            return _fail("LEARNFLOW_PLUGIN_SCENE_TOO_LARGE", f"scene exceeds {_MAX_NODES} nodes")
        if len(scene_graph.relations) > _MAX_RELATIONS:
            return _fail("LEARNFLOW_PLUGIN_SCENE_TOO_LARGE", f"scene exceeds {_MAX_RELATIONS} relations")

        motion_payload = args.get("motion_plan")
        if motion_payload is None:
            motion_plan = MotionPlan(scene_id=scene_graph.scene_id)
        elif isinstance(motion_payload, dict):
            motion_plan = MotionPlan.model_validate(motion_payload)
        else:
            return _fail("LEARNFLOW_PLUGIN_INVALID_MOTION_PLAN", "motion_plan must be an object when provided")

        if motion_plan.scene_id != scene_graph.scene_id:
            return _fail(
                "LEARNFLOW_PLUGIN_SCENE_MISMATCH",
                "motion_plan.scene_id must match scene_graph.scene_id",
            )
        if any(event.trigger is not None for event in motion_plan.events):
            return _fail(
                "LEARNFLOW_PLUGIN_TRIGGERED_MOTION_UNSUPPORTED",
                "LearnFlow Capability Plugin accepts only untriggered motion; narration-beat orchestration is a later checkpoint",
            )
        motion_plan.validate_with_scenegraph(scene_graph)

        canonical_input = {
            "schema_version": "learnflow-plugin-run-input-v1",
            "scene_graph": scene_graph.model_dump(mode="json"),
            "motion_plan": motion_plan.model_dump(mode="json"),
            "scene_duration": duration,
        }
        canonical = _canonical_bytes(canonical_input)
        run_id = hashlib.sha256(canonical).hexdigest()[:16]
        run_dir = _run_dir(run_id)
        input_path = run_dir / "input.json"

        if input_path.exists():
            if input_path.read_bytes() != canonical:
                return _fail(
                    "LEARNFLOW_PLUGIN_RUN_ID_COLLISION",
                    "deterministic run_id collision with different canonical input",
                )
            cached = True
        else:
            _atomic_write_json(input_path, canonical_input)
            cached = False

        _atomic_write_json(
            run_dir / "state.json",
            {
                "schema_version": "learnflow-plugin-run-state-v1",
                "run_id": run_id,
                "stage": "CREATED",
                "input_sha256": hashlib.sha256(canonical).hexdigest(),
            },
        )
        return _ok(
            action="create",
            run_id=run_id,
            stage="CREATED",
            cached=cached,
            scene_id=scene_graph.scene_id,
            node_count=len(scene_graph.nodes),
            relation_count=len(scene_graph.relations),
        )
    except Exception as exc:
        return _fail("LEARNFLOW_PLUGIN_CREATE_FAILED", f"{type(exc).__name__}: {exc}")


def handle_run(args: dict[str, Any], **_kwargs: Any) -> str:
    """Compile one created run through public frozen Core V2 contracts."""
    try:
        if not isinstance(args, dict):
            return _fail("LEARNFLOW_PLUGIN_INVALID_ARGUMENTS", "arguments must be an object")
        unexpected = sorted(set(args) - {"run_id"})
        if unexpected:
            return _fail("LEARNFLOW_PLUGIN_UNEXPECTED_ARGUMENT", f"unexpected argument(s): {unexpected}")
        run_id = _validate_run_id(args.get("run_id"))
        run_dir, payload = _load_created_run(run_id)

        core = _public_core_types()
        SceneGraph = core["SceneGraph"]
        MotionPlan = core["MotionPlan"]
        scene_graph = SceneGraph.model_validate(payload["scene_graph"])
        motion_plan = MotionPlan.model_validate(payload["motion_plan"])
        duration = _normalize_duration(payload["scene_duration"])

        layout_graph = core["compile_scene_layout"](scene_graph)
        motion_schedule = core["schedule_motion_plan"](
            motion_plan,
            duration,
            graph=scene_graph,
        )
        compiled_motion = core["compile_motion_schedule"](motion_schedule)

        layout_payload = layout_graph.model_dump(mode="json")
        motion_payload = compiled_motion.model_dump(mode="json")
        _atomic_write_json(run_dir / "layout.json", layout_payload)
        _atomic_write_json(run_dir / "compiled_motion.json", motion_payload)
        _atomic_write_json(
            run_dir / "state.json",
            {
                "schema_version": "learnflow-plugin-run-state-v1",
                "run_id": run_id,
                "stage": "COMPILED",
                "input_sha256": _sha256(payload),
                "layout_sha256": _sha256(layout_payload),
                "compiled_motion_sha256": _sha256(motion_payload),
            },
        )
        return _ok(
            action="run",
            run_id=run_id,
            stage="COMPILED",
            scene_id=scene_graph.scene_id,
            layout_feasible=bool(layout_graph.feasible),
            motion_event_count=len(compiled_motion.events),
            layout_sha256=_sha256(layout_payload),
            compiled_motion_sha256=_sha256(motion_payload),
        )
    except Exception as exc:
        return _fail("LEARNFLOW_PLUGIN_RUN_FAILED", f"{type(exc).__name__}: {exc}")


def handle_render(args: dict[str, Any], **_kwargs: Any) -> str:
    """Render through the public facade with LearnFlow-owned path/profile."""
    try:
        if not isinstance(args, dict):
            return _fail("LEARNFLOW_PLUGIN_INVALID_ARGUMENTS", "arguments must be an object")
        unexpected = sorted(set(args) - {"run_id"})
        if unexpected:
            return _fail("LEARNFLOW_PLUGIN_UNEXPECTED_ARGUMENT", f"unexpected argument(s): {unexpected}")
        run_id = _validate_run_id(args.get("run_id"))
        run_dir, payload = _load_created_run(run_id)
        layout_path = run_dir / "layout.json"
        motion_path = run_dir / "compiled_motion.json"
        if not layout_path.is_file() or not motion_path.is_file():
            return _fail(
                "LEARNFLOW_PLUGIN_NOT_COMPILED",
                "run must pass learnflow_run before learnflow_render",
                run_id=run_id,
            )

        core = _public_core_types()
        scene_graph = core["SceneGraph"].model_validate(payload["scene_graph"])
        layout_graph = core["LayoutGraph"].model_validate(_read_json(layout_path))
        compiled_motion = core["CompiledMotionArtifact"].model_validate(_read_json(motion_path))

        render_dir = run_dir / "render"
        output_path = render_dir / "scene.mp4"
        artifact_path = render_dir / "artifact.json"
        profile = core["RenderProfile"](
            profile_id="hermes-learnflow",
            fps=30,
            crf=18,
            preset="medium",
        )

        if output_path.is_file() and artifact_path.is_file():
            artifact = core["RenderedArtifact"].model_validate(_read_json(artifact_path))
            cached = True
        else:
            render_dir.mkdir(parents=True, exist_ok=True)
            artifact = core["render_scene_video"](
                scene_graph,
                layout_graph,
                compiled_motion,
                output_path,
                profile=profile,
            )
            _atomic_write_json(artifact_path, artifact.model_dump(mode="json"))
            cached = False

        if not output_path.is_file() or output_path.stat().st_size <= 0:
            return _fail("LEARNFLOW_PLUGIN_RENDER_MISSING", "renderer did not produce a non-empty MP4")

        relative_output = f".hermes_runtime/learnflow-plugin/runs/{run_id}/render/scene.mp4"
        artifact_payload = artifact.model_dump(mode="json")
        _atomic_write_json(
            run_dir / "state.json",
            {
                "schema_version": "learnflow-plugin-run-state-v1",
                "run_id": run_id,
                "stage": "RENDERED",
                "input_sha256": _sha256(payload),
                "layout_sha256": _sha256(_read_json(layout_path)),
                "compiled_motion_sha256": _sha256(_read_json(motion_path)),
                "render_artifact_sha256": _sha256(artifact_payload),
            },
        )
        return _ok(
            action="render",
            run_id=run_id,
            stage="RENDERED",
            cached=cached,
            output=relative_output,
            artifact_id=artifact.artifact_id,
            duration=artifact.duration,
            width=artifact.width,
            height=artifact.height,
            fps=artifact.fps,
            frame_count=artifact.frame_count,
            frame_digest=artifact.frame_digest,
            source_hash=artifact.source_hash,
        )
    except Exception as exc:
        return _fail("LEARNFLOW_PLUGIN_RENDER_FAILED", f"{type(exc).__name__}: {exc}")
