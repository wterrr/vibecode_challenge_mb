# Agent-Aware QA

Agent-Aware QA is the deterministic ownership layer between existing QA/VLM reports and the component allowed to repair each problem.

Status: PASS. Accepted CI run `37445667469` proves authoritative scene/video QA ingestion, deterministic ownership routing, 25 fail-closed regressions, exact pinned Hermes repair-task schema compatibility for Research/Script/Pedagogy/Visual, Core delegation blocking, and Core Freeze preservation.

## Ownership

- evidence unsupported / contradicted / uncertain → Research Orchestration;
- narration factual mismatch → Script Agent;
- pedagogical structure / concept progression → Pedagogy Agent;
- semantic visual intent / modality → Visual Director;
- deterministic geometry/render issues → Core Repair;
- video pacing and transition-continuity mechanics → deterministic Core temporal/transition repair;
- scene-critic patches already supported by the deterministic Repair Engine stay in Core;
- scene-level `CHANGE_VISUAL_INTENT` and other SceneGraph-regeneration requests return to Visual Director.

## Boundary

This stage routes repair intent only. It does not implement Hooks, Budget accounting, Skills, Kanban, retry policy, renderer code, geometry, or a new agent runtime.

Core-owned repair intent cannot be converted into a Hermes task. Agent repair tasks reuse the already accepted Research, Pedagogy, Script, and Visual Director task builders so their existing contracts and boundaries remain authoritative.

## Verification

    python scripts/verify_agent_aware_qa.py
    pytest -q --confcutdir=tests/hermes tests/hermes/test_agent_aware_qa.py
    python scripts/verify_v2_core_freeze.py

Pinned Hermes verification checks the routed agent task schemas against the exact accepted runtime.
