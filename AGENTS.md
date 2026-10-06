# LearnFlow Agent Instructions

## Project goal

LearnFlow V2 generates educational videos through a typed semantic pipeline. Hermes is the control plane; LearnFlow Core V2 is the deterministic production engine.

## Architecture boundary

Hermes may own research strategy, evidence judgment, pedagogy, narrative, semantic visual direction, semantic QA, orchestration, and repair intent.

Hermes must not own geometry, pixel coordinates, renderer implementation, layout constraints, timeline arithmetic, schema validation, codec validation, retry accounting, cost accounting, atomic publication, or security policy.

## Frozen Core

The current Core Freeze is authoritative at:

- `benchmarks/core_freeze/manifest.json`
- `scripts/verify_v2_core_freeze.py`

Before changing any Core-adjacent implementation, run:

```bash
python scripts/verify_v2_core_freeze.py
```

Do not modify files protected by the Core Freeze manifest during routine Hermes work. A genuine Core change requires the explicit CORE UNFREEZE → regression → Core Gate → evidence freeze → new Core Freeze cycle.

## Hermes stage discipline

Work one named Hermes stage at a time in the order defined by `PLAN_V2.md`. Names in source control, runtime paths, CI, logs, status files, tests, and documentation must describe their purpose. Do not introduce opaque ordinal checkpoint codes.

Accepted stages:

- **Hermes Bootstrap — PASS.** The live OpenRouter smoke passed on 2026-10-06. The primary model was attempted first; the accepted free fallback `nvidia/nemotron-3.5-lightning:free` completed the read-tool round-trip. Offline verification and the Core Freeze guard also passed.
- **LearnFlow Capability Plugin — PASS.** The exact pinned Hermes runtime discovers the project plugin and dispatches `learnflow_create → learnflow_run → learnflow_render`. Integration verification renders a real MP4 and preserves the Core Freeze boundary.
- **Agent Contracts — PASS.** `LearningBrief`, `ResearchPack`, `EvidenceGraph`, `PedagogyPlan`, `LessonScript`, `Storyboard`, `AgentRun`, and `BudgetLedger` are strict, versioned, canonically serializable artifacts with cross-artifact integrity checks.
- **Fact Verification — PASS.** A deterministic source-grounding/contradiction gate controls factual narration eligibility; Hermes semantic verdicts are structured but cannot override missing evidence.
- **Pedagogy Agent — PASS.** Hermes produces structured pedagogy from approved claims only; deterministic checks require researched concept progression, objective assessment coverage, and Script readiness.
- **Script Agent — PASS.** Hermes produces `LessonScript` narration with exact PedagogyPlan claim preservation, objective coverage, required teaching functions, and no visual implementation fields.

Accepted stage: **Agent Contracts — PASS.** The coherent artifact-chain verifier, 11 contract regressions, and Core Freeze guard passed.

Accepted stage: **Research Orchestration — PASS.** Hermes native nested delegation, isolated child contexts, bounded depth/concurrency, leaf recursion blocking, structured child outputs, and provenance-preserving merge are all verified.

Accepted stage: **Fact Verification — PASS.** Source-grounded evidence, cycle-safe provenance, contradiction signaling, unsupported-claim blocking, factual narration claim gating, and pinned Hermes semantic-review compatibility are verified.

Accepted stage: **Pedagogy Agent — PASS.** Hermes receives fact-approved research only, unsafe/forged approvals are rejected before context exposure, and deterministic validation enforces concept provenance, assessment coverage, examples, and Script readiness.

Accepted stage: **Script Agent — PASS.** Hermes writes structured narration only; deterministic validation preserves the exact PedagogyPlan claim set, objective coverage, factual claim binding, and the Script/Visual boundary. Next authorized stage: **Visual Director**, which has not started yet.

During Visual Director, implement only semantic visual direction that converts LessonScript segments into schema-valid SceneGraph outputs with semantic layout hints and no pixel coordinates. Do not implement Agent-Aware QA, Hooks + Budget, Skills, or Kanban Durability yet.

## LearnFlow Capability Plugin safety

The project-local plugin lives at `.hermes/plugins/learnflow/` and exposes exactly:

- `learnflow_create`
- `learnflow_run`
- `learnflow_render`

The model-facing surface is semantic only. It must not accept arbitrary output paths, pixel coordinates, absolute font sizes, renderer code, FFmpeg expressions, FPS/CRF/preset overrides, or renderer objects.

`learnflow_render` must call the public `learnflow_v2.render.render_scene_video` facade. The plugin must not import `learnflow_v2.render.backend` or instantiate `DeterministicPillowRenderer` directly.

Controlled artifacts belong under `.hermes_runtime/learnflow-plugin/runs/`. `LEARNFLOW_PLUGIN_RUNTIME_ROOT` is an operator/test override and is not a model-facing tool argument.

Project plugins are trusted-code opt-in. Enable project-plugin discovery only for this trusted repository with `HERMES_ENABLE_PROJECT_PLUGINS=true`.

## Hermes Bootstrap safety

The live smoke is read-only. It may read `hermes/bootstrap/tool_read_fixture.txt` and return the expected sentinel, but it must not edit repository files.

Use `openai/gpt-6-luna` as the primary model and `nvidia/nemotron-3.5-lightning:free` as the accepted no-credit fallback. Record which model actually passed.

Never commit API keys or copy them into logs. `OPENROUTER_API_KEY` belongs only in the local ignored `.env` file or process environment.

## Verification

Hermes Bootstrap:

```bash
python scripts/run_hermes_bootstrap_smoke.py --offline-fixture hermes/bootstrap/fixtures/successful_tool_roundtrip.jsonl
pytest -q --confcutdir=tests/hermes tests/hermes/test_bootstrap.py
python scripts/verify_v2_core_freeze.py
```

LearnFlow Capability Plugin:

```bash
pytest -q --confcutdir=tests/hermes tests/hermes/test_learnflow_plugin.py
python scripts/verify_v2_core_freeze.py
```

Pinned-runtime discovery and execution:

```bash
HERMES_ENABLE_PROJECT_PLUGINS=true \
  .hermes_runtime/hermes-agent/venv/bin/python \
  scripts/verify_learnflow_plugin.py
```

## Agent Contracts boundary

The public control-plane contracts live in `agent_contracts/`. Keep them renderer-independent and geometry-free.

Agent Contracts may define strict artifact schemas, cross-artifact reference validation, canonical serialization, provenance, run-audit records, and budget state. They must not execute research, generate pedagogy/script/storyboards with an LLM, invoke rendering, or implement delegation/hooks.

Verification:

```bash
python scripts/verify_agent_contracts.py
pytest -q --confcutdir=tests/hermes tests/hermes/test_agent_contracts.py
python scripts/verify_v2_core_freeze.py
```

## Research Orchestration boundary

Research topology is fixed to Director → Research Orchestrator → at most three specialist researchers. Configure Hermes with `max_spawn_depth: 2`, `max_concurrent_children: 3`, and `oneshot_max_children: 3`.

Use Hermes native delegation and isolated child contexts. Do not implement a second agent runtime, message bus, or recursive scheduler in LearnFlow.

Specialist roles are Concept Researcher, Evidence Researcher, and Misconception Researcher. Leaf specialists must not delegate further.

Every evidence claim must preserve declared source IDs and source locators. Research Orchestration may assemble `ResearchPack` and `EvidenceGraph`, but contradiction resolution and unsupported-claim blocking belong to the later Fact Verification stage.

## Fact Verification boundary

Fact Verification evaluates `ResearchPack` + `EvidenceGraph` before factual narration. A claim is narratable only when deterministic verification finds a real source-grounded support/derivation path and no contradiction or unresolved semantic uncertainty.

Do not treat `ResearchClaim.source_ids` alone as proof. Declaring a source ID is not equivalent to an evidence path.

Claim-to-claim cycles must not self-ground. Use fixed-point source provenance so a cycle becomes grounded only if some path reaches a real source node.

Hermes semantic review is advisory in the positive direction: `SUPPORTED` cannot override missing deterministic evidence. `CONTRADICTED` or `UNCERTAIN` must fail closed.

Every factual narration must carry one or more approved `claim_id` values. Pedagogy and Script stages must consume this gate rather than re-deciding evidence validity.

## Pedagogy Agent boundary

Pedagogy Agent consumes `LearningBrief`, `ResearchPack`, `EvidenceGraph`, and `FactVerificationReport`. Its model-facing research context must exclude blocked factual claims.

A plan may use only fact-approved `claim_id` values in worked examples, analogies, and misconceptions. Concept progression may use only researched concepts. Every learning objective must have at least one assessment probe, and at least one worked example or analogy is required before Script Agent.

Pedagogy Agent must not write narration, instantiate `LessonScript`/`ScriptSegment`, produce visual coordinates, create SceneGraph objects, render video, or implement later QA/budget/scheduling stages.

## Script Agent boundary

Script Agent consumes only a Script-ready `PedagogyPlan` plus the exact factual claims selected by that plan. It must not see or reintroduce blocked/unselected claims.

The union of `claim_ids` in the produced `LessonScript` must equal the union of claim IDs selected by the PedagogyPlan. Repeating a preserved claim across multiple segments is allowed; dropping a selected claim or adding another claim is not.

Every PedagogyPlan learning objective must appear in at least one script segment. EXPLAIN, COMPARE, DEMONSTRATE, and SUMMARIZE segments must carry claim IDs when the plan contains factual claims.

Script Agent may write spoken/subtitle narration and choose `TeachingFunction`. It must not create SceneGraph objects, pixel coordinates, layout/motion/camera/typography instructions, renderer calls, FFmpeg commands, or implementation code.
