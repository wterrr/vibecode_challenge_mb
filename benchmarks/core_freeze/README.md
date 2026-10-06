# LearnFlow V2 Core Freeze

Status: **COMPLETE** once this freeze record is merged to `main`.

This directory closes the boundary between the accepted deterministic V2 Core and V2D/Hermes.

## Frozen identities

- Accepted Core engine commit: `fdad3db1340d8b28175ab5382d800ff79df9a8a0`
- Corrected benchmark: `v2-core-gate-v2`
- Official evidence-freeze commit: `4b2cc7887773a8fb81dee36010fcae3bc2015ccb`
- Official workflow run: `37412433812`
- Official artifact: `11389249199`
- V1 rollback/reference commit: `f6dae0e8510a6db8fc49a761eddc2a055ffaefda`
- V1 baseline: `v1-cp10`

The machine-readable source of truth is `manifest.json`.

## What is protected

The manifest pins Git blob identities for the accepted Core implementation under:

`concepts`, `core`, `core_gate`, `layout`, `motion`, `qa`, `render`,
`repair`, `scenegraph`, `transitions`, and `videoqa`.

It also freezes the corrected benchmark contract/runner, the V1 baseline capture contract,
and the dependency declaration files used by the accepted engine.

The official compact Core Gate evidence is independently pinned so historical evidence cannot
silently drift after Hermes work starts.

## Hermes boundary

Hermes/V2D may add a control plane **outside** the protected Core namespaces and consume the
typed artifacts/contracts exposed by Core. Hermes must not patch layout, renderer, motion,
deterministic QA, repair, or the frozen benchmark in place.

If a real Core defect requires one of those files to change, the sequence is:

```text
declare CORE UNFREEZE
→ change Core + focused regressions
→ full V2 regression
→ rerun corrected frozen Core Gate (or version benchmark only if old metric is invalid)
→ freeze new official evidence
→ publish a new Core Freeze manifest/version
```

## Rollback boundary

V1 CP10 remains the rollback/reference boundary. The historical freeze commit is pinned for
reproduction; product fallback should prefer the isolated V1 runtime under `app/` rather than
silently rewriting V1 during V2D integration.

## Verification

Run:

```bash
python scripts/verify_v2_core_freeze.py
python scripts/evaluate_v2_core_gate.py
pytest -q --confcutdir=tests/v2 tests/v2/test_core_freeze.py tests/v2/test_core_gate.py
```

A protected file edit, a new implementation file inside a protected Core namespace, evidence drift,
or a rollback/gate identity change fails closed.

## Evidence limitations retained

This freeze does not upgrade the claims of the benchmark:

- `static_composition_proxy_v2` is not a human aesthetic score;
- persistent-object MOVE is not covered end-to-end by the three frozen lessons;
- V1's deterministic 40-character subtitle truncation is parity evidence, not production subtitle UX;
- Python transitive dependencies are not lockfile-proven by this record.
