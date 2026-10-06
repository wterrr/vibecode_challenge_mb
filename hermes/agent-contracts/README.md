# Agent Contracts

This stage defines the typed control-plane artifacts that connect Hermes reasoning stages without moving geometry, rendering code, or execution policy into the model layer.

## Public architecture contracts

The package `agent_contracts/` exports the eight artifacts required by `PLAN_V2.md`:

- `LearningBrief`
- `ResearchPack`
- `EvidenceGraph`
- `PedagogyPlan`
- `LessonScript`
- `Storyboard`
- `AgentRun`
- `BudgetLedger`

Supporting records and enums exist only to make these artifacts strict and composable.

## Invariants

- immutable Pydantic models with `extra="forbid"`;
- contract schema version `1.0`;
- deterministic canonical JSON and SHA-256 artifact digests;
- every research claim references declared source provenance;
- evidence edges close over declared source/claim IDs;
- evidence validation rejects claims without support/derivation edges;
- pedagogy binds to its `LearningBrief`, `ResearchPack`, and `EvidenceGraph`;
- lesson-script claim/objective references must resolve upstream;
- storyboard covers every script segment exactly once and in narrative order;
- storyboard exposes semantic visual intent only, with no pixel geometry or renderer controls;
- `AgentRun` stage artifact references resolve against an unambiguous artifact registry;
- run status cannot hide failed/blocked stage state;
- `BudgetLedger` cannot represent overspend or usage above configured limits.

## Explicit non-goals

This stage does not implement actual agents, delegation, research execution, fact-check execution, pedagogy generation, script generation, Visual Director generation, hooks, cost collection, or scheduling. Those are later named stages.

## Verification

```bash
python scripts/verify_agent_contracts.py
pytest -q --confcutdir=tests/hermes tests/hermes/test_agent_contracts.py
python scripts/verify_v2_core_freeze.py
```
