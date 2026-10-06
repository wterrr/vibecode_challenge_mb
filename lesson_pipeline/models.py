"""Typed result contracts for the accepted LearnFlow Lesson Pipeline."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from agent_contracts import (
    ContractModel,
    EvidenceGraph,
    LearningBrief,
    LessonScript,
    PedagogyPlan,
    ResearchPack,
    Storyboard,
)
from fact_verification import FactVerificationReport
from learnflow_v2.concepts import ConceptRegistrySchema
from learnflow_v2.render import RenderedArtifact
from learnflow_v2.scenegraph import SceneGraph


def _tupleize(value: Any):
    return tuple(value) if isinstance(value, list) else value


class SceneRenderReceipt(ContractModel):
    scene_id: str = Field(..., min_length=1)
    capability_run_id: str = Field(..., min_length=1)
    output: str = Field(..., min_length=1)
    duration: float = Field(..., gt=0.0)
    frame_digest: str = Field(..., min_length=1)
    source_hash: str = Field(..., min_length=1)


class LessonPipelineResult(ContractModel):
    run_id: str = Field(..., min_length=1)
    learning_brief: LearningBrief
    research_pack: ResearchPack
    evidence_graph: EvidenceGraph
    fact_verification: FactVerificationReport
    pedagogy_plan: PedagogyPlan
    lesson_script: LessonScript
    storyboard: Storyboard
    concept_registry: ConceptRegistrySchema
    scenegraphs: tuple[SceneGraph, ...] = Field(..., min_length=1)
    scene_renders: tuple[SceneRenderReceipt, ...] = Field(..., min_length=1)
    final_video: RenderedArtifact
    stage_order: tuple[str, ...] = Field(..., min_length=1)
    artifact_root: str = Field(..., min_length=1)

    @field_validator("scenegraphs", "scene_renders", "stage_order", mode="before")
    @classmethod
    def _tuples(cls, value: Any):
        return _tupleize(value)


# Backward-compatible type alias for historical artifacts/tests outside this repo.
EndToEndResult = LessonPipelineResult
