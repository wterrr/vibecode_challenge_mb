# V3-27 — Frozen Six-Domain E2E Coverage Audit and No-Cherry-Pick Evidence

**Scope:** one user-authorized checkpoint, stacked on PR #60, no main merge, no paid API, no participant recruitment, no release. **Selection frozen in a separate earlier commit \`e2c2d9cd39a1860601f8b56744685aac49690a62\`** before any V3-27 render adapter was committed.

## 1. Pre-attempt topic lock

Read \`benchmarks/learnflowbench/corpus_v1.json\` and immutable V3-01 protocol. Exclude the 12 confirmatory IDs and exposed Binary Search \`lfb-005-cs\`, then in each of the six corpus domains sort available topic IDs lexically and select *index 1 (zero-based)*; same rule across all domains, before rendering. Never substitute topics based on results. The full input query SHA-256 is stored in \`benchmarks/learnflowbench/v3/v3_27_locked_development_topics.json\`; mutation tests recompute and reject drift.

| Domain | Locked topic | Target |
|---|---|---|
| Computer Science | lfb-002-cs | Functions and parameters |
| Mathematics | lfb-020-math | Slope of a line |
| Physics | lfb-036-physics | Velocity versus acceleration |
| Biology | lfb-054-biology | Photosynthesis |
| Chemistry | lfb-071-chemistry | Acids and bases |
| History | lfb-086-history-general | Causes of World War I |

These 6 are **development coverage attempts**, NOT the separate 12 V3-16 confirmatory topics. Every attempt counts, including FAILURE or ABSTAIN. Selection index 1 is openly declared, not statistically representative or randomized.

## 2. Audit: actual pipeline and reuse-first verdict

| Desired stage | Observed existing code | End-to-end availability |
|---|---|---|
| Research | Hermes Research / approved claims, V2 evidence machinery | No source-grounded runtime for arbitrary six frozen domain prompts wired into V3 render |
| Script | Hermes Script and voice-authoring contracts | No certified generic six-domain script-to-typed semantic event compiler |
| Pedagogy | V3-09 \`pedagogy_planner.py\` with objective/misconception provenance | Standalone artifact; no universal narrated renderer handoff |
| Visual Director | V3-04 \`pattern_router.py\` returns SELECTED_UNRENDERABLE for candidates without rendering owner | Semantic selection alone never authorizes an MP4; no general six-domain bridge |
| Renderers | V3-06 sequence, V3-07 Code/Process, V3-08 finite polynomial graph/equation, V3-15 bounded State Machine | Finite independent verified renderers, none a universal domain source generator |
| Narration | V3-19 audio-matched multi-scene Binary Search + V3-20 measured physical utterances | Fully source-certified only for Binary Search, a repeatedly exposed example |
| MP4 assembly | V2 FFmpeg assembler reused for binary; V3-22/24 native H264 renderer | Source-bound real MP4 exists; not general all-domain AV |
| QA | V3-10/11/12 source/geometry/publish blocked; 13 critic adapter, 14 bounded repair, V3-26 Chrome E2E | Component engineering QA yes; factual/human teaching/cross-domain end-to-end gate NOT established |
| Production | V3-18 local developer-only binary preview, V3-19 guarded lesson preview; regular jobs remain V2 | No authorized V3 production route, correctly BLOCKED |

**Reuse-first bounded bridge:** Reuse V3-08 \`FunctionGraph\`, \`GraphPoint\`, source-hashed \`SceneGraph\`, \`verify_function_graph\`, \`draw_function_frame\`, V3 blackboard Computer Modern, offline eSpeak/Narrated V3-19 physical WAV methods and FFmpeg H264/AAC. Add generic **integer linear function** parameterized by slope/intercept, actual math-certified point slopes, narration utterance per graph state with measured WAV samples, 720p18fps native frames and exact per-beat SRT. No hard-coded MP4 per topic, no generated arbitrary code, no card fallback. This is a **bounded narrated math partial adapter**, not Research/Script/Pedagogy/Visual Director end-to-end execution. The deterministic educational prose is marked author template and math fact proof is arithmetic, not externally cited domain research. No dishonest claim of general English-script correctness.

**All other five locked topics explicitly ABSTAIN** because the existing renderer contracts do not certify the corresponding source domain and generic multi-domain script/action event handoff. For example a CS code drawing does not establish a lesson about function parameters; a polynomial graph cannot stand in for velocity/acceleration without a sourced physical model; cyclic process diagrams do not prove photosynthesis chemistry or WWI causal history.

## 3. Required actual runtime evidence

Run \`python scripts/verify_v3_27_six_domain_coverage.py --output-dir ...\` on the frozen sources:
- Generate \`v3_27_six_domain_coverage.json\`, \`v3_27_coverage_matrix.md\` and \`v3_27_issue_inventory.json\` for all 6 attempts. Unsupported cases receive **no fabricated video timestamp**.
- For the certified math partial adapter only, generate actual 1280×720 H264/AAC, SRT, JSON with input/source/scenegraph/spec/MP4 hashes, actual sampled utterance durations and audio RMS in EACH segment, original frame replay against post-encode decoded H264, and contact sheet from ALL authored beats (not selected prettiest moments).
- Negative tests: missing/changed locked topic, substitution, different corpus query SHA, unsupported domain incorrectly dispatched to math, source polynomial incorrect, overwrite, missing part of six denominator.
- No human rating, word-level alignment or commercial rights assertion. Original frozen V2/Hermes, V3-01 benchmark protocol and LearnFlowBench remain unchanged.
- Since Research/Script/Pedagogy/Visual Director cannot currently produce certified arbitrary-domain grounded instructions, **V3-27 full E2E PASS must be NO-GO (0/6)** even if one independently proven narrated specialized math video passes engineering QA. This is a substantive pipeline integration blocker, not an excuse to drop failures.

## 4. Capability-gap decision and next single checkpoint

STOP/NO-GO for multi-domain E2E. The next bounded CP should be **V3-28 — General Source-Grounded Lesson Compiler/Renderer Adapter**, first solving the gap from externally evidenced factual claims + script + pedagogy/typed semantic object to specialized renderer with real narration, using predefined domain schema and abstentions. Do **not** solve this by adding six hard-coded lesson videos, bypassing V3-04 select-unrenderable, deprecating V3-16 frozen 12-topic protocol or using CONCEPT_CARD fallback.

**Pending V3-27 exact-HEAD run:** Append engineering artifacts, direct visual contact-sheet review, factual constraints and CI once completed; keep honest NO-GO otherwise.


## 5. Actual six-topic execution, decoded video review and scoped decision (2026-10-09)

**Exact implementation SHA \`3675c14766c5003a773ec8f74d8f2612de2743cd\`**, dedicated [V3-27 workflow #37879738883](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37879738883) SUCCESS: 8 V3-27 direct source/mutation tests PASS, 97 prior V3 renderer/Pedagogy/Narrated tests PASS, 39 frozen V2 and 86 Hermes tests PASS, immutable V3-16 preregistration / LearnFlowBench / Core Freeze PASS. The exact source snapshot retains frozen \`benchmarks/learnflowbench/v3/preregistered_pilot_v1.json\` and unchanged main.

**Actual first pass defect (not concealed):** initial workflow #37879486511 rendered real MP4 and 6/6 ledger but failed one parameterized negative-source unit test because slope=-2, intercept=+2 exceeded V3-08's intentionally restricted graph y-axis; adapted the valid fixture without weakening renderer axis safety, and added explicit overflow-rejection mutation. First-pass decoded contact sheet showed inherited V3-08 green developer point ID crossing the caption divider, despite pixel replay PASS. Fixed by reserving bottom .812h with black background and moving subtitle divider to .83h; added pixel-level gutter regression. Re-rendered full MP4 and inspected all 9 decoded mid-beat frames: footer no longer contains \`Point point-N\` above the subtitle line.

**Independently downloaded final real artifact [#11593343670](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37879738883/artifacts/11593343670)**, CRC PASS, 7 members: \`v3_27_six_domain_coverage.json\`, \`v3_27_coverage_matrix.md\`, \`v3_27_issue_inventory.json\`, one native MP4/SRT/source QA JSON and all-nine-frames decoded contact sheet. Real \`ffprobe\`: H264 1280×720/18fps, **656 decoded video frames**, AAC mono, 9 measured local eSpeak utterances; source arithmetic coefficients \`f(x)=x+1\`, exact user topic \`lfb-020-math\`. Actual MP4 SHA-256 \`a4bfdc67bf429c9181a00e13da669d2bd777603039c853a5d1ad39895d593849\`; QA **max decoded frame source-relative RGB MAE=0.134**, 9 non-silent AAC PCM RMS by segment \`[0.092,0.0957,0.1001,0.1012,0.0947,0.0903,0.0918,0.0855,0.097]\`. These numbers verify source-bound media, not learner understanding or pleasant voice.

**Actual non-cherry-picked denominator:** 6/6 exact locked attempts; **one real but PARTIAL specialized math narrated MP4**, 5 explicit ABSTAIN with domain-specific reasons, **0 failed runtime attempts**, and **0/6 full Research→Script→Pedagogy→Visual Director→Renderer→Narration→MP4→QA E2E PASS** because the required middle owners did not run on arbitrary-source topics. No replacements, no silent universal CONCEPT_CARD, no paid API, no human study and no release.

**Decision: V3-27 multi-domain end-to-end acceptance NO-GO.** Its bounded source-selection/partial-media-and-gap audit can be technically verified, but the explicit all-domain user acceptance cannot pass. Next single capability checkpoint: **V3-28 General Source-Grounded Script/Pedagogy/Visual-to-Renderer Compiler**, first proving proper provenance/event-to-narration handoff on more than one independently sourced topic. Do not claim reliability, physics/chemistry/history factual QA or 3Blue1Brown-quality on this evidence. Documentation-only follow-up commit needs own exact-HEAD tests, and review status must distinguish that from implementation SHA.
