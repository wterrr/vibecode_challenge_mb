# V3-60 — Independent pedagogical quality review (preregistered)

## Frozen study scope

This is a **masked three-arm within-topic quality assessment**, not a user-learning RCT or an agent creativity evaluation. Registration is `benchmarks/learnflowbench/v3/v3_60_independent_review_preregister.json`, the first child commit on this branch (`89c7e92ed81f9b49685f51319da8b8ddc0bc9b79`). Nine MP4s were inherited byte-for-byte from successful V3-59 push run [#38380316466](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38380316466), masked artifact ID `11803826367`, admin SHA/treatment mapping artifact ID `11804490041`. The review cannot silently change videos, cases, labels, sounds, or criteria after seeing scores.

The subjects are **attention_reversed_query, fraction_equivalence, process_heldout_unknown**. Three masked clips per subject are differentiated only by suffix A, B or C. The source variants are frozen V3-57 original motion, V3-58 static end-state and V3-59 causal semantic reveal. **Do not show the treatment key to raters.** Do not send `admin_treatment_key.json` or `v359_results.json` with the reviewer kit.

## Recruit and preserve independence

At least **three actual external human reviewers**, not project agents or invented personas, must review **all nine clips**. Coordinator collects voluntary informed consent, modest eligibility description (visual learning / comprehension experience), relevant conflicts, and signed or directly attested independence/no collaboration; use pseudonymous IDs, not names in the score file. Preserve reviewer eligibility and original consent evidence privately outside the public repository. Do not claim automated proof of reviewer identity or independent review.

Each reviewer receives a different **unassigned blank** form template; coordinator assigns Rater IDs and uses the forms in the printed video order to counterbalance first-seen position. This is condition-masked, **not double-blind**: motion versus static may be visually identifiable. Same narrator audio, length, case and host facts per triplet do not isolate pure motion causality; static end-state reveals the answer earlier.

Reviewers watch each MP4 in full, may replay, and report `replay_count`. Five criteria are rated independently, integer **1–5** (1 = very poor/misleading, 2 = major defect, 3 = acceptable with weaknesses, 4 = good, 5 = extremely clear):

| Criterion | Rater-facing question |
| --- | --- |
| clarity | Is the concept and its intended claim understandable? |
| causal_witness | Is the explanatory cause visibly established before its effect? |
| semantic_continuity | Do persistent objects, references and states remain coherent? |
| legibility | Are notation, text, color contrast and graphical details actually readable? |
| pacing | Is there enough time to see, reason about and absorb the transitions? |

Confidence is 1–5; `watched_full_video` must be `YES`. Any criterion scored 1 or 2 needs a **concrete timestamp**, e.g. `6.5s: result appears before evidence`, and short failure description. Unratable clips stop panel completeness rather than being silently imputed. Report clipping, split-line difficulty and synchronization concerns even if the overall score is otherwise positive.

## Independent data and locked analysis

1. Download `v360-9-native-masked-reviewer-kit-UNRATED` produced by the V3-60 workflow. Each of 3 templates contains 9 rows with **no scores filled in**. Reviewer coordinator assigns one template per genuine rater.
2. Keep template clip IDs unchanged; obtain 9 scored rows per reviewer and combine them into ONE CSV with one header and the exact columns. No duplicates or omitted rows. Do not include private names or contact details.
3. **Before** accessing or revealing the separate admin key, run `python scripts/run_v3_60_independent_review.py seal --ratings-csv complete_ratings.csv --lock-json locked_scores.json`. Archive the original CSV and JSON and their SHA-256. The tool validates shape and writes an immutable-by-convention lock: an auditor must confirm chronology and custody independently.
4. Coordinator writes a separate `attestations.json` object with `reviewers` pseudonym keys; for each reviewer four booleans `consented`, `external_human`, `conflict_disclosed`, `reviewer_confirmed_no_collaboration` must be true. These booleans are declarations, **not identity proofs**.
5. Only after the lock, use the **separately held original** `admin_treatment_key.json`: `python scripts/run_v3_60_independent_review.py analyze --ratings-csv complete_ratings.csv --lock-json locked_scores.json --admin-key admin_treatment_key.json --attestations-json attestations.json --output analysis.json`.
6. Auditor inspects source consent/eligibility, time ordering, reviewer's familiarity with topic, visible causal errors and timestamp failures; reject forged or collusive submissions. The automatically generated report always remains `PENDING_MANUAL_PROVENANCE_AND_REVIEWER_AUDIT`, never claiming automatic human independence or learning gain.

## Frozen analysis and interpretation

Primary comparison per rater per subject: causal reveal minus original motion on **causal_witness**; also causal reveal minus static. Descriptive median of nine reviewer–topic paired differences, along with the three **per-topic medians**, ranges and disagreements. Since reviewers rate multiple videos, 9 paired differences are **not nine independent people**. No significance test, causal effect size or population claim.

The preregistered *directional screen* is satisfied only when (a) medians causal-versus-original and causal-versus-static are both >=+0.5; (b) at least two of three topic medians are nonnegative against both; and (c) median causal-minus-original legibility >=-0.5. Also report all secondary outcomes and all negative cases without post-hoc exclusions. This is **only a prioritization screen**, not quality GO or learning evidence. No software result promotes a release.

If there are no valid independent ratings, preserve `UNRATED_NO_REVIEWERS`. Real model-generated creativity has **NOT_TESTED** status, true word-level speech alignment is **UNMEASURED**, human learning effect is **NOT_MEASURED**, and production is **BLOCKED**.

## Technical commands (offline)

```bash
python scripts/run_v3_60_independent_review.py verify --clips-dir /path/to/nine_masked_mp4s --full-decode
python scripts/run_v3_60_independent_review.py prepare --clips-dir /path/to/nine_masked_mp4s --output /fresh/reviewer_kit --full-decode
python -m pytest -q tests/v3/test_v3_60_independent_review.py
```

The `prepare` command copies only the exact nine verified masked MP4 files and blank templates, never the admin mapping. Existing GitHub Actions artifacts have a finite retention period. If they expire, re-render from frozen V3-57..59 source with native validation and compare with the frozen hashes before substituting them; a mismatch is a **new protocol**, not a silent replacement.

## Predeclared failure inventory

- Changed SHA, missing clip, wrong codec/frame/audio parity -> **STOP**.
- Treatment mapping leaked before rating lock -> **review compromised**.
- Less than 3 actual independent reviewers, incomplete 9-video panels, missing low-score timestamps -> **NO-GO**.
- Apparent result-before-cause, unreadable labels, misleading graphs, false process completion -> log case/clip/second, never hide.
- Double-blind or pure-motion claim -> invalid; V3-58's static condition bundles motion with early answer.
- Automatically fabricated human ratings, invented listener effects, computed p-values on repeated within-person samples -> prohibited.
