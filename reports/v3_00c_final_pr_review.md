# V3-00C Final PR Review → V3-00D Corrective Closure

**Repository:** [wterrr/vibecode_challenge_mb](https://github.com/wterrr/vibecode_challenge_mb)  
**PR:** [#33](https://github.com/wterrr/vibecode_challenge_mb/pull/33)  
**Branch:** `chatgpt/v3-00b-selective-integration` (created from original `main`)  
**Audit scope:** Offline-only security and integration review; **no merge**, no V3-01 and no paid API.

## Previous gate (V3-00C): FIX

All 11 GitHub Actions on initial PR head `7529f229` passed, including Core Freeze, V2D Contract, 74 tests and 14 renderer passes / 5 skips. Importantly `live-provider-pilot` was skipped. However audit discovered two merge blockers in `scripts/export_live_v2d_evidence.py`:

- **S1:** destination ancestor of source was allowed and `shutil.rmtree(destination)` could delete original source on operator misconfiguration;
- **S2:** `lesson-runs` could be a symlink into an external directory (the leaf-only symlink check was insufficient).

The reviewed CI path was safe; no incident was demonstrated. Full CI success did **not** waive these defects. Source: [PR #33 V3-00C review](https://github.com/wterrr/vibecode_challenge_mb/pull/33#issuecomment-6052127592).

## V3-00D exact code diff and safety arguments

**Fix SHA:** [`e33fd574525a8f26588b0def34f67dcb0aa4caa5`](https://github.com/wterrr/vibecode_challenge_mb/commit/e33fd574525a8f26588b0def34f67dcb0aa4caa5); [two-file comparison](https://github.com/wterrr/vibecode_challenge_mb/compare/7529f229c86869454164d8118d7b7184e98676ed...e33fd574525a8f26588b0def34f67dcb0aa4caa5).

| File | Change | Why |
| --- | --- | --- |
| `scripts/export_live_v2d_evidence.py` | bidirectional ancestor checks; reject roots/existing output and symlinks across all exported path components; validate staging copy; private tempfile staging, final rename and owned-only staging cleanup | eliminates destructive output reuse and input path symlink traversal under controlled CI |
| `tests/hermes/test_final_v2_semantic_consistency.py` | +8 regression tests covering parent/self/child/root paths, sentinel output, dangling/existing symlink output, symlinked lesson-runs/run/subdir/leaf, partial-secret failure and successful allowlisted exports | demonstrates fail-closed behavior and input integrity |

**No changes to:** frozen `learnflow_v2/**`, model defaults, provider runner, subtitle policy, V1 rollback, original Action #181, historical corpus or publication permissions. This checkpoint does not depend on third-party code and follows PLAN_V3 reuse-first.

**Atomicity boundary:** Staging is written to a private random directory in the output's parent filesystem and moved at completion. No deletion of any caller-provided destination is permitted. This is atomic publication against ordinary failures in isolated CI. A malicious concurrent process capable of creating an empty destination directory precisely between existence check and `os.rename` is outside this checkpoint's threat model; a true multi-writer publication would require an OS-level no-replace rename/exclusive lock.

## Fresh offline evidence on code SHA

- [Push integration CI #37727235950](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37727235950): **SUCCESS**; `CORE_FREEZE=PASS`, `LIVE_V2D_CONTRACT=PASS`, **82 passed**, renderer **14 passed / 5 skipped**.
- [PR integration CI #37727239593](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37727239593): **SUCCESS**.
- [Governed V2D PR CI #37727239570](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37727239570): contract job **SUCCESS**; live provider job **SKIPPED** (no paid call).
- Remaining PR jobs: **pending final all-green confirmation before changing Draft to Ready for review**.

## Security, rollback and merge decision

- Allowlisted artifact output still includes only declared report/evidence assets; `hermes-home/auth.json`, governance logs, cache and auth state are not copied. JSON matching known credential markers aborts publication and deletes only owned staging.
- No branch or main Core Freeze changes; `main` remains `29fab1d5738ccb060502c8ae82e2e31f00360811` as observed at checkpoint start.
- V2 default free model remains unchanged. Provider workflow is manual-dispatch only, and the PR's provider job skip is demonstrated.
- Rollback if user authorizes merge later: revert PR #33 merge commit; no V2 source migration or historical artifact rewrite is necessary.
- **V3-00D code gate: PASS. Full PR merge readiness: PENDING remaining workflow results and user authorization.** The PR is not merged and this report is not an approval to implement V3-01.
