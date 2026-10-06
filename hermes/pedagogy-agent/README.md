# Pedagogy Agent

This stage uses Hermes to turn fact-verified research into a structured `PedagogyPlan`, then applies a deterministic script-readiness gate.

**Status: PASS.** Accepted CI proves approved-claim-only context, forged-report rejection before Hermes exposure, pedagogy completeness, 13 regressions, pinned Hermes schema compatibility, and Core Freeze preservation.

## Hermes responsibilities

- propose learning objectives and measurable assessment criteria;
- identify learner-appropriate prerequisites;
- order researched concepts into a teaching progression;
- choose worked examples and analogies;
- surface misconceptions and corrections;
- create assessment probes.

Hermes receives only approved factual claims. Blocked claim content is withheld from the research view.

## Deterministic responsibilities

- bind the plan to the exact `LearningBrief`, `ResearchPack`, and `EvidenceGraph`;
- require the fact report to cover the exact research claim set;
- reject any fact report that approves a claim blocked by recomputed deterministic Fact Verification;
- reject examples/analogies/misconceptions that reference blocked claims;
- reject concept progression containing concepts absent from researched concepts;
- require every learning objective to be covered by at least one assessment probe;
- require at least one worked example or analogy before Script Agent.

## Boundary

This stage does not write narration, create `LessonScript`, create `SceneGraph`, choose visual geometry, render video, or implement later QA/budget/scheduling stages.
