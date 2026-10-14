# V3-62 — Creative Pedagogical Storytelling Upgrade: bounded held-out native study

**Scope:** research-only prototype, no genuine model-authored lesson generation or 3Blue1Brown equivalence claim. **Base:** [V3-61 Draft PR #97](https://github.com/wterrr/vibecode_challenge_mb/pull/97), frozen parent HEAD `a9473bef73f0dbf63a921bdbdb9bcacf2f1321f2`. **First child prereg commit:** `0cd28c18c862c28c00fe2a30e595a179326006e4` before implementation, `benchmarks/learnflowbench/v3/v3_62_creative_storytelling_preregister.json`.

## Research reuse-first decisions

- **V3-56 3B1B evidence:** 18 Read pages and first-party source scenes, 113 Read-sequence beats; one original Attention Ch6 native source film physically sampled, 0 of 12 anchors independently verified with native word-aligned speech. Reuse the hypotheses about cognitive conflict, stable visual referents, mechanism-before-result, purposeful narration timing. Do not copy or republish 3B1B images/voice/scenes; do not invent 15 complete video audits. Evidence: `reports/v3_56_pedagogical_prompt_architecture.md`.
- **V3-47/51/53:** Reuse design principles from typed semantic transformation grammar, SceneGraph finite compiler, director choices and source-fact binding. Their implementations remain in place; V3-62 is an opt-in **sidecar held-out renderer**, not a rewrite or live agent prompt change.
- **V3-57/58/59:** The three optimized topics (Attention, Fraction, Process) and known reveal-before-cause failures are excluded from V3-62 selection. Technical native frame and AAC comparisons reuse the V3-57/59 FFmpeg/Pillow evidence pattern, not human efficacy.
- **V3-60/61:** Existing masked review process still has **zero genuine reviewer submissions**. New animations do not inherit an independent quality score.

## Registered evaluation subjects and ground truth

| Held-out topic | Exact host ground truth | Invariant / caution |
| --- | --- | --- |
| probability_complement_3_of_8 | 3 favored of 8 equally likely outcomes; 5 in complement | 8 persistent boxes, `3/8+5/8=1`, total never changes |
| constant_speed_distance | 3 m/s for 4 s yields exactly 12 m | Marker ID persists, position increases 0→3→6→9→12 monotonically, final result only after travel |
| water_reaction_balance | 2 H2 + O2 → 2 H2O | 4 H and 2 O atom IDs conserved, schematic **inventory**, never a reaction trajectory or kinetics model |

Three distinct visual grammars and layouts, rather than three bespoke attention storyboards. Two registered visual emphasis strategies `focus_first` and `witness_first` are finite host-provided choices, NOT autonomous creative authoring.

## What was implemented

- `learnflow_v3/creative_pedagogical_director.py` implements a typed frozen 5-act progression: QUESTION → SETUP → TRANSFORM → WITNESS → CLOSE, host-computed ledger hashes, claim and referent binding, narration/per-act highlights and exact validation against a canonical source. Prospective narrowly scoped `proposed_visual_choice` accepts only case/style/fact hash; it never accepts model Python or invented equations.
- `learnflow_v3/creative_pedagogical_native.py` builds persistent box outcomes, a time–distance track, and stable atom circles with interpolation, evidence-before-result timing, readable narration segments, and identical audio across a **causal timeline** and matched **end-state-hold** control. The control deliberately exposes the answer earlier and removes gradual transformation; it is not a pure isolated animation counterfactual.
- `scripts/run_v3_62_creative_storytelling.py` audits prereg ledger parity, renders six native H264/AAC videos at 1280×720, 15 FPS, fully decodes frames with FFmpeg, freezes SHA-256/video counts/audio packet hashes, tests decoded frame difference at pre-result and witness intervals, and saves visual reference stills and receipts.
- `tests/v3/test_v3_62_creative_storytelling.py` contains 27 passed offline checks as seen in GitHub Actions [run #38498843970](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38498843970), including hostile corruption of claim, narration, referent, model origin, evidence hash, visual style, early reveal, false conservation and forbidden publishing/word alignment.
- `.github/workflows/v3-62-creative-storytelling.yml` separates fast proof tests from a native six-MP4 build; no model API, no arbitrary model Python, no main merge.

## Experimental estimand and limits

This checkpoint can test **host-renderer feasibility and geometric/temporal integrity** on three new domains, not improvement in lesson quality. Control and treatment have the same pre-recorded espeak narration, total frames and AAC packet hash. However, control is answer-first and static, so any difference confounds revelation timing and motion. Pixel differentiation is a technical witness, not proof that a viewer learned. Voice is offline TTS, not word-aligned human-style directing. English narration and visuals are templates, not an agent-authored lesson in response to arbitrary user queries. The limited finite grammar should be reviewed qualitatively instead of automatically equated to 3Blue1Brown.

**Success only if** exact-head strict tests PASS and six physical MP4s pass ffprobe, full FFmpeg decode, per-pair equal audio/frame count, and source-vs-encoded semantic time receipts. Otherwise FAIL CLOSED.

## Evidence / verdict

- **Strict offline design and negative test gate:** 27 PASS at #38498843970.
- **Actual held-out six MP4 native gate:** pending completion of native job #115640875417 at time of this entry; do not claim success before artifact and decoded receipts.
- **Real model-authored scene planning:** NOT TESTED.
- **Native word-level narration alignment:** UNMEASURED.
- **Independent human visual/pedagogical quality:** UNRATED.
- **Human learning gain:** NOT MEASURED.
- **Production:** BLOCKED.

**Next action after native PASS:** actually inspect decoded stills and videos for text legibility, spatial focus, meaningful invariants, pacing and false intuitions; compare to heldout control without claiming causality. Obtain a separate independently rated panel, or run a strictly limited genuine model-authored proposal test only if user explicitly authorizes provider costs. No source 3B1B media redistributed.
