#!/usr/bin/env python3
"""Deterministic verification for LearnFlow Research Orchestration."""

from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_contracts import (
    EvidenceEdge,
    EvidenceNodeKind,
    EvidenceRelation,
    LearningBrief,
    ResearchClaim,
    ResearchExample,
    ResearchMisconception,
    SourceRecord,
    SourceType,
)
from research_orchestration import (
    ConceptResearchFindings,
    EvidenceResearchFindings,
    MisconceptionResearchFindings,
    ResearchRole,
    build_director_delegate_task,
    build_research_orchestration_plan,
    merge_specialist_findings,
)


def main() -> int:
    brief = LearningBrief(
        brief_id="brief.gradient-descent",
        user_query="Explain gradient descent to a beginner.",
        learner_level="beginner",
        target_duration_minutes=3,
        language="en",
        constraints=("avoid calculus-heavy derivations",),
    )

    plan = build_research_orchestration_plan(brief)
    roles = tuple(task.role for task in plan.specialist_tasks)
    if roles != (
        ResearchRole.CONCEPT,
        ResearchRole.EVIDENCE,
        ResearchRole.MISCONCEPTION,
    ):
        raise SystemExit(f"RESEARCH_ORCHESTRATION=FAIL roles={roles!r}")

    director_task = build_director_delegate_task(brief)
    if set(director_task) != {"goal", "context", "output_schema"}:
        raise SystemExit("RESEARCH_ORCHESTRATION=FAIL director task surface")
    director_context = json.loads(director_task["context"])
    if len(director_context["research_plan"]["specialist_tasks"]) != 3:
        raise SystemExit("RESEARCH_ORCHESTRATION=FAIL specialist fan-out")

    concept = ConceptResearchFindings(
        concepts=("loss", "gradient", "learning rate"),
        open_questions=("How should the learning rate be chosen?",),
    )
    source = SourceRecord(
        source_id="evidence.source.textbook",
        source_type=SourceType.BOOK,
        title="Introductory optimization text",
        locator="book:optimization:intro",
    )
    evidence = EvidenceResearchFindings(
        sources=(source,),
        claims=(
            ResearchClaim(
                claim_id="evidence.C001",
                statement="Gradient descent updates parameters to reduce an objective.",
                source_ids=(source.source_id,),
                confidence=0.99,
                concept_ids=("gradient", "loss"),
            ),
        ),
        evidence_edges=(
            EvidenceEdge(
                edge_id="evidence.E001",
                from_kind=EvidenceNodeKind.SOURCE,
                from_id=source.source_id,
                to_claim_id="evidence.C001",
                relation=EvidenceRelation.SUPPORTS,
            ),
        ),
    )
    misconception_source = SourceRecord(
        source_id="misconception.source.guide",
        source_type=SourceType.DOCUMENT,
        title="Teaching guide",
        locator="document:gradient-descent:misconceptions",
    )
    misconceptions = MisconceptionResearchFindings(
        sources=(misconception_source,),
        claims=(
            ResearchClaim(
                claim_id="misconception.C001",
                statement="For minimization, updates move locally against the gradient.",
                source_ids=(misconception_source.source_id,),
                confidence=0.95,
            ),
        ),
        evidence_edges=(
            EvidenceEdge(
                edge_id="misconception.E001",
                from_kind=EvidenceNodeKind.SOURCE,
                from_id=misconception_source.source_id,
                to_claim_id="misconception.C001",
                relation=EvidenceRelation.SUPPORTS,
            ),
        ),
        misconceptions=(
            ResearchMisconception(
                misconception_id="M001",
                statement="Minimization moves with the gradient.",
                correction="Minimization moves against the gradient locally.",
                claim_ids=("misconception.C001",),
            ),
        ),
        examples=(
            ResearchExample(
                example_id="X001",
                description="A downhill slope analogy.",
                claim_ids=("misconception.C001",),
            ),
        ),
    )
    merged = merge_specialist_findings(
        pack_id="research.gradient-descent",
        graph_id="evidence.gradient-descent",
        topic="gradient descent",
        concept_findings=concept,
        evidence_findings=evidence,
        misconception_findings=misconceptions,
    )

    if merged.research_pack.sources[0].locator != source.locator:
        raise SystemExit("RESEARCH_ORCHESTRATION=FAIL source locator changed")
    if merged.research_pack.claims[0].source_ids != ("evidence.source.textbook",):
        raise SystemExit("RESEARCH_ORCHESTRATION=FAIL source provenance changed")
    if merged.evidence_graph.claim_ids != ("evidence.C001", "misconception.C001"):
        raise SystemExit("RESEARCH_ORCHESTRATION=FAIL claim IDs changed")
    if merged.research_pack.sources[1].locator != misconception_source.locator:
        raise SystemExit("RESEARCH_ORCHESTRATION=FAIL sibling provenance changed")

    print("RESEARCH_ORCHESTRATION=PASS")
    print("tree=Director -> Research Orchestrator -> 3 specialist researchers")
    print("max_delegation_depth=2")
    print("max_specialists=3")
    print("provenance=preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
