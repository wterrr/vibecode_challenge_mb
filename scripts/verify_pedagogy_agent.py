#!/usr/bin/env python3
"""Acceptance verifier for the LearnFlow Pedagogy Agent."""

from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_contracts import (
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
    ResearchMisconception,
    ResearchPack,
    SourceRecord,
)
from fact_verification import verify_facts
from pedagogy_agent import (
    PedagogyIssue,
    build_pedagogy_agent_task,
    require_script_ready,
    validate_pedagogy_plan,
)


def build_fixture():
    brief = LearningBrief(
        brief_id="brief.gradient",
        user_query="Explain gradient descent to a beginner.",
        learner_level="beginner",
        target_duration_minutes=4,
        language="en",
    )
    s1 = SourceRecord(
        source_id="S1",
        title="Optimization source",
        locator="https://example.test/optimization",
    )
    s2 = SourceRecord(
        source_id="S2",
        title="Counter source",
        locator="https://example.test/counter",
    )
    pack = ResearchPack(
        pack_id="research.gradient",
        topic="gradient descent",
        concepts=("loss", "gradient", "learning rate"),
        sources=(s1, s2),
        claims=(
            ResearchClaim(
                claim_id="C1",
                statement="Gradient descent updates parameters to reduce a loss.",
                source_ids=("S1",),
                confidence=0.95,
            ),
            ResearchClaim(
                claim_id="C2",
                statement="A larger learning rate always improves convergence.",
                source_ids=("S1", "S2"),
                confidence=0.4,
            ),
        ),
        misconceptions=(
            ResearchMisconception(
                misconception_id="M1",
                statement="Move with the gradient when minimizing.",
                correction="Move against the gradient locally.",
                claim_ids=("C1",),
            ),
        ),
    )
    graph = EvidenceGraph(
        graph_id="evidence.gradient",
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


def build_plan(brief, pack, graph):
    return PedagogyPlan(
        plan_id="pedagogy.gradient",
        brief_id=brief.brief_id,
        research_pack_id=pack.pack_id,
        evidence_graph_id=graph.graph_id,
        learning_objectives=(
            LearningObjective(
                objective_id="O1",
                description="Explain the purpose of loss and gradient.",
                assessment_criterion="Learner can describe why updates reduce loss.",
            ),
            LearningObjective(
                objective_id="O2",
                description="Explain the role of the learning rate.",
                assessment_criterion="Learner can describe the trade-off qualitatively.",
            ),
        ),
        prerequisites=("basic arithmetic",),
        concept_order=("loss", "gradient", "learning rate"),
        worked_examples=(
            PedagogyExample(
                example_id="X1",
                concept="gradient",
                description="Use a downhill-loss example.",
                claim_ids=("C1",),
            ),
        ),
        analogies=(
            PedagogyExample(
                example_id="A1",
                concept="learning rate",
                description="Compare step size to cautious versus oversized downhill steps.",
                claim_ids=("C1",),
            ),
        ),
        misconceptions=(
            PedagogyMisconception(
                misconception_id="PM1",
                misconception="Minimization moves with the gradient.",
                correction="Minimization moves against the gradient locally.",
                claim_ids=("C1",),
            ),
        ),
        assessment_probes=(
            AssessmentProbe(
                probe_id="P1",
                prompt="Why does the update move opposite the gradient?",
                expected_outcome="It locally reduces the loss.",
                objective_ids=("O1",),
            ),
            AssessmentProbe(
                probe_id="P2",
                prompt="What can happen if steps are too large?",
                expected_outcome="The learner identifies overshooting as a risk.",
                objective_ids=("O2",),
            ),
        ),
    )


def main() -> int:
    brief, pack, graph, fact_report = build_fixture()
    if fact_report.approved_claim_ids != ("C1",):
        raise SystemExit("PEDAGOGY_AGENT=FAIL fixture fact gate")

    task = build_pedagogy_agent_task(brief, pack, graph, fact_report)
    context = json.loads(task["context"])
    exposed_claim_ids = tuple(
        claim["claim_id"] for claim in context["research"]["claims"]
    )
    if exposed_claim_ids != ("C1",):
        raise SystemExit(
            f"PEDAGOGY_AGENT=FAIL blocked claim leaked to Hermes: {exposed_claim_ids!r}"
        )

    plan = build_plan(brief, pack, graph)
    validation = validate_pedagogy_plan(
        plan,
        brief=brief,
        pack=pack,
        graph=graph,
        fact_report=fact_report,
    )
    require_script_ready(validation)
    if not validation.ready_for_script:
        raise SystemExit("PEDAGOGY_AGENT=FAIL valid plan not script-ready")

    blocked_plan = plan.model_copy(
        update={
            "worked_examples": (
                PedagogyExample(
                    example_id="X-blocked",
                    concept="learning rate",
                    description="A blocked factual example.",
                    claim_ids=("C2",),
                ),
            )
        }
    )
    blocked_validation = validate_pedagogy_plan(
        blocked_plan,
        brief=brief,
        pack=pack,
        graph=graph,
        fact_report=fact_report,
    )
    if PedagogyIssue.BLOCKED_CLAIM_REFERENCE not in blocked_validation.issues:
        raise SystemExit("PEDAGOGY_AGENT=FAIL blocked claim not rejected")

    print("PEDAGOGY_AGENT=PASS")
    print("approved_claim_filter=PASS")
    print("objectives=PASS")
    print("prerequisites=PASS")
    print("concept_progression=PASS")
    print("examples_and_analogies=PASS")
    print("misconceptions=PASS")
    print("assessment_coverage=PASS")
    print("blocked_claim_reference_rejected=PASS")
    print("script_readiness_gate=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
