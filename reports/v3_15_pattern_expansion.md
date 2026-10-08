# V3-15 — Evidence-gated Pattern Expansion: cyclic STATE_MACHINE

**Date:** 2026-10-08. **Verdict:** initial 2-golden/243-test bounded engineering PASS; exact layout-corrected PR-head CI pending. This checkpoint validates a **bounded standalone candidate renderer** and explicitly does not authorize changing the frozen V3-04 canonical router, production publishing, or the locked 12-topic evaluation.
**Stack:** PR #48 from PR #47 head `f34ad2fdf342cb7e0a057e788517905aec843c6c`. Frozen main remains `a06e0b0b5f35e9147b4081da7ed7f7934affe0c6`; no merge.

## 1. Demand first — frozen source, not ad hoc examples

Read `benchmarks/learnflowbench/v3/preregistered_pilot_v1.json` and the immutable LearnFlowBench corpus, both verified using the existing `scripts/verify_v3_benchmark_protocol.validate()` and `SOURCE_SHA256`. **Exactly 2 of the 12 locked topic queries** suggest a bounded *candidate* where a cyclic finite-state representation is semantically different from the V3-07 existing acyclic directed `PROCESS_FLOW`:
- `lfb-006-cs`: HTTP request lifecycle — author-curated retry/response state graph with WAITING → RETRY → SENT → WAITING cycle, plus guarded response branch.
- `lfb-016-cs`: Distributed transactions — author-curated wait/retry and commit/abort branch, an illustrative state-machine rather than a certified full distributed protocol implementation.

Other ten selected topics receive explicit `NO_NEW_FAMILY_EVIDENCE_ABSTAIN`; no family minted from keyword heuristics and no data-leak replacement to preregistered topics. **“2 candidates among 12” does NOT mean the other ten are known ineligible, or that specialized visual utilization is 2/12.** All topic-level learner adequacy is UNMEASURED. Two source-topic SHA hashes come from exact frozen `(topic_id, query)`; no source facts are asserted beyond author-curated illustrative states.

## 2. Reuse-first and genuine new semantics

Reused source hash `learnflow_v2.repair.compute_content_hash`, the already validated V3-01 prereg protocol, fixed V3-06 `SequenceRenderProfile`, real `_mean_absolute_error`, exact H264 ordinal-frame decode from V3-11, blackboard style `cmu_font` from installed `fonts-cmu`, CPU Pillow/FFmpeg. V3-07 `layout_process` explicitly rejects directed cycles rather than misrepresenting them as linear process graphs; this checkpoint does not weaken that policy. No upstream Manim/Code2Video/ALGOGEN source copied and no new Python executables from LLM.

**New** `learnflow_v3/state_machine_renderer.py`: immutable bounded `MachineState`, `MachineTransition`, `MachineBeat`, `StateMachineLesson` strict contracts with directed edges, exact trigger labels, legal state/transition/beat object identity, start/terminal state, topology replay and genuine cycle or branching requirement. Refuses ungrounded topic, missing transitions, invented triggers, duplicate IDs, wrong terminal, unreachable states, graph changes and unsupported self-loops. Stable renderer-owned node center per sorted state ID; black Computer Modern, animated actual transit token traveling on a semantic edge, highlighted actual active state, visible guard/event. Fixed finite budgets of nodes/edges/beats/frames, no generic CONCEPT_CARD fallback or LLM-authored coordinates/code.

No authorty is conferred by a render contract. The canonical V3-04 `RepresentationType` has only four frozen families, and **this new standalone STATE_MACHINE is explicitly NOT registered for automatic production routing** (`registered_in_v3_04_router=False`). It requires a future separate owner-approved canonical schema/router integration plus its own regression, not false success from a standalone MP4.

## 3. Real H264 and independent replay

`render_state_machine` encodes to a temporary H264 MP4 in the same directory with no preexisting target; **replays the original finite-state trace and verifies actual H264 codec, decoded frame count, video dimensions, video/source SHA, exact time-indexed middle-beat pixel anchors, cross-beat *graph-area* state change and *within-beat* graph-area transition motion** before atomic no-clobber linking to the output; failed proof deletes the temporary output and retains original files. Video has no verified TTS/AV synchronization. This is a geometric/pixel source verification, **not independent visual recognition or correctness of HTTP/distributed transaction facts**.

`scripts/verify_v3_pattern_coverage.py` emits two genuine MP4 golden clips plus JSON per-topic eligibility/abstention, source graph, frame and source evidence. `tests/v3/test_pattern_coverage.py` verifies both clips and negative mutations: malformed edge IDs/guarded triggers, fabricated graph/beat/terminal, duplicates, off-scope pilot source, forged query SHA/video bytes/pixel evidence, overwrites, and `V3-07 cyclic PROCESS_FLOW` rejection, no card fallback.

## 4. Acceptance and scope

Commands:
```bash
python -m pytest -q --confcutdir=tests/v3 tests/v3/test_pattern_coverage.py
python scripts/verify_v3_pattern_coverage.py --output-dir /tmp/v3_15_evidence
```
Conclusive code-head CI/real metrics must be appended after completion. Hard gates: frozen V2/Hermes, benchmark prereg, LearnFlowBench, Core Freeze; no paid/free model calls or publication.

**Not established:** independently rated representation appropriateness, C5 ≥70% specialized pattern usage, C5 low card-collapse on a real 12-topic end-to-end pilot, voice-aligned pedagogy, real instructions vs synthetic traces, historical/scientific truth of arbitrary topic source, multi-family automated routing, human comprehension, 3Blue1Brown visual parity, and full video lesson quality. This is **one** evidence-gated experimental family, not indiscriminate pattern expansion. V3-13 critic and V3-14 real incremental repair efficacy research gaps remain OPEN.

Next single separately authorized CP from PLAN_V3.md: **V3-16 Human pilot/ablation (protocol and authorization gates only unless separately authorized to run real participants/APIs).**


## Initial measured code-head, actual screenshot inspection and layout correction

[Initial revised-source workflow #37757306255](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37757306255) passed **243 V3, 39 frozen V2, 86 Hermes** tests and immutable prereg/Bench/Core Freeze. Its two actual H264 MP4 clips encode **70 frames HTTP / 50 frames distributed transactions**, 640×360 12 fps, respectively; min decoded cross-state ROI MAE **2.499 / 2.023** and min within-beat transition ROI MAE **0.163 / 0.210**. [Artifact #11540916348](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37757306255/artifacts/11540916348) archived actual videos/source graph JSON. Both MP4s were downloaded and ffprobe independently confirmed H264 frame counts. The sampled screenshots showed actual active state highlights/edge movement but also a *visual geometry bug*: upper node box intersected header divider at y=103/540 screen height, despite decoded pixel PASS. Renderer-owned radial layout y center/radius corrected to keep node bounding boxes entirely between title divider and lower event footer; added header/footer 16:9 node-box clearance tests, and rerun on final PR head required. The bounded blackboard illustration is still relatively sparse and not evidence of human-rated visual excellence.

C5 70% real pilot usage, general learner preferences, instruction correctness, V2 improvement, independent factual validation, synchronized narrated full lesson, critic/genuine human study and any production router registration are **NOT ESTABLISHED**.
