# V3-33 — Six Unseen Domains, Transfer Audit & Independent Educational Quality Gate

**Scope:** stacked on V3-32 PR #66, never merge `main`. Source-only offline analysis + **two previously exposed regression-control videos**, not six new-topic media. No LLM provider usage. Preregistration commit: `8dcb2d32f856af0808bf7abb79c3ddb772cd4450` BEFORE adding audit implementation. No replacing selected topics based on render support. The V3-16 12-topic confirmatory manifest is never consumed.

## 1. Frozen new topic selection: predeclared, independent of renderer outcomes

Selection: for each domain in fixed order Math, Physics, Chemistry, Biology, CS, History, take the lexicographically smallest unused corpus `topic_id` AFTER excluding the V3-16 12 registered/diagnostic topics, all six V3-27 development topics, and Binary Search `lfb-005-cs`. Exclude V3-30–32 `lfb-002-cs` too. All inputs are drawn from the immutable LearnFlowBench 100-topic corpus and are hashed by exact UTF-8 query bytes; no cherry-picked replacement.

| Domain | Preregistered topic | Query SHA256 | Content |
|---|---|---|---|
| Math | `lfb-018-math` | `376a06049a51990ddb7fe7a340ef42222b8d89ed601fa8a22dfe971524cf113d` | Fractions and ratios |
| Physics | `lfb-035-physics` | `db9ae242a3743d4192886745cd90b49bbc0ce38691873a190e542dff02563d8a` | Newton's three laws |
| Chemistry | `lfb-070-chemistry` | `c54209c5d23e8b4374e1a4346d273cdfad7fabf67cb2b912a6af18e8b8f5b880` | Periodic table trends |
| Biology | `lfb-053-biology` | `17a66c0b9105f09fb100df5383a2effd3ad5b2d66ff07fcbad63378c0b0e494c` | DNA versus RNA |
| CS | `lfb-001-cs` | `0c3bcb5132b4ebc199e6519d930d54e2bc947928570d17d2f41cb62c02f02d3d` | Variables and data types |
| History | `lfb-085-history-general` | `7f350923fc7e25b9d8b2468ca47ae3ede6d87d9de568eff1fec99d702319bdbe` | Industrial Revolution |

Manifest: `benchmarks/learnflowbench/v3/v3_33_locked_unseen_topics.json`. Detect and FAIL on hash drift, topic replacement, frozen leak, wrong domain, dropped row. No hidden selection attempts.

## 2. Actual Research → Lesson → Visual → AV reuse audit

| Component | Confirmed reusable evidence | Still missing for NEW selected topics |
|---|---|---|
| Research | Hermes ResearchPack, EvidenceGraph, FactReport and publisher quotation validation; V3-28 source-bound OpenStax math and physics claims; Python V3-30 source certificate | Independent **topic-specific** sources and verified claims for all six new concepts. Reusing an old citation to cover unrelated content is prohibited |
| Script | V3-32 `LessonSemanticContract` typed source→example→objectives→event narration and five strict beat gates | V3-32 is restricted to `lfb-002-cs` and bounded one-argument integer function semantics; not a general curriculum model |
| Pedagogy | V3-09/Hermes typed plans, source-bound template composer on V3-28 two author-curated sources | General concept-sensitive objectives, misconceptions and assessments for these six new topics |
| Visual Director | V3-04 semantic router; V3-28 passes Visual Director typed certificate | Routing candidate is `SELECTED_UNRENDERABLE` without certified family semantic adapter |
| Specialized math | V3-08 finite polynomial FunctionGraph; V3-27/28 certified **linear slope** geometry | Fractions and ratios are **not** a linear slope lesson. Do not draw a fake graph |
| Specialized physics | V3-28 constant-acceleration `v(t)=v0+at` | Newton's **three laws** need sourced forces, motion and corresponding certified examples; a velocity graph is insufficient |
| Code/Process | V3-07 restricted integer assignments and process topology, V3-31/32 bounded function AST | Variables **and data types** lack independently certified type semantics and a topic-specific five-beat contract; code assignment demo alone is partial, not acceptance |
| State Machine | V3-15 bounded curated state transition video | No audited facts or transition semantics for biology/chemistry/history; diagrams cannot substitute for evidence |
| Audio & MP4 | Native eSpeak physical WAV→AAC/H264/SRT, decoded source-frame evidence; CMU background black | Need fact-bound narration+semantics before rendering **these** new topics |
| QA/production | Frozen V2 quality gates and source/pixel/temporal checks | Human teaching-quality/aesthetic ratings, fact subject-matter expert confirmation and commercial rights |

Result: **0/6 preregistered new topics currently has an exact bound source + worked example + script + semantics + verified renderer path**. Therefore **6/6 ABSTAIN**, **0/6 new videos** and **0/6 end-to-end generalization PASS**; this is a valid falsification result, not failure of the CI runner. No auto `CONCEPT_CARD` fallback; no source/video hashes may be fabricated to change an ABSTAIN.

## 3. Actual prior-exposed video positive controls (EXCLUDED from new coverage)

To ensure the existing renderer remains functional, reuse V3-28 `source_grounded_compiler.run` with **unchanged** two author-seeded, source-cited development examples: `lfb-020-math` (slope) and `lfb-036-physics` (velocity/constant acceleration). Run actual offline native H264/AAC MP4s with source-bound Hermes Research/Evidence/Fact, V3-09 Pedagogy and Visual Director certificate checks, decoded pixel replay, source claim IDs, WAV-measured SRT and AAC. These are **regression controls**, not fresh topic wins. Both have historically succeeded; this specific checkpoint needs its own exact-head output to claim positive-control PASS.

V3-31 true actual MP4: [run #37899219231](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37899219231), hash `09354fe9d11a336da204a234d8bb12dde64d051ac55bbaf44ce77a72dee9dff1`, 4 stages/441 frames, AAC non-silent. V3-32 true actual MP4: [run #37902091916](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37902091916), hash `37eb049461786a47f50dfdc158a8253db9fc173c5a86e1252a7a92dc30205225`, 5 stages/674 frames. Both files and original receipt were downloaded, SHA verified, and five-beat decoded V3-32 contact sheet inspected. V3-32 improves the visible argument→parameter→expression→return causal progression and includes an explicit arithmetic explanation. **This is descriptive evolution, not a blinded, statistically validated educational improvement**.

## 4. Separate educational-quality rubric, not a technical rebranding

Eight preregistered quality dimensions: factual correctness, conceptual clarity, explanatory completeness, cognitive load, visual hierarchy, pacing, narration–visual alignment and visual creativity. Each has a proposed verification method (independent subject-matter reviewer or blinded learner with standardized rubric, plus decoded measurable audio/pixel evidence). **No qualified human reviewers were recruited**. All scores remain `null`, assessor count 0 and final `NOT_ASSESSED`. Codec PASS, low source-frame MAE, and non-silent audio only prove media integrity; they do not guarantee teaching, legibility for target learners or beautiful instructional animation.

Suggested future study (NOT part of V3-33): independently recruit reviewers for math/physics/CS, time-stamped issues, pairwise blind V3-31 versus V3-32 preference and pre/post novice comprehension, preregister success thresholds and handle contradictory ratings transparently. Never fabricate score.

## 5. Falsification/acceptance

- No overlap with frozen V3-16, V3-27 or Binary Search; verify immutable query SHA and one-attempt-per-domain denominator.
- Every unsupported new topic ABSTAIN with exact reason, provenance and `null` MP4; concept-card fallback forbidden.
- Two **old** domain-specific positive controls render actual offline MP4s with H264/AAC codec, SRT, decoded pixels, source provenance, and non-silent AAC; 0 additional provider requests.
- Contract integrity, forged media/source PASS, forged human scores and mutation tests fail closed. Benchmark/Core frozen regressions unchanged.
- Artifacts include six-domain coverage matrix, machine-readable ABSTAIN report, control MP4 receipts/contact sheets, quality rubric and exact-head audit report.

**Pre-run verdict:** New-topic source-bound generalization NO-GO 0/6; engineering positive-control status PENDING CI; independent educational-quality status NOT_ASSESSED and production BLOCKED. Never merge main based on old-control technical PASS.

## 6. Executed V3-33 no-cherry-pick coverage and *actual* native control artifacts (2026-10-09)

Implementation SHA `272a99911ae40f03205dc1520ca94f3cba7cf598`, [GitHub Actions #37904218175](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37904218175) **SUCCESS**: 11/11 anti-overclaim/selection/mutation tests PASS before media (one media-only test deselected), then 73/73 combined previous checkpoint/regression tests PASS after rendering. Frozen V3-16 benchmark 12 topics 6 domains 4 easy/medium/hard PASS, LearnFlowBench PASS, V2 Core PASS. Zero provider/API calls. First CI run #37904010569 correctly FAILed when negative tests detected that ABSTAIN schema allowed a non-null renderer; changed schema to `renderer:None` and preserved the adversarial test rather than weakening it.

Actual [artifact #11604165488](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37904218175/artifacts/11604165488) was downloaded and ZIP CRC was independently checked: PASS, 15 files including six-domain machine ledger, coverage matrix, eight-dimensional quality gate, two actual H264/AAC MP4+SRT, source/scene/Script compiler receipts and all decoded contact sheets. Both bytes match compiler SHA256:

| Control (OLD, outside unseen denominator) | Real MP4 SHA256 | Frames | Runtime | Max decoded MAE | AAC RMS by physical beat |
|---|---|---:|---:|---:|---|
| V3-28 Math `lfb-020-math` | `523aac6f863c6dbb3a72f314c8ace917bdb5ed2931a65154836dea4c47fed19d` | 377 | 20.94s | 0.114 | [0.0895, 0.0930, 0.0894, 0.0933, 0.0884] |
| V3-28 Physics `lfb-036-physics` | `abe5aa75fbb81223aa779bc4b172f91f23284e51f984140f473dbefdbb7fcec4` | 404 | 22.44s | 0.147 | [0.0825, 0.0832, 0.0770, 0.0831, 0.0847] |

All checks at real 1280×720 18fps AAC/H264; both original program-generated SRT subtitle timings are derived from physical WAV beat samples, not fabricated word timestamps. They are **previously exposed controls** and cannot be advertised as V3-33 unseen model generalization. The source URLs are existing manually authored OpenStax citations with checked source relation and deterministic arithmetic; source URLs alone do NOT prove external semantic fact review.

### 6.1 Manual (unscored) contact/movie QA issue inventory — timestamp-grounded

The five decoded Math frames show the linear curve `y=1+x`, stable axes and sequential true point highlights. The captions narrate points at 0–4.17, 4.17–8.11, 8.11–11.72, 11.72–15.22, and 15.22–20.94 seconds. **Issue M-1 (0–20.94s):** educational structure is repetitive plotted-point enumeration with the core slope meaning primarily summarized in the last beat. This is a visual-pedagogy concern, not an independently confirmed comprehension failure.

The five Physics frames depict source-bound `v(t)=1+t` plus `a=1 m/s²`, with correct axes labels `time (s)` and `velocity (m/s)`. The five clips run 0–3.83, 3.83–7.56, 7.56–11.39, 11.39–15.22, 15.22–22.44 seconds. **Issue P-1 (0–15.22s):** data-point narration alone may not teach the causal connection between acceleration and the linear velocity graph. **Issue P-2 (15.22–22.44s):** only the final beat verbalizes acceleration, with no direct visualized force/mechanism. This remains the old constant acceleration topic, **not** Newton's three laws.

Comparison using two independently downloaded prior real MP4s: V3-31 (4 beats, 441 frames/24.50s) changes the state table but omits an explicit Evaluate step and audible `3+2=5` explanation; V3-32 (5 beats, 674 frames/37.44s) introduces a distinct, narrated Evaluate stage 22.06–30.39s and Return 30.39–37.44s with an animated value token. **This is observed implementation change, not causal evidence of higher learning outcomes**. The V3-32 audio-relative event fractions are planned from sampled beat duration; they are *not* independently aligned word onset timestamps.

### 6.2 Final scientific decision

**New-topic support** = 0/6 certified source-to-renderer paths; 6/6 principled ABSTAIN; 0 new-topic MP4; no concept-card fallback, no replacements. **Old renderer regression** = 2/2 real source-bound Math/Physics MP4 technical PASS, excluded from the new denominator. **True autonomous LLM authoring and multi-domain transfer** = NOT PROVEN (host compiler does not count). **Human educational quality and professional visual creativity** = NOT ASSESSED; all eight structured rubric scores are null with zero assessors. **Production** = BLOCKED. Additional source families and general semantic planning must be implemented before revisiting this frozen development set; do not tune the chosen topics after observing these outcomes.

Final documentation-commit HEAD will require fresh CI PASS; the confirmed media/artifact above pertains to the referenced exact implementation SHA.
