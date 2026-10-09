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
