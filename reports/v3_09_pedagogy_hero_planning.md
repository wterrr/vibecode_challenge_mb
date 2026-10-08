# V3-09 — Source-Grounded Pedagogy + Hero Planner

**Date:** 2026-10-08
**Status:** bounded offline engineering PASS at implementation SHA `18c551eb74173c42c898cf2e20f117974dab8dbf`. Final documentation/PR HEAD CI must be rechecked.
**Base:** stacked on V3-08 PR #41 SHA `8d2dffccd572fdedb69d0d600cae25ce159a4585`; no main merge, paid LLM use, V2 Core change or V3-10 work.

## 1. Scope, reuse-first, scientific claims

- Reuses existing project-owned `pedagogy_agent.gate.validate_pedagogy_plan`, `script_agent.gate.validate_lesson_script`, `fact_verification` claims, V2 `PedagogyPlan/LessonScript/ResearchPack/EvidenceGraph`, V2 `ConceptRegistry` and `compute_content_hash`, and V3-02 `VisualTeachingPlan`. This is a **deterministic bounded V3 adapter**, not another free-form Pedagogy Agent or runtime model planner.
- Previously researched [Code2Video](https://github.com/showlab/Code2Video) MIT @ `1142d8e14cdc2806df85aedb0fbb5dca474caa0f` for pedagogy decompositions, critic and research claims. No upstream source vendored; no generated Manim/Python, no model provider calls. This checkpoint performs **planning only**, with no MP4/animation/human study.
- Inputs are already-authored and verified instructional sources. The planner **does not independently verify natural-language truths or discover improved content**, and therefore cannot imply it generates a pedagogically superior script.

## 2. Canonical source binding and progressive teaching trace

- `compile_pedagogy_and_hero` invokes Hermes Pedagogy/Script gates, including Fact Verification/claim safety, objective/assessment checks, factual claim preservation and script boundary checks. It also checks exact learner profile/duration, all V3 objective IDs, every script segment mapped 1:1 and in order to V3 beats, each beat claim in the **approved** claim set and originating script segment, section/objective alignment, V2 canonical concept registry ID/key pairs, and complete section-level mental-model fields.
- `PrerequisiteDAG` only accepts **explicit** typed edges from existing V2 `concept_order` tokens, requires valid ordering and acyclicity. No magical prerequisite inference; missing evidence produces a declared graph with **zero inferred edges**.
- Every V2 misconception requires an explicit `MisconceptionBinding` to a valid V3 teaching beat, with corresponding approved claim IDs and the **verbatim correction present in actual spoken text or subtitle**. The substring check is a conservative syntactic provenance guard, not a semantic entailment or pedagogical correctness theorem.
- Every learning objective must map to script segments, V3 beats and actual assessment probe IDs. Mutating objective/claim/segment order, prerequisites, correction text, approved fact gate, or canonical concept refs rejects before output.

## 3. TeachingMoment + fixed-budget engineering ablation

- Deterministic candidate eligibility: V3 section declares `hero_candidate=True`; beat is essential dynamic state change, carries approved claim evidence and script objectives, and its section allows a non-card representation. No generic CONCEPT_CARD conversion, no invented geometry or renderer instructions.
- Candidates are sorted deterministically by bounded importance plus explicit misconception-correction priority; selection limited to 1–3 moments. Each retains source beat/section/objectives/claims/misconceptions/representation/essential transition and final section visual budget.
- Total visual budget is **fixed** by request and capped by V3 `visual_complexity_budget` per section. A uniform baseline and prioritized hero allocation share identical sources and total units. Priority only transfers units from non-hero sections above their minimum allocation to eligible hero sections within capacity. If the budget is not reallocatable, the planner emits `UNIFORM_FALLBACK_NO_CAPACITY`, never a fake benefit.
- The output carries source input hashes, a control hash, objective/claim coverage and deterministic decision hash, with a source-recompile verifier. `learning_gain`, `human_clarity_delta` and `independent_human_review` are hard-typed `UNMEASURED`; `render_ready=False`.
- **Important ablation boundary:** `5/5` vs `8/2` is a **resource-allocation/coverage counterfactual**, not E3/E4 actual video or expert-rater evaluation. Fixed rendering engine, identical script/audio/temporal conditions and blinded ratings are required separately in V3-16.

## 4. Reproducible offline evidence

Initial V3-09 CI revealed two genuine bugs: passing nested Pydantic instances to frozen V2 `canonical_json` before serialization, and an adversarial test feeding Pydantic computed fields into the fact report constructor. Both were fixed and retested.

[Passing implementation run #37747346591](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37747346591):
- **129 V3 tests PASS** (V3 typed contract/signal/router/trace/planner/negative mutations).
- **40 Hermes Pedagogy/Script tests PASS**.
- **39 frozen V2 registry/SceneGraph/repair tests PASS**.
- `V3_BENCHMARK_PREREG=PASS`, `LEARNFLOW_BENCH_CONTRACT=PASS`, `CORE_FREEZE=PASS`.
- `V3_09_PEDAGOGY_HERO=PASS objectives=2 misconceptions=1 hero_moments=1 budget=10 baseline=5,5 hero=8,2 human_learning=UNMEASURED`; all 10 units accounted for, 3 transferred, no hidden rendering or model calls.
- Real machine-readable [JSON evidence artifact #11536880070](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37747346591/artifacts/11536880070) contains provenance, baseline, intervention and explicit unmeasured outcomes.
- Reproduce: `python -m pytest -q --confcutdir=tests/v3 tests/v3/test_pedagogy_planning.py` and `python scripts/verify_v3_pedagogy_planning.py --output-file /tmp/pedagogy_hero_ablation.json`.

## 5. Limits, NO-GO claims, and next boundary

- No LLM generation, no source semantically proven by the planner, no human learning or preference gains, no real matched-budget MP4 production experiment, no end-to-end orchestration integration, no visual scene readability or swept geometry proof.
- One simple offline fixture **does not** prove that hero planning improves learning; do not state +10 pp, transfer across all six domains or release confidence.
- V3-10 Beat-Visual Grounding remains **not implemented**. It should consume typed planner output but must independently check visible event timing and frames, without upgrading this planning-only result to pixel proof.
- Review-only PR, no automatic merge of #34–#42 into `main`.

**Verdict:** bounded V3-09 offline source-integrity and fixed-budget **engineering PASS**, subject to final PR-head CI and review. Not a production or human-evaluation PASS.
