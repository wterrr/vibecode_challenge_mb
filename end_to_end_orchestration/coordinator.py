"""Bounded coordinator connecting accepted Hermes stages to frozen Core V2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Protocol, TypeVar

from pydantic import BaseModel

from agent_contracts import (
    AgentContractError,
    LearningBrief,
    LessonScript,
    PedagogyPlan,
)
from fact_verification import verify_facts
from pedagogy_agent import (
    build_pedagogy_agent_task,
    require_script_ready,
    validate_pedagogy_plan,
)
from research_orchestration import (
    ResearchOrchestrationResult,
    build_director_delegate_task,
)
from script_agent import (
    build_script_agent_task,
    require_visual_director_ready,
    validate_lesson_script,
)
from visual_director import (
    VisualDirectorOutput,
    build_visual_concept_registry,
    build_visual_director_task,
    require_core_ready,
    validate_visual_director_output,
)

from .artifacts import write_artifact_bundle
from .core import CapabilityCoreGateway
from .models import EndToEndResult


STAGE_ORDER = (
    "research_orchestration",
    "fact_verification",
    "pedagogy_agent",
    "script_agent",
    "visual_director",
    "core_v2",
    "video_assembly",
)

T = TypeVar("T", bound=BaseModel)


class StructuredAgentRunner(Protocol):
    """Provider-neutral structured executor implemented by the Hermes host layer."""

    def run(self, *, stage: str, task: dict, output_model: type[T]) -> T | dict: ...


def _execute(
    runner: StructuredAgentRunner,
    *,
    stage: str,
    task: dict,
    output_model: type[T],
) -> T:
    raw = runner.run(stage=stage, task=task, output_model=output_model)
    if isinstance(raw, output_model):
        return raw
    return output_model.model_validate(raw)


def _semantic_run_id(*artifacts: BaseModel) -> str:
    payload = [
        artifact.model_dump(mode="json", exclude_none=True) for artifact in artifacts
    ]
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def run_end_to_end(
    brief: LearningBrief,
    *,
    runner: StructuredAgentRunner,
    core_gateway: CapabilityCoreGateway,
    runtime_root: str | Path,
) -> EndToEndResult:
    """Execute the accepted typed pipeline and fail closed at every boundary."""

    research = _execute(
        runner,
        stage="research_orchestration",
        task=build_director_delegate_task(brief),
        output_model=ResearchOrchestrationResult,
    )
    research.evidence_graph.validate_against_research_pack(research.research_pack)

    fact_report = verify_facts(research.research_pack, research.evidence_graph)

    pedagogy = _execute(
        runner,
        stage="pedagogy_agent",
        task=build_pedagogy_agent_task(
            brief,
            research.research_pack,
            research.evidence_graph,
            fact_report,
        ),
        output_model=PedagogyPlan,
    )
    pedagogy_validation = validate_pedagogy_plan(
        pedagogy,
        brief=brief,
        pack=research.research_pack,
        graph=research.evidence_graph,
        fact_report=fact_report,
    )
    require_script_ready(pedagogy_validation)

    script = _execute(
        runner,
        stage="script_agent",
        task=build_script_agent_task(
            brief,
            research.research_pack,
            research.evidence_graph,
            fact_report,
            pedagogy,
        ),
        output_model=LessonScript,
    )
    script_validation = validate_lesson_script(
        script,
        brief=brief,
        pack=research.research_pack,
        graph=research.evidence_graph,
        fact_report=fact_report,
        pedagogy=pedagogy,
    )
    require_visual_director_ready(script_validation)

    visual = _execute(
        runner,
        stage="visual_director",
        task=build_visual_director_task(
            brief,
            research.research_pack,
            research.evidence_graph,
            fact_report,
            pedagogy,
            script,
        ),
        output_model=VisualDirectorOutput,
    )
    registry = build_visual_concept_registry(pedagogy)
    visual_validation = validate_visual_director_output(
        visual,
        script=script,
        registry=registry,
    )
    require_core_ready(visual_validation)

    run_id = _semantic_run_id(
        brief,
        research,
        fact_report,
        pedagogy,
        script,
        visual,
        registry.to_schema(),
    )
    run_dir = Path(runtime_root) / run_id
    final_path = run_dir / "final.mp4"
    scene_renders, final_video = core_gateway.render_lesson(
        scenegraphs=visual.scenegraphs,
        storyboard_scenes=visual.storyboard.scenes,
        script=script,
        output_path=final_path,
    )
    if not final_path.is_file() or final_path.stat().st_size <= 0:
        raise AgentContractError("End-to-End Orchestration did not produce final.mp4")

    result = EndToEndResult(
        run_id=run_id,
        learning_brief=brief,
        research_pack=research.research_pack,
        evidence_graph=research.evidence_graph.model_dump(mode="json"),
        fact_verification=fact_report,
        pedagogy_plan=pedagogy,
        lesson_script=script,
        storyboard=visual.storyboard,
        concept_registry=registry.to_schema(),
        scenegraphs=visual.scenegraphs,
        scene_renders=scene_renders,
        final_video=final_video,
        stage_order=STAGE_ORDER,
        artifact_root=str(run_dir),
    )
    write_artifact_bundle(result, run_dir)
    return result
