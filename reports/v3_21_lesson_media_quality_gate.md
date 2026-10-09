# V3-21 — Real Lesson Visual, Audio & Pedagogy Quality Evidence Gate

**Scope:** draft PR #55 stacked on PR #54; review-only offline developer material. No paid API, new model, human participants, production publishing or change to frozen V2 Core/main.

## Original actual media: observations and timestamps

Source: final V3-20 Action #37866581541, artifact #11588587891. Same input for both MP4s: sorted array [0,2,4,7,11,15,15,21,30], target 15, certified leftmost match at index 5. Prior V3-19: 538 decoded H264 frames / 7 narrated scenes. Corrected V3-20: 541 decoded H264 frames / 10 independently spoken semantic events. Both video files are 640x360 at 12fps with AAC and burned SRT.

V3-20 fixes a real timing bug rather than demonstrating independent teaching gain: first OBSERVE starts 14.333s and first APPLY starts 17.333s. First next OBSERVE starts 20.000s; decoded ROI (x0..640,y80..235) MAE at final frame 239→240 was 0.056929, versus the historical pre-fix defect MAE 4.1208. This is selected frame continuity, not a claim of word-level or pedagogical alignment.

| Issue | Timestamp | Observation grounded in media/code | Decision |
| --- | --- | --- | --- |
| P0 audience legibility | 0.000–45.083s | Existing MP4 native resolution 640x360, 12fps. Overlay in narrated_lesson uses CMU 14/15px source fonts; separate tiny array numbers, index hints and subtitles. No viewer-distance or independent text legibility test. | LEARNER_READY BLOCKED; a 1280x720 or larger sample and readability review is required separately. |
| P1 utterance ≠ forced words | OBSERVE 14.333; APPLY 17.333; next OBSERVE 20.000 | WAV-based utterance boundaries have physical sample counts; there are no independently measured individual word onsets or phoneme alignments. | Word-level and transcript-as-heard UNMEASURED. |
| P1 possible cognitive load | 14.333–33.500s | Three compare/apply phases, animated bounds and spoken events; processing time and student comprehension have not been evaluated. | Independent blinded study needed; no measured comprehension gain. |
| P1 voice quality | Entire clip | eSpeak source and AAC PCM are measurable, but intelligibility/pronunciation/naturalness cannot be judged from low clipping/RMS alone. | Human/ASR voice quality UNMEASURED. |
| P0 release rights | Entire clip | GPL-family eSpeak program/voice downstream commercial output rights have not been independently cleared. | RELEASE BLOCKED. |
| P0 scientific external validity | Entire clip | One Binary Search case; no 12-topic matched study or blinded audience ratings. | V3-16 empirical and 3Blue1Brown visual-parity claims UNMEASURED. |

## Implementation and source-aware evidence gate

Reuse V3-05 trace, V3-06 black CMU renderer, V3-19/20 source video pipeline, original eSpeak WAV, FFmpeg and frozen V2/Hermes contracts. New learnflow_v3/lesson_quality.py independently reopens actual input MP4/receipt/SRT, validates bytes against known SHA, source trace and 10 event identities, probes actual H264+AAC streams, frame duration and native resolution, decodes entire AAC to 16k PCM, records per-utterance energy and words/minute from known script + physically measured utterance durations. These speech pace numbers are **not** independently verified transcript-as-heard.

For selected actual compressed video frames, extract native pixel data via FFmpeg. Compare frame boundaries at each APPLY→next OBSERVE/RESULT in the same ROI as the V3-20 reproducible visual rewind; reject discontinuities exceeding 2.0 mean RGB delta. Generate a contact sheet using frames from actual MP4, not fabricated renderer stills. Negative tests include SRT/hash/receipt/proof tampering, forged claims, malformed cue timing, audio silence and invalid sample sequences. Hard evidence corruption fails closed rather than yielding a scoring estimate.

**Important separation:** Integrity gate PASS means verified media and bounded source consistency; learner-ready and production gates remain BLOCKED. Hardcoded 1280x720 is a prerequisite to inspect, **not** proof of readability at that resolution. A black background and installed CMU source font do not independently prove aesthetics or readability. A 12fps preview can be accepted for CPU smoke, but is not an audience-quality target.

## Future human rubric: design only, NOT conducted

Pre-register blinded side-by-side V2/V3 clips across frozen V3-16 topics and failure/abstention cases. Require independent raters and documented device/viewing distance; measure source correctness (hard gate), variable/pointer causal clarity, mobile/TV number legibility, speech comprehension and pronunciation, subtitle accessibility, amount of narration-induced waiting, cognitive load, smoothness, aesthetic preference, and a recall/application question scored against hidden ground truth. Use anchored 1–5 labels with inter-rater disagreement and failure-inclusive denominator. Do not manufacture ratings or infer learning gain from pixel entropy; do not revise a preregistered metric after seeing outcomes. Human study, providers and commercial voice clearance require separate user authorization.

## Acceptance decision

This checkpoint must publish a JSON quality evidence ledger and contact sheet from a real same-source MP4 pair, with positive/negative CI and frozen regression checks on **exact PR head**. Engineering PASS is bounded. Student quality and release intentionally remain NO-GO. One responsible separately approved follow-up is a 1280x720/1080p typography and pacing retrofit (V3-22), followed by the independent preregistered human-quality evaluation, not an automatic rollout.

Source files: scripts/verify_v3_lesson_quality.py; tests/v3/test_lesson_quality.py; .github/workflows/v3-lesson-media-quality.yml; PLAN_V3.md; LEARNFLOW_V3_RESEARCH_NOTES.md.
