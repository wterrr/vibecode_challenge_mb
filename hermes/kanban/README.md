# Kanban Durability

This stage uses **native Hermes Kanban** as the durable work queue for long-running LearnFlow production.

Status: IMPLEMENTED_AWAITING_CI.

## Purpose

The accepted synchronous `lesson_pipeline/` remains the source of truth for stage behavior and deterministic gates. Kanban adds persistence, dependencies, claims, restart recovery, bounded retry, human handoff, and durable audit history around that pipeline.

No second task database, message bus, or scheduler is implemented in LearnFlow.

## Durable lesson DAG

    research-evidence
          ↓
       pedagogy
          ↓
        script
          ↓
    visual-direction
          ↓
        render
          ↓
        review

Every card uses a native Hermes idempotency key and a shared durable workspace under the operator-selected runtime root. Mutable task state lives only in the native Kanban SQLite board.

## Worker profiles

Reviewed templates create exactly three Hermes profiles:

- `learnflow-research`
- `learnflow-production`
- `learnflow-review`

Profiles contain no secrets. Project-local Skills are **not trusted by default**. An operator must first review the accepted Skills and explicitly opt into project trust when installing profiles.

## Recovery semantics

Native Hermes owns:

- dependency gating (`todo → ready`);
- atomic claim (`ready → running`);
- run identity and claim leases;
- stale/crashed worker recovery;
- bounded task retry/failure breaker;
- persistent comments/events/runs;
- reclaim/resume after restart.

LearnFlow does not mirror these mutable statuses into another store. `durable_job.json` contains only stable job/template/workspace/task-ID mapping.

## Boundary

Kanban must not re-decide evidence validity, pedagogy, script correctness, visual semantics, geometry, budget policy, repair ownership, or publication authorization.

Runtime Governance remains authoritative for provider/tool cost/retry limits. Kanban `max_retries` is a worker/task failure breaker, not a replacement for provider retry accounting.

## Verification

    python scripts/verify_kanban_durability.py
    pytest -q --confcutdir=tests/hermes tests/hermes/test_durable_jobs.py
    python scripts/verify_v2_core_freeze.py

The pinned-runtime verifier additionally proves idempotent seeding, native dependency promotion, state persistence across connection restart, native reclaim/resume, preservation of completed work, shared workspace, and three valid worker profiles.
