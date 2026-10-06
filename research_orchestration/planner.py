"""Build the bounded Hermes delegation plan for LearnFlow research."""

from __future__ import annotations

import json

from agent_contracts import LearningBrief, ResearchPack, EvidenceGraph

from .models import (
    ConceptResearchFindings,
    EvidenceResearchFindings,
    MAX_DELEGATION_DEPTH,
    MAX_SPECIALIST_RESEARCHERS,
    MisconceptionResearchFindings,
    ResearchOrchestrationPlan,
    ResearchOrchestrationResult,
    ResearchRole,
    SpecialistTask,
)


def _schema(model_type) -> dict:
    return model_type.model_json_schema()


def build_research_orchestration_plan(brief: LearningBrief) -> ResearchOrchestrationPlan:
    """Create the exact three-role research fan-out passed to a Hermes orchestrator child."""

    shared = {
        "brief_id": brief.brief_id,
        "user_query": brief.user_query,
        "learner_level": brief.learner_level,
        "language": brief.language,
        "constraints": list(brief.constraints),
        "rules": [
            "Do not invent sources.",
            "Preserve stable source identifiers and locators.",
            "Return only JSON matching the supplied output schema.",
            "Do not render, publish, or modify LearnFlow Core.",
        ],
    }

    tasks = (
        SpecialistTask(
            role=ResearchRole.CONCEPT,
            goal="Map the concepts and unresolved questions needed to teach this topic accurately.",
            context=json.dumps(
                {
                    **shared,
                    "focus": "concept definitions, terminology, prerequisite distinctions, open questions",
                    "provenance_rule": "Do not make factual claims that require sources in this role.",
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            output_schema=_schema(ConceptResearchFindings),
        ),
        SpecialistTask(
            role=ResearchRole.EVIDENCE,
            goal="Collect source-grounded factual claims and explicit evidence links for the lesson.",
            context=json.dumps(
                {
                    **shared,
                    "focus": "authoritative sources, claim statements, confidence, source-to-claim evidence edges",
                    "provenance_rule": (
                        "Every claim must reference declared source_ids; every source keeps its original locator. "
                        "Namespace source_id and claim_id values with the prefix 'evidence.' so sibling outputs cannot collide."
                    ),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            output_schema=_schema(EvidenceResearchFindings),
        ),
        SpecialistTask(
            role=ResearchRole.MISCONCEPTION,
            goal="Identify learner misconceptions and useful examples tied to evidence-backed claims.",
            context=json.dumps(
                {
                    **shared,
                    "focus": (
                        "common misconceptions, corrections, examples, plus the sources and factual claims "
                        "needed to support those corrections/examples"
                    ),
                    "provenance_rule": (
                        "This child is isolated from Evidence Researcher. Create only LOCAL source_ids/claim_ids "
                        "backed by your own sources; namespace them with prefix 'misconception.'. "
                        "Misconceptions/examples may reference only those local claim_ids."
                    ),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            output_schema=_schema(MisconceptionResearchFindings),
        ),
    )

    return ResearchOrchestrationPlan(
        plan_id=f"research-plan:{brief.brief_id}",
        brief_id=brief.brief_id,
        max_delegation_depth=MAX_DELEGATION_DEPTH,
        max_specialists=MAX_SPECIALIST_RESEARCHERS,
        specialist_tasks=tasks,
    )


def build_director_delegate_task(brief: LearningBrief) -> dict:
    """Return the single native Hermes delegate_task entry for the Research Orchestrator."""

    plan = build_research_orchestration_plan(brief)
    specialist_payload = [
        {
            "role": task.role.value,
            "goal": task.goal,
            "context": task.context,
            "output_schema": task.output_schema,
        }
        for task in plan.specialist_tasks
    ]
    context = {
        "learning_brief": json.loads(brief.to_canonical_json()),
        "research_plan": {
            "plan_id": plan.plan_id,
            "max_delegation_depth": plan.max_delegation_depth,
            "max_specialists": plan.max_specialists,
            "specialist_tasks": specialist_payload,
        },
        "execution_contract": [
            "Use native Hermes delegate_task exactly once for the specialist fan-out.",
            "Dispatch no more than the three supplied specialist tasks.",
            "Each specialist receives only its own goal/context/output_schema.",
            "No specialist may depend on a sibling specialist's IDs or output.",
            "Do not ask a specialist to delegate further.",
            "Preserve source_id, locator, claim_id and evidence-edge provenance exactly.",
            "Synthesize a ResearchPack and EvidenceGraph; do not perform Fact Verification in this stage.",
            "Return only JSON matching ResearchOrchestrationResult.",
        ],
    }
    return {
        "goal": (
            "Act as LearnFlow Research Orchestrator. Fan out the supplied specialist research tasks "
            "through Hermes native delegation, then synthesize the typed research artifacts."
        ),
        "context": json.dumps(context, ensure_ascii=False, sort_keys=True),
        "output_schema": ResearchOrchestrationResult.model_json_schema(),
    }


def expected_hermes_limits() -> dict[str, int | bool]:
    return {
        "max_spawn_depth": MAX_DELEGATION_DEPTH,
        "max_concurrent_children": MAX_SPECIALIST_RESEARCHERS,
        "oneshot_max_children": MAX_SPECIALIST_RESEARCHERS,
        "orchestrator_enabled": True,
    }
