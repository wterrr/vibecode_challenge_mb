# LearnFlow V2D — Final Offline Semantic Consistency & Evidence Redaction Audit

**Date:** 2026-10-08  
**Scope:** One offline checkpoint on `chatgpt/live-v2d-gpt6-luna-paid-pilot`. No V3 implementation and no paid API requests.  
**Historical original:** [Action #181](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37721597623), commit `cb605dc1104e87f9ac8640db2a6c49ceb27a159b`. Retained unchanged.  
**Code commits:** `373bf557b5d24f738fb4e8472f874130db972e5f`, `0113b3a526a33d520a98f5dcf7d6a46b1ce09abd`.

## Final checkpoint verdict — PASS (offline guard), NOT a retroactive #181 semantic PASS

### Reproduced historical defect (MEASURED)

`concept_registry.json` entry `c_workedexam_e8f1933850` describes finding **16** in `[2,5,8,12,16,23,38]`. However, `script.json`, `storyboard.json` and `scenegraphs/002.json` describe finding **24** in `[3,7,12,18,24,31,40]`. SceneGraph's `found` node uses that stale `concept_ref`/semantic key.

Running the new validator on the actual extracted #181 JSON produces:
`HISTORICAL_181_SEMANTIC=FAIL_AS_EXPECTED`, `SEMANTIC_WORKED_EXAMPLE_MISMATCH`, scene `scene-worked-trace`. The original video and archived artifacts were not modified.

### Changes on the pilot branch (FACT)

- `live_evaluation/semantic_consistency.py`: fail-closed deterministic pilot validator of numeric worked examples across ConceptRegistry, the selected script segment's subtitle, storyboard visual intent and SceneGraph target/array/result nodes. It also enforces registry label↔canonical key↔deterministic ID and SceneGraph concept-ref semantic key consistency when those keys are present.
- `live_evaluation/pilot.py`: invokes validator immediately after typed lesson pipeline returns, before external TTS and production rendering. Frozen Core V2 is unchanged.
- `tests/hermes/test_final_v2_semantic_consistency.py`: eight positive/negative regressions (historical mismatch, corrected example, contradictory found node, unrelated non-example, stale registry key, stale node key, allowlisted export, blocked credential).
- `scripts/export_live_v2d_evidence.py` and `.github/workflows/live-v2d-evaluation.yml`: allowlisted upload from `.hermes_runtime/approved-live-v2d-evidence`, replacing the old upload of the entire Hermes runtime directory. Excludes `hermes-home/`, `auth.json`, `governance/`, raw logs, caches and state DB. JSON evidence matching known credential patterns causes export failure.
- `.github/workflows/final-v2-offline-preflight.yml`: includes these regressions in the offline-only path.

This is a deliberately **narrow numeric worked-example validator**, not a universal semantic-equivalence oracle. It does not prove that every free-text analogy, arbitrary algorithm trace, or unnumbered concept is semantically consistent.

### Historical export security review (MEASURED)

Historical Action #181 ZIP has **74 entries** including `hermes-home/auth.json` and runtime state/cache. Presence of an authentication file is verified; an exposed plaintext provider API key was **not established**. The new allowlist exporter was replayed locally over the unaltered #181 data, yielding **52 evidence files**, including `final.mp4` and `concept_registry.json`, excluding `auth.json` and Hermes runtime/home files. Future exports require the new allowlist; no paid production run was performed to generate an additional ZIP.

### Offline CI verification (MEASURED)

[Final V2 Offline Preflight #4 — run 37723264679](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37723264679) on commit `0113b3a526a33d520a98f5dcf7d6a46b1ce09abd`:

| Check | Outcome |
| --- | --- |
| `python scripts/verify_v2_core_freeze.py` | **CORE_FREEZE=PASS** |
| `python scripts/verify_live_v2d_evaluation.py` | **LIVE_V2D_CONTRACT=PASS** |
| Hermes/subtitle/semantic regressions | **87 passed** |
| Frozen V2 renderer regressions | **14 passed, 5 skipped** |
| Paid OpenRouter dispatch/API | **NONE** |
| Main branch and frozen Core | **UNCHANGED** |

Only an automatic **Final V2 Offline Preflight** workflow was triggered by the pilot-branch push. Action #181 was not retried or edited.

### PLAN_V3 drafting decision — CONDITIONAL

This checkpoint closes the **missing semantic-drift detection** and unsafe future evidence-export path. It does **not** repair the historical model-generated example mismatch in #181, nor turn the three-card video into an algorithm-state animation. Therefore:

1. Keep #181 as a real technical end-to-end SUCCESS with an explicitly documented historical semantic-consistency defect.
2. A human reviewer/user must accept the video's minimum readable factual content and acknowledge the historical exception before treating #181 as sufficient evidence to **draft** `PLAN_V3.md` under the budget-constrained waiver.
3. Reliability ≥98%, a 100-topic live study, human visual quality benchmark and learning-outcome improvements remain **UNMEASURED/DEFERRED**.
4. Drafting `PLAN_V3.md` does not authorize V3 implementation.

**No automatic paid rerun, no topic/model substitution, no changes to `main`, and no V3 implementation.**
