# V3 Integration Closure — actual caller / consumer / dead-code audit

**Review commit lineage:** stacked PR #51 on PR #50 at `f2de4adabc61706a7e243490e32124601c65962a` (main frozen `a06e0b0b5f35e9147b4081da7ed7f7934affe0c6`). **No merge, no paid provider call, no publication or human study.**

**Result state:** Offline vertical slice implementation delivered. Exact HEAD CI and artifact check pending; the work is **not production-ready**, nor a complete human-approved lesson. Production and V3-16 human quality gates remain BLOCKED.

## Authoritative scope & first confirmed P0

The FastAPI route `app/main.py:create_app` → `app/pipeline/factory.py:create_pipeline` → `app/pipeline/real.py:RealVideoPipeline` → `app/rendering/router.py:RendererRouter` still uses legacy concept/process/comparison/illustration. The other accepted V2 route `lesson_pipeline/coordinator.py:run_lesson_pipeline` → `lesson_pipeline/core.py:CapabilityCoreGateway.render_lesson` → Hermes `learnflow_create/run/render` still feeds frozen V2 Core. Their inspected imports contain **zero LearnFlow V3 imports**. This checkpoint deliberately does **not** alter either product path or frozen V2 Core.

The historical V3-04 `VisualPatternRoute` is always `SELECTED_UNRENDERABLE` with `render_ready=False`; this is a deliberate truthful semantic-only contract, **not an implementation of V3 renderer routing**. V3-03's `require_render_consumption()` also refuses globally because many original semantic fields are declared unconsumed. Integration avoids modifying these locks and instead supplies a separate **certified one-family adapter** that requires the original route decision, V3-05 trace, V3-10 beat and replayed pixels. It explicitly enumerates remaining deferred signals and blocks unimplemented hero/cognitive requests rather than misreporting global consumption.

## Per-module implementation/consumer inventory (manual synthesis)

`scripts/audit_v3_reachability.py` produces a **machine-readable module + public-API inventory**, including direct AST callers and actual use of import names, test references and conservative status. The machine report is the primary enumerated inventory; this table adds the interpretation for the frozen repo.

| Module | Upstream call owner | Downstream/evidence consumer | Integration state / residual |
| --- | --- | --- | --- |
| `models.py` | V3 semantic source | validation/router and most V3 modules; tests contracts | INTERNAL_LIBRARY: V2/3 contract bridge, no production caller |
| `validation.py` | router, signal audit | V2 registry+scene+script gates; tests contracts | INTERNAL_LIBRARY and bounded offline integration |
| `signal_preservation.py` | V3 router & new integration | V2 content hashes, audit of consumed/deferred semantic leaves | PARTIAL_INTEGRATION; global render consumption still blocked |
| `pattern_router.py` | binary trace, new integration | VariantAttempt + RouteStatus evidence | SEMANTIC_ONLY; no built-in dispatch; adapter supports binary ONLY |
| `binary_search_trace.py` | offline lesson source + V3-06 | certified trace ledger/route, V3-10 pixel grounding | OFFLINE_INTEGRATION_ONLY |
| `sequence_renderer.py` | new integration adapter + other specialized renderers | H264 scene → beat QA → assembled video | OFFLINE_INTEGRATION_ONLY; no production registration |
| `beat_grounding.py` | new integration + V3-12 | verified essential beat→pixels from real decoded H264 | OFFLINE_INTEGRATION_ONLY; no narration sync |
| `code_process_renderer.py` | V3-07 script/test; integration topology predicate only | standalone CPU H264, DAG checker | PARTIAL: renderer unconnected, process/cyclic ABSTAIN |
| `math_renderer.py` | V3-08 script/test | standalone graph/equation MP4 | DEMO_ONLY; no production dispatch |
| `state_machine_renderer.py` | V3-15 script/test | standalone two author-curated pilot H264 | DEMO_ONLY; missing RepresentationType, renderer/route connector |
| `pedagogy_planner.py` | V3-09 scripts/tests | GroundedPedagogyPlan/hero ablation | OFFLINE planning only; not consumed by assembly scheduler |
| `blackboard_style.py` | specialized renderer helpers | shared Computer Modern/blackboard checks | INTERNAL_LIBRARY; reused, not orphan |
| `temporal_geometry.py` | V3-11/V3-14 | layout certificates and motion safety | INTERNAL_LIBRARY; demo-only full-scene scope |
| `temporal_demo_renderer.py` | V3-11/V3-13/14/17 | real temporal H264 QA for standalone demo | DEMO/INTERNAL; not combined into binary timeline |
| `artifact_critic.py` | V3-13 script/test | strict callback-bound reviewer contract | INTENTIONALLY_OFFLINE: no real VLM connector/human gold labels |
| `artifact_refine.py` | V3-14 script/test | one-track rollback from author-seeded snapshot | INTENTIONALLY_OFFLINE: no ArtifactIssue→LocalRepairIntent bridge; full clip reencode |
| `publication_gate.py` | V3-12/13/17 and new integration | actual scene source replay, FAIL-CLOSED | INTENTIONALLY_NO_PRODUCTION_WRITER |
| `evaluation_pilot.py` | V3-16 script/test, V3-17 audit | A/B manifest + synthetic statistical rehearsal | INTENTIONALLY_OFFLINE: real 12-pair human study NOT RUN |
| `release_gate.py` | V3-17 script/test and RGB helper in new integration | frozen Core checks, demo pixel parity/local simulated route | INTENTIONALLY_OFFLINE: not a production rollback |
| `offline_lesson_source.py` | integrated offline CLI/test | constructs certified author-authored V2/V3 source artifacts | NEW OFFLINE INTEGRATION SOURCE, no golden/test imports |
| `integration_slice.py` | `scripts/verify_v3_integration_closure.py` and tests | certified route, H264 scene, beat QA, ffmpeg remux, blocked review | NEW OFFLINE VERTICAL SLICE; only WORKED_EXAMPLE_BOARD |
| `__init__.py` | V3 consumers of public package exports | re-export canonical contracts and binary oracle | PACKAGE FACADE; incomplete exported registry intentionally |

**Potential orphan rules:** no library/API is automatically deleted from static absence. `POTENTIAL_ORPHAN_VERIFY_MANUALLY` means _no named static reference found_ and may reflect reflection, a public extension point or tests importing by path. Actual app import graph remains the primary production truth. Avoid the term production-wired for a module only imported from scripts, CI, test or V3 demos.

## Narrow integrated offline vertical slice (real MP4, NOT a full lesson)

1. Project-authored, fixed Binary Search case `values=[1,3,5,7,9,12,12,14,18], target=12` is built by `learnflow_v3.offline_lesson_source` with typed V2 registry, storyboard, script, SceneGraph and V3 teaching plan, pattern, beat and state ledger. **No import from golden-render scripts or test fixtures**.
2. `certify_and_route_binary_search`: actual independent V3-05 oracle; V3-02 V2/3 semantic validation; V3-03 source/signal hashes; V3-04 honest `SELECTED_UNRENDERABLE`; explicit new boundary dispatches only `WORKED_EXAMPLE_BOARD → STATEFUL_SEQUENCE_BINARY_SEARCH`. Other families `ABSTAIN_UNCONNECTED_FAMILY`, or process cyclic `ABSTAIN_INVALID_TOPOLOGY`. No CONCEPT_CARD fallback.
3. V3-10 compiles a manifest from the original claim IDs, semantic object IDs, step IDs, beat IDs, script segment IDs, exact frame intervals; the original V3-06 scene renderer emits a **real 640×360 H264 at 12fps**. The V3-10 verifier reads decoded frames and replays source/manifest. This is **renderer-synthetic beat timing**, not real speech alignment.
4. Separate FFmpeg `-map 0:v:0 -c:v copy -an` **one-scene timeline remux** creates another actual MP4; every RGB pixel in every decoded frame must hash identically to the original verified scene. This reuses FFmpeg without pretending a one-scene remux is a fully narrated/multiscene compositor.
5. V3-12 `review_binary_publication` replays certified source and real scene pixel QA. Requires `PUBLISH_BLOCKED`. A Pydantic receipt preserves stage order, trace/route/ledger/scene/object/claim/beat hashes, per-beat timeline, assembled file hash, full decoded RGB hash, declared unconsumed signals, no narration/production/human approval. An independent post-generation verifier recalculates key source and video hashes and reads the actual JSON receipt.
6. Uses private temporary work dir for each invocation; final MP4 is hard-linked only after all replays. Fault injection before/after assembly and **after final video link** cleans partial outputs and never overwrites pre-existing files. The script emits actual clip, immutable receipt and machine-readable call-graph JSON.

## Negative & contract mismatch controls

- Missing adapter gives ABSTAIN and **no output**, while missing specialized families (math, code/process, state machine, concept card) never silently downconvert to a card.
- V3-04's PROCESS_NETWORK semantic branch does not guarantee DAG; integrated dispatcher invokes V3-07 DAG checker for process and abstains on a directed cycle. A cyclic diagram does not pass because the semantic router says NETWORK.
- Immutable truth checks reject spoofed script numeric example, lost claim/beat/object references, changed source hash, output MP4 bytes appended or swapped, forged receipt-release flag and pre-existing output.
- `hero_candidate=True` and non-default cognitive-load requests **abort**, because this adapter cannot consume the requested planning signal. Other fields remain listed under `PARTIAL_DECLARED_DEFERRED` and cannot be mistaken for a globally complete signal proof.
- The historical V3-14 patch-only code is not a real localized video edit; it restores an entire trusted geometry track and reencodes a full MP4. **Not merged into new integrated renderer; remains a future guard**. Historical V3-13 reviewer callback likewise not promoted to actual VLM gate.
- Verify `PLAN_V3.md` reproducibility path drift: baseline and code/process command paths were specified before scripts existed. Correct path documentation; do not fake execution.

## Evidence, blockers, next decision

CI command (offline, CPU only): `python -m pytest -q --confcutdir=tests/v3 tests/v3/test_integration_closure.py`; `python scripts/verify_v3_integration_closure.py --output-dir /tmp/v3_integration`; `python scripts/verify_v2_core_freeze.py`.

Final V3 closure acceptance is **BOUNDED_OFFLINE_VERTICAL_SLICE_PASS** only after exact PR-head CI finishes and the H264/JSON inventory artifact is downloadable. **Real app registration, provider-bearing video generation, narration/TTS timing, full scene temporal certificate, whole-lesson fact/pedagogy quality, critic accuracy, local repair economics, full 12 paired topics and human scores remain NOT ESTABLISHED.** DO NOT merge frozen main, publish, claim 3B1B parity, or treat this as product release.
