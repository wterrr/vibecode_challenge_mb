# V3-56 — Native Speech–Visual Grounding & Pedagogical Timing Audit

**Scope:** exact V3-56 on [Draft PR #90](https://github.com/wterrr/vibecode_challenge_mb/pull/90), based on original parent HEAD `b684ec498ac84dbf08fbd9a9bde3ddd0e8500ab3`. **Preregistered FIRST** at commit `fc3a403c5a4d79ea0ac5c5409bfdf6a5f2aa7575`, before new signal analysis. No model API, no merge main, no frozen V2/production prompt modifications. No original audio/video/images copied to GitHub.

## 0. Exact initial GitHub/reuse audit

- PR #90 was open/Draft, parent `chatgpt/v3-55-independent-pedagogical-quality`, actual HEAD `b684ec4` before the new prereg commit.
- Initial two exact-head CI: Push [#38335917417](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38335917417), PR [#38335919407](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38335919407) both **queued**, not passed.
- Reused `research/v3_56_attention_alignment_preregister.json` and `research/v3_56_attention_native_caption_alignment.json`: 12 third-party **2outube** caption cues paired to 60 native video frames. **No native speech-to-word proof exists in these receipts**. Reused `research/v3_56_attention_ch6_native_video_receipt.json`, audio PCM/native frame probes, 18 Read/source research records, V3-55 native H264 baseline, and `learnflow_v3/lesson_quality.py` which explicitly reports `measured_word_alignment=UNMEASURED` / `independent_transcript_as_heard=UNMEASURED`.
- The user-provided file SHA was independently rehashed locally and matches `439e154fffbb8696a37753d765c4f64bc06d25fbb17cb3d98bcc842045d85cb9`, **56,718,320 bytes**, 1,569.191429 s, 1280×720/30 fps, 47,076 H264 frame positions, AAC 44,100 Hz. No substitute video used.

## 1. Offline ASR/forced-alignment feasibility (research of actual implementations)

| Candidate | First-party docs / licence | Expected offline use | Current outcome |
|---|---|---|---|
| [OpenAI Whisper](https://github.com/openai/whisper) | MIT code **and published model weights** | English `tiny.en` or `base.en`, ffmpeg, PyTorch, 30s segment decoding. Segment times ≠ guaranteed word alignment | Python package absent and **weights absent** |
| [SYSTRAN faster-whisper](https://github.com/SYSTRAN/faster-whisper) | MIT wrapper, CTranslate2 inference | CPU `int8` ASR on original WAV with known checkpoint SHA | Package/checkpoint absent |
| [ggml-org whisper.cpp](https://github.com/ggml-org/whisper.cpp) | MIT implementation | Local C++ CPU decoder; requires GGML model bytes | Binary/model absent |
| [m-bain/WhisperX](https://github.com/m-bain/whisperX) | BSD-2-Clause wrapper; **phoneme model has separate model-card/licence** | ASR → phoneme forced alignment → manual segment verification | Alignment model/weights absent |

**Direct environment audit:** Python can import PyTorch and torchaudio, `librosa` and `soundfile`, and `ffmpeg` is installed. `faster_whisper`, `whisper`, `whisperx`, `vosk` and `transformers` are absent. Cache/system search found no usable Whisper/Wav2Vec/Vosk checkpoint. Direct HTTPS to `huggingface.co` and GitHub raw failed with DNS `NameResolutionError`; therefore no offline speech recognizer was run and **zero speech phrases were independently recognized**. We did not substitute remote ASR, user-uploaded captions, or a model API. Model/library licences do not confer rights to redistribute the user-provided 3B1B film or speech.

**Manual listen policy:** No independent human listening/transcription occurred in this tool environment. A sound file or RMS trace is **not** equivalent to having heard the words. All 12 native speech phrase/word timestamps remain `null`; confidence/error cannot be computed without native speech reference, and no made-up WER is reported.

## 2. Original MP4 evidence collected in this checkpoint

**Video:** OpenCV decoded native timestamps (seek by milliseconds) at 2-second intervals across 28-second windows centered on each of the 12 registered anchors. Each window contains 15 frames (180 samples total) with grayscale-downsampled 320×180 `sha256` of the first frame. Mean absolute luminance difference (0–255) and fraction of pixels whose change exceeded 25 were computed across successive 2-second pairs. A peak is the **largest sampled pixel change**, NOT exact first visible semantic action or a proven edited cut.

**Audio:** `ffmpeg -vn -ac 1 -ar 8000 -f s16le` decoded all **12,553,265 mono PCM samples** (1,569.158125 seconds), RMS computed for 0.5-second bins in caption-centered windows. RMS is nonzero through much of the recording, but this is **mixture audio** (speaker + music/SFX) and cannot identify uttered words, speaker boundaries, meaningful pauses or narration–visual causal lag.

Machine-readable evidence: [`research/v3_56_native_speech_visual_grounding.json`](../research/v3_56_native_speech_visual_grounding.json). Verify with `python scripts/verify_v3_56_native_speech_grounding.py`.

### 12 anchor measurements — directly native image/PCM, *caption remains external*

| Lesson concept | External caption cue (s) | Largest *sampled* native image change (s) | Mean absolute gray difference | Difference from **caption proxy** (s), NOT speech lag |
|---|---:|---:|---:|---:|
| Mole contextual ambiguity | 109 | 119–121 | 36.888 | +10 |
| Persistent example sentence | 269 | 269–271 | 32.542 | 0 |
| Query motivation | 357 | 374–376 | 11.981 | +17 |
| Query-to-Key transition | 458 | 466–468 | 36.904 | +8 |
| Attention score matrix | 514 | 526–528 | 15.218 | +12 |
| Softmax | 589 | 588–590 | 36.079 | −1 |
| Causal masking | 691 | 707–709 | 19.153 | +16 |
| Values | 815 | 815–817 | 33.329 | 0 |
| Value weighting | 862 | 894–896 | 10.652 | +32 |
| Multi-head | 1231 | 1235–1237 | 31.190 | +4 |
| Output matrix | 1349 | 1342–1344 | 36.735 | −7 |
| Back to context | 1413 | 1434–1436 | 19.718 | +21 |

**Critical caveat:** These last-column values have **no evidential status as voice-to-screen delay**. They subtract a caption proxy time from the largest 2-second frame-difference interval within an arbitrarily selected nearby probe window. They are intentionally retained as descriptive forensic cues to prioritize future original-speech listening; not even an automatically detected onset of a semantic object. For example, the Value-weighting +32s peak does not mean the narrator speaks 32s before animation; there may be multiple meaningful transformations and static holds in that period. A 2-second sampling interval cannot attest a precise cut or 0.1s timing.

### Negative/uncertainty controls on the audio signal

- A 0-RMS region can indicate muted audio, a lull in music or a low-level signal; non-zero RMS can be speech, ambience, effects or soundtrack. Neither yields a textual transcript.
- The first visual max-difference interval need not be the requested beat's explanatory event. A scene cut or unrelated layout change can dominate the metric.
- A phrase in a third-party timecoded caption may not appear in the original AAC, and its timestamp may lead/follow actual pronunciation. Until manual/acoustic ASR proof exists, `native_speech_onset_s`, `word_error_rate` and `native_utterance_to_visual_lead_lag_s` remain null.
- Positive findings from visual receipts are not made stronger by assigning the caption language to native audio without validation.

## 3. Pedagogical decision analysis, strict source classification

| Mechanism | Verified in native video/scene images | Read/caption-derived hypothesis (not confirmed from native speech) | Design choice if later reproduced independently |
|---|---|---|---|
| Context-dependent token | Repeated `mole` with different pictures/word contexts and vectors | Initial narration raises a semantic ambiguity before resolving it | Pedagogy Agent should define `learning_difficulty` and explicit later `explanatory_closure` |
| Single running example | Words from `a fluffy blue creature...` reappear as E/Q/K/V referents | Voice may introduce example *before* exact frame appears | Maintain canonical `semantic_referent`; never enforce narration word == graphic reveal frame |
| Query → Key | Query projection and candidate token keys visually distinguished | Adjective metaphor is explicitly an example, not an empirically inspected trained head | `explanation_truth_mode=ILLUSTRATION` vs `HOST_VERIFIED_FACT` |
| One pair → full matrix | Pairwise Q/K grid and focus shift physically visible | One worked interaction may ease generalization | Verify cell calculation in ledger; then expand to N×N with stable referent mapping |
| Causal masking | Prefix/triangular attention pattern illustrated | Narration rationale for mask is a **caption-grounded** hypothesis | Separate `requires_prior_prefix_example` from host mask numerical verifier |
| Scores vs Value transport | Colored Q/K scoring and Value arrows/weighted update | Speaker distinguishes *selection* from *what is carried* | Typed `SCORE_SELECTION` and `CONTENT_TRANSPORT` operations with separate witnesses |
| Dense matrix hold | Some matrix frames nearly static across 2–10 seconds | Static display may aid cognitive processing; no listener pause proved | `OBSERVE_HOLD` with legibility + narration truth, no mandatory animation |
| One head → many | Distinctive stacked attention heads physically introduced | Architecture recap likely returns from example to whole model | `one_to_many` with head-specific object/claim references |

These are **instructional-design hypotheses grounded in visual observations**, not measured student learning. They may be falsified by independent learner evaluations.

## 4. Direct V3-55 gap audit (reuse-first, unequal runtimes explicitly noted)

Confirmed V3-55 native Attention reversed-query H264/AAC artifact `v355_attention_reversed_query/composed_attention_native.mp4` measured **63.8s at 15fps, 1280×720**. Compared against the 3B1B film's **1,569.19s / 30fps**; **NOT A MATCHED EXPERIMENT**.

| Layer | Existing LearnFlow source/reused mechanism | What the native 3B1B observation exposes | Proposed contract/compiler/critic delta | Gate |
|---|---|---|---|---|
| Pedagogy | `pedagogy_agent/hermes.py` fact-approved objectives/analogies | Need an explicit contextual confusion and mental-model change rather than a generic objective | V3-only `learning_difficulty`, `target_mental_model`, counterexample/probe, source-grounded | Existing role extended ONLY after validation |
| Script | `script_agent/hermes.py` approved claim IDs and narration segment functions | The same narrative problem returns across visually different math representations | `beat_id`, purpose, canonical visual referent, separate spoken cue source, planned hold | No native speech evidence means alignment NO-GO |
| Visual Director | Frozen V2's four layouts and `CONCEPT_CARD` fallback; V3 finite Creative SceneGraph | Real visual transitions include word→vector→matrix and one-cell→grid | V3 research sidecar referent mapping + representation-transform trace, not changing V2 Core | Unsupported operations must fail closed |
| Creative/Motion Director | `learnflow_v3/creative_motion_director.py` `intro/compare/normalize/inspect/transport/compose`; Attention A1–A4 host facts | Select versus transport, mask and purposeful static inspection all have different semantic witnesses | Map finite ops to `SCORE_SELECTION`, `CONTENT_TRANSPORT`, `QUESTION_HOLD`, `STATIC_COMPARISON`; ledger proofs | NO free model-authored Python; compiler capabilities limited |
| Native compiler | `creative_scene_graph.py` reveal/emphasize/connect/hide/move/replace and Manim finite primitives | No proof of generic deforming semantic representation with object continuity across modality | Support bounded `representation_change`, `expand_example`, explicit unsupported states only after separate tests | Research design only |
| Critic/QA | `lesson_quality.py` video/audio quality, `measured_word_alignment=UNMEASURED`; existing independent packet design | Audio RMS and video H264 truth ≠ native narrated fact | Validate `NATIVE_WORDS_REVIEWED` or distinguish `EXTERNAL_CAPTION_PROXY`, real semantic observable, blind review | Speech alignment **NO-GO** now |

**No conclusion that 3B1B scores better than LearnFlow on a fair quality metric**; the measured difference in length and frame rate would confound any such inference.

## 5. Exact gates and scientific decision

| Acceptance area | Result |
|---|---|
| Original input MP4 / SHA / codec / 47,076 frames | PASS |
| All 12 visual windows measured on direct native frames | PASS for frame-based evidence |
| All 26:09 AAC decoded; 0.5-second energy windows measured | PASS for *signal*, not language |
| ASR offline provenance/license feasibility study | Completed; execution **BLOCKED** (packages/checkpoints missing; no network) |
| Independent recognized native phrases | **0/12**, below preregistered minimum 8/12 |
| Sentence / phrase / word-level native speech timestamps | **NO-GO / NOT VERIFIED** |
| Speech cue to animation onset delay in seconds | **UNMEASURED**; only external-caption-to-pixel-proxy intervals provided |
| Pedagogical mechanism grounded in visible movie | **BOUNDED RESEARCH GO**, no learner outcome |
| V3 Pedagogical Explanation Contract proposal | **RESEARCH-ONLY GO**, runtime adapter/compiler NOT VALIDATED |
| V3-55 quality superiority comparison | **NOT A CONTROLLED EXPERIMENT** |
| Full 15-video audiovisual study | **NO-GO**, one full original video frame-sampled; native word alignment unverified |
| Production | **BLOCKED**; no main merge/model API |

**Why true native speech alignment cannot be claimed:** No executable ASR+valid pretrained checkpoint could be obtained in this environment, no original words were independently listened through, and audio waveform alone cannot resolve words. These are *material* restrictions, not a reason to falsify timings or promote captions to native evidence.

**Single next permissible activity, inside V3-56 scope rather than jumping to V3-57:** Provide a local offline ASR checkpoint with SHA/model licence and trusted install path (or a permitted media interface with actual spoken-word listening), then run *exactly the same 12 frozen anchor windows* and independently compare with caption hypotheses. Only after >=8 native phrases are verified with error-bound timestamps may the native speech gate change. Do not run a service API or use the public transcript as phoneme ground truth.

Machine tests `scripts/verify_v3_56_native_speech_grounding.py`, `tests/v3/test_v3_56_native_speech_grounding.py` explicitly reject forged transcript, false WER, fake visual PTS, caption/speech timestamp conflation, changed licence status and production GO.


### Reproducible local-ASR path (provided but NOT run)

A separate [offline-only optional runner](../scripts/run_v3_56_local_asr_candidates.py) now exists for a **later** explicitly supplied licensed local CTranslate2 Whisper checkpoint. It requires the exact original media SHA, the local weights' SHA-256, origin/license receipt and allowed-use acknowledgement. It accepts only a model DIRECTORY, passes `local_files_only=True`, and never requests hosted inference or automatically downloads model files. It produces **ASR CANDIDATES ONLY**, not native certified speech. Original transcript candidates must stay outside the repository unless a later privacy/rights review explicitly authorizes them. New negative tests `tests/v3/test_v3_56_local_asr_candidates.py` verify failure on wrong video SHA, absent model files, incorrect weight digest and unapproved rights, **without running any ASR**.

This implementation closes a *reproducibility tooling* gap but **does not resolve the missing model checkpoint, manual listening or native word-alignment NO-GO**. Retain native audio phrase gate at 0/12.
