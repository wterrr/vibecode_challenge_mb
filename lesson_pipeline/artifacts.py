"""Replayable artifact bundle persistence for the LearnFlow Lesson Pipeline."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .models import LessonPipelineResult


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=True)
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _atomic_write_json(path: Path, value: Any) -> str:
    payload = _canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(payload)
    os.replace(tmp, path)
    return hashlib.sha256(payload).hexdigest()


def write_artifact_bundle(result: LessonPipelineResult, run_dir: str | Path) -> dict:
    """Persist the typed semantic chain plus render manifest."""

    root = Path(run_dir)
    root.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    artifacts = {
        "learning_brief.json": result.learning_brief,
        "research_pack.json": result.research_pack,
        "evidence_graph.json": result.evidence_graph,
        "fact_verification.json": result.fact_verification,
        "pedagogy_plan.json": result.pedagogy_plan,
        "script.json": result.lesson_script,
        "storyboard.json": result.storyboard,
        "concept_registry.json": result.concept_registry,
        "render_manifest.json": {
            "run_id": result.run_id,
            "stage_order": list(result.stage_order),
            "scene_renders": [
                item.model_dump(mode="json") for item in result.scene_renders
            ],
            "final_video": result.final_video.model_dump(mode="json"),
        },
    }
    for relative, value in artifacts.items():
        hashes[relative] = _atomic_write_json(root / relative, value)

    scene_dir = root / "scenegraphs"
    for index, graph in enumerate(result.scenegraphs, start=1):
        relative = f"scenegraphs/{index:03d}.json"
        hashes[relative] = _atomic_write_json(root / relative, graph)

    manifest = {
        "schema_version": "lesson-pipeline-artifact-manifest-v1",
        "run_id": result.run_id,
        "artifacts": [
            {"path": path, "sha256": digest}
            for path, digest in sorted(hashes.items())
        ],
        "final_video": str(Path(result.final_video.path)),
    }
    _atomic_write_json(root / "artifact_manifest.json", manifest)
    return manifest
