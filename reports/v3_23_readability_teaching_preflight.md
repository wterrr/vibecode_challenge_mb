# V3-23 — Actual Video Readability & Lesson Teaching Review Preflight

**Authorized scope:** user requested next checkpoint after V3-22. Stacked on PR #56; no merge to `main`, no paid API, participants, real scoring study or commercial release. This is **not** a blinded/rater-validated study. Neither technical video pixels nor model-generated preferences can establish user comprehension.

## Research, provenance and comparison design

Reuse source-bound native 720p renderer from V3-22, certified utterance-event trace V3-20 and V3-21 real video audit, V3-16 registered rubric and 12-topic human evaluation design. Do not alter the frozen V3-16 preregistration or invent a pilot; a single Binary Search example with different output resolutions can never show a distributional V2/V3 learner benefit or conceal which arm is HD. The reviewer packet explicitly describes the 360p and HD variants as **nonblinded** and asks for human feedback only after separately authorized recruitment and consent.

Project-native media: H264/AAC source video SHA `b68a9d8dca9c40c97cb0946e2efbb6da905aa7619fdfd6ea1b1121867714f100` (640×360, 12fps, 541 frames); HD H264/AAC SHA `7942d193f0b14c9ced4999909fbaa4efd45e72d40c01a3994dbba8bfc8cbe17e` (1280×720, 24fps, 1082 frames). Original AAC packets identical by ADTS digest, not independently assessed pronunciation. Source utterance event start times and sample-aligned SRT were measured in V3-20. No forced word/phoneme recognition.

## Timestamped issue inventory with supporting source/decoded pixels

| ID / severity | Time | Observation | Gate |
| --- | --- | --- | --- |
| TYPE_MICROCOPY_AND_ARRAY_INDEX / P1 review | 17.333s | Core Computer Modern small label derives from `round(17 × 720 / 540) = 23 px`, while V3-22 main action/caption overlays are 32 px; source screenshot includes small index row below numeric cells and microcopy under title. Project diagnostic threshold 28 px applies **only** to directing a rater's attention; not a universal accessibility standard. | NEEDS real-device distance review |
| BEGINNER_FACING_TECHNICAL_JARGON / P2 | 0.000s | Top secondary line reads `Verified leftmost-index trace / immutable item IDs`, valid for audit but not obvious beginner-oriented scaffolding. | Independent content/visual hierarchy review |
| DUPLICATE_LEFTMOST_REASONING / P1 | 22.333s → 33.500s | Certified trace first records duplicate 15 at index 6, then earlier duplicate at index 5. State changes and segment starts are source-correct; whether this explanation teaches the *why* requires a novel transfer question. | Human transfer assessment NOT RUN |
| VOICE_AND_WORD_TIMINGS / P1 | 14.333s onwards | Timed SRT, AAC and WAV source prove utterance boundaries but not individual word onsets, pronunciation or listener comprehension. | Independent listening needed |
| VISUAL_STORYTELLING_DENSITY / P2 | 17.333s | HD decoded frame shows correct array, pointer labels, action and caption but substantial unused black regions. 720p scale alone does not guarantee engaging teaching visuals. | Manual visual director / didactics review |

Actual decoded pixel check (pre-registered sampling) at frame indices 344, 416, 480, 642, 804, 920: visible light caption-band pixel ratios respectively **0.01123, 0.01071, 0.00983, 0.00987, 0.01321, 0.04670**. These are descriptive non-OCR measurements for y=604..705, x=64..1215; all sampled captions are nonempty. This does **not** prove text is easily readable, accessible or semantically correct.

## Implementation and fail-closed acceptance

- `learnflow_v3/review_preflight.py` reuses the certified V3-22 `verify_hd` source/video/AAC proof plus 10 V3-20 SRT events. Independently reads H264 frame pixels, records CMU font bounding geometry, original WAV-duration/script word rates and timestamped issue inventory.
- `scripts/verify_v3_review_preflight.py` writes an evidence JSON, an **unscored** reviewer JSON packet, a header-only blank CSV and reviewer instructions. Reviewer tasks cover factual trace correctness, change causality, leftmost-duplicate understanding, hierarchy, index/label legibility, subtitles, audio pacing/intelligibility, cognitive load and new-question transfer.
- Keep real trial permission `NOT_RUN_UNAUTHORIZED`, participants=0, ratings=0, student-ready/release BLOCKED. Reject source video mutation, filled-in pretend reviewer scores, fabricated randomized blindness, altered rubric, fake release status, report changes, missing media and output overwrites.
- In CI generate actual V3-20 and native V3-22 MP4s, audit them and retain both with the blank packet. Run V3-22/V3-20 positive and adversarial tests, Frozen V2/Hermes, V3-01 protocol, LearnFlowBench and Core Freeze. No source audio changes or new production route.

## Rubric and independent testing limitations

A human review **may be separately authorized later**, not completed here. Require participants to record physical screen size, viewing distance, hearing environment, 1–5 anchored response per dimension, frame timestamp and reason; leave blank when unassessed. A valid true blinded/matched claim would additionally require a fixed independently commissioned V3-16 12-topic V2/V3 panel, reviewer independence, baseline pairing, consent, seed/mapping protection and paired statistics. This one video pair is strictly a qualitative follow-up review packet, NOT V3-16.

Future question (unseen by baseline authoring): for sorted [1,3,3,3,8], where is the **leftmost** index of 3, and why check earlier matches after equality? Hold the reference answer outside reviewer-facing materials.

**Acceptance state:** engineering review preflight must pass exact PR-head Actions with actual video, generated blank packet and negative tests; no human-learning PASS, publication remains BLOCKED. Unresolved small-label/jargon/storytelling issues should inform separately scoped visual edits, not be silently normalized away.
