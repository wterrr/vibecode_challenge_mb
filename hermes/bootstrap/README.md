# Hermes Bootstrap

This directory contains the accepted Hermes runtime pin, OpenRouter configuration, smoke fixtures, and verification status for LearnFlow.

## Status

**PASS — 2026-10-06**

The historical user-local live OpenRouter smoke completed successfully with `nvidia/nemotron-3.5-lightning:free`. The current runtime policy is stricter: **all LearnFlow-owned OpenRouter calls must use model slugs ending in `:free`**. Paid OpenRouter models are rejected before a request is sent.

The offline stream contract, bootstrap tests, and LearnFlow Core Freeze guard also passed. Session identifiers, token accounting, API keys, and trajectory contents are intentionally not committed.

## Pinned runtime

| Item | Pin |
|---|---|
| Hermes repository | `NousResearch/hermes-agent` |
| Stable release | `v2026.9.24` |
| Package version | `0.21.5` |
| Commit | `f97608f178d1ffeca59860195ab7da295f7c8e5f` |
| Provider | `openrouter` |
| Primary model | `nvidia/nemotron-3.5-lightning:free` |
| Model policy | `:free` only; paid OpenRouter slugs fail closed |
| Programmatic protocol | `--format stream-json` |

Do not install from Hermes `main`; use the exact pinned commit.

## Install

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_hermes_bootstrap.ps1
```

WSL2 / Linux / macOS:

```bash
bash scripts/install_hermes_bootstrap.sh
```

## Configure OpenRouter

Keep the real credential only in the ignored local `.env`. The key may have paid balance, but LearnFlow's OpenRouter policy rejects any model slug that is not a `:free` variant:

```text
OPENROUTER_API_KEY=<your-key>
```

## Live smoke

```bash
python scripts/run_hermes_bootstrap_smoke.py
```

The smoke is read-only and must read `hermes/bootstrap/tool_read_fixture.txt`. The expected sentinel is:

```text
HERMES_BOOTSTRAP_OK:LEARNFLOW-BOOTSTRAP-FIXTURE-v1
```

On success the runner prints `HERMES_BOOTSTRAP_LIVE=PASS` and stores local-only artifacts under `.hermes_runtime/bootstrap/`.

## Offline verification

```bash
python scripts/run_hermes_bootstrap_smoke.py --offline-fixture hermes/bootstrap/fixtures/successful_tool_roundtrip.jsonl
pytest -q --confcutdir=tests/hermes tests/hermes/test_bootstrap.py
python scripts/verify_v2_core_freeze.py
```

Expected first command: `HERMES_BOOTSTRAP_OFFLINE=PASS`.
