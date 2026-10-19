# V3-93 — REAL PAID GPT-6 Luna → Native Lesson: TECHNICAL PASS, VISUAL NOT PASS

**Date:** 2026-10-19 UTC. **Deadline:** 2026-10-21. User explicitly authorized GPT instead of a free model and increasing V3-92 output ceiling from 2,500. **Parent:** Draft PR #129 frozen HEAD `2620270f7863efa43b3c0e21a58acda88655fdae`. **First-child prereg:** `e062207b2d2bd32875cb6cf83bd735cb1fa635ea` before implementation or payment. **Child PR:** Draft #130. No merge into main.

## Exact design and reuse-first
- Paid **`openai/gpt-6-luna`**, OpenRouter pinned `provider.order=[OpenAI]`, **`allow_fallbacks=false`**, `require_parameters=true`, strict JSON schema, `reasoning_effort=low`, **`max_completion_tokens=16000`**. Single unique trigger, **1 HTTP POST maximum; no retry** and no alternate/free provider.
- Current public catalog showed **$0.10/M input, $0.50/M output**. The single-request conservative token-cost estimate using 16,000 output and 3,028-byte exact request: **$0.0083028**, below prereg $0.01 boundary. This is an application-side upper estimate, **NOT a provider-enforced dedicated lifetime key cap**. Current key GET authenticated and remaining budget was sufficient to pass the frozen preflight. No key/guardrail changes.
- Model authors compact visual pedagogy decisions and five original sentences. Source facts/12 object identity/3×4 ↔ 4×3/answer timing are controlled by host; native rendering reuses V3-64 old source-bound compiler. No model Python execution, no arbitrary topic generalization.

## Independently observed CI
- [Exact-parent offline native+tests push #39196780568](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/39196780568): **SUCCESS** at HEAD `8836cadee5c80c1f5bb6b7f970658883f372a3c5`. **23/23 new V3-93 hostile tests + 80/80 V3-92/91/64 regression tests**, V2 Core Freeze PASS, V3 benchmark protocol PASS; two host-only H264/AAC native controls PASS.
- [Exact paid live one-shot #39197145291](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/39197145291): **SUCCESS** at unique trigger HEAD `4e0082ee6550cae81487981f828ceacd53be9612`. GitHub steps verify exactly one paid trigger, preflight parent success, real model POST, provider provenance, host semantic admission and native full decode.
- [First-party live artifact #12162327395](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/39197145291/artifacts/12162327395) physically downloaded, ZIP SHA256 **`6c05b0304b88cfde503b54364904e18f88b62841a90a8562c863e02555185c54`**, 1,782,373 bytes. Contains original accepted GPT JSON (1,110B), original native host control MP4 and generated GPT-candidate MP4, decoded frame screenshots, receipts.

### Genuine provider receipt
| Property | Observed |
| --- | --- |
| Actual provider model | `openai/gpt-6-luna` |
| Provider requests | **1**, retries **0** |
| `finish_reason` | **`stop`** |
| Input / output / total tokens | **576 / 552 / 1,128** |
| Actual provider-reported cost | **USD $0.000330264** |
| Estimated one-request ceiling | **USD $0.0083028** (estimated, not key cap) |
| Response ID | Captured as SHA256 only `b80a95fc7372c75f7ef0150d875d93c50f48a6877a838bcde19072c66376e174` |
| Candidate SHA256 | `1060c980edf45213642606c04beb80d3f115ae7dafd920580a778c226238f96a` |
| Real external attribution | `GENUINE_GPT6_LUNA_NETWORK` |
| Original narrative beats | **5 of 5** distinct from frozen host control |
| Model-selected composition | **`side_by_side`** (renderer currently only shifts one array to left — not two distinct panels) |
| Model-selected motion | **`smooth_morph`** |
| Host source ledger | `8ea108abef60738268892c74b9013da33e9d09064fb2e9de19f234ca4f6fee76` |

### Native verified media
- Generated model-authored candidate (historical compiler's generic filename `model_unverified.mp4`, model provenance proven **separately** by live receipt): **H.264/AAC 1280×720, 15fps, 441 frames, ~29.4s**, SHA256 **`fcc26242ce903e48c80ffb95015a7fe666bc9e894aa8f4b7d10caec63331a3a6`**.
- Original HOST_TEST_ONLY counterfactual: **441 frames**, SHA256 **`16fc3ab269dba51ad7f122b2047844c6ad987b18365b8a5409eba20bdec3923a`**.
- Host-native QA: both complete decode, SHA, 12 IDs, source-math 3×4=4×3=12, native midpoint MAD=16.0819, early-to-witness MAD=11.6985. The two videos use **different narration audio**, so comparison is confounded; do not claim improved learning effectiveness.

## Independent image inspection — BLOCKING VISUAL DEFECTS
Original candidate decoded frames were inspected directly after downloading the live MP4; technical PASS alone did not reveal these:
1. **~00:11.7 / TRANSFORM:** screen text `Every object retains its own identity` **overlaps squares at the lower left**. Model chose `side_by_side`; host rendering draws a left-aligned *single* array, not genuine comparative side-by-side stages. This is both a label collision and a mismatch between model intent and renderer composition.
2. **~00:22.0 / WITNESS:** the same label **overlaps squares**; the fourth row of squares descends into the lower caption area, **occluding the spoken sentence display**.
These occur in the host-native **layout/rendering layer**, not the GPT-generated mathematical claims. They must be repaired in the generating geometry with across-timeline collision tests; no screenshot overlays, padding-only masks or retouch. Preserve original accepted GPT JSON/SHA and old MP4/SHA as immutable evidence.

**Critical quality verdict:** Authenticated GPT authoring + true native 2-MP4 conversion **TECHNICAL PASS**; visual aesthetics/legibility **NOT PASS** on independent frame inspection; 3Blue1Brown creative or educational parity **NOT PROVEN**; independent humans **0**; learning gain **NOT MEASURED**; general AI topic coverage **NOT PROVEN**; production **BLOCKED**.

## Ready next action, no new paid API required
V3-94 proposal: **GPT-authored Scene Layout Geometry + Timeline Collision Repair**. Consume the **exact original V3-93 accepted storyboard** from archived first-party artifact (SHA frozen) without another LLM request. Correct `side_by_side` contract to true parallel before/after representation or clearly fail-closed when unsupported; move identity label into a reserved nonoverlapping region, keep arrays fully above subtitle baseline at all 441 frames, prove consistent persistent object IDs and source math. Preregister both defect timestamps and zero-overlap acceptance before patch. Add timeline-geometry collision + subtitle boundary tests and verify real decoded corrected H264/AAC video. Keep original film and PR #130 as frozen evidence, no altered user-facing quality claims until human review.

## Release boundary
For 21 October deadline: original V3-90 remains bounded offline fallback. V3-93 is a **new genuine GPT-backed technical proof of concept** but its visual collision means **not production/human acceptance**. Draft PR #130, main unmerged; do not repeat/retigger its paid request.

Final: **PAID GPT MODEL AUTHENTICATED · 1 POST · $0.000330264 reported · 5/5 GPT captions · NATIVE H264/AAC PASS · VISUAL QA NOT PASS · HUMAN UNRATED · PROD BLOCKED.**
