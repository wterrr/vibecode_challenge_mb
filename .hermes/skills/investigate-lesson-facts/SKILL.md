---
name: investigate-lesson-facts
description: "Investigate factual lesson content through LearnFlow Research Orchestration and deterministic Fact Verification while preserving provenance and blocked-claim semantics."
platforms: [linux, macos, windows]
version: 1.0.0
metadata:
  hermes:
    tags: [learnflow, research, evidence, provenance, fact-checking]
    related_skills: [build-evidenced-lesson, repair-failed-lesson]
when_to_use:
  - The user wants to research or verify lesson facts before pedagogy or narration.
  - A factual claim was routed back to Research by Agent-Aware QA.
when_not_to_use:
  - The task is only wording/pacing repair for an already approved claim.
  - The problem is geometry, layout, or visual rendering.
---

# Investigate Lesson Facts

Use the accepted Research Orchestration and Fact Verification stages. Do not create a separate research runtime.

## Procedure

1. Start from the current `LearningBrief` and preserve its topic/audience constraints.
2. Use the accepted Director → Research Orchestrator → bounded specialist topology.
3. Preserve source IDs, source locators, claim IDs, and claim-to-source/claim-to-claim provenance.
4. Merge specialist outputs only through the accepted research contract.
5. Run deterministic Fact Verification on the resulting `ResearchPack` and `EvidenceGraph`.
6. Treat deterministic missing evidence as blocking even if an LLM semantic reviewer says `SUPPORTED`.
7. Treat contradiction or unresolved semantic uncertainty as blocking.
8. Return the typed research/evidence/fact-verification artifacts. Do not write lesson narration in this skill.
9. When this skill is invoked for a routed repair, modify only the affected claims/evidence and preserve unrelated research.

## Hard Rules

- Declaring a source ID is not proof; a real grounded support/derivation path is required.
- Claim cycles cannot self-ground.
- Never fabricate a citation, locator, source, claim ID, or verification verdict.
- Never reclassify a blocked claim simply to unblock downstream stages.
- Never edit geometry, SceneGraph layout, renderer behavior, budgets, or publication state.
- Do not use durable Kanban execution here.

## Completion Criteria

The investigation is complete when all returned factual claims have explicit provenance and Fact Verification clearly identifies approved, contradicted, unsupported, and uncertain claims.

Read `references/evidence-policy.md` before resolving disputed factual claims.
