# V3-71 — Native masked reviewer kit: physical verification and research boundary

**2026-10-14 · Research only · Parent V3-70 PR #106 frozen HEAD `4f12f5a5b093b2d44719dc1ddb02733a70444267`.** First child prereg `f48bcc75a99b937746b6c9a1d99291c2b54c74ec` preceded the systematic full-decode and 1-fps metric pass. **Disclosure:** investigator already had downloaded the ZIP, verified per-file hashes/codecs and previewed 4 sampled stills per video *before* preregistration. Thus the visual notes below are explicitly EXPLORATORY, never confirmatory human evidence.

## Reused frozen source

Original immutable GitHub Actions artifact **#11863189967**, `v361-offline-assigned-masked-reviewer-ui-UNRATED`, from [V3-61 run #38496967796](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38496967796). ZIP contains exactly **16 files:** nine original masked MP4s, three original reviewer HTML forms, JS/CSS, start instructions, masked manifest. No original media, score rubric, ordinal contrast, reviewer form order, treatment key, V2 Core, production prompts or V3-70 files are modified. Original artifact previously advertised expiry 2026-10-21 UTC. The V3-60 prereg and existing V3-61 actual UI checks are source of truth.

## Physical decoded evidence (local, real source bytes)

- **9/9 MP4 SHA-256 exactly match the ORIGINAL frozen V3-60/61 masked manifest**.
- **9/9 complete FFmpeg video decodes PASS** (not just MP4 container inspection); native H.264/AAC, 1280×720, 15 fps.
- Native groups have same audio-elementary packet SHA and frame counts within each topic: Fraction **340** each, Process **344** each, Attention **355** each.
- Durations per video by topic: Fraction **22.70s**, Process **22.93s**, Attention **23.72s**; aggregate sum **208.05s** over nine movies. Original 3 HTMLs remain condition-masked; no admin mapping or treatment names exposed in user-facing UI.

### Descriptive sampled teaching-region pixel change (NOT explanatory quality)

Exploratory audit at 1 frame/sec, scaled to 320×180 RGB; teaching region crop x=10:310, y=25:137 excludes much of footer/subtitles. Mean absolute RGB change divided by 255 between consecutive samples:

| Masked case | A | B | C |
| --- | ---: | ---: | ---: |
| Fraction | 0.000808 | 0.000948 | 0.000807 |
| Process | 0.004626 | 0.005524 | 0.003555 |
| Attention | 0.002936 | 0.002822 | 0.002833 |

These are pixel-difference proxies on masked conditions, **not human scores**, not comparable across unrelated layouts, and not proof that change is pedagogically causal. All masks/visual regions were selected as described in prereg. The score protocol remains untouched.

## Visual risk inventory from actual four-sample contact sheets (exploratory)

- **Fraction 7.7s:** masked A already displays `4/6` and division markers, while B/C show `2/3`. At **13.2s** the three clips show `4/6`. This is an observable timing difference and means an apparent preference may combine motion with answer timing.
- **Process 13.3s:** all three views display the final START→ACTION→CHECK state and UNKNOWN outcome. The sampled stills alone cannot certify the temporal history of the three interventions; review full MP4s rather than relying on stills.
- **Attention 8.1s:** masked C displays weights `w(A)=0.330`, `w(B)=0.670` with a softmax-stage caption; A/B sampled frames show score-selection graphics at this time. Again, this is not purely a movement-only manipulation.
- **Across all 3 topics:** supporting sentence labels/section navigation render relatively small in 480-pixel-downscaled review contact sheets and large dark negative space is visible. Whether this impairs comprehension/readability on full-screen 1280×720 **requires external humans**. These notes are not an independent blinded reviewer outcome.

## New repeatable fail-closed preflight

`scripts/run_v3_71_masked_native_preflight.py` reuses unchanged V3-60 `verify_packet`, V3-61 `preregistered` and the 3 frozen `template_rows` orders to gate: exact 16-file ZIP inventory, bounded/untraversable members, nine SHA-256 + full H264/AAC decode/parity, real HTML form IDs and order, local CSP and no network/admin mapping. It emits a **sanitized receipt only**; no private scores, mock human identities or unblinding. `tests/v3/test_v3_71_masked_native_preflight.py` performs archive-tamper and negative controls using explicit synthetic mutations of the real masked ZIP. Dedicated workflow uses ONLY preexisting native GitHub artifact #11863189967 and no model/provider API. **CI pass is not claimed until observed against PR exact HEAD.**

## Scientific decision

This closes at most the **MEDIA/DISTRIBUTION TECHNICAL PREFLIGHT**, not V3-60 human review. External independent raters currently **0**; human pedagogical quality **UNRATED**, actual learner gain **NOT_MEASURED**, genuinely autonomous model storytelling **NOT_TESTED**, equivalence to 3Blue1Brown **NOT_DEMONSTRATED**, production **BLOCKED**. Do not use the small 3×3 masked pilot to claim population-level efficacy, 3B1B parity or release GO. Human reviews require actual voluntary recruitment, private consent/independence and 3 complete score packets sealed by V3-70 BEFORE treatment mapping is unblinded. **No merge main, no key mutation, no model POST/GET, no prompt or video changes.**
