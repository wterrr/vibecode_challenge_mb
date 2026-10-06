"""Deterministic Core V2 handoff for the accepted LearnFlow Lesson Pipeline."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable, Protocol

from agent_contracts import LessonScript, StoryboardScene
from learnflow_v2.render import RenderArtifactKind, RenderedArtifact, assemble_video
from learnflow_v2.scenegraph import SceneGraph

from .models import SceneRenderReceipt


class CapabilityCall(Protocol):
    def __call__(self, args: dict, **kwargs) -> str: ...


class SceneDurationResolver(Protocol):
    def __call__(self, scene: StoryboardScene, script: LessonScript) -> float: ...


def default_scene_duration(scene: StoryboardScene, script: LessonScript) -> float:
    """Deterministic narration-length estimate owned by the host, never Hermes."""

    by_id = {segment.segment_id: segment for segment in script.segments}
    words = 0
    for segment_id in scene.script_segment_ids:
        segment = by_id[segment_id]
        words += len(re.findall(r"\S+", segment.spoken_text))
    return min(30.0, max(1.0, words / 2.5))


def _parse_response(raw: str, *, action: str) -> dict:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{action} returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{action} returned a non-object response")
    if not payload.get("success"):
        error = payload.get("error") or {}
        raise RuntimeError(
            f"{action} failed: {error.get('code', 'UNKNOWN')} "
            f"{error.get('message', '')}".strip()
        )
    return payload


class CapabilityCoreGateway:
    """Runs semantic scenes via learnflow_create -> learnflow_run -> learnflow_render.

    The gateway receives tool callables rather than importing plugin internals. This
    keeps the coordinator coupled to the accepted capability contract, not renderer
    implementation details.
    """

    def __init__(
        self,
        *,
        create: CapabilityCall,
        run: CapabilityCall,
        render: CapabilityCall,
        repo_root: str | Path,
        duration_resolver: SceneDurationResolver = default_scene_duration,
    ) -> None:
        self._create = create
        self._run = run
        self._render = render
        self._repo_root = Path(repo_root).resolve()
        self._duration_resolver = duration_resolver

    def render_lesson(
        self,
        *,
        scenegraphs: tuple[SceneGraph, ...],
        storyboard_scenes: tuple[StoryboardScene, ...],
        script: LessonScript,
        output_path: str | Path,
    ) -> tuple[tuple[SceneRenderReceipt, ...], RenderedArtifact]:
        if len(scenegraphs) != len(storyboard_scenes):
            raise RuntimeError("Core handoff requires one SceneGraph per Storyboard scene")

        receipts: list[SceneRenderReceipt] = []
        rendered: list[RenderedArtifact] = []
        for scene, graph in zip(storyboard_scenes, scenegraphs, strict=True):
            if scene.scene_id != graph.scene_id:
                raise RuntimeError(
                    f"Core handoff scene mismatch: {scene.scene_id!r} != {graph.scene_id!r}"
                )
            duration = float(self._duration_resolver(scene, script))
            created = _parse_response(
                self._create(
                    {
                        "scene_graph": graph.model_dump(mode="json"),
                        "scene_duration": duration,
                    }
                ),
                action="learnflow_create",
            )
            run_id = str(created["run_id"])
            compiled = _parse_response(
                self._run({"run_id": run_id}),
                action="learnflow_run",
            )
            if not compiled.get("layout_feasible"):
                raise RuntimeError(
                    f"Core layout is not feasible for scene {scene.scene_id!r}"
                )
            result = _parse_response(
                self._render({"run_id": run_id}),
                action="learnflow_render",
            )

            relative_output = Path(str(result["output"]))
            clip_path = (
                relative_output
                if relative_output.is_absolute()
                else self._repo_root / relative_output
            )
            if not clip_path.is_file() or clip_path.stat().st_size <= 0:
                raise RuntimeError(
                    f"learnflow_render reported missing clip for scene {scene.scene_id!r}"
                )

            artifact = RenderedArtifact(
                artifact_id=str(result["artifact_id"]),
                kind=RenderArtifactKind.SCENE,
                path=str(clip_path),
                duration=float(result["duration"]),
                width=int(result["width"]),
                height=int(result["height"]),
                fps=int(result["fps"]),
                frame_count=int(result["frame_count"]),
                frame_digest=str(result["frame_digest"]),
                source_hash=str(result["source_hash"]),
            )
            rendered.append(artifact)
            receipts.append(
                SceneRenderReceipt(
                    scene_id=scene.scene_id,
                    capability_run_id=run_id,
                    output=str(result["output"]),
                    duration=artifact.duration,
                    frame_digest=artifact.frame_digest,
                    source_hash=artifact.source_hash,
                )
            )

        final_artifact = assemble_video(rendered, output_path)
        return tuple(receipts), final_artifact
