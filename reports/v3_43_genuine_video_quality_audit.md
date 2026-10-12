# V3-43 — Genuine Video Visual & Pedagogical Quality Audit

**Checkpoint:** V3-43. **Subject:** ONE frozen genuine GPT-6 Luna model-authored video from V3-42. **Scope:** Offline audit and requirements, **not an improved render, not a second GPT-6 Luna trial**. Stack on V3-42 Draft PR #76 HEAD 72cb594; preregistration committed at a6d36a5 BEFORE audit implementation.

## Primary evidence and immutable source

- Authentic push [Actions #38189257163](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38189257163), one model POST run_attempt=1; [artifact #11721146374](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38189257163/artifacts/11721146374) named v3-42-genuine-model-video-or-failclosed-receipt.
- Raw model response SHA256: 724206bd43281221d7667f0943db8940059aa1584d4b375b7fdd77eaf74af320.
- Model plan SHA256: 031af8c8aae1681b1919eb5e95dbfef50657fef2b17a573a4e7c2a8ca6da5b97. Host-generated Manim source SHA256: 116179fb12337816a05820ea5dc98ce3da20f01b68f1afb158c9700f2d1baa22.
- Real MP4 SHA256: f92c47bbacf25a6c9dead39fcca05cc761276927537ed41d9e513f9f868e047a. H.264/AAC, 1280×720, 590 frames at 15 fps, approximately 39.333 s. Four WAV segments and external SRT subtitles. No claim of actual burned-in subtitles.
- Original visual evidence inspected: actual MP4 frames near 0.5, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 27, 30, 33, 36 and 39 seconds, plus model scene JSON and host Manim code. **This is one observed video, not a dataset estimate.**

## Preregistered objective/semantic issue inventory

| ID | Time (s) | Priority | Observed evidence | Pedagogical risk / proposed remediation |
| --- | --- | --- | --- | --- |
| V343_FIRST_WHOLE_VISUAL_LAG | 0.00–5.52 | P1 | Beat 1 narration starts 0.0. Title FadeIn ends 1.84, shaded half ends 3.68 and remaining half ends 5.52. Label finishes at 7.36. | Speech describes a two-piece whole before both parts are visible. Reveal both halves together, then animate highlighting them. |
| V343_FOUR_PIECE_REVEAL_LAG | 9.20–17.147 | P1 | Beat 2 narration starts at 9.20; four quarter rectangles are added one by one: final cell only finishes at approx 17.147, label at 19.133. | Words 'four equal pieces' arrive before all cells. First transform whole 2-piece partition into 4 equal pieces or show complete grid rapidly, then progressively shade 2 cells. |
| V343_ARITHMETIC_EXPLANATION_NOT_SHOWN | 19.133–29.533 | P1 | Beat 3 says multiplying numerator AND denominator by 2, while visible scene text is title, 1/2, 2/4 and '='. Manim shows + moves '=' and briefly Indicates fraction labels, but no times-two operation. | Core rule is explained only verbally, not demonstrated visually. Explicitly animate (1×2)/(2×2)=2/4 or map each half into two equal subparts. |
| V343_DIFFERENT_SIZED_WHOLES | 17.147–39.333 | P1 | Left whole: two 1.3×1.8 rectangles = 4.68 units². Right whole: four 1.1×1.0 rectangles = 4.40 units²; relative area mismatch 6.36% compared with the right. Both shaded fractions **do** correctly equal 0.5. | Fractions are mathematically correct regardless of different picture scales; however, stating 'same amount' can imply a fixed reference whole. Render equal-sized whole outlines and subdivisions to prevent ambiguity. |

**Additional manual observations, not automatically proven comprehension failures:** Large black margins/limited use of screen (local 0.5 s sampling gave approx 9.33% median pixels with luminance greater than 30), the active objects occupy a relatively small central strip; on-screen text is small when viewed at reduced size. 66% of adjacent 0.5 s sampled frame pairs changed little (mean-absolute grayscale delta <0.001 of full range). Motion is mainly serial FadeIn/Indicate, with a single explicit move of the equals sign. These descriptive statistics are **not standardized thresholds for good design**; no 'quality score of 3/10' should be fabricated from them.

## Four beats and audio evidence

| Beat | Timeline | Visual representation | Caption/narration QA |
| --- | --- | --- | --- |
| 1 | 0.00–9.20 s | 2 equal-looking rectangles, one shaded, then 1/2 | Physical WAV exists and signal present; captions repeat model's beat narration, but object/claim timing lags. |
| 2 | 9.20–19.133 s | Four rectangles added serially, two shaded, then 2/4 | Caption text matches authored narration and starts on beat; not word-aligned to complete partition. |
| 3 | 19.133–29.533 s | Reveal and reposition '=', highlight 1/2 and 2/4 | Central times-two relationship is NOT shown even though spoken. |
| 4 | 29.533–39.333 s | Replay emphasis of shaded pieces | Recap is mathematically coherent but largely repetitive, little new explanatory visual. |

**Evidence category distinction:** Actual presence of H.264/AAC, non-silent beat WAV, caption text and timeline are verifiable. This audit does **not** independently transcribe the audio, certify text-to-voice alignment at word level, judge synthetic voice prosody, perform blinded student scoring, or claim learning gain. A subtitle file alone does not imply burned-in captions.

## Criteria and theoretical rationale

The exact cutoffs (5% area mismatch warning, >3 seconds between the narrated visual event's beat start and the complete corresponding partition, raw pixel-change thresholds) were preregistered in V3-43 and are LOCAL risk indicators, not externally validated pass/fail norms.

The reason to inspect temporal contiguity comes from Mayer's [Temporal Contiguity Principle](https://www.cambridge.org/core/books/abs/multimedia-learning/temporal-contiguity-principle/2236655CB3759154DF148595FF2EC1FC): relevant speech and visuals are generally better taught in close temporal relation. [Fiorella & Mayer's multimedia-learning discussion](https://www.cambridge.org/core/books/abs/cambridge-handbook-of-multimedia-learning/principles-for-reducing-extraneous-processing-in-multimedia-learning/F29A19FCD34C542806F736E0661C05F5) motivates signaling and eliminating distraction; neither reference provides a measured outcome for THIS video. Different scaling of fraction visuals can be mathematically legitimate if the reference unit changes, hence the area issue is a communication risk, not a fabricated mathematical falsehood.

## Implementation and independent reproducibility

- Module: learnflow_v3/genuine_video_quality_audit.py. Verify fixed source SHA hashes and true model origin from prereg + receipts, rerun ffprobe H.264/AAC, inspect actual WAV segments and external SRT, parse *host-generated* animation timings, decode original MP4 frames via FFmpeg at 2fps 320×180, report occupancy/activity summary and create contact filmstrip from **decoded frames**.
- Tests: tests/v3/test_v3_43_genuine_video_quality_audit.py checks real video plus negative modifications (tampered MP4, model scene, Manim, SRT, provider receipt, forged synthetic origin, missing audio, registration drift). Never silently repair.
- GitHub Actions: .github/workflows/v3-43-genuine-video-quality-audit.yml downloads EXACT V3-42 real artifact using GitHub read-only token, reruns V3-36 genuine provenance gate, emits v3_43_audit.json, v3_43_real_video_timeline.jpg and legacy regression results. Zero OpenRouter key or inference jobs. Frozen V3-42 success and budget remain untouched.
- Offline command from repository root (with local artifact previously downloaded):
  python -m learnflow_v3.genuine_video_quality_audit --artifact-dir /path/to/v3_42_real_artifact --output-dir /tmp/v3_43_quality_evidence

## Outcome and next engineering decision

**V3-42 technical video: PASS. V3-43 visual-pedagogical readiness: NEEDS REDESIGN / NOT CERTIFIED. Production remains BLOCKED.** Do not promote "valid scene" to "good lesson." Next work (separate checkpoint) should improve **semantic events → synchronized visual transformations → more legible layout → richer but relevant animation** by changing host constraints, storyboard contracts and rendering, then assess again against the SAME rubric. Keep the original V3-42 video and metrics immutable. A comparative real-model study needs a new preregistration and authorization; it is NOT part of V3-43.
