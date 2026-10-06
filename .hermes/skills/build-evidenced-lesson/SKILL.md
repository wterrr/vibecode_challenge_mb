---
name: build-evidenced-lesson
description: "Run the accepted LearnFlow lesson pipeline from a validated LearningBrief to verified semantic scenes and a rendered lesson without bypassing gates."
platforms: [linux, macos, windows]
version: 1.0.0
metadata:
  hermes:
    tags: [learnflow, education, lesson, orchestration, evidence, rendering]
    related_skills: [investigate-lesson-facts, repair-failed-lesson, review-lesson-before-publication]
when_to_use:
  - The user wants LearnFlow to create a complete evidence-grounded lesson or educational video.
  - The task should traverse the accepted typed research, pedagogy, script, visual, Core, and QA boundaries.
when_not_to_use:
  - The user only wants a factual investigation; use investigate-lesson-facts.
  - The user already has a failed lesson artifact chain that needs selective repair; use repair-failed-lesson.
  - The task is only a final release/readiness review; use review-lesson-before-publication.
---

# Build an Evidenced Lesson

Use the existing accepted LearnFlow stages. This skill is a procedure, not a second orchestration runtime.

## Preconditions

- Start from a schema-valid `LearningBrief`.
- Keep Core Freeze intact.
- Runtime governance must remain active for governed agent/provider/tool operations.
- Do not trust a model-generated artifact merely because it is syntactically valid; run the deterministic gate owned by that stage.

## Procedure

1. Run **Research Orchestration** using Hermes native bounded delegation.
2. Validate the returned `ResearchPack` and `EvidenceGraph`.
3. Run deterministic **Fact Verification**.
4. Stop factual progression if unsupported, contradicted, or unresolved claims are blocked.
5. Run **Pedagogy Agent** only with fact-approved research and require Script readiness.
6. Run **Script Agent** and require exact Pedagogy claim preservation plus Visual-Director readiness.
7. Build the deterministic lesson `ConceptRegistry`.
8. Run **Visual Director** and require semantic Storyboard/SceneGraph coverage plus Core readiness.
9. Hand Core-ready scenes through the accepted capability sequence:
   - `learnflow_create`
   - `learnflow_run`
   - `learnflow_render`
10. Assemble the final lesson with the existing deterministic Core public API.
11. Run authoritative scene/video QA.
12. If QA finds a problem, use **Agent-Aware QA** ownership routing. Do not improvise repair ownership.
13. Persist the replayable typed artifact chain and governance evidence.
14. Treat publication as a separate governed action. Rendering a video is not publication.

## Hard Rules

- Never invent or silently replace `claim_id`, concept identity, scene identity, or artifact provenance.
- Never send blocked factual claims to Pedagogy or Script.
- Never generate pixel coordinates, renderer implementation, codec commands, or arbitrary rendering code.
- Never repair geometry, timeline arithmetic, or deterministic Core patches in Hermes.
- Never skip a deterministic readiness gate because an upstream agent appears confident.
- Never bypass hard budget reservations or publication policy.
- Never convert this procedure into a parallel scheduler or alternative agent runtime.
- Do not use durable Kanban execution in this procedure.

## Failure Handling

- Evidence failure → Research / Fact Verification boundary.
- Narration factual failure → Script Agent.
- Pedagogy progression/alignment failure → Pedagogy Agent.
- Semantic visual failure → Visual Director.
- Geometry/layout/temporal/selective patch failure → deterministic Core repair.
- Strict critic outage/invalid response → respect the authoritative QA blocker state.
- Budget/policy refusal → stop before dispatch; do not retry outside governance.

## Completion Criteria

A lesson is complete only when the accepted artifact chain is coherent, Core produced the video, authoritative QA is non-blocking, governance limits were respected, and the run remains replayable.

Read `references/artifact-chain.md` for the artifact and ownership checklist.
