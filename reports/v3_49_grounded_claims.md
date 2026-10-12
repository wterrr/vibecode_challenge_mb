# V3-49 — Generalizable Semantic Claim Grounding (bounded fraction-ratio transfer)

**Status:** Implementation submitted; exact-HEAD CI and actual decoded video evidence NOT YET ACCEPTED. Scientific scope is strictly equivalent fractions, not arbitrary lessons or six-domain generalization.

## Parent, preregistration, why this checkpoint
Stack directly on V3-48 Draft PR #82 exact parent `ed201a4cd31c429a6a979e3b857716c8afe0fa0d`. Preregistration committed FIRST on child branch at `96c08f2`, file `benchmarks/learnflowbench/v3/v3_49_grounded_claims_preregister.json`; new case selection was frozen before code.

V3-48 found that globally fixed F1/F2/F3 claim IDs valid for 1/2→2/4 are unsafe to reuse for new fractions. **We retain the old strict guards unchanged** and add a distinct, versioned host-evidence adapter rather than make V3-45 accept any mismatched value.

## Grounded claim contract
`learnflow_v3/grounded_fraction_claims.py` uses strict bounded `FractionTopic` with source numerator/denominator, multiplication factor and explicit expected target. The validator checks nonzero bounds, exact integer numerator and denominator transformation, reduction by `Fraction`, and whole geometry. Claim bundle consists of LOCAL topic-bound F1/F2/F3 roles, source-topic SHA256 and one SHA256 per independent fact payload. The proof, all visible numerical labels and narration are generated from the typed, verified topic, rather than accepted as arbitrary prose.

Each F1/F2/F3 role gets new exact content for its own evidence SHA. These roles **are not** a change to the frozen global V3-45 claim bank and must not be exported as that provider schema. Version is `v3-49-host-grounded-fractions-v1`. The code is host-owned and does not execute model-generated Python.

## Reuse-first native animation
Reuse V3-44's already verified `SemanticLesson` partition/ratio validator and finite Manim compiler; reuse V3-47's `subdivide/equivalence_link` grammar and audio-beat semantic windows; reuse native Docker Manim `network=none`, CMU font, espeak, deterministic WAV-to-H264/AAC mux, decoded frames, pixel visibility proof and V3-36 negative genuine-model provenance gate.

New-topic selection preregistered:
| ID | Role | Identity |
| --- | --- | --- |
| dev_two_thirds | development | 2/3 = 4/6, factor 2 |
| heldout_one_third | heldout new ratio | 1/3 = 3/9, factor 3 |
| heldout_three_quarters | heldout new ratio | 3/4 = 9/12, factor 3 |

These were not included in V3-45's frozen 1/2 = 2/4 fixture. They test bounded new values, more source cells and a different factor. They are **not** independent domain generalization; selection was preregistered rather than unbiased.

## Accept/reject gates
- 3 independently generated true native MP4s 1280×720 H264/AAC 15fps, physical speech/WAV budget matched to encoded frames.
- SHA256 source topic, claim bundle, Manim source and MP4; evidence graph stable through checked renderer. All source-tile subdivision guides and an algebra proof cue must be present in independently decoded frames at expected beat events.
- Offline claim mutations (mismatch, reused SHA, wrong proof, text/code injection, incorrect factors, unsafe topics), frozen V3-48/V3-47/V3-45 and V2/V3 benchmark/safety checks all fail closed.
- Provenance MUST remain `HOST_SYNTHETIC`; no fabricated model run, no live provider requests and no fallback to static card.
- Human preference/understanding **UNRATED**. Genuine provider compatibility **NOT TESTED**. Cross-domain generalization **NOT CERTIFIED**. Production **BLOCKED** regardless of offline pass; PR stays Draft and `main` unchanged.

## Actual empirical results
Exact-HEAD Action, video SHA, per-topic beat frame/pixel audit and negative-control status: **PENDING**. Do NOT call checkpoint FINAL PASS without inspecting real output from the exact HEAD.
