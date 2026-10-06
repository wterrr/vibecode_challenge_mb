#!/usr/bin/env python3
"""Acceptance verifier for the LearnFlow Script Agent."""

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
    LessonScript,
    PedagogyExample,
    PedagogyMisconception,
    PedagogyPlan,
    ResearchClaim,
    ResearchPack,
    ScriptSegment,
    SourceRecord,
    TeachingFunction,
)
from fact_verification import verify_facts
from script_agent import (
    ScriptIssue,
    build_script_agent_task,
    require_visual_director_ready,
    validate_lesson_script,
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
    report = verify_facts(pack, graph)
    pedagogy = PedagogyPlan(
        plan_id="pedagogy.gradient",
        brief_id=brief.brief_id,
        research_pack_id=pack.pack_id,
        evidence_graph_id=graph.graph_id,
        learning_objectives=(
            LearningObjective(
                objective_id="O1",
                description="Explain loss and gradient.",
                assessment_criterion="Learner can explain why the update reduces loss.",
            ),
            LearningObjective(
                objective_id="O2",
                description="Reason about step size qualitatively.",
                assessment_criterion="Learner can identify overshooting risk.",
            ),
        ),
        prerequisites=("basic arithmetic",),
        concept_order=("loss", "gradient", "learning rate"),
        worked_examples=(
            PedagogyExample(
                example_id="X1",
                concept="gradient",
                description="Walk downhill on a loss landscape.",
                claim_ids=("C1",),
            ),
        ),
        analogies=(
            PedagogyExample(
                example_id="A1",
                concept="learning rate",
                description="Compare step size to cautious downhill steps.",
                claim_ids=("C1",),
            ),
        ),
        misconceptions=(
            PedagogyMisconception(
                misconception_id="M1",
                misconception="Move with the gradient when minimizing.",
                correction="Move against the gradient locally.",
                claim_ids=("C1",),
            ),
        ),
        assessment_probes=(
            AssessmentProbe(
                probe_id="P1",
                prompt="Why move against the gradient?",
                expected_outcome="To reduce loss locally.",
                objective_ids=("O1",),
            ),
            AssessmentProbe(
                probe_id="P2",
                prompt="What can oversized steps do?",
                expected_outcome="Overshoot useful updates.",
                objective_ids=("O2",),
            ),
        ),
    )
    return brief, pack, graph, report, pedagogy


def build_script(pedagogy):
    return LessonScript(
        script_id="script.gradient",
        pedagogy_plan_id=pedagogy.plan_id,
        segments=(
            ScriptSegment(
                segment_id="S01",
                spoken_text="Today we will build an intuition for gradient descent.",
                subtitle_text="Build intuition for gradient descent.",
                spoken_language="en",
                subtitle_language="en",
                objective_ids=("O1",),
                teaching_function=TeachingFunction.INTRODUCE,
            ),
            ScriptSegment(
                segment_id="S02",
                spoken_text="Gradient descent changes parameters in a direction intended to reduce the loss.",
                subtitle_text="Update parameters to reduce loss.",
                spoken_language="en",
                subtitle_language="en",
                claim_ids=("C1",),
                objective_ids=("O1",),
                teaching_function=TeachingFunction.EXPLAIN,
            ),
            ScriptSegment(
                segment_id="S03",
                spoken_text="Imagine taking a careful downhill step, checking the slope again after each move.",
                subtitle_text="Take a careful downhill step.",
                spoken_language="en",
                subtitle_language="en",
                claim_ids=("C1",),
                objective_ids=("O1", "O2"),
                teaching_function=TeachingFunction.DEMONSTRATE,
            ),
            ScriptSegment(
                segment_id="S04",
                spoken_text="What risk appears when a step is too aggressive?",
                subtitle_text="What can an oversized step cause?",
                spoken_language="en",
                subtitle_language="en",
                objective_ids=("O2",),
                teaching_function=TeachingFunction.CHECK,
            ),
            ScriptSegment(
                segment_id="S05",
                spoken_text="The key idea is to use the gradient to choose updates that reduce loss while reasoning carefully about step size.",
                subtitle_text="Use gradient information to reduce loss.",
                spoken_language="en",
                subtitle_language="en",
                claim_ids=("C1",),
                objective_ids=("O1", "O2"),
                teaching_function=TeachingFunction.SUMMARIZE,
            ),
        ),
    )


def main() -> int:
    brief, pack, graph, report, pedagogy = build_fixture()
    if report.approved_claim_ids != ("C1",):
        raise SystemExit("SCRIPT_AGENT=FAIL fixture Fact Verification")

    task = build_script_agent_task(brief, pack, graph, report, pedagogy)
    context = json.loads(task["context"])
    if [claim["claim_id"] for claim in context["selected_fact_claims"]] != ["C1"]:
        raise SystemExit("SCRIPT_AGENT=FAIL selected claim context")

    script = build_script(pedagogy)
    validation = validate_lesson_script(
        script,
        brief=brief,
        pack=pack,
        graph=graph,
        fact_report=report,
        pedagogy=pedagogy,
    )
    require_visual_director_ready(validation)
    if not validation.ready_for_visual_director:
        raise SystemExit("SCRIPT_AGENT=FAIL valid script rejected")

    missing_claim_script = script.model_copy(
        update={
            "segments": tuple(
                segment.model_copy(update={"claim_ids": ()})
                for segment in script.segments
            )
        }
    )
    missing = validate_lesson_script(
        missing_claim_script,
        brief=brief,
        pack=pack,
        graph=graph,
        fact_report=report,
        pedagogy=pedagogy,
    )
    if ScriptIssue.CLAIM_SET_MISMATCH not in missing.issues:
        raise SystemExit("SCRIPT_AGENT=FAIL dropped claim not detected")

    print("SCRIPT_AGENT=PASS")
    print("claim_ids_preserved=PASS")
    print("teaching_function_per_segment=PASS")
    print("factual_segment_claim_binding=PASS")
    print("objective_coverage=PASS")
    print("no_visual_coordinates_or_implementation_code=PASS")
    print("visual_director_readiness_gate=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
