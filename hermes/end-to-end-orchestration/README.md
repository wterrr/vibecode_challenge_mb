# End-to-End Orchestration

This stage connects the already accepted LearnFlow Hermes stages into one bounded typed pipeline and hands validated semantic scenes to frozen Core V2 through the accepted LearnFlow capability surface.

Status: IMPLEMENTED_AWAITING_CI.

## Pipeline

    LearningBrief
      -> Research Orchestration (Hermes native delegation)
      -> deterministic Fact Verification
      -> Pedagogy Agent
      -> deterministic pedagogy gate
      -> Script Agent
      -> deterministic script gate
      -> Visual Director
      -> deterministic visual/core-readiness gate
      -> learnflow_create
      -> learnflow_run
      -> learnflow_render
      -> public Core V2 assemble_video
      -> final.mp4

## Rules

- no second agent runtime, message bus, or recursive scheduler;
- Research Orchestration remains the only nested delegation stage and continues to use Hermes native delegation;
- every downstream agent task is built only after the previous deterministic gate passes;
- blocked factual claims never reach Pedagogy/Script;
- Visual Director remains semantic-only;
- Core capability calls receive SceneGraph plus host-owned duration only;
- output paths, renderer settings, geometry, pixels, codec controls, timeline implementation, and assembly remain deterministic host/Core responsibilities;
- Agent-Aware QA, Hooks + Budget, Skills, and Kanban Durability are intentionally out of scope.

## Replayable artifacts

Each successful run writes a controlled directory containing the typed chain, SceneGraphs, render manifest, artifact manifest, and final.mp4.

## Verification

    python scripts/verify_end_to_end_orchestration.py
    pytest -q --confcutdir=tests/hermes tests/hermes/test_end_to_end_orchestration.py
    python scripts/verify_v2_core_freeze.py

Exact pinned Hermes schema compatibility and project-plugin discovery are verified in the End-to-End Orchestration workflow.
