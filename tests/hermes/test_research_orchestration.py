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
    assemble_specialist_delegation_results,
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
        source_id="evidence.S1",
        title="Source",
        locator="https://example.test/source",
    )
    findings = EvidenceResearchFindings(
        sources=(source,),
        claims=(
            ResearchClaim(
                claim_id="evidence.C001",
                statement="Supported claim.",
                source_ids=("evidence.S1",),
                confidence=0.9,
            ),
        ),
        evidence_edges=(
            EvidenceEdge(
                edge_id="evidence.E1",
                from_kind=EvidenceNodeKind.SOURCE,
                from_id="evidence.S1",
                to_claim_id="evidence.C001",
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
    assert result.research_pack.claims[0].source_ids == ("evidence.S1",)
    assert result.evidence_graph.edges[0].from_id == "evidence.S1"
    assert result.research_pack.sources[1].source_id == "misconception.S1"
    assert result.research_pack.claims[1].claim_id == "misconception.C1"


def test_misconception_findings_reject_unknown_local_claim_before_merge():
    _, evidence = _evidence()
    with pytest.raises(ValidationError, match="unknown local claims"):
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


def test_sibling_specialists_use_indexes_not_model_generated_ids():
    task = build_director_delegate_task(_brief())
    context = json.loads(task["context"])
    specialists = context["research_plan"]["specialist_tasks"]
    evidence_context = json.loads(specialists[1]["context"])
    misconception_context = json.loads(specialists[2]["context"])
    assert "zero-based source_indexes" in evidence_context["provenance_rule"]
    assert "isolated from Evidence Researcher" in misconception_context["provenance_rule"]
    assert "zero-based claim_indexes" in misconception_context["provenance_rule"]
    for specialist in specialists[1:]:
        schema_text = json.dumps(specialist["output_schema"], sort_keys=True)
        for forbidden in ("source_id", "claim_id", "edge_id", "concept_ids"):
            assert forbidden not in schema_text
    assert any(
        "No specialist may depend on a sibling" in rule
        for rule in context["execution_contract"]
    )


def test_specialist_id_namespaces_are_schema_enforced():
    with pytest.raises(ValidationError, match="evidence.*namespace"):
        EvidenceResearchFindings(
            sources=(
                SourceRecord(
                    source_id="wrong.S1",
                    title="Source",
                    locator="https://example.test/source",
                ),
            ),
            claims=(
                ResearchClaim(
                    claim_id="wrong.C1",
                    statement="Claim.",
                    source_ids=("wrong.S1",),
                    confidence=0.8,
                ),
            ),
            evidence_edges=(
                EvidenceEdge(
                    edge_id="wrong.E1",
                    from_kind=EvidenceNodeKind.SOURCE,
                    from_id="wrong.S1",
                    to_claim_id="wrong.C1",
                    relation=EvidenceRelation.SUPPORTS,
                ),
            ),
        )



def _delegation_payload_for_assembly():
    summaries = (
        json.dumps(
            {
                "concepts": ["demo"],
                "open_questions": [],
            }
        ),
        json.dumps(
            {
                "sources": [
                    {
                        "title": "Evidence source",
                        "locator": "https://docs.python.org/3/tutorial/",
                        "source_type": "WEB",
                    }
                ],
                "claims": [
                    {
                        "statement": "Supported claim.",
                        "source_indexes": [0],
                        "confidence": 0.9,
                    }
                ],
            }
        ),
        json.dumps(
            {
                "sources": [
                    {
                        "title": "Misconception source",
                        "locator": "https://docs.python.org/3/tutorial/",
                        "source_type": "WEB",
                    }
                ],
                "claims": [
                    {
                        "statement": "Correction claim.",
                        "source_indexes": [0],
                        "confidence": 0.9,
                    }
                ],
                "misconceptions": [
                    {
                        "statement": "Wrong idea.",
                        "correction": "Correct idea.",
                        "claim_indexes": [0],
                    }
                ],
                "examples": [
                    {
                        "description": "Example.",
                        "claim_indexes": [0],
                    }
                ],
            }
        ),
    )
    return {
        "results": [
            {
                "task_index": index,
                "status": "completed",
                "truncated": False,
                "schema_valid": True,
                "summary": summary,
            }
            for index, summary in enumerate(summaries)
        ]
    }


def test_host_assembly_is_deterministic_when_hermes_result_order_changes():
    plan = build_research_orchestration_plan(_brief())
    payload = _delegation_payload_for_assembly()
    first = assemble_specialist_delegation_results(
        plan=plan,
        brief_id="brief.demo",
        topic="Explain demo.",
        delegation_payload=payload,
    )
    second = assemble_specialist_delegation_results(
        plan=plan,
        brief_id="brief.demo",
        topic="Explain demo.",
        delegation_payload={
            "results": list(reversed(payload["results"]))
        },
    )
    assert first.to_canonical_json() == second.to_canonical_json()
    assert first.evidence_graph.claim_ids == tuple(
        claim.claim_id
        for claim in first.research_pack.claims
    )


@pytest.mark.parametrize(
    "mutation,match",
    [
        (
            lambda rows: rows[:-1],
            "exactly 3 specialist results",
        ),
        (
            lambda rows: [
                {
                    **rows[0],
                    "schema_valid": False,
                    "schema_errors": ["bad"],
                },
                *rows[1:],
            ],
            "failed output schema validation",
        ),
        (
            lambda rows: [
                {
                    **rows[0],
                    "status": "failed",
                    "error": "provider error",
                },
                *rows[1:],
            ],
            "provider error",
        ),
    ],
)
def test_host_assembly_fails_closed_on_missing_or_invalid_specialist(
    mutation,
    match,
):
    plan = build_research_orchestration_plan(_brief())
    payload = _delegation_payload_for_assembly()
    with pytest.raises(AgentContractError, match=match):
        assemble_specialist_delegation_results(
            plan=plan,
            brief_id="brief.demo",
            topic="Explain demo.",
            delegation_payload={
                "results": mutation(payload["results"])
            },
        )



def test_specialist_wire_schemas_are_compact_and_definition_free():
    plan = build_research_orchestration_plan(_brief())
    for task in plan.specialist_tasks:
        encoded = json.dumps(task.output_schema, sort_keys=True)
        assert "$defs" not in encoded
        assert "schema_version" not in encoded
        assert len(encoded) < 5000


def test_source_specialists_forbid_placeholder_locators_without_assuming_web_backend():
    plan = build_research_orchestration_plan(_brief())
    evidence_context = json.loads(plan.specialist_tasks[1].context)
    misconception_context = json.loads(plan.specialist_tasks[2].context)
    for context in (evidence_context, misconception_context):
        assert "If a web-search capability is actually available" in context["retrieval_rule"]
        assert "do not fabricate placeholder domains" in context["retrieval_rule"]
        assert "example.com" in context["retrieval_rule"]



def test_host_assigns_stable_ids_and_edges_from_indexes():
    plan = build_research_orchestration_plan(_brief())
    result = assemble_specialist_delegation_results(
        plan=plan,
        brief_id="brief.demo",
        topic="Explain demo.",
        delegation_payload=_delegation_payload_for_assembly(),
    )
    assert tuple(s.source_id for s in result.research_pack.sources) == (
        "evidence.S001",
        "misconception.S001",
    )
    assert tuple(c.claim_id for c in result.research_pack.claims) == (
        "evidence.C001",
        "misconception.C001",
    )
    assert tuple(e.edge_id for e in result.evidence_graph.edges) == (
        "evidence.E001",
        "misconception.E001",
    )
    assert result.research_pack.claims[0].concept_ids == ()


def test_host_rejects_bad_indexes_and_placeholder_locators():
    plan = build_research_orchestration_plan(_brief())
    bad_index = _delegation_payload_for_assembly()
    evidence = json.loads(bad_index["results"][1]["summary"])
    evidence["claims"][0]["source_indexes"] = [9]
    bad_index["results"][1]["summary"] = json.dumps(evidence)
    with pytest.raises(AgentContractError, match="outside"):
        assemble_specialist_delegation_results(
            plan=plan,
            brief_id="brief.demo",
            topic="Explain demo.",
            delegation_payload=bad_index,
        )

    placeholder = _delegation_payload_for_assembly()
    misconception = json.loads(placeholder["results"][2]["summary"])
    misconception["sources"][0]["locator"] = "https://example.com/fake"
    placeholder["results"][2]["summary"] = json.dumps(misconception)
    with pytest.raises(AgentContractError, match="placeholder source locator"):
        assemble_specialist_delegation_results(
            plan=plan,
            brief_id="brief.demo",
            topic="Explain demo.",
            delegation_payload=placeholder,
        )



def test_specialist_wire_rejects_tool_call_object_even_with_required_fields():
    from research_orchestration import validate_specialist_summary

    malformed = json.dumps(
        {
            "sources": [
                {
                    "title": "Python tutorial",
                    "locator": "https://docs.python.org/3/tutorial/",
                }
            ],
            "claims": [
                {
                    "statement": "Python names can be bound to objects.",
                    "source_indexes": [0],
                    "confidence": 0.9,
                }
            ],
            "calls": [
                {
                    "name": "web_search",
                    "args": {"query": "python variables"},
                }
            ],
        }
    )
    with pytest.raises(AgentContractError, match="unexpected fields"):
        validate_specialist_summary(ResearchRole.EVIDENCE, malformed)
