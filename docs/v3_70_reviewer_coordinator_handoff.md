# V3-70 — Coordinator handoff for independent human reviews

**Status:** research intake infrastructure, **zero confirmed actual human reviewers**. Do not submit data fabricated by tests, agents, or simulated browser interactions. This is a condition-masked descriptive pilot, NOT double-blind. The static control also advances the answer reveal, so it is not a pure motion-only causal ablation.

## 1. Distribute the frozen V3-61 offline kit

Obtain the original 9-clip V3-61 artifact from https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38496967796 (artifact ID 11863189967; initially retained through 2026-10-21 UTC). Verify 9 masked native MP4 SHA-256 digests against V3-60 preregistration. Do NOT provide the admin treatment key. If artifact expires, recreate only from frozen source and reverify every SHA; changed source means a new protocol, never substitute silently.

Three distinct eligible, external, consenting reviewers receive respectively reviewer_01.html, reviewer_02.html and reviewer_03.html (one form per reviewer), locally with all media, CSS and JS. Each watches 9 full videos, scores 5 original V3-60 criteria plus confidence and replay count, and records timestamped reasons when any criterion is <=2. Each person exports one original unmodified CSV. Do not claim viewing events prove genuine attention or identity.

## 2. Preserve private evidence and prepare coordinator attestations

Keep the three original CSV exports in one private folder containing ONLY these three CSV files. Assign distinct pseudonyms with no real names/emails, and keep original consent, reviewer eligibility, conflicts, assignment log and independent provenance privately outside GitHub. Do not upload personal consent documentation or reviewer scores as Actions artifacts.

Create an external JSON for the same three pseudonyms. The example below is deliberately **FALSE BY DEFAULT** and does not count as evidence. Each individual flag may be set true only after checking real, privately held source evidence. Use distinct form_number values 1, 2, 3 matching the assigned HTML page:

```json
{
  "checkpoint": "V3-70",
  "coordinator_confirmed_no_admin_mapping_seen": false,
  "reviewers": {
    "reviewer_01": {
      "form_number": 1,
      "consented": false,
      "external_human": false,
      "eligible": false,
      "conflict_disclosed": false,
      "reviewer_confirmed_no_collaboration": false,
      "coordinator_checked_original_consent_privately": false,
      "coordinator_checked_distinct_individual_privately": false
    }
  }
}
```

Repeat the reviewer object for reviewers 02 and 03, with form numbers 2 and 3. The script can validate the assertion structure, not independently verify truthful consent or genuine independence.

## 3. Collect and lock before any treatment unblinding

Run only on a PRIVATE LOCAL MACHINE, not GitHub Actions, with the admin treatment key still sealed separately:

```bash
python scripts/run_v3_70_review_intake.py \
  --submissions-dir /PRIVATE/three_original_csvs \
  --attestations-json /PRIVATE/attestations.json \
  --out-dir /PRIVATE/new_v370_locked_intake
```

The destination must not exist beforehand. Missing rows, changed clip order, duplicated reviewers, inconsistent forms, low score without timestamp, formula injection, test-only pseudonyms, symlinks, or administrator files fail closed. The script reuses the unchanged V3-60 validation and seal, then writes three PRIVATE local files: complete_ratings.csv, locked_scores.json, intake_receipt.json. The receipt includes hashes and pseudonyms only, not human-identifying source documents.

## 4. Audit, then analyze independently

The independent auditor must personally verify original consent/eligibility, conflict information, chronology, independent score origination, score lock SHA and evidence custody. Only **after** locking may the coordinator access the separately held original V3-59 admin key and use the V3-60 analyze subcommand. Its descriptive paired ordinal estimates must not become p-values or claims of learner gain, production release, or 3Blue1Brown parity.

With no actual human submissions: HUMAN QUALITY = UNRATED; LEARNER GAIN = NOT_MEASURED; GENUINE MODEL CREATIVITY = NOT_TESTED; PRODUCTION = BLOCKED.
