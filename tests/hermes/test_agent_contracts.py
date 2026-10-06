from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from agent_contracts import (
    AgentContractError,
    AgentRun,
    AgentRunStatus,
    AgentStageRecord,
    ArtifactRef,
    BudgetLedger,
    BudgetLimits,
    BudgetSpend,
    BudgetUsage,
    EvidenceEdge,
    EvidenceGraph,
    EvidenceNodeKind,
    EvidenceRelation,
    LearningBrief,
    LessonScript,
    PedagogyPlan,
    ResearchClaim,
    ResearchPack,
    ScriptSegment,
    SourceRecord,
    Storyboard,
    StoryboardScene,
    TeachingFunction,
)

ROOT = Path(__file__).resolve().parents[2]


def _source():
    return SourceRecord(
        source_id="S1",
        title="Source",
        locator="https://example.test/source",
    )


def _pack():
    return ResearchPack(
        pack_id="research.demo",
        topic="demo",
        sources=(_source(),),
        claims=(
            ResearchClaim(
                claim_id="C001",
                statement="A supported claim.",
                source_ids=("S1",),
                confidence=0.9,
            ),
        ),
    )


def _graph():
    graph = EvidenceGraph(
        graph_id="evidence.demo",
        research_pack_id="research.demo",
        source_ids=("S1",),
        claim_ids=("C001",),
        edges=(
            EvidenceEdge(
                edge_id="E1",
                from_kind=EvidenceNodeKind.SOURCE,
                from_id="S1",
                to_claim_id="C001",
                relation=EvidenceRelation.SUPPORTS,
            ),
        ),
    )
    graph.validate_against_research_pack(_pack())
    return graph


def test_public_eight_contracts_and_verifier_pass():
    proc = subprocess.run(
        [sys.executable, "scripts/verify_agent_contracts.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "AGENT_CONTRACTS=PASS" in proc.stdout
    assert (
        "LearningBrief -> ResearchPack -> EvidenceGraph -> PedagogyPlan -> "
        "LessonScript -> Storyboard"
    ) in proc.stdout


def test_contracts_are_frozen_extra_forbid_and_canonical_roundtrip():
    brief = LearningBrief(
        brief_id="brief.demo",
        user_query="Explain a topic.",
        learner_level="beginner",
        target_duration_minutes=2,
        language="en",
    )
    with pytest.raises(ValidationError):
        LearningBrief(
            brief_id="brief.demo",
            user_query="Explain a topic.",
            learner_level="beginner",
            target_duration_minutes=2,
            language="en",
            x=100,
        )
    with pytest.raises(ValidationError):
        brief.user_query = "mutate"
    payload = brief.to_canonical_json()
    assert payload == brief.to_canonical_json()
    assert LearningBrief.from_canonical_json(payload) == brief
    assert len(brief.content_sha256()) == 64


def test_research_pack_requires_declared_source_references():
    with pytest.raises(ValidationError, match="unknown sources"):
        ResearchPack(
            pack_id="research.bad",
            topic="bad",
            sources=(_source(),),
            claims=(
                ResearchClaim(
                    claim_id="C001",
                    statement="Unsupported ref.",
                    source_ids=("S404",),
                    confidence=0.5,
                ),
            ),
        )


def test_evidence_graph_requires_support_for_every_claim():
    pack = _pack()
    graph = EvidenceGraph(
        graph_id="evidence.bad",
        research_pack_id=pack.pack_id,
        source_ids=("S1",),
        claim_ids=("C001",),
        edges=(),
    )
    with pytest.raises(AgentContractError, match="without supporting"):
        graph.validate_against_research_pack(pack)


def test_lesson_script_blocks_unknown_claim_ids():
    graph = _graph()
    pedagogy = PedagogyPlan(
        plan_id="pedagogy.demo",
        brief_id="brief.demo",
        research_pack_id="research.demo",
        evidence_graph_id=graph.graph_id,
        learning_objectives=(
            {
                "objective_id": "O1",
                "description": "Understand the claim.",
                "assessment_criterion": "Can restate it.",
            },
        ),
        concept_order=("demo",),
    )
    script = LessonScript(
        script_id="script.demo",
        pedagogy_plan_id=pedagogy.plan_id,
        segments=(
            ScriptSegment(
                segment_id="segment.1",
                spoken_text="Narration.",
                subtitle_text="Narration.",
                spoken_language="en",
                subtitle_language="en",
                claim_ids=("C404",),
                objective_ids=("O1",),
                teaching_function=TeachingFunction.EXPLAIN,
            ),
        ),
    )
    with pytest.raises(AgentContractError, match="unknown claims"):
        script.validate_against(graph, pedagogy)


def test_storyboard_requires_exact_script_coverage_and_order():
    script = LessonScript(
        script_id="script.demo",
        pedagogy_plan_id="pedagogy.demo",
        segments=(
            ScriptSegment(
                segment_id="segment.1",
                spoken_text="One.",
                subtitle_text="One.",
                spoken_language="en",
                subtitle_language="en",
                teaching_function=TeachingFunction.INTRODUCE,
            ),
            ScriptSegment(
                segment_id="segment.2",
                spoken_text="Two.",
                subtitle_text="Two.",
                spoken_language="en",
                subtitle_language="en",
                teaching_function=TeachingFunction.EXPLAIN,
            ),
        ),
    )
    storyboard = Storyboard(
        storyboard_id="storyboard.demo",
        script_id=script.script_id,
        scenes=(
            StoryboardScene(
                scene_id="scene.1",
                script_segment_ids=("segment.2", "segment.1"),
                teaching_function=TeachingFunction.EXPLAIN,
                visual_intent="Semantic diagram.",
            ),
        ),
    )
    with pytest.raises(AgentContractError, match="exactly once and in order"):
        storyboard.validate_against_script(script)


def test_storyboard_contract_exposes_no_geometry_or_renderer_controls():
    fields = json.dumps(Storyboard.model_json_schema(), sort_keys=True).lower()
    for forbidden in (
        '"x"',
        '"y"',
        "pixel_width",
        "pixel_height",
        "font_size",
        "output_path",
        "render_profile",
        "ffmpeg",
        "renderer_code",
    ):
        assert forbidden not in fields


def test_budget_ledger_rejects_overspend_and_limit_overrun():
    with pytest.raises(ValidationError, match="overspent"):
        BudgetLedger(
            ledger_id="budget.bad",
            max_usd=1.0,
            spent=BudgetSpend(llm=1.01),
        )
    with pytest.raises(ValidationError, match="usage exceeds subagent_calls"):
        BudgetLedger(
            ledger_id="budget.bad-usage",
            max_usd=1.0,
            limits=BudgetLimits(subagent_calls=1),
            usage=BudgetUsage(subagent_calls=2),
        )


def test_agent_run_requires_registered_artifact_refs():
    with pytest.raises(ValidationError, match="unregistered artifacts"):
        AgentRun(
            run_id="run.bad",
            brief_id="brief.demo",
            root_agent_id="director",
            status=AgentRunStatus.SUCCEEDED,
            artifacts=(
                ArtifactRef(artifact_type="learning-brief", artifact_id="brief.demo"),
            ),
            stages=(
                AgentStageRecord(
                    step_id="step.1",
                    stage_name="Agent Contracts",
                    agent_id="director",
                    status=AgentRunStatus.SUCCEEDED,
                    input_artifact_ids=("brief.demo",),
                    output_artifact_ids=("storyboard.missing",),
                ),
            ),
        )
