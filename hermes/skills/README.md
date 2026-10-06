# LearnFlow Skills

This stage packages stable LearnFlow operating procedures as native Hermes project-local skills.

Status: IMPLEMENTED_AWAITING_CI.

## Accepted skill candidates

- `build-evidenced-lesson` — complete accepted lesson pipeline;
- `investigate-lesson-facts` — Research Orchestration + Fact Verification procedure;
- `repair-failed-lesson` — authoritative QA → Agent-Aware ownership → selective repair procedure;
- `review-lesson-before-publication` — final provenance/QA/governance readiness review.

Each project skill lives under `.hermes/skills/<name>/SKILL.md` and may use only `references/` support files in this checkpoint. No skill contains scripts, templates, renderer code, or another orchestrator.

## Trust and review

Pinned Hermes discovers repo-local `.hermes/skills` only for an explicitly trusted project root and security-scans each project skill. CI uses an isolated profile that trusts the checkout solely for verification.

The repository does **not** auto-add itself to `skills.trusted_project_dirs`. Production activation remains an operator decision after manual review, matching the PLAN requirement that skills are reviewed before production use.

## Boundary

Skills are procedures. They reuse the accepted typed stages, deterministic gates, capability plugin, Agent-Aware QA routing, and Runtime Governance. They cannot change ownership or make blocked artifacts valid by instruction.

Kanban Durability is intentionally not implemented in this stage.

## Verification

    python scripts/verify_learnflow_skills.py
    pytest -q --confcutdir=tests/hermes tests/hermes/test_learnflow_skills.py
    python scripts/verify_v2_core_freeze.py

The pinned-runtime verifier additionally proves exact Hermes project-skill discovery, security-scan acceptance, `skill_view` loading, and linked-reference resolution.
