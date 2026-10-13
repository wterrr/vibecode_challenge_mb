# V3-56 — Evidence-Based Pedagogical Design Research & Agent Prompt Architecture

**Date:** 2026-10-13. **Status:** RESEARCH SPECIFICATION GO (bounded), **PRODUCTION NO-GO**, **PEDAGOGICAL/CREATIVE GAINS NOT MEASURED**.  
**Base:** [V3-55 Draft PR #89](https://github.com/wterrr/vibecode_challenge_mb/pull/89), exact `42dd591e4c5ce52f3d1bf251810c111d0019ab4a`.  
**Preregistration FIRST child commit:** `665b85526f4d0ae7ae0473f7701b3d12e894d3ce`. No production prompt or V2 Core changed; zero model-provider POSTs.  
**Machine evidence:** [18-lesson corpus](../research/v3_56_3b1b_lesson_evidence.json); [5-role typed architecture](../research/v3_56_agent_prompt_architecture.json); [A/B/C protocol](../research/v3_56_abc_evaluation_protocol.json); [strict offline verifier](../scripts/verify_v3_56_research.py).

## 0. Mandatory V3-55 closeout before branching

- Parent V3-55 PR #89 remains Draft, not merged; HEAD `42dd591`.
- Exact SHA Push #38328985561 completed SUCCESS; exact SHA PR #38328989638 completed SUCCESS. Push artifact #11781674076 name `v3-55-THREE-DOMAIN-NATIVE-HOST-TRIAL-QUALITY-NO-GO`.
- **Independently downloaded actual artifact** `/mnt/data/v3-55-native-exact-head.zip`, extracted three actual output files, SHA256 byte-for-byte equal to native receipts; `ffprobe` confirms video h264+audio aac, 1280×720, 15 fps:
  - Fraction 2/3→4/6: `1ec4e42275d46fdad0b618c3922ca5522197eed150cec2f1ef1e94c06a1ff092`, 499 frames, 33.27 s.
  - Ordered process: `2802f2ebf913bffaca380bd531bfa5fea6c47fe9e0a6913b6b5c47deea63ae54`, 513 frames, 34.20 s.
  - Attention reversed query: `5cbf7afde4b72166841c881b1111b057456037a3626d7822f3d17e76c8ff4aa3`, 957 frames, 63.80 s.
- Personally reviewed decoded frame samples at ~12%, 35%, 60%, 88% of each MP4. At 3.9/11.6/19.9/29.2 s, fraction shows physical segmentation and identity of shaded amount, but only two narrow diagrams and text. Process at 4.1/11.9/20.5/30.0 s remains a mostly static Start–Verify–Finish graph with arrows. Attention at 7.7/22.3/38.2/56.1 s shows query/keys, scores and colored value contribution, but layout uses very small labels and large blank regions.
- The prior CI visually witnessed narrow domain semantic events. It did **not** assess a human learner; packet is anonymous and scores blank. **V3-55 verdict: scoped technical PASS; creative pedagogical quality NO-GO/UNRATED; model authored FALSE; production BLOCKED**. This is NOT positive evidence for V3-56 prompt efficacy.

## 1. Reuse-first actual code audit at exact V3-55 HEAD

| Module | Observed behavior | What is missing / boundary |
|---|---|---|
| `pedagogy_agent/hermes.py` | Objectives, approved fact IDs, analogy/worked examples, assessment probes; no renderer coordinates | No typed target mental model, misconception hypothesis or before-after learner interpretation |
| `script_agent/hermes.py` | Fact claim indexes restored by host, objective indexes, teaching_function, spoken narration; segments can't invent claims | No machine-checkable link between an utterance and an observed conceptual transformation |
| `visual_director/hermes.py` | Frozen `CONCEPT_CARD`, `PROCESS`, `COMPARISON`, `HIERARCHY`; explicit preferential `CONCEPT_CARD` for dense scenes; forbids motion, camera, final pixel placement | This is intentional V2 compatibility, NOT safely removable in the current Core route |
| `visual_director/gate.py`, `visual_director/models.py` | V2 purpose, exact script/claim mapping and topology constraints | No V3 cognitive/visual witness sidecar currently travels through this model |
| `learnflow_v3/creative_scene_graph.py` | V3-51 six finite actions `reveal`, `emphasize`, `connect`, `hide`, `move`, `replace`; attention A1–A4 ledger | Not a generic deformable grid, physics, probability, 3D or Fourier animation grammar |
| `learnflow_v3/pedagogical_visual_grammar.py`, `semantic_scene_wire.py` | V3-47 five fraction/process operators, source/target identity, strict numeric claim scope and UNKNOWN predicate | Re-keyed graph and local fraction are not new knowledge families; no invented boolean condition |
| `learnflow_v3/creative_motion_director.py` | V3-53 bounded attention compare→normalize→transport→compose and optional intro/inspect, host-computed QKV | Specialized to Attention and three styles, not general visual thinking |
| `learnflow_v3/creative_candidate_acceptance.py` | strict mock wire stage diagnostics, V3-54 frozen attention topic | No general LLM schema success from mocked admission |
| `learnflow_v3/creative_visual_quality_gate.py` | foreground occupancy, sampled decoded change, pixel differences | Pixel diversity is not explanatory quality |
| `learnflow_v3/lesson_quality.py`, `independent_quality_pilot.py`, `artifact_critic.py` | media QA, human reviewer packet machinery, critique stages | Word-level alignment unmeasured, real human ratings absent; reuse this workflow before adding another agent |

**Causal decomposition:** Prompt presently restricts the frozen V2 director; its schema prevents extra operations; the current V3 compilers support finite domain operations only; creative QA lacks external comprehension evidence. A single larger prompt cannot solve all four independently.

## 2. First-party comparative corpus — 18 Read lessons

All 18 exact URLs below were opened and first-party Read content examined; visible lesson prose with embedded `Image`/`Video` markers supported the representation descriptions. The final two design columns are **our analytical inferences grounded in that content**, not quotations, validated learning outcomes, or a certified reconstruction of motion from an encoded clip. **Full video playback, soundtrack, word-level timing and per-video shot timestamps were not independently reviewed in this checkpoint**. Three corresponding scene-code files were retrieved and read via the original 3b1b GitHub repository. For all other lessons, source-to-video mapping remains unverified.

| # | Official Read | Cluster | Explanatory representation (analysis) | Mechanism suggested by Read (analysis) | Code evidence |
|---:|---|---|---|---|---|
| 1 | [la_span](https://www.3blue1brown.com/lessons/span/) | linear-algebra | two labeled basis vectors + resulting tip | change two scalar coefficients while vector identities persist | scene source inspected |
| 2 | [la_linear](https://www.3blue1brown.com/lessons/linear-transformations/) | geometric-transformation | grid + basis arrows + test point | apply shared map to grid and point, preserve parallel lines | scene source inspected |
| 3 | [la_matrix](https://www.3blue1brown.com/lessons/matrix-multiplication/) | geometric-transformation | fixed test point on persistent grid; first + second transform | rotate/shear sequentially then collapse to composition | source UNKNOWN |
| 4 | [la_det](https://www.3blue1brown.com/lessons/determinant/) | geometric-transformation | unit square + deformed region boundary | transform entire region, track oriented area ratio | source UNKNOWN |
| 5 | [la_eigen](https://www.3blue1brown.com/lessons/eigenvalues/) | geometric-transformation | persistent candidate arrow and underlying grid | transform grid while one direction stays collinear | source UNKNOWN |
| 6 | [la_dot](https://www.3blue1brown.com/lessons/dot-products/) | spatial-reasoning | two arrows, fixed projection axis | project one onto other; continue into scalar mapping | source UNKNOWN |
| 7 | [la_cross](https://www.3blue1brown.com/lessons/cross-products/) | spatial-reasoning | two vectors spanning a parallelogram | change vectors while preserving parallelogram identity | source UNKNOWN |
| 8 | [calc_essence](https://www.3blue1brown.com/lessons/essence-of-calculus/) | calculus | circle, expanding concentric rings, unwrapped strip | slice ring then straighten into nearly rectangles | source UNKNOWN |
| 9 | [calc_deriv](https://www.3blue1brown.com/lessons/derivatives/) | calculus | car trajectory, secant endpoints and tangent | shrink separation between two persistent points | scene source inspected |
| 10 | [calc_integration](https://www.3blue1brown.com/lessons/integration/) | calculus | area strips + moving upper endpoint | grow accumulation while corresponding area function updates | source UNKNOWN |
| 11 | [calc_exp](https://www.3blue1brown.com/lessons/eulers-number/) | calculus | population markers + continuous growth curve | population scales over equal time intervals | source UNKNOWN |
| 12 | [prob_bayes](https://www.3blue1brown.com/lessons/bayes-theorem/) | probability-area | population rectangle subdivided by condition and outcome | resize/condition subregion while area identities retained | source UNKNOWN |
| 13 | [compo_fourier](https://www.3blue1brown.com/lessons/fourier-series/) | composition-temporal | vector chain with persistent phase/frequency IDs | rotate components while tip-to-tail sum traces path | source UNKNOWN |
| 14 | [nn_intro](https://www.3blue1brown.com/lessons/neural-networks/) | computation-temporal | input pixel grid and activation nodes | propagate changes through layers with identity of each unit | source UNKNOWN |
| 15 | [nn_gradient](https://www.3blue1brown.com/lessons/gradient-descent/) | computation-temporal | point on loss landscape and parameter update arrow | iteratively move parameters along gradient | source UNKNOWN |
| 16 | [nn_gpt](https://www.3blue1brown.com/lessons/gpt/) | computation-temporal | token boxes then embedding vectors and layered blocks | flow contextual token representation through stages | source UNKNOWN |
| 17 | [nn_attention](https://www.3blue1brown.com/lessons/attention/) | computation-temporal | persistent tokens, Q/K projections, values and context | scores→softmax→weighted transport to context | source UNKNOWN |
| 18 | [nn_mlp](https://www.3blue1brown.com/lessons/mlp/) | computation-temporal | token feature vector and intermediate activations | feature expansion, activation and projection back | source UNKNOWN |

**Source-code sample audit:** `3b1b/videos/_2016/eola/chapter2.py` blob `c5f01b7` defines classes including `ShowVaryingLinearCombinations` / `LinearDependentVectors`; `_2016/eola/chapter3.py` blob `0fc0fc4` includes `TransformManyVectors`, `TransformInfiniteGrid`; `_2017/eoc/chapter2.py` blob `e1e2744` includes `IntroduceCar`, `ShowSpeedometer`, `CompareTwoTimes`. This shows those mechanisms are represented in scene source; no code copied, built or executed; no per-shot timecodes certified.

**Licensing caution:** Original [3b1b/videos](https://github.com/3b1b/videos) scene code is **CC BY-NC-SA 4.0**; 3b1b/manim engine is MIT and Manim Community is a distinct independently maintained edition. Reuse high-level teaching ideas only, write new implementations, never port commercial scene scripts or media without clearance.

## 3. Transferable pedagogical design principles: principle → field → host test

| Principle | Research support | Proposed V3 contract field | Host validation / gap |
|---|---|---|---|
| Observable problem before formalism | Essence of Calculus circle area; derivative speed paradox; Fourier drawing | `learning_difficulty`, `probe_question`, `target_mental_model` | question maps to approved objective and eventual observable witness; judgment of relevance still human-rated |
| Persistent object identity | linear grid/basis, circle rings, token/value carriers | `persistent_semantic_objects[].object_id/identity_invariant` | preserve deterministic object IDs across beats or explicitly validate split/merge; reject vanishing/replaced labels as unproved motion |
| Invariant-preserving transformation | determinant area scale, fraction same area, Fourier vector sum | `verified_transformations[].invariants` | host verifies exact math/trace and rendered before-after if known; otherwise UNSUPPORTED |
| Representation chosen by mechanism | area for Bayes, grid for matrix, rotating vectors for Fourier | `visual_representation.representation_kind`, `why_this_representation` | selection from finite certified capabilities; can't claim unimplemented 3D/field physics |
| Progressive revelation | ML token→embedding→QKV; secant→tangent; span→basis | `narration_anchors[].relative_order` | topological ordering of prerequisites, no equation prematurely asserted |
| Continuous causal motion | basis deformation, gradient descent state change, attention value transport | `verified_transformations.precondition/postcondition` | decoded pixel/video object region witness agrees with source ground truth |
| Questions/checkpoints and closure | circle area rediscovery, Euler growth, conditional Bayes | `learning_difficulty.probe_question`, `explanatory_closure` | probe must refer to same claim/model, not just narration filler |
| Audio/visual explanatory synchronization | all lessons; exact timing intentionally unverified | `narration_anchors.time_source` | real audio-derived beat frames only, word alignment explicitly unknown unless measured |
| Unsupported operation must fail closed | LearnFlow existing V2/V3 safety | `unsupported_capability_outcome` | reject unverified transform and prevent decorative `CONCEPT_CARD` from silently claiming successful explanation |
| Evidence-based independent critic | V3-23/V3-48/V3-55 review precedent | `expected_observable_explanation`, critic output | technical native witness is prerequisite, not sufficient for independent expert preference or learner test |

## 4. V3 Pedagogical Explanation Contract (PEC)

The proposal is research-only and **NOT WIRED** to production. Machine-readable version [v3_56_agent_prompt_architecture.json](../research/v3_56_agent_prompt_architecture.json) provides Draft 2020-12 JSON schema, required fields and typed safety checks. The expanded per-role [research-only system/developer prompt templates](../research/v3_56_agent_prompt_templates.md) define concrete cognitive, narration, visual, motion and critic responsibilities; none is active in production. Mandatory groups:

1. `scope`: canonical topic/approved claims + host evidence digest.
2. `learning_difficulty`: hypothesized misconception, probe question, explicitly not measured learner state.
3. `target_mental_model`: mental model and observable conceptual change.
4. `visual_representation`: kind and bounded `capability_ids`.
5. `persistent_semantic_objects`: names, IDs, invariants, grounded claim IDs.
6. `verified_transformations`: finite op, input and output persistent IDs, claim IDs, evidence hash, before/after predicates, invariant, supported renderer capability.
7. `narration_anchors`: beat ID, referenced object/transform indexes, ORDER_ONLY or real audio-derived timing, no fake word timestamps.
8. `expected_observable_explanation`: what must actually appear in decoded video for each transformation.
9. `explanatory_closure`: resolves initial question or explicitly notes limitation.
10. `unsupported_capability_outcome`: supported, unsupported evidence/capability or deferred human review, publication fail closed.

**Cross-field host checks (must implement in later checkpoint, not yet present):** claim set subset of approved IDs; evidence SHA exact, renderer capability enumerated; transformation inputs/outputs exist and reference persistent objects; no changing object identity without declared mapping; beat order corresponds to source truth; every major transform has encoded physical witness; unsupported publication forbidden; provenance and expert-human evaluation separate. A JSON Schema alone cannot prove any of these semantic invariants.

### Agent integration architecture

```text
Research/fact ledger ── canonical approved claims/hash (HOST)
  ↓
Existing PedagogyPlan + optional V3 Cognitive Design sidecar
  ↓
Existing LessonScript + optional V3 Narrative/anchor sidecar
  ↓
Existing Visual Director (V2 route untouched) / separate V3 Visual Thinking plan
  ↓
Existing Creative/Motion Director + declared finite capabilities
  ↓
Host evidence validator → isolated compiled Manim → real MP4
  ↓
Existing video quality/critic + independent blind human reviews
```

**Agent drafts** are per-role in machine spec. Pedagogy: learner misconception hypothesis, desired observable mental model; Script: question→prediction→observe→formalize→closure, each beat claim-bound; Visual Director V3: choose finite visual metaphor + persistent objects, if unsupported explicitly decline; Creative/Motion Director: schedule finite source-grounded actual state changes, no free code; Critic: compare claimed observable against H264 and separate judgment from scoreless pixel gates. Reuse the existing five service roles, **do not create five new agents**.

V2 Core's `CONCEPT_CARD` fallback continues unchanged for V2. V3 may create a separate opt-in sidecar only. This requires an adapter/routing proposal before any production code changes. A V3 plan cannot silently pass into frozen V2 schemas.

## 5. Evaluation plan — designed, not executed

[Machine-readable A/B/C protocol](../research/v3_56_abc_evaluation_protocol.json):

- **A:** frozen prompt + frozen V2 Core.
- **B:** proposed V3 agent prompts + the **same frozen V2 Core**; record every unsupported visual request/reject, never erase before counting.
- **C:** same prompts as B + separately certified expressive V3 renderer. Equal source claim ledger, topics, inference parameters, request/tokens budget, narration/audio constraints and eligibility.
- Freeze four topic ID feasibility pilot: basis change, conditional sampling, damped oscillator, graph search. Not in prompt examples. For reliable efficacy claims require a separate disjoint >=24-topic domain-stratified confirmatory plan and >=3 independent blinded raters per video.
- Predefine invalid output, claim rejection, no video, unrenderable operator, sync and overlap failures as **intention-to-treat failures**. Reject selection of only successful examples.
- Primary paired clarity comparisons B−A (prompt) and C−B (renderer) with per-topic bootstrap CI and correction for two comparisons; proposed minimum practical difference >=0.5 on 5-point scale, 95% CI lower >0 for >=24-topic prereg sample. Four topics are only feasibility, not inferential power.
- No real provider calls or rater ratings are claimed here. Any quality effect remains **NOT TESTED**.

### Confounders and hard risks

1. A/B may have fundamentally different ability to express V3 sidecar in V2; treat unrenderable as failure, no silent dropping / creative quality claim.
2. Attention-specific evidence and fraction grammar are NOT generalized to arbitrary Physics or Bayes.
3. Inferred learner misconceptions from lesson Read are not validated psychology.
4. Audio-derived beat alignment does not establish word-level synchronization.
5. Personal visual inspection by researchers is not blinded human preference or learner outcome.
6. Per-video 3B1B source-code/timeline mapping is mostly missing; no fake timestamps or copying.
7. Provider output variance may remain if seed is unsupported; record it, not confound with prompt improvement.
8. Intellectual property: high-level teaching principles are general ideas; original scene/audio/image reproduction prohibited.

## 6. Acceptance and follow-up

| Gate | Result |
|---|---|
| V3-55 exact HEAD CI / downloaded native AV receipts | PASS (technical bounded); QUALITY NO-GO |
| 15+ first-party Read and six mechanism clusters | 18 direct READ verified (Read-only level) |
| 15 end-to-end source/video timing audits | **NOT DONE**. Specific timecodes UNKNOWN |
| >=3 matched 3B1B source code scene files read | 3 inspected, **not run** |
| Principle mapped to contract + host validator / unsupported capability | SPECIFIED, semantic validators **NOT IMPLEMENTED** |
| System/developer prompts per existing five roles | RESEARCH DRAFT, not applied |
| Frozen V2 unmodified, paid model calls zero | PASS by scoped changes |
| A/B/C fairness prereg and negative controls | SPECIFIED only, not executed |
| Human educational or creative improvement | **NOT MEASURED** |

**Decision: BOUNDED RESEARCH GO for documentation/contract feasibility; NO-GO for deployment, model quality claims, blanket 3B1B method emulation or claim of video-level comparative validation.** It would be misleading to call this a fully verified 15–20 *video* study: first-party Read was examined for 18, but only scene code for 3 and no end-to-end media timing for any. Future research must close that gap independently before citing exact teaching-video pacing.

**Exactly one next checkpoint proposal:** V3-57 — V3-sidecar Contract Adapter & Offline Host Witness Feasibility. Implement cross-field validated PEC on existing host ledger and 3 deliberately disjoint test families; compare an A/B at frozen renderer *without calling paid provider until separately approved*; preregister all unsupported results. Do not alter V2 Core. If it cannot represent a real mental-model change for heldout visual mechanism, stop rather than decorating with cards. Production remains BLOCKED.

## 7. Evidence-depth correction after direct 3B1B source audit

Supplemental prereg `593d1db5cf6f34d4d83d657862074816d6d48d9b` and [deep evidence report](v3_56_deep_video_audit_addendum.md) contain **18 actual first-party source Python files (by SHA) and 113 Read-sequence pedagogical beats**, not just the original three scene files. These reveal both animations and deliberate static reasoning. Euler `e` Read explicitly pivots to numeric patterns when geometry does not provide a clear explanation; Fourier introduces a formula teaser before the complete explanation; Bayes benefits from static representative counts; grid transforms need a static reference backdrop.

This uncovered and corrected a real specification error: initial PEC forced an integer `transformation_index` for every explanatory witness. Now `STATIC_COMPARISON`, `QUESTION_HOLD` and `SYMBOLIC_DEDUCTION` have null index; verified animated witnesses still require a real transform integer. These are **research-only schema and proposed prompt edits**, not proof of model/renderer generalization.

**Do not misrepresent this addendum as video analysis. Actual 3B1B edited video decoding and voice alignment = 0 of the 15 required clips.** This deeper first-party READ+SCENE_SOURCE examination improves the architecture recommendations, but the requested video/temporal checkpoint remains **NO-GO**, and production BLOCKED until actual video/audio receipts can be collected. Offline verifier `python scripts/verify_v3_56_deep_video_audit.py` must report `VIDEO_AUDIT_NO_GO` even when evidence integrity tests succeed.


## Dated correction — user supplied actual Attention Ch6 MP4 after preceding report

This earlier report was true **at the time written**: no original native edited films had been acquired. The user has subsequently supplied the **full native Chapter 6 Attention MP4** (SHA `439e154fffbb8696a37753d765c4f64bc06d25fbb17cb3d98bcc842045d85cb9`). We directly decoded and visually inspected frames across the 26:09 file, including 105 samples every 15s and ~70 denser samples, and verified an AAC soundtrack physically exists. See [new native-video evidence report](v3_56_attention_ch6_native_video_audit.md), [timestamp receipt](../research/v3_56_attention_ch6_native_video_receipt.json).

**Current amended count: 1 of 15 original edited complete native files visually sampled, 0 of 15 complete word-aligned audiovisual pedagogical reviews.** The Read-only 113 beats in the prior dataset remain read-based, not retroactively labeled timestamps. The displayed earlier `0/15` film-available count is historical; the full requirement of 15 matched video + speech audits remains NO-GO. Scope is V3-56 Draft PR #90 only, production blocked.


### Dated addition — external caption proxy ↔ user original MP4 frame evidence

The user uploaded the full actual 26-minute Attention Ch6 MP4. Beyond the original timecoded video storyboard, a later V3-56 research extension preregistered `377d1d03d47135a1b6c113e4e529d9a5ac6bc42c` and paired **12 third-party timecoded caption cues** to **60 newly decoded native frames and original AAC PCM signal**. Strong examples: at **01:49**, caption topic `mole` leads visible mole introduction ~02:01; at **05:57–06:34** a *made-up* adjective–noun mechanism becomes a visible query; at **14:30–14:54** a held matrix transitions into weighted Value contributions. Full report [Narration–Visual Alignment](v3_56_attention_narration_visual_alignment.md), machine receipt [12 anchors](../research/v3_56_attention_native_caption_alignment.json), strict verifier `scripts/verify_v3_56_attention_alignment.py`.

**Scientific limitation:** the third-party mirrored caption is NOT independent native ASR, and PCM energy/RMS cannot identify uttered words or pauses over music. Therefore exactly **12 bounded caption-topic/native-frame correspondences, 0 native word-aligned records**; the requested 15-film audiovisual study remains NO-GO. The PEC proposal gained an optional source-scoped LEAD/OVERLAP/FOLLOW link, with tests disallowing caption-proxy-to-native-speech claim laundering. Original 3B1B video/screenshots not redistributed to repo, V2 Core/production unchanged.


### Evidence-depth update — Native Speech–Visual Grounding (2026-10-13)

A new within-V3-56 source-scoped probe preregistered before measurements (`fc3a403c5a4d79ea0ac5c5409bfdf6a5f2aa7575`) used the **same original uploaded 26:09 Attention MP4** and the same 12 external-caption anchors. Actual decoded audio = **12,553,265 mono PCM samples at 8kHz**, 0.5s RMS; video = **180 directly decoded 2s-spaced native image samples** around anchors with frame SHA, strongest/weakest measured image change intervals. See [report](v3_56_native_speech_visual_grounding.md) and [receipt](../research/v3_56_native_speech_visual_grounding.json).

**Do not retrospectively upgrade external captions, frame-change peaks, or native audio RMS to observed words:** environment lacks ASR packages and pretrained model weights, with blocked model-host downloads; human native speech transcription was not independently performed. **Native word/sentence/phrase alignment = NO-GO, 0/12 verified versus >=8 prereg threshold**. The initial 12 external-cue-to-frame correspondences remain valid in their limited scope, not speech alignment. Visual explanation and optional PEC architecture = **bounded research only**, real learning outcomes and production release remain BLOCKED. No model API, no main merge, no V2 Core changes.
