# H-01 — Hermes bootstrap

This directory implements the first Hermes checkpoint from `PLAN_V2.md`.

## Pinned runtime

| Item | Pin |
|---|---|
| Hermes repository | `NousResearch/hermes-agent` |
| Stable release | `v2026.9.24` |
| Package version | `0.21.5` |
| Commit | `f97608f178d1ffeca59860195ab7da295f7c8e5f` |
| Provider | `openrouter` |
| Model | `openai/gpt-6-luna` |
| Programmatic protocol | `--format stream-json` |

The release tag resolves to the exact commit above. Do not install from Hermes `main` for this checkpoint.

## Why the live smoke is local-only

The repository and CI intentionally do not contain `OPENROUTER_API_KEY`. H-01 therefore has two verification layers:

1. **offline contract verification** — pin, config, project instructions, stream parser and Core Freeze all pass without a network credential;
2. **live OpenRouter smoke** — run locally with your own ignored `.env` and require a real Hermes agent → tool → structured-result trajectory.

The checkpoint must remain `IMPLEMENTED_AWAITING_LIVE_SMOKE` until layer 2 passes.

## Install the pinned Hermes runtime

The wrapper installs Hermes into the ignored project-local `.hermes_runtime/` directory, so it does not replace your normal Hermes profile.

### Windows PowerShell

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_hermes_h01.ps1
```

### WSL2 / Linux / macOS

```bash
bash scripts/install_hermes_h01.sh
```

Both wrappers download the installer from the exact pinned Hermes commit and then verify that the installed checkout is exactly that commit.

## Configure the API key

Copy `.env.example` to `.env` if you do not already have one, then set:

```text
OPENROUTER_API_KEY=sk-or-v1-...
```

Do not commit `.env`. The smoke runner loads only `OPENROUTER_API_KEY` from this project-local file and passes it to the isolated Hermes process.

## Run the real H-01 smoke

From the repository root:

```bash
python scripts/run_hermes_h01_smoke.py
```

The smoke launches Hermes with provider `openrouter`, model `openai/gpt-6-luna`, file tools only, `--format stream-json`, and a read-only request that must read `hermes/h01/smoke_fixture.txt`.

Pass criteria:

```text
system/init event exists
→ at least one tool_use
→ matching successful tool_result
→ terminal result.exit_code == 0
→ final text contains HERMES_H01_OK:LEARNFLOW-H01-FIXTURE-v1
→ session trajectory exports successfully with --redact
```

On success the script prints `H01_LIVE=PASS`.

Local artifacts are written under the ignored path:

```text
.hermes_runtime/h01/
├── smoke_stream.jsonl
├── trajectory.jsonl
└── result.json
```

## Offline verification

No API key is required:

```bash
python scripts/run_hermes_h01_smoke.py --offline-fixture hermes/h01/fixtures/stream_success.jsonl
pytest -q --confcutdir=tests/hermes tests/hermes/test_h01_bootstrap.py
python scripts/verify_v2_core_freeze.py
```

Expected first command: `H01_OFFLINE=PASS`.

## What H-01 deliberately does not do

H-01 does not implement the LearnFlow Hermes plugin, multi-agent research, pedagogy, script generation, Visual Director, agent-aware QA, budget hooks, skills, or Kanban. Those begin at H-02 and later.
