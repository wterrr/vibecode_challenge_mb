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
    EvidenceEdge,
    EvidenceNodeKind,
    EvidenceRelation,
    LearningBrief,
    ResearchClaim,
    ResearchExample,
    ResearchMisconception,
    SourceRecord,
)
from research_orchestration import (
    ConceptResearchFindings,
    EvidenceResearchFindings,
    MisconceptionResearchFindings,
    ResearchOrchestrationPlan,
    ResearchRole,
    SpecialistTask,
    build_director_delegate_task,
    build_research_orchestration_plan,
    merge_specialist_findings,
)


def _brief():
    return LearningBrief(
        brief_id="brief.demo",
        user_query="Explain demo.",
        learner_level="beginner",
        target_duration_minutes=2,
        language="en",
    )


def _evidence():
    source = SourceRecord(
        source_id="S1",
        title="Source",
        locator="https://example.test/source",
    )
    findings = EvidenceResearchFindings(
        sources=(source,),
        claims=(
            ResearchClaim(
                claim_id="C001",
                statement="Supported claim.",
                source_ids=("S1",),
                confidence=0.9,
            ),
        ),
        evidence_edges=(
            EvidenceEdge(
                edge_id="E1",
                from_kind=EvidenceNodeKind.SOURCE,
                from_id="S1",
                to_claim_id="C001",
                relation=EvidenceRelation.SUPPORTS,
            ),
        ),
    )
    return source, findings


def test_deterministic_verifier_passes():
    proc = subprocess.run(
        [sys.executable, "scripts/verify_research_orchestration.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "RESEARCH_ORCHESTRATION=PASS" in proc.stdout
    assert "provenance=preserved" in proc.stdout


def test_plan_has_exact_three_unique_specialist_roles():
    plan = build_research_orchestration_plan(_brief())
    assert plan.max_delegation_depth == 2
    assert plan.max_specialists == 3
    assert [task.role for task in plan.specialist_tasks] == [
        ResearchRole.CONCEPT,
        ResearchRole.EVIDENCE,
        ResearchRole.MISCONCEPTION,
    ]
    assert all(task.output_schema for task in plan.specialist_tasks)


def test_director_delegates_one_orchestrator_task_with_typed_result():
    task = build_director_delegate_task(_brief())
    assert set(task) == {"goal", "context", "output_schema"}
    assert "toolsets" not in task
    assert "Research Orchestrator" in task["goal"]
    context = json.loads(task["context"])
    assert context["research_plan"]["max_delegation_depth"] == 2
    assert context["research_plan"]["max_specialists"] == 3
    assert len(context["research_plan"]["specialist_tasks"]) == 3
    assert "research_pack" in task["output_schema"]["properties"]
    assert "evidence_graph" in task["output_schema"]["properties"]


def test_plan_rejects_more_than_three_specialists():
    base = build_research_orchestration_plan(_brief())
    extra = SpecialistTask(
        role=ResearchRole.CONCEPT,
        goal="extra",
        context="extra",
        output_schema={"type": "object"},
    )
    with pytest.raises(ValidationError, match="exceeds specialist limit|roles must be unique"):
        ResearchOrchestrationPlan(
            plan_id="research-plan:overflow",
            brief_id="brief.demo",
            specialist_tasks=base.specialist_tasks + (extra,),
        )


def test_merge_preserves_source_locator_and_claim_source_ids():
    source, evidence = _evidence()
    result = merge_specialist_findings(
        pack_id="research.demo",
        graph_id="evidence.demo",
        topic="demo",
        concept_findings=ConceptResearchFindings(concepts=("demo",)),
        evidence_findings=evidence,
        misconception_findings=MisconceptionResearchFindings(
            sources=(
                SourceRecord(
                    source_id="misconception.S1",
                    title="Misconception source",
                    locator="https://example.test/misconception",
                ),
            ),
            claims=(
                ResearchClaim(
                    claim_id="misconception.C1",
                    statement="Correction claim.",
                    source_ids=("misconception.S1",),
                    confidence=0.9,
                ),
            ),
            evidence_edges=(
                EvidenceEdge(
                    edge_id="misconception.E1",
                    from_kind=EvidenceNodeKind.SOURCE,
                    from_id="misconception.S1",
                    to_claim_id="misconception.C1",
                    relation=EvidenceRelation.SUPPORTS,
                ),
            ),
            misconceptions=(
                ResearchMisconception(
                    misconception_id="M1",
                    statement="Wrong idea.",
                    correction="Correct idea.",
                    claim_ids=("misconception.C1",),
                ),
            ),
            examples=(
                ResearchExample(
                    example_id="X1",
                    description="Example.",
                    claim_ids=("misconception.C1",),
                ),
            ),
        ),
    )
    assert result.research_pack.sources[0].locator == source.locator
    assert result.research_pack.claims[0].source_ids == ("S1",)
    assert result.evidence_graph.edges[0].from_id == "S1"
    assert result.research_pack.sources[1].source_id == "misconception.S1"
    assert result.research_pack.claims[1].claim_id == "misconception.C1"


def test_merge_rejects_misconception_claim_not_in_evidence():
    _, evidence = _evidence()
    with pytest.raises(AgentContractError, match="unknown claims"):
        merge_specialist_findings(
            pack_id="research.demo",
            graph_id="evidence.demo",
            topic="demo",
            concept_findings=ConceptResearchFindings(concepts=("demo",)),
            evidence_findings=evidence,
            misconception_findings=MisconceptionResearchFindings(
                sources=(
                    SourceRecord(
                        source_id="misconception.S1",
                        title="Misconception source",
                        locator="https://example.test/misconception",
                    ),
                ),
                claims=(
                    ResearchClaim(
                        claim_id="misconception.C1",
                        statement="Correction claim.",
                        source_ids=("misconception.S1",),
                        confidence=0.9,
                    ),
                ),
                evidence_edges=(
                    EvidenceEdge(
                        edge_id="misconception.E1",
                        from_kind=EvidenceNodeKind.SOURCE,
                        from_id="misconception.S1",
                        to_claim_id="misconception.C1",
                        relation=EvidenceRelation.SUPPORTS,
                    ),
                ),
                misconceptions=(
                    ResearchMisconception(
                        misconception_id="M1",
                        statement="Wrong idea.",
                        correction="Correct idea.",
                        claim_ids=("C404",),
                    ),
                ),
            ),
        )


def test_orchestration_surface_contains_no_renderer_controls():
    paths = [
        ROOT / "research_orchestration" / "models.py",
        ROOT / "research_orchestration" / "planner.py",
        ROOT / "research_orchestration" / "merge.py",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()
    for forbidden in (
        "deterministicpillowrenderer",
        "render_scene_video",
        "ffmpeg",
        "output_path",
        "pixel_width",
        "pixel_height",
    ):
        assert forbidden not in text


def test_bootstrap_config_bounds_hermes_delegation():
    text = (ROOT / "hermes" / "bootstrap" / "config.yaml").read_text(encoding="utf-8")
    assert "max_spawn_depth: 2" in text
    assert "max_concurrent_children: 3" in text
    assert "oneshot_max_children: 3" in text
    assert "orchestrator_enabled: true" in text


def test_sibling_specialists_do_not_depend_on_each_others_ids():
    task = build_director_delegate_task(_brief())
    context = json.loads(task["context"])
    specialists = context["research_plan"]["specialist_tasks"]
    evidence_context = json.loads(specialists[1]["context"])
    misconception_context = json.loads(specialists[2]["context"])
    assert "prefix 'evidence.'" in evidence_context["provenance_rule"]
    assert "isolated from Evidence Researcher" in misconception_context["provenance_rule"]
    assert "prefix 'misconception.'" in misconception_context["provenance_rule"]
    assert any(
        "No specialist may depend on a sibling" in rule
        for rule in context["execution_contract"]
    )
