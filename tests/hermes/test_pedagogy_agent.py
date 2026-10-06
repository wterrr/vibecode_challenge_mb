from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_contracts import (
    AgentContractError,
    AssessmentProbe,
    EvidenceEdge,
    EvidenceGraph,
    EvidenceNodeKind,
    EvidenceRelation,
    LearningBrief,
    LearningObjective,
    PedagogyExample,
    PedagogyMisconception,
    PedagogyPlan,
    ResearchClaim,
    ResearchPack,
    SourceRecord,
)
from fact_verification import (
    ClaimVerification,
    FactVerificationReport,
    VerificationIssue,
    verify_facts,
)
from pedagogy_agent import (
    PedagogyIssue,
    build_pedagogy_agent_task,
    require_script_ready,
    validate_pedagogy_plan,
)


def fixture():
    brief = LearningBrief(
        brief_id="brief.demo",
        user_query="Explain demo.",
        learner_level="beginner",
        target_duration_minutes=3,
        language="en",
    )
    s1 = SourceRecord(source_id="S1", title="One", locator="https://example.test/1")
    s2 = SourceRecord(source_id="S2", title="Two", locator="https://example.test/2")
    pack = ResearchPack(
        pack_id="research.demo",
        topic="demo",
        concepts=("first", "second"),
        sources=(s1, s2),
        claims=(
            ResearchClaim(
                claim_id="C1",
                statement="Supported.",
                source_ids=("S1",),
                confidence=0.9,
            ),
            ResearchClaim(
                claim_id="C2",
                statement="Contradicted.",
                source_ids=("S1", "S2"),
                confidence=0.5,
            ),
        ),
    )
    graph = EvidenceGraph(
        graph_id="evidence.demo",
        research_pack_id=pack.pack_id,
        source_ids=("S1", "S2"),
        claim_ids=("C1", "C2"),
        edges=(
            EvidenceEdge(
                edge_id="E1",
                from_kind=EvidenceNodeKind.SOURCE,
                from_id="S1",
                to_claim_id="C1",
                relation=EvidenceRelation.SUPPORTS,
            ),
            EvidenceEdge(
                edge_id="E2",
                from_kind=EvidenceNodeKind.SOURCE,
                from_id="S1",
                to_claim_id="C2",
                relation=EvidenceRelation.SUPPORTS,
            ),
            EvidenceEdge(
                edge_id="E3",
                from_kind=EvidenceNodeKind.SOURCE,
                from_id="S2",
                to_claim_id="C2",
                relation=EvidenceRelation.CONTRADICTS,
            ),
        ),
    )
    return brief, pack, graph, verify_facts(pack, graph)


def good_plan(brief, pack, graph):
    return PedagogyPlan(
        plan_id="pedagogy.demo",
        brief_id=brief.brief_id,
        research_pack_id=pack.pack_id,
        evidence_graph_id=graph.graph_id,
        learning_objectives=(
            LearningObjective(
                objective_id="O1",
                description="Understand first concept.",
                assessment_criterion="Explain it correctly.",
            ),
            LearningObjective(
                objective_id="O2",
                description="Connect first to second.",
                assessment_criterion="Describe the relationship.",
            ),
        ),
        prerequisites=("basic vocabulary",),
        concept_order=("first", "second"),
        worked_examples=(
            PedagogyExample(
                example_id="X1",
                concept="first",
                description="Worked example.",
                claim_ids=("C1",),
            ),
        ),
        misconceptions=(
            PedagogyMisconception(
                misconception_id="M1",
                misconception="Wrong idea.",
                correction="Correct idea.",
                claim_ids=("C1",),
            ),
        ),
        assessment_probes=(
            AssessmentProbe(
                probe_id="P1",
                prompt="Check O1.",
                expected_outcome="Correct O1 response.",
                objective_ids=("O1",),
            ),
            AssessmentProbe(
                probe_id="P2",
                prompt="Check O2.",
                expected_outcome="Correct O2 response.",
                objective_ids=("O2",),
            ),
        ),
    )


def validate(plan, brief, pack, graph, report):
    return validate_pedagogy_plan(
        plan,
        brief=brief,
        pack=pack,
        graph=graph,
        fact_report=report,
    )


def test_acceptance_verifier_passes():
    proc = subprocess.run(
        [sys.executable, "scripts/verify_pedagogy_agent.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PEDAGOGY_AGENT=PASS" in proc.stdout
    assert "script_readiness_gate=PASS" in proc.stdout


def test_good_plan_is_script_ready():
    brief, pack, graph, report = fixture()
    result = validate(good_plan(brief, pack, graph), brief, pack, graph, report)
    assert result.ready_for_script
    assert result.issues == ()
    require_script_ready(result)


def test_blocked_claim_reference_is_rejected():
    brief, pack, graph, report = fixture()
    plan = good_plan(brief, pack, graph).model_copy(
        update={
            "worked_examples": (
                PedagogyExample(
                    example_id="X2",
                    concept="second",
                    description="Uses blocked claim.",
                    claim_ids=("C2",),
                ),
            )
        }
    )
    result = validate(plan, brief, pack, graph, report)
    assert PedagogyIssue.BLOCKED_CLAIM_REFERENCE in result.issues
    assert result.blocked_claim_ids == ("C2",)
    with pytest.raises(AgentContractError, match="not ready"):
        require_script_ready(result)


def test_unknown_concept_is_rejected():
    brief, pack, graph, report = fixture()
    plan = good_plan(brief, pack, graph).model_copy(
        update={"concept_order": ("first", "hallucinated-concept")}
    )
    result = validate(plan, brief, pack, graph, report)
    assert PedagogyIssue.UNKNOWN_CONCEPT in result.issues
    assert result.unknown_concepts == ("hallucinated-concept",)


def test_every_objective_requires_assessment_probe():
    brief, pack, graph, report = fixture()
    plan = good_plan(brief, pack, graph).model_copy(
        update={
            "assessment_probes": (
                AssessmentProbe(
                    probe_id="P1",
                    prompt="Check only O1.",
                    expected_outcome="O1.",
                    objective_ids=("O1",),
                ),
            )
        }
    )
    result = validate(plan, brief, pack, graph, report)
    assert PedagogyIssue.OBJECTIVE_WITHOUT_ASSESSMENT in result.issues
    assert result.unassessed_objective_ids == ("O2",)


def test_plan_requires_example_or_analogy_before_script():
    brief, pack, graph, report = fixture()
    plan = good_plan(brief, pack, graph).model_copy(
        update={"worked_examples": (), "analogies": ()}
    )
    result = validate(plan, brief, pack, graph, report)
    assert PedagogyIssue.MISSING_EXAMPLE in result.issues


def test_fact_report_must_cover_exact_research_claim_set():
    brief, pack, graph, _ = fixture()
    forged = FactVerificationReport(
        report_id="fact.partial",
        research_pack_id=pack.pack_id,
        evidence_graph_id=graph.graph_id,
        claims=(
            ClaimVerification(
                claim_id="C1",
                grounded_source_ids=("S1",),
                support_edge_ids=("E1",),
            ),
        ),
    )
    with pytest.raises(AgentContractError, match="cover every"):
        validate(good_plan(brief, pack, graph), brief, pack, graph, forged)


def test_fact_report_cannot_approve_deterministically_blocked_claim():
    brief, pack, graph, _ = fixture()
    forged = FactVerificationReport(
        report_id="fact.forged",
        research_pack_id=pack.pack_id,
        evidence_graph_id=graph.graph_id,
        claims=(
            ClaimVerification(
                claim_id="C1",
                grounded_source_ids=("S1",),
                support_edge_ids=("E1",),
            ),
            ClaimVerification(
                claim_id="C2",
                grounded_source_ids=("S1",),
                support_edge_ids=("E2",),
            ),
        ),
    )
    with pytest.raises(AgentContractError, match="approves claims blocked"):
        validate(good_plan(brief, pack, graph), brief, pack, graph, forged)


def test_hermes_task_exposes_only_approved_claim_content():
    brief, pack, graph, report = fixture()
    task = build_pedagogy_agent_task(brief, pack, graph, report)
    context = json.loads(task["context"])
    assert [claim["claim_id"] for claim in context["research"]["claims"]] == ["C1"]
    assert context["fact_verification"]["blocked_claim_ids"] == ["C2"]
    assert all(
        claim["claim_id"] != "C2" for claim in context["research"]["claims"]
    )


def test_hermes_task_requires_all_pedagogical_outputs_and_preserves_boundaries():
    brief, pack, graph, report = fixture()
    task = build_pedagogy_agent_task(brief, pack, graph, report)
    properties = task["output_schema"]["properties"]
    for field in (
        "learning_objectives",
        "prerequisites",
        "concept_order",
        "worked_examples",
        "analogies",
        "misconceptions",
        "assessment_probes",
    ):
        assert field in properties
    context = json.loads(task["context"])
    assert "Do not write lesson-script narration." in context["instructions"]
    assert any("visual coordinates" in item for item in context["instructions"])


def test_pedagogy_surface_has_no_script_visual_or_renderer_implementation():
    paths = [
        ROOT / "pedagogy_agent" / "models.py",
        ROOT / "pedagogy_agent" / "gate.py",
        ROOT / "pedagogy_agent" / "hermes.py",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()
    for forbidden in (
        "scriptsegment(",
        "storyboardscene(",
        "render_scene_video",
        "deterministicpillowrenderer",
        "ffmpeg",
        "pixel_width",
        "pixel_height",
    ):
        assert forbidden not in text


def test_fact_report_can_be_stricter_than_baseline_gate():
    brief, pack, graph, report = fixture()
    stricter = FactVerificationReport(
        report_id="fact.stricter",
        research_pack_id=pack.pack_id,
        evidence_graph_id=graph.graph_id,
        claims=(
            ClaimVerification(
                claim_id="C1",
                issues=(VerificationIssue.SEMANTIC_UNCERTAINTY,),
                grounded_source_ids=("S1",),
                support_edge_ids=("E1",),
            ),
            report.claims[1],
        ),
    )
    plan = good_plan(brief, pack, graph)
    result = validate(plan, brief, pack, graph, stricter)
    assert PedagogyIssue.BLOCKED_CLAIM_REFERENCE in result.issues
    assert result.blocked_claim_ids == ("C1",)


def test_hermes_task_rejects_forged_fact_approval_before_context_exposure():
    brief, pack, graph, _ = fixture()
    forged = FactVerificationReport(
        report_id="fact.forged-for-context",
        research_pack_id=pack.pack_id,
        evidence_graph_id=graph.graph_id,
        claims=(
            ClaimVerification(
                claim_id="C1",
                grounded_source_ids=("S1",),
                support_edge_ids=("E1",),
            ),
            ClaimVerification(
                claim_id="C2",
                grounded_source_ids=("S1",),
                support_edge_ids=("E2",),
            ),
        ),
    )
    with pytest.raises(AgentContractError, match="approves claims blocked"):
        build_pedagogy_agent_task(brief, pack, graph, forged)
