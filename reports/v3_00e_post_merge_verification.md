# V3-00E — Approved Merge and Post-Merge Offline Verification

**Date:** 2026-10-08. **Final gate: PASS.** This report records a completed selective integration and its post-merge checks; it does **not** authorize V3-01 implementation or any paid API call.

## 1. Approval and exact git refs

- Explicit user request: execute **V3-00E — Approved Merge & Post-Merge Offline Verification** after approving merge of [PR #33](https://github.com/wterrr/vibecode_challenge_mb/pull/33). No automatic merging of other branches or PRs.
- PR head approved and verified before merge: `cac628f9af255b2543feafbd9b2ebeadbe414ffa`; the merged change is selective V2D production-safe gating, **not** the GPT-6 Luna pilot fast-forward.
- Original `main`: `29fab1d5738ccb060502c8ae82e2e31f00360811`.
- **Merge commit on `main`: [`be19b4819b8c23c19713b6351d384411b29bf29b`](https://github.com/wterrr/vibecode_challenge_mb/commit/be19b4819b8c23c19713b6351d384411b29bf29b)**; GitHub API returned `merged=true`. The PR is closed as merged.
- Merge method `merge` preserved the candidate commit history; `expected_head_sha` guarded against head changes.
- Post-merge documentation-only continuity commit is recorded in Git history separately from the verified merge commit. The code results below refer specifically to `be19b4819b8c23c19713b6351d384411b29bf29b`.

## 2. Evidence: all CI passed before and after merge

**Before merge:** 11/11 GitHub Actions workflow runs for PR SHA `cac628f9` completed **SUCCESS**; 0 failed/pending, and GitHub PR was `mergeable=true`. The governed live-provider job was **SKIPPED**. A new production-neutral offline CI trigger on push to `main` was reviewed as part of that PR.

**After merge:** all **10/10** workflow runs on exact main merge commit `be19b4819b8c23c19713b6351d384411b29bf29b` completed **SUCCESS**, with 0 failed/pending.

| Post-merge workflow | Run ID | Conclusion |
| --- | --- | --- |
| Governed V2D Offline Regression Gate | [37728464626](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37728464626) | **SUCCESS** |
| Governed Live V2D Evaluation | [37728464657](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37728464657) | **SUCCESS: contract passed, live-provider-pilot SKIPPED** |
| Agent Contracts | [37728464643](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37728464643) | SUCCESS |
| Pedagogy Agent | [37728464651](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37728464651) | SUCCESS |
| Research Orchestration | [37728464632](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37728464632) | SUCCESS |
| LearnFlowBench | [37728464679](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37728464679) | SUCCESS |
| Visual Director | [37728464663](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37728464663) | SUCCESS |
| Lesson Pipeline | [37728464736](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37728464736) | SUCCESS |
| Script Agent | [37728464641](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37728464641) | SUCCESS |
| Fact Verification | [37728464649](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37728464649) | SUCCESS |

**Direct verified offline log output on `main`, workflow #37728464626:**

```text
CORE_FREEZE=PASS
LIVE_V2D_CONTRACT=PASS
82 passed
14 passed, 5 skipped
```

The 82 tests cover existing V2D contract plus new semantic identity, subtitle, evidence-redaction, symlink escape and destructive-path regression cases. The renderer suite passed 14 cases with 5 skipped; skips are not counted as successes. These results do not claim end-to-end video pedagogy quality or population reliability.

## 3. Security, Core Freeze, rollback and historical evidence

- `hermes/bootstrap/config.yaml` on `main` retains **`nvidia/nemotron-3.5-lightning:free`** as default; `openai/gpt-6-luna` was not promoted to default.
- `.github/workflows/live-v2d-evaluation.yml` gates its `live-provider-pilot` job on `workflow_dispatch` only. **The actual merge push run #37728464657 skipped the provider job** and only performed non-provider contract checks.
- The evidence artifact uploader uses an allowlisted output directory and conditions upload on the export step's success. The exporter now rejects destructive ancestor destinations, existing caller-owned outputs, symlink traversal and credential-marked JSON. Its mutation/negative tests passed offline.
- No merge diff under `learnflow_v2/**`, `benchmarks/core_freeze/**`, or `hermes/bootstrap/**`. `scripts/verify_v2_core_freeze.py` passed on the actual merge commit; the original Core Freeze manifest and V1 rollback referent remain unchanged.
- **Original Action #181**: [run 37721597623](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37721597623) remains `completed/success`, attempt 1, with artifact `governed-live-v2d-pilot` ID `11525814288`; the historical registry (find 16) vs script/video (find 24) mismatch is unchanged and must not be retroactively marked PASS.
- Rollback procedure **only if separately authorized**: revert merge commit on main using `git revert -m 1 be19b4819b8c23c19713b6351d384411b29bf29b`, resolve dependencies carefully, rerun offline gate and confirm default model and Core Freeze. Do not rewrite #181 nor silently reset protected history.
- Continuing limitations: semantic guard addresses a narrow family of numeric worked examples, no universal semantic proof; short subtitles remain opt-in, and a multiwriter malicious race against POSIX rename was not proven safe. No paid API was invoked by these automated merge workflows.

## 4. Final decision and next authorized boundary

**V3-00E: PASS.** PR #33 has been integrated safely and inspected on `main`; the default V2 route, Core Freeze, deterministic regressions, and historical evidence were preserved.

**V3-01 — Benchmark Preregistration** is the one proposed next checkpoint, but **was not implemented** in V3-00E. Begin only on user approval, with the reuse-first policy and pinned baseline from `PLAN_V3.md`. No implementation of other V3 capabilities and no paid-provider job is authorized by this result.
