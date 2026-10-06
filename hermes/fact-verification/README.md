# Fact Verification

This stage gates research claims before they can be used as factual narration.

## Authority split

- Hermes may perform semantic evidence judgment and emit a structured `SemanticFactReview`.
- LearnFlow deterministic verification has final authority over whether a claim may enter narration.
- A Hermes `SUPPORTED` verdict cannot override missing source-grounded evidence.
- A Hermes `CONTRADICTED` or `UNCERTAIN` verdict can make an otherwise grounded claim fail closed.

## Deterministic checks

- every ResearchPack claim is evaluated exactly once;
- source grounding requires a real path from a `SOURCE` node through `SUPPORTS` / `DERIVES` edges;
- claim-only derivation cycles do not count as evidence;
- cycles with a real source-supported branch converge correctly through fixed-point propagation;
- any explicit `CONTRADICTS` edge flags the target claim;
- unsupported, contradicted, or semantically uncertain claims are not eligible for factual narration;
- every factual narration must reference at least one known approved `claim_id`.

## Scope boundary

This stage does not generate pedagogy, lesson script, storyboard, visual geometry, rendering, QA repair, hooks/budget enforcement, Skills, or Kanban.

## Verification

```bash
python scripts/verify_fact_verification.py
pytest -q --confcutdir=tests/hermes tests/hermes/test_fact_verification.py
python scripts/verify_v2_core_freeze.py
```

Exact pinned Hermes contract compatibility:

```bash
HERMES_HOME="$PWD/.hermes_runtime/fact-verification/verify-home" \
  .hermes_runtime/hermes-agent/venv/bin/python \
  scripts/verify_hermes_fact_verification.py
```
