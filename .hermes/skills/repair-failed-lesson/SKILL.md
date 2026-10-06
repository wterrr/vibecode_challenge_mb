---
name: repair-failed-lesson
description: "Repair a failed LearnFlow lesson selectively by consuming authoritative QA results and following Agent-Aware QA ownership instead of letting an agent repair the wrong layer."
platforms: [linux, macos, windows]
version: 1.0.0
metadata:
  hermes:
    tags: [learnflow, qa, repair, selective-repair, routing]
    related_skills: [build-evidenced-lesson, investigate-lesson-facts, review-lesson-before-publication]
when_to_use:
  - Authoritative scene or video QA reports a blocking issue.
  - A LearnFlow artifact chain failed a readiness or publication review and needs local repair.
when_not_to_use:
  - The lesson has no authoritative QA failure and simply needs to be built from scratch.
  - The user wants an unrelated Core engine change.
---

# Repair a Failed Lesson

Repair only through the owner selected by Agent-Aware QA. A repair intent is not permission to cross architecture boundaries.

## Procedure

1. Load the current typed artifact chain and the authoritative QA result:
   - scene routing starts from `QualityGateResult`;
   - video routing starts from `VideoCriticResult`.
2. Run deterministic **Agent-Aware QA** routing.
3. Validate every referenced scene, node, relation, group, claim, segment, and objective against the current artifact chain.
4. If the router emits a blocker with no repair owner, stop. Do not invent an owner.
5. Dispatch each repair intent only to its assigned owner.
6. Preserve unaffected content and IDs wherever the accepted repair task requires selective repair.
7. Re-run the deterministic gate for the repaired artifact.
8. Invalidate and rebuild only downstream artifacts affected by the accepted change.
9. Re-run authoritative QA before considering the lesson repaired.
10. Keep Runtime Governance active for every governed agent/tool/provider operation.

## Ownership Matrix

- unsupported / contradicted / uncertain evidence → Research Orchestration;
- factual narration mismatch or narration redundancy → Script Agent;
- concept progression / pedagogical alignment → Pedagogy Agent;
- semantic visual intent/modality → Visual Director;
- bbox/layout/readability/routing/motion patches supported by Core → deterministic Core Repair;
- pacing/transition mechanics → deterministic Core temporal/transition repair.

## Hard Rules

- Never turn a Core repair intent into a Hermes task.
- Never turn a semantic visual issue into pixel coordinates or manual layout.
- Never rewrite factual evidence in Script to hide a Research failure.
- Never rebuild the whole video for a local repair unless dependency invalidation proves it necessary.
- Never ignore stale/unknown scope references.
- Never bypass strict critic failure policy, budget refusal, or publication policy.
- Do not use durable Kanban execution in this procedure.

## Completion Criteria

Repair is complete only after the corrected artifact passes its deterministic gate, affected downstream artifacts are rebuilt selectively, authoritative QA is non-blocking, and repair history remains explainable.

Read `references/repair-routing.md` for the owner/action matrix.
