#!/usr/bin/env python3
"""Build and cross-validate a coherent Agent Contracts artifact chain."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_contracts import (
    AgentRun,
    AgentRunStatus,
    AgentStageRecord,
    ArtifactRef,
    AssessmentProbe,
    BudgetLedger,
    BudgetLimits,
    BudgetSpend,
    BudgetUsage,
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
    ResearchMisconception,
    ResearchPack,
    ScriptSegment,
    SourceRecord,
    SourceType,
    Storyboard,
    StoryboardScene,
    TeachingFunction,
)


def build_chain():
    brief = LearningBrief(
        brief_id="brief.gradient-descent",
        user_query="Explain gradient descent to a beginner.",
        learner_level="beginner",
        target_duration_minutes=3,
        language="en",
        constraints=("avoid calculus-heavy derivations",),
    )
    source = SourceRecord(
        source_id="source.textbook",
        source_type=SourceType.BOOK,
        title="Introductory optimization text",
        locator="book:optimization:intro",
    )
    pack = ResearchPack(
        pack_id="research.gradient-descent",
        topic="gradient descent",
        concepts=("gradient", "loss", "learning rate"),
        sources=(source,),
        claims=(
            ResearchClaim(
                claim_id="C001",
                statement="Gradient descent iteratively updates parameters to reduce an objective.",
                source_ids=(source.source_id,),
                confidence=0.99,
                concept_ids=("gradient", "loss"),
            ),
        ),
        misconceptions=(
            ResearchMisconception(
                misconception_id="misconception.direction",
                statement="The update moves in the gradient direction.",
                correction="For minimization, the update moves against the gradient direction.",
                claim_ids=("C001",),
            ),
        ),
    )
    evidence = EvidenceGraph(
        graph_id="evidence.gradient-descent",
        research_pack_id=pack.pack_id,
        source_ids=(source.source_id,),
        claim_ids=("C001",),
        edges=(
            EvidenceEdge(
                edge_id="edge.source-to-c001",
                from_kind=EvidenceNodeKind.SOURCE,
                from_id=source.source_id,
                to_claim_id="C001",
                relation=EvidenceRelation.SUPPORTS,
            ),
        ),
    )
    evidence.validate_against_research_pack(pack)

    pedagogy = PedagogyPlan(
        plan_id="pedagogy.gradient-descent",
        brief_id=brief.brief_id,
        research_pack_id=pack.pack_id,
        evidence_graph_id=evidence.graph_id,
        learning_objectives=(
            LearningObjective(
                objective_id="objective.update-rule",
                description="Explain why minimization moves opposite the gradient.",
                assessment_criterion="Learner can identify the correct update direction.",
            ),
        ),
        concept_order=("loss", "gradient", "learning rate"),
        worked_examples=(
            PedagogyExample(
                example_id="example.hill",
                concept="gradient",
                description="Use a downhill slope analogy.",
                claim_ids=("C001",),
            ),
        ),
        misconceptions=(
            PedagogyMisconception(
                misconception_id="pedagogy-misconception.direction",
                misconception="Move with the gradient to minimize.",
                correction="Move against the gradient to reduce the objective locally.",
                claim_ids=("C001",),
            ),
        ),
        assessment_probes=(
            AssessmentProbe(
                probe_id="probe.direction",
                prompt="Which direction should a minimization update move?",
                expected_outcome="Opposite the gradient.",
                objective_ids=("objective.update-rule",),
            ),
        ),
    )
    pedagogy.validate_against(brief, pack, evidence)

    script = LessonScript(
        script_id="script.gradient-descent",
        pedagogy_plan_id=pedagogy.plan_id,
        segments=(
            ScriptSegment(
                segment_id="segment.intro",
                spoken_text="Gradient descent repeatedly changes parameters to reduce a loss.",
                subtitle_text="Gradient descent repeatedly changes parameters to reduce a loss.",
                spoken_language="en",
                subtitle_language="en",
                claim_ids=("C001",),
                objective_ids=("objective.update-rule",),
                teaching_function=TeachingFunction.EXPLAIN,
                emphasis=("reduce a loss",),
            ),
        ),
    )
    script.validate_against(evidence, pedagogy)

    storyboard = Storyboard(
        storyboard_id="storyboard.gradient-descent",
        script_id=script.script_id,
        scenes=(
            StoryboardScene(
                scene_id="scene.downhill",
                script_segment_ids=("segment.intro",),
                teaching_function=TeachingFunction.EXPLAIN,
                visual_intent="Show a semantic downhill-loss metaphor with no pixel geometry.",
                concept_refs=("gradient", "loss"),
                continuity_keys=("concept:loss",),
            ),
        ),
    )
    storyboard.validate_against_script(script)

    refs = tuple(
        ArtifactRef(
            artifact_type=kind,
            artifact_id=artifact_id,
            content_sha256=artifact.content_sha256(),
        )
        for kind, artifact_id, artifact in (
            ("learning-brief", brief.brief_id, brief),
            ("research-pack", pack.pack_id, pack),
            ("evidence-graph", evidence.graph_id, evidence),
            ("pedagogy-plan", pedagogy.plan_id, pedagogy),
            ("lesson-script", script.script_id, script),
            ("storyboard", storyboard.storyboard_id, storyboard),
        )
    )
    run = AgentRun(
        run_id="run.gradient-descent",
        brief_id=brief.brief_id,
        root_agent_id="lesson-director",
        status=AgentRunStatus.SUCCEEDED,
        artifacts=refs,
        stages=(
            AgentStageRecord(
                step_id="step.contract-smoke",
                stage_name="Agent Contracts verification",
                agent_id="contract-verifier",
                status=AgentRunStatus.SUCCEEDED,
                input_artifact_ids=(brief.brief_id,),
                output_artifact_ids=(storyboard.storyboard_id,),
            ),
        ),
    )
    budget = BudgetLedger(
        ledger_id="budget.gradient-descent",
        max_usd=1.0,
        spent=BudgetSpend(llm=0.10, vlm=0.03, image=0.05),
        limits=BudgetLimits(subagent_calls=12, vlm_repairs=8, image_generations=10),
        usage=BudgetUsage(subagent_calls=1, vlm_repairs=0, image_generations=0),
    )
    return brief, pack, evidence, pedagogy, script, storyboard, run, budget


def main() -> int:
    artifacts = build_chain()
    names = [type(item).__name__ for item in artifacts]
    expected = [
        "LearningBrief",
        "ResearchPack",
        "EvidenceGraph",
        "PedagogyPlan",
        "LessonScript",
        "Storyboard",
        "AgentRun",
        "BudgetLedger",
    ]
    if names != expected:
        raise SystemExit(f"AGENT_CONTRACTS=FAIL exports={names!r}")

    hashes = [item.content_sha256() for item in artifacts]
    if len(hashes) != len(set(hashes)):
        raise SystemExit("AGENT_CONTRACTS=FAIL duplicate canonical artifact hashes")

    budget = artifacts[-1]
    print("AGENT_CONTRACTS=PASS")
    print("chain=" + " -> ".join(names[:6]))
    print("runtime=AgentRun budget=BudgetLedger")
    print(f"remaining_usd={budget.remaining_usd:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
