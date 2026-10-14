# V3-63 — Five-role creative storyboard admission & native decision impact

**Date:** 2026-10-14. **Research parent:** V3-62 Draft PR #98 exact HEAD `66671cecf8c11779cf5f5041df9254726a3d2de6`. **Prereg FIRST child commit:** `006caa9d5056da852a3751123ee429f57c07163f`, created before implementation. **Zero model API requests, no production prompts or V2 Core edits, no main merge.**

## Research gap and reusable implementation

The previous V3-62 3-domain native renderer passed physics/probability/chemistry technical checks but all five pedagogical narration acts, all source claims and all scene objects were written by the host. This proved only a **bounded source-coded animator**, not model creative planning. V3-56 defined five specialist roles (cognitive, narrative, visual, motion and visual critic) but did not carry them safely through the host renderer. V3-54 already introduced a model-shaped structured wire, though scoped to Attention.

V3-63 is a **five-role contract and renderer impact preflight**, not a provider experiment. The design allows a future explicitly supplied external JSON proposal; the acceptance implementation never treats an unknown origin as genuine model authorship. All positive CI proposals come from deterministic `test_only_packet` fixtures. Reviewer count is still zero.

## Cross-field five-role contract

- **Cognitive:** choose a registered misconception hypothesis and an approved probe tied to one of the three V3-62 host fact ledgers; label as hypothesized, not measured learner confusion.
- **Narrative:** choose problem-first vs contrast-first framing, invariant-focused vs transfer-question closure; narration **remains byte-identical host-owned**.
- **Visual:** require the exact domain representation and stable referent ID; choose whether to visually focus a persistent active object or a source-backed invariant.
- **Motion:** select a finite continuous or 4-step quantized transformation and a deliberate/short hold; witness remains after the transformation, with no fabricated word-level speech alignment.
- **Visual Critic:** bind the only permitted per-case risk and native before/after evidence requirement; prohibit early answer and invented quality ratings.

`learnflow_v3/five_role_creative_admission.py` uses strict typed Pydantic input, `extra=forbid`, bounded 16 KiB JSON with duplicate-key and nonfinite-value rejection; recomputes every host ledger SHA and checks all cross-role fields. No arbitrary generated Python, equations, model-created facts, model timestamps, or production flags may enter the trusted compiler. Candidate origin remains `EXTERNALLY_SUPPLIED_UNKNOWN_UNVERIFIED` or `HOST_TEST_ONLY`, never a provider proof.

`learnflow_v3/five_role_creative_native.py` reuses original frozen V3-62 geometry and fact witnesses, only adjusts source-safe attention focus and transformation schedule. A physics case renders **two physical H264 videos** with the same exact original V3-62 AAC packet bitstream and frame count. A decoded source-frame pixel difference must be nonzero; before/after verified state difference remains visible. Static pixel differences alone must never be labeled comprehension gains.

`scripts/run_v3_63_five_role_creativity.py` validates two positive host-test candidate variants on **each** of the three V3-62 topics, renders a matched pair only for the predeclared Physics 3m/s × 4s case, and reports `actual_model_generated_proposals=0`. The other topics undergo strict story validation and source-controlled rendering tests without two full native movies each.

## CI and results

Prereg path: `benchmarks/learnflowbench/v3/v3_63_five_role_creativity_preregister.json`.
Tests: `tests/v3/test_v3_63_five_role_creativity.py`.
Workflow: `.github/workflows/v3-63-five-role-creative-admission.yml`.

- **Strict tests:** [push run #38500464351](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38500464351), 38 tests passed, including malformed/duplicate/oversize wire, evidence hash, all 5 role identities, early reveal, invalid referents, fake publication and nonexistent renderer capabilities.
- **Native two-video gate:** same run, native job #115646074267. **Await final CI status and downloaded artifact**; do not conflate a queued or running job with PASS.
- No prior source video SHA, audio or narrator identity is changed on disk; new native candidate video SHA is receipt-bound.

## Known science and capability boundaries

This checkpoint still **does not** demonstrate that an LLM chose, invented, orchestrated or reviewed a full lesson. Candidate decision space is small and enumerated, both native variants are test fixtures, and all five narration strings remain host-authored. The visual difference may be technically observable without being aesthetically or pedagogically better. Two policies differ in pacing, focus and framing simultaneously, not a clean causal experiment of a single visual factor. Physics is the only predeclared full native candidate pair; cannot claim model-style generalization or wide subject support. There are no native utterance-word alignment receipts, actual external reviewer scores or human learning gains. It is important not to claim 3Blue1Brown-like quality.

**Gate interpretation:** after native CI PASS, `BOUNDED_5ROLE_ADMISSION_AND_NATIVE_EFFECT_PASS` only. Independent human quality `UNRATED`; real model-authored creativity `NOT_TESTED`; student learning `NOT_MEASURED`; production `BLOCKED`. The next scientific test, if approved, must use at least one genuinely external model-generated candidate from a new held-out user query under a preregistered single-request budget, with unchanged fact ledger and strict comparison against the deterministic fixture baseline. Otherwise retain NO-GO for true agent creative autonomy.
