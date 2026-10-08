# V3-00 — Baseline, Branch Merge Gate & Reuse Inventory

**Status:** **V3-00 AUDIT PASS / FULL FAST-FORWARD NO-GO / SELECTIVE INTEGRATION REQUIRES APPROVAL.** Fresh offline CI passed on audit HEAD.  
**Scope:** V3-00 only. **NO MERGE**, no V3 capability implementation, no paid model call and no changes to frozen V2 Core.  
**Evidence time:** 2026-10-08. Branch HEAD prior to audit: `a1e4e8b72f4e63e9cde0ffd4351df9a936900d9a`. Main HEAD: `29fab1d5738ccb060502c8ae82e2e31f00360811`.

## A. Primary sources and historical evidence

Read in repository at pinned HEAD: `PLAN_V3.md` v3.0.1-draft (especially `8.3 Reuse-first`), `PLAN_V2.md` (Core Freeze, benchmark, 2026-10-08 waiver), `LEARNFLOW_V3_RESEARCH_NOTES.md`, `reports/v2_final_semantic_consistency_offline_audit.md`, `benchmarks/learnflowbench/README.md`, and `benchmarks/core_freeze/manifest.json`.

- Core Freeze: `learnflow-v2-core-freeze-2026-10-06`; accepted engine `fdad3db1340d8b28175ab5382d800ff79df9a8a0`; historical evidence `4b2cc7887773a8fb81dee36010fcae3bc2015ccb`; V1 rollback `f6dae0e8510a6db8fc49a761eddc2a055ffaefda`.
- Frozen Core Gate from manifest: `v2-core-gate-v2 PASS`, workflow `37412433812`. This is old **frozen** evidence, not new population-level quality evidence.
- Live Action #181 `37721597623` completed SUCCESS at `cb605dc`. Historical binary search example has registry 16 vs script/render 24 semantic mismatch; **retain original artifact unmodified**.
- Offline #4 `37723264679` completed SUCCESS at `0113b3a`: `CORE_FREEZE=PASS`; `LIVE_V2D_CONTRACT=PASS`; 87 semantic/subtitle/Hermes tests PASS; 14 renderer PASS / 5 SKIP. Subsequent commits up to current base were documentation only.
- Original #181 ZIP locally inspected: 74 entries, SHA256 `dc27818f5018a2732d320d4fda0e01f59498f8473b9345b46623a43fc87f4829`, `hermes-home/auth.json` **present**. This does not prove secret plaintext exposure, but old whole-runtime artifact export is unacceptable. New allowlist and negative secret tests require continued scrutiny.
- Full 100-topic paid benchmark, empirical ≥98% end-to-end reliability, human aesthetic and learning outcomes remain **UNMEASURED**.

## B. Commit ancestry and merge answer

GitHub compare `main...chatgpt/live-v2d-gpt6-luna-paid-pilot` at pinned SHAs: **27 ahead, 0 behind; main is the merge base; 23 files changed**. This means a fast-forward is *technically* possible at this snapshot, **not** that it is safe for production. The current pilot contains a default `openai/gpt-6-luna` model in `hermes/bootstrap/config.yaml`, narrowly scoped paid policy, and branch-env-dependent rendering. A blind fast-forward could unintentionally alter production policy and should **not** be executed.

GitHub PR history: #1–#32 except #8 and #14 (closed unmerged) and #11 (still open old renderer PR) were merged as PRs. Historical branch divergence is not proof that the feature is absent after later replacement; **no stale PR may be blindly merged**.

### B1. Complete 27-commit inventory

Classification is of **what is reusable from each commit**, not permission to cherry-pick it without dependency audit. `SUPERSEDED` means the earlier intermediate commit should not be applied as an independent change when the final branch already contains its effective replacement.

| # | Commit | Decision | Commit purpose |
| ---: | --- | --- | --- |
| 1 | [`32bcbd0295`](https://github.com/wterrr/vibecode_challenge_mb/commit/32bcbd02954f87b14c58126fd3983ce06cc706b3) | **EXPERIMENTAL** | test(live-v2d): isolated one-off GPT-6 Luna paid pilot |
| 2 | [`ce8e4d9c1a`](https://github.com/wterrr/vibecode_challenge_mb/commit/ce8e4d9c1ad54224bf0d9d2d2d13d010744bf848) | **EXPERIMENTAL** | fix(live-v2d): omit unsupported temperature in GPT-6 Luna capability probe |
| 3 | [`36c3c6a63d`](https://github.com/wterrr/vibecode_challenge_mb/commit/36c3c6a63dcac771eceb59942a0f8d0092691a89) | **EXPERIMENTAL** | fix(live-v2d): enable GPT-6 Luna tool calls and emit unbuffered diagnostics |
| 4 | [`49dfa2dd3b`](https://github.com/wterrr/vibecode_challenge_mb/commit/49dfa2dd3b6762eb41b71eee37f508a44f70aeda) | **EXPERIMENTAL** | fix(live-v2d): use canonical Hermes reasoning config for GPT-6 Luna |
| 5 | [`481dc52f45`](https://github.com/wterrr/vibecode_challenge_mb/commit/481dc52f45060980211518a35543d0a28cefdba6) | **KEEP** | fix(live-v2d): repair Visual Director semantic gate failures within bounded loop |
| 6 | [`4c2c17b508`](https://github.com/wterrr/vibecode_challenge_mb/commit/4c2c17b508f86dbbf9d56e56ee96a8d4bac74af5) | **KEEP** | test(live-v2d): mock Hermes output-schema module in offline semantic repair regressions |
| 7 | [`9cc69e2e69`](https://github.com/wterrr/vibecode_challenge_mb/commit/9cc69e2e69dd1431cfb4d09476f51777f0480f52) | **EXPERIMENTAL** | fix(live-v2d): bound Luna Visual requests and capture hang diagnostics |
| 8 | [`3e59e24f46`](https://github.com/wterrr/vibecode_challenge_mb/commit/3e59e24f4697377df600ac2fcdfbf03be50fb2a1) | **EXPERIMENTAL** | perf(render): crop node alpha layers and validate immutable scene inputs once per render |
| 9 | [`98a7338a26`](https://github.com/wterrr/vibecode_challenge_mb/commit/98a7338a26455bae962f8eaf1221d080ffae7c3b) | **KEEP** | ci(live-v2d): gate expensive Luna pilot on render pixel-parity tests |
| 10 | [`ba659bca93`](https://github.com/wterrr/vibecode_challenge_mb/commit/ba659bca933bb1e7e62b0ecb509392da23ebb2f3) | **KEEP** | ci(live-v2d): install Kiwi layout dependency before renderer tests |
| 11 | [`ee59422593`](https://github.com/wterrr/vibecode_challenge_mb/commit/ee59422593db68188cc6088cd3cb504f0858324e) | **EXPERIMENTAL** | perf(live-v2d): restore frozen Core; optimize paid-pilot rendering in isolated adapter |
| 12 | [`4ecce3ac0f`](https://github.com/wterrr/vibecode_challenge_mb/commit/4ecce3ac0f8fd89a1ea3adbae87720d476bd2404) | **EXPERIMENTAL** | fix(live-v2d): stream decoded RGB checksum without buffering entire production video |
| 13 | [`7c40d69d5d`](https://github.com/wterrr/vibecode_challenge_mb/commit/7c40d69d5d2f9ad5842a2be62c694ef8ed50000a) | **KEEP** | test(live-v2d): make streaming-only guard robust to adapter docstring |
| 14 | [`1c94a87cbc`](https://github.com/wterrr/vibecode_challenge_mb/commit/1c94a87cbce8b3743f9f992523f8064c8b45ebf1) | **EXPERIMENTAL** | ci(live-v2d): reserve single paid final topic for manual dispatch only |
| 15 | [`0ce06f8402`](https://github.com/wterrr/vibecode_challenge_mb/commit/0ce06f84029bbb6f5d9c27807cc34cd5cd75dbaa) | **KEEP** | docs(v2): record single paid final benchmark and scoped V3 planning gate |
| 16 | [`a5b99c7150`](https://github.com/wterrr/vibecode_challenge_mb/commit/a5b99c7150f66f2defc326ff6376eae16b5fcd49) | **SUPERSEDED** | docs(ci): require explicit user topic selection and paid one-shot confirmation |
| 17 | [`b97df802bc`](https://github.com/wterrr/vibecode_challenge_mb/commit/b97df802bcac6d773cde9579087f01a2ebb1416c) | **KEEP** | docs(ci): lock preregistered Binary Search topic for final paid V2 gate |
| 18 | [`9c0243a173`](https://github.com/wterrr/vibecode_challenge_mb/commit/9c0243a1735aff974b934496dd7bb9a8e8bdce5b) | **KEEP** | fix(v2-final): short timed TTS subtitles with safe band and offline-only preflight |
| 19 | [`813e6b4ca4`](https://github.com/wterrr/vibecode_challenge_mb/commit/813e6b4ca4074f62a3c16dfdb23a5615026326ce) | **KEEP** | test(v2-final): align streaming checksum regression with readable subtitle adapter |
| 20 | [`d94fdd1475`](https://github.com/wterrr/vibecode_challenge_mb/commit/d94fdd147524b789ce22bedecfc12c85ace25616) | **KEEP** | ci(v2-final): rerun offline preflight when legacy regression guard changes |
| 21 | [`cb605dc110`](https://github.com/wterrr/vibecode_challenge_mb/commit/cb605dc1104e87f9ac8640db2a6c49ceb27a159b) | **KEEP** | docs(v2-final): record offline subtitle replay and passing preflight evidence |
| 22 | [`373bf557b5`](https://github.com/wterrr/vibecode_challenge_mb/commit/373bf557b5d24f738fb4e8472f874130db972e5f) | **KEEP** | fix(v2d): fail closed on cross-artifact worked-example drift; redact pilot evidence by allowlist |
| 23 | [`0113b3a526`](https://github.com/wterrr/vibecode_challenge_mb/commit/0113b3a526a33d520a98f5dcf7d6a46b1ce09abd) | **KEEP** | test(v2d): enforce registry key and node semantic identity on worked examples |
| 24 | [`efd19bc4bb`](https://github.com/wterrr/vibecode_challenge_mb/commit/efd19bc4bb3b8f2bf8e79ea50cf3e4e7e10c6b53) | **KEEP** | docs(v2-final): record offline semantic gate, redaction proof, and V3 conditions |
| 25 | [`7a8a8df051`](https://github.com/wterrr/vibecode_challenge_mb/commit/7a8a8df051a42234aa97b2375346a108ce593b19) | **KEEP** | docs(v3): add evidence-gated architecture plan and research synthesis |
| 26 | [`f13e87d18a`](https://github.com/wterrr/vibecode_challenge_mb/commit/f13e87d18a8ce4e09157ef95b53b254833d83207) | **SUPERSEDED** | docs(v3): correct baseline regression terminology |
| 27 | [`a1e4e8b72f`](https://github.com/wterrr/vibecode_challenge_mb/commit/a1e4e8b72f4e63e9cde0ffd4351df9a936900d9a) | **KEEP** | docs(v3): require licensed upstream reuse audit before new implementation |

### B2. Complete 23-file inventory

| # | File | Decision | Merge rationale |
| ---: | --- | --- | --- |
| 1 | `.github/workflows/final-v2-offline-preflight.yml` | **KEEP** | Only offline Core/contract/renderer regression runner; extend with V3-00 audit check, no provider calls |
| 2 | `.github/workflows/live-v2d-evaluation.yml` | **EXPERIMENTAL** | Preserve as historic isolated paid/manual pilot; do NOT merge dispatch settings to production |
| 3 | `.hermes/plugins/learnflow/tools.py` | **EXPERIMENTAL** | Contains pilot-only optimized renderer injection; split adapter from generic plugin first |
| 4 | `LEARNFLOW_V3_RESEARCH_NOTES.md` | **KEEP** | Canonical research continuity, include licensing and evidence limitations |
| 5 | `PLAN_V2.md` | **KEEP** | Historical scope/waiver documentation; no relaxation of frozen technical evidence |
| 6 | `PLAN_V3.md` | **KEEP** | Reviewed V3 plan document only; no implementation authorization |
| 7 | `hermes/bootstrap/config.yaml` | **EXCLUDE** | Paid openai/gpt-6-luna set as default: unacceptable promotion to main/default model |
| 8 | `lesson_pipeline/media_digest_adapter.py` | **EXPERIMENTAL** | Pilot-only memory-bounded RGB digest; candidate for separately benchmarked portable backend |
| 9 | `lesson_pipeline/production.py` | **EXPERIMENTAL** | Contains branch/env-conditional paid caption and streaming behavior; split normal subtitle policy before production |
| 10 | `lesson_pipeline/render_adapter.py` | **EXPERIMENTAL** | Pilot-only raster optimization; parity tests passed but policy tied to Luna branch |
| 11 | `lesson_pipeline/subtitle_policy.py` | **KEEP** | Pure short-caption timing and safe-band policy, portable behind explicit production flag and tests |
| 12 | `lesson_pipeline/subtitle_render_adapter.py` | **EXPERIMENTAL** | Paid-branch ffmpeg subtitle style override, needs accessibility/device QA and backend independence |
| 13 | `live_evaluation/hermes_runner.py` | **EXPERIMENTAL** | Mixed general semantic preflight and paid Luna reasoning/timeouts; separate changes before main |
| 14 | `live_evaluation/model_probe.py` | **EXPERIMENTAL** | Specific GPT-6 Luna protocol compatibility; isolate from production default candidates |
| 15 | `live_evaluation/pilot.py` | **KEEP** | Narrow numeric example drift guard before TTS; keep pilot scope and document limited generality |
| 16 | `live_evaluation/semantic_consistency.py` | **KEEP** | Portable fail-closed worked-example gate, but not general proof of semantic correctness |
| 17 | `openrouter_policy.py` | **EXPERIMENTAL** | Paid model exception gated to pilot GitHub ref; keep only in isolated evaluation path, not general production |
| 18 | `reports/v2_final_semantic_consistency_offline_audit.md` | **KEEP** | Reproducible historical #181 and CI evidence; never retroactively overwrite |
| 19 | `scripts/export_live_v2d_evidence.py` | **KEEP** | Allowlisted evidence export, excludes Hermes auth/runtime; security review still required |
| 20 | `scripts/run_live_v2d_pilot.py` | **EXPERIMENTAL** | Paid-specific traceback watchdog and pilot model selection, isolated evaluation only |
| 21 | `tests/hermes/test_final_v2_semantic_consistency.py` | **KEEP** | Positive/negative regression tests, credential and identity checks |
| 22 | `tests/hermes/test_final_v2_subtitles.py` | **KEEP** | Caption safety and Core Freeze regression tests |
| 23 | `tests/hermes/test_live_v2d_evaluation.py` | **EXPERIMENTAL** | Mixed standard and Luna-specific tests; retain for pilot, cherry-pick reusable assertions |

**Categories:** `KEEP` = worth selective integration after controls; `EXPERIMENTAL` = preserve on isolated pilot/port selected logic only; `SUPERSEDED` = old interim commit made redundant by later change; `EXCLUDE` = should not land in production. Zero changed files under `learnflow_v2/` frozen namespaces (confirmed compare output). Metadata/hash CI is the ultimate check.

**Atomic dependency warning:** Taking a `KEEP` file does **not** imply it can be dropped into main without its imports/configuration. E.g. `live_evaluation/pilot.py` needs `semantic_consistency.py`; `subtitle_policy.py` is otherwise unused by production unless the gated callsite is adapted. Combine selected changes on a dedicated non-main integration branch and test the full dependency graph. Never cherry-pick mixed provider-dependent commits merely to move one small utility.

## C. Reuse-first and license audit

**Priorities:** existing project-owned V2 API → maintained reusable dependency → narrowly adapted third-party code (license/NOTICE preserved) → new code only for uncovered, verified contracts. The full external upstream candidate audit belongs to each later checkpoint; V3-00 provides initial **source+API inventory**, not upstream runtime quality certification.

| Upstream (pinned SHA) | License / status | Proven modules and constraints | Recommendation |
| --- | --- | --- | --- |
| [showlab/Code2Video](https://github.com/showlab/Code2Video/tree/1142d8e14cdc2806df85aedb0fbb5dca474caa0f) (`1142d8e14c`) | **MIT** | LICENSE; src/agent.py, scope_refine.py, eval_AES.py, eval_TQ.py, src/requirements.txt; deps: manim==0.19.0, openai==1.90.0, numpy==2.2.6, scipy==1.15.3. Source-line-number Manim repair and provider-coupled evaluator; do not run arbitrary agent code or copy full pipeline. | **ADAPT_DESIGN_OR_SMALL_SUBSET_ONLY** |
| [ManimCommunity/manim](https://github.com/ManimCommunity/manim/tree/23ae68f4dd5817d49760b338e14b92757a2369b5) (`23ae68f4dd`) | **MIT + LICENSE.community review** | LICENSE; pyproject.toml declares 0.21.0, Python>=3.11; deps: Cairo/Pango, ffmpeg, OpenGL stack, Manim Community >=0.21.0 selected candidate. Native system dependencies, text/font parity, render time, compatibility gap with Code2Video 0.19.0 and ALGOGEN 0.18.1. | **OPTIONAL_PINNED_BACKEND_SPIKE** |
| [MAC-AutoML/ALGOGEN-lab](https://github.com/MAC-AutoML/ALGOGEN-lab/tree/1bb093c76499135ecf54fc8030219a4e7ee4424c) (`1bb093c764`) | **NO LICENSE FOUND (root, GitHub repository metadata)** | renderer/manim_renderer.py; run_pipeline.py; requirements.txt pinned manim==0.18.1; deps: manim==0.18.1, numpy==1.26.4, jsonschema==4.20.0. No permission demonstrated to copy source; design/behavior may be studied and independently implemented. | **STUDY_ONLY_NO_COPY** |
| [wterrr/vibecode_challenge_mb](https://github.com/wterrr/vibecode_challenge_mb/tree/29fab1d5738ccb060502c8ae82e2e31f00360811) (`29fab1d573`) | **PROJECT OWNED (verify collaborators' contributions before redistribution)** | benchmarks/core_freeze/manifest.json and learnflow_v2 typed modules; deps: Pydantic v2, Kiwi 1.5.1, Graphviz/ELK, Pillow, FFmpeg. Frozen namespaces may only be consumed, not modified. | **REUSE_EXISTING_V2_API_FIRST** |

**Code2Video deep API audit:** `src/agent.py` ~913 lines, `generate_outline`/`generate_storyboard`/`get_mllm_feedback`; `src/scope_refine.py` ~803 lines, `ScopeRefineFixer` and `ManimCodeErrorAnalyzer` heavily coupled to Python code-line repairs and Manim; `src/eval_AES.py` and `src/eval_TQ.py` call external model APIs. Copying whole agent pipeline is not economical or equivalent to typed LearnFlow artifact repair. Prefer reusing the protocol/rubric and independently building typed adapters; selective MIT-source reuse only if the exact functions are decoupled and LICENSE retained.

**Manim Community API/license audit:** at SHA `23ae68f4` `pyproject.toml` reports `manim==0.21.0`, Python ≥3.11, MIT (`LICENSE` and additional community license). Code2Video requirement is `manim==0.19.0`; ALGOGEN requirement `manim==0.18.1`: do not mix renderers or call versions interchangeable without a minimal pinned compatibility/runtime benchmark. Compare cold import, deployment size, P95 render cost, deterministic output, text/fonts, safe fallback, exact frame timing. No Manim dependency was installed by this checkpoint.

**ALGOGEN restriction:** repository root contains no LICENSE file and GitHub license metadata is absent; no permission to copy its source established. `run_pipeline.py` / `renderer/manim_renderer.py` are analyzed as behavior/architecture references ONLY; do not vendor or transplant any of their code or embedded media.

### C1. Capability-by-capability reuse decision (C1–C12)

| Capability | Existing LearnFlow implementation | External candidate | Proposed strategy | Validation required at its own later checkpoint |
| --- | --- | --- | --- | --- |
| **C1 Pedagogy Planner** | `pedagogy_agent/models.py; agent_contracts/lesson.py` | Code2Video src/agent.py::generate_outline | **ADAPT** | No pedagogical-performance transfer from upstream; bounded typed plan. Suggested baseline: `pytest -q --confcutdir=tests/hermes tests/hermes/test_pedagogy_agent.py` (not executed as V3 evidence) |
| **C2 Hero Section Allocation** | `agent_contracts/lesson.py; pedagogy_agent/*` | Code2Video src/agent.py::generate_storyboard | **ADAPT** | No new full agent; fixed animation-budget ablation needed. Suggested baseline: `pytest -q --confcutdir=tests/hermes tests/hermes/test_pedagogy_agent.py` (not executed as V3 evidence) |
| **C3 Visual Director** | `visual_director/gate.py; visual_director/models.py` | Code2Video src/agent.py; external planning semantics | **REUSE_V2_AND_ADAPT** | Representation choice must stay semantic, not raw coordinates. Suggested baseline: `pytest -q --confcutdir=tests/hermes tests/hermes/test_visual_director.py` (not executed as V3 evidence) |
| **C4 Beat-Visual Goal Binding** | `learnflow_v2/motion/beats.py; lesson_pipeline/production.py` | MINARD grounded narration (paper only) | **REUSE_V2_AND_ADAPT** | Caption timing alone does not prove meaningful visual state. Suggested baseline: `pytest -q --confcutdir=tests/hermes tests/hermes/test_lesson_pipeline.py` (not executed as V3 evidence) |
| **C5 Pattern Library** | `learnflow_v2/scenegraph/schema.py; learnflow_v2/layout/router.py; learnflow_v2/render/backend.py` | Manim Community 0.21 optional backend; Code2Video generated-code design only | **REUSE_V2_PLUS_TRUSTED_ADAPTER** | Current V2 paints generic cards, requiring bounded typed pattern compiler. Suggested baseline: `pytest -q --confcutdir=tests/v2 tests/v2/test_render_v2.py` (not executed as V3 evidence) |
| **C6 Artifact Critic** | `learnflow_v2/qa/critic.py; learnflow_v2/videoqa/critic.py` | Code2Video src/eval_AES.py and agent.py::get_mllm_feedback | **WRAP_EXISTING** | Provider-coupled upstream and possible fail-open; human-labeled issue corpus. Suggested baseline: `pytest -q --confcutdir=tests/v2 tests/v2/test_vlm_critic_v2_12_gate.py` (not executed as V3 evidence) |
| **C7 ArtifactRefine** | `learnflow_v2/repair/engine.py; learnflow_v2/repair/artifacts.py` | Code2Video src/scope_refine.py::ScopeRefineFixer | **REUSE_V2_PATCH_CORE** | Upstream source-line patch incompatible with typed ID diff; measure isolated repair. Suggested baseline: `pytest -q --confcutdir=tests/v2 tests/v2/test_repair_v2_13_engine.py` (not executed as V3 evidence) |
| **C8 Verified Algorithm Trace** | `learnflow_v2/motion/compiler.py; SceneGraph typed nodes` | ALGOGEN-lab run_pipeline.py + renderer/manim_renderer.py (NO LICENSE; study only) | **INDEPENDENT_NEW_ADAPTER** | Trace state source is new glue; avoid copying unlicensed code; oracle on binary search. Suggested baseline: `pytest -q --confcutdir=tests/hermes tests/hermes/test_live_v2d_evaluation.py` (not executed as V3 evidence) |
| **C9 Signal Preservation** | `learnflow_v2/concepts/registry.py; live_evaluation/semantic_consistency.py` | ALGOGEN RSL dead-field finding (research only) | **REUSE_V2_PLUS_TESTS** | Validator is narrow for numeric worked examples; structural+mutation tests needed. Suggested baseline: `pytest -q --confcutdir=tests/hermes tests/hermes/test_final_v2_semantic_consistency.py` (not executed as V3 evidence) |
| **C10 Fail-Closed QA & Publication** | `learnflow_v2/qa/analyzer.py; runtime_governance/*` | Code2Video critic fail-open patterns as negative case | **REUSE_V2_AND_HARDEN** | Make CRITIC_UNAVAILABLE explicit; do not promote deterministic PASS. Suggested baseline: `python scripts/verify_v2_core_freeze.py` (not executed as V3 evidence) |
| **C11 Temporal Keyframe Layout** | `learnflow_v2/layout/collision.py; learnflow_v2/layout/continuity.py; learnflow_v2/motion/compiler.py` | OmniManim/SGA papers; Manim Community optional shapes | **REUSE_V2_PLUS_NEW_TEMPORAL_ADAPTER** | Swept collision is not proven by endpoint-only layout; no LLM geometry. Suggested baseline: `pytest -q --confcutdir=tests/v2 tests/v2/test_render_v2.py` (not executed as V3 evidence) |
| **C12 Beat-to-Visual Evidence** | `learnflow_v2/motion/beats.py; lesson_pipeline/production.py; videoqa/*` | MINARD and ManiBench measurement ideas (papers only) | **ADAPT_WITH_RENDER_PROOF** | Pixel-level visual event proof requires a new per-beat trace; speech/text sync insufficient. Suggested baseline: `pytest -q --confcutdir=tests/hermes tests/hermes/test_lesson_pipeline.py` (not executed as V3 evidence) |

The decision is **REUSE/ADAPT-FIRST**, not blind source copying. In particular, new V3 code is justified only for `VisualTeachingPlan`, stateful representation+trace mapping, temporal geometry proof, per-beat semantic pixel evidence and new typed adapter bridges **after** demonstrating they are absent from V2 and not sustainably importable.

### C2. Mandatory acceptance of any third-party reused module

1. Exact module path/function, pinned commit SHA, upstream test command and real example output;
2. SPDX/license + copyrights/NOTICE, separate third-party assets and transitive-license review;
3. typed contract adapter and deterministic behavior under chosen local renderer profile; negative case and rollback;
4. no provider network calls or arbitrary generated rendering code in offline CI; security and source provenance;
5. actual integration-time+maintenance comparison vs smallest owned adapter, not just lines of code;
6. before shipping, a human reviewer signs off license and quality; **these upstream candidate integrations are currently NOT TESTED**.

## D. Fresh offline V3-00 verification contract

Deliverables: this report, machine-readable `reports/v3_00_reuse_inventory.json`, and `scripts/verify_v3_baseline.py`. Offline GitHub workflow on the pilot branch runs:

```bash
python scripts/verify_v3_baseline.py
python scripts/verify_v2_core_freeze.py
python scripts/verify_live_v2d_evaluation.py
pytest -q --confcutdir=tests/hermes tests/hermes/test_live_v2d_evaluation.py tests/hermes/test_final_v2_subtitles.py tests/hermes/test_final_v2_semantic_consistency.py
pytest -q --confcutdir=tests/v2 tests/v2/test_render_v2.py
```

Verifier validates snapshot/coverage (27 commits, 23 files, C1–C12, no protected Core changes, no unlicensed-copy approval) **and now checks every recommended baseline test path exists**. **Core Freeze script independently validates exact frozen Git blob SHA and full protected-file set**. The workflow remains strictly offline: no API key env or model/provider calls.

**Fresh definitive run: [Final V2 Offline Preflight #37725705499](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37725705499), code/inventory HEAD `217bd0575e7e14141fa24fd320efa76edcf391b3`.** Log-confirmed results:

| Gate | Verified output |
| --- | --- |
| V3-00 inventory baseline | `V3_00_BASELINE=PASS commits=27 files=23 capabilities=12` |
| Frozen Core | `CORE_FREEZE=PASS` |
| V2D contract | `LIVE_V2D_CONTRACT=PASS` |
| Offline Hermes/subtitle/semantic regression | `87 passed` |
| Offline renderer regression | `14 passed, 5 skipped` |
| Provider-paid workflow | Not triggered; `Final V2 Offline Preflight` only |

**Interpretation:** V3-00 audit is a **PASS**, while selection+safe merge remains **BLOCKED pending explicit approval**, and blanket pilot→main fast-forward is **NO-GO**. This is not a new V3 quality outcome, nor a test of upstream Manim runtime.

## E. Gate decision and candidate integration protocol

**V3-00 audit completion: PASS.** Completed full categorized inventories, verified license findings, documented production-merge blockers and a fresh offline CI PASS. The standalone V2D `#181` remains technical-only historical evidence with known semantic drift.

**Straight merge `pilot → main`: NO-GO** due to paid-default config and branch-specific experimental changes. **Safe selective integration: CONDITIONAL GO to PREPARE ONLY**, subject to explicit user authorization.

Proposed integration branch from latest main (no changes to main until approval) follows:
1. Snapshot main SHA, select KEEP files/hunks with dependency-aware extraction (not all KEEP files necessarily whole-file copy). Review source-level diff and license again.
2. Port semantic drift detection, protected redacted evidence export, optional general caption safe-band policy and tests behind an explicit production-safe, free-by-default config.
3. Reject paid branch default config; preserve production model policy and disabled-on-push provider behavior. Keep pilot-only render adapters and Luna-specific probes in isolated history unless separately justified.
4. Pin environment, run freeze + all V2 tests + new security/provenance negatives in branch CI, inspect test skips and changed diff; confirm V1 fallback unchanged.
5. Merge `main` only after an explicit user approval, verified green checks and no pipeline spend risk. Archive #181 unchanged.

### F. Residual issues and single next checkpoint

- **BLOCKER to straight merge:** paid model default in Hermes bootstrap, paid workflow/model gates and branch-specific rendering behavior.
- **BLOCKER to V3 implementation:** reviewed production integration base and explicit sign-off not yet established.
- **KNOWN LIMITATION:** semantic validator covers a narrow class of numeric search examples; general visual-event/semantic consistency is V3 work, not declared solved by V3-00.
- **UNMEASURED:** human quality, larger live reliability, deterministic-performance parity for optional Manim backend and upstream copyright of embedded assets.
- **SECURITY:** historical #181 ZIP had `auth.json`; no proof that plaintext secrets were exposed. Do not distribute it without further secrets review.

**Exactly ONE next checkpoint:** **V3-00B — Selective Integration Candidate & Offline Gate**, subject to explicit user authorization. Prepare a candidate **non-main** integration branch that ports only reviewed KEEP pieces, handles mixed dependencies safely, runs frozen Core and full offline regressions, and produces a final reviewable diff/PR. Do not merge main without separate approval. Do not implement V3-01 or call paid APIs.
