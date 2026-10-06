# Research Orchestration

This stage uses Hermes native `delegate_task` rather than implementing a parallel agent framework.

## Topology

```text
Lesson Director (depth 0)
  -> Research Orchestrator (depth 1)
       -> Concept Researcher (depth 2 leaf)
       -> Evidence Researcher (depth 2 leaf)
       -> Misconception Researcher (depth 2 leaf)
```

Hard limits:

- `delegation.max_spawn_depth = 2`
- `delegation.max_concurrent_children = 3`
- `delegation.oneshot_max_children = 3`
- leaf researchers cannot call `delegate_task`
- each child receives only its own goal/context/output schema

## LearnFlow-owned responsibilities

- define the three bounded specialist roles;
- build typed Hermes task specifications;
- require structured specialist output schemas;
- preserve `source_id`, source `locator`, `claim_id`, and evidence edges;
- deterministically merge specialist findings into `ResearchPack` + `EvidenceGraph`;
- reject unknown claim/source references.

## Hermes-owned responsibilities

- create isolated child conversations;
- provide native `delegate_task` fan-out;
- enforce runtime delegation depth/concurrency;
- strip recursive delegation from leaf children;
- validate per-child `output_schema`;
- maintain child session/trajectory lifecycle.

## Non-goals

This stage does not implement Fact Verification, contradiction resolution, pedagogy generation, script generation, Visual Director behavior, rendering, hooks/budget enforcement, Skills, or Kanban.

## Verification

```bash
python scripts/verify_research_orchestration.py
pytest -q --confcutdir=tests/hermes tests/hermes/test_research_orchestration.py
python scripts/verify_v2_core_freeze.py
```

Pinned Hermes integration:

```bash
HERMES_HOME="$PWD/.hermes_runtime/research-orchestration/verify-home" \
  .hermes_runtime/hermes-agent/venv/bin/python \
  scripts/verify_hermes_research_delegation.py
```
