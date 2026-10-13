# CI Recovery & Workflow Fan-out Remediation — evidence ledger (2026-10-13)

## Scope & baseline
- Repository: wterrr/vibecode_challenge_mb.
- Research checkpoint frozen: Draft PR #93 (V3-59), HEAD `0edad793046b49a5ca69c45d87fffe52ada62570`. No merge or model API activity.
- Operations-only branch: `ops/v3-ci-fanout-gate-20261013`, stacked on PR #93, not on main.
- GitHub REST Actions backlog observed: 2,351 queued originally, later 2,095 and 2,116; changing counts alone do **not** certify cancellation.
- Original V3-59 exact-head run #38345567800 and V3-58 #38345567741 were still queued at audit. Neither decoded MP4 receipt nor human-review outcome has been certified.

## Failure inventory and grounded root cause
- The stacked V3-59 branch contained 81 workflow files; main had 21 at the comparison time.
- Specialized V3-43..59 workflows matched changes to canonical `PLAN_V3.md` and `LEARNFLOW_V3_RESEARCH_NOTES.md`, even when unrelated to their code.
- Legacy V3 workflow families matched broad `learnflow_v3/**` and/or `tests/v3/**` paths and triggered on every stacked PR.
- `on.pull_request.paths` checks the **PR cumulative changed-file set**, not just the most recently changed file, which amplified fan-out.
- In-flight jobs succeeded while thousands remained queued; no evidence of an outright GitHub Actions outage.

## Implemented (non-production, reviewable, single ops PR)
1. Strip shared canonical documentation from scientific checkpoint-specific PR path filters V3-43 and V3-44..59; retain their own code, benchmark, test, report and workflow triggers.
2. Restrict older broad V3 regression gates to pull requests targeting `main` (and preserve original checkpoint push triggers), retaining integration coverage while eliminating duplicate runs on stacked PR bases.
3. For all modified workflow families, add stable per-workflow/per-PR `concurrency` and `cancel-in-progress: false`, preserving in-progress evidence while limiting queued duplicates. It is **not** a blanket cancellation mechanism.
4. Add a single minimal shared-document integrity workflow (`.github/workflows/v3-canonical-docs.yml`).
5. Add an offline falsifiable trigger-matrix verifier (`scripts/verify_v3_ci_scope.py`) plus a lightweight exact-head audit workflow (`.github/workflows/v3-ci-scope-audit.yml`). Simulated input includes V3-59 code/test/docs changes with stacked base; requires only V3-59 and at most two other specific workflows, zero unrelated scientific workflows on docs-only changes, and legacy V3 contract jobs preserved on main integration PRs.

## Backlog cancellation isolation
- Existing cleanup workflow is on `ops/ci-queue-cleanup-20261013`, triggered as [#38347969904](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38347969904). It was queued on last known check; no accepted cancellation counts yet. Its scope is bounded to queued, older PR actions; V3-57/58/59 are protected.
- This patch does **not** cancel in-flight runs, does **not** falsely claim the backlog was drained, and does **not** merge main. A separate authorized Actions cleanup is necessary for existing historical queue.

## Acceptance to verify after CI scheduling
- [ ] Exact ops-branch trigger-matrix audit completed PASS; inspect logs and any failure.
- [ ] Count PR-triggered workflows on this isolated PR; distinguish initial one-time workflow-file self-triggers from ongoing docs-only updates.
- [ ] Confirm future representative V3-59 stacked doc/code PR changes trigger a bounded set; no unintended critical gate missing.
- [ ] Confirm main integration PR still executes legacy V3 broad regression.
- [ ] Confirm cleanup job accepted cancellations (or disclose its API-permission error); compare queued counts before and after.
- [ ] Re-evaluate PR #93 exact-head V3-59 CI/video artifacts before any scientific or production promotion.

## Restrictions
No V2 Core edits; no production-prompt edits; no model calls; no main merge; V3-59 semantic video/ASR/visual quality remain UNRATED until actual native artifact checks. This is an infrastructure change only.
