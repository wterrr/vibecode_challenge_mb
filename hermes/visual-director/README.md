# Visual Director

This stage uses Hermes to convert an accepted LessonScript into semantic visual direction while keeping geometry and pixels inside LearnFlow Core V2.

Status: IMPLEMENTED_AWAITING_CI.

## Hermes responsibilities

- create the semantic Storyboard;
- create exactly one SceneGraph for each storyboard scene;
- preserve LessonScript segment order and coverage;
- choose visual intent, semantic node/relation/group structure, layout intent, reading direction, and symbolic style tokens;
- maintain concept continuity using the deterministic lesson ConceptRegistry;
- improve visual rhythm and diversity without inventing geometry.

## Deterministic responsibilities

- revalidate the complete Script Agent gate before exposing the script to Visual Director;
- construct ConceptRegistry deterministically from the approved PedagogyPlan concept progression before Hermes runs;
- require every script segment exactly once and in order;
- require SceneGraph scene IDs to match Storyboard scene IDs one-for-one and in order;
- require scene teaching functions and semantic purposes to align;
- require Storyboard concept refs, continuity keys, and SceneGraph concept refs to agree with the ConceptRegistry;
- validate every SceneGraph with the frozen V2.1 semantic schema and registry-aware validator;
- reject empty graphs, pixel/geometry directives, and renderer implementation metadata.

## Boundary

Visual Director owns meaning and semantic visual structure only. It does not own layout coordinates, dimensions, absolute typography, motion paths, camera, timeline arithmetic, renderer code, FFmpeg, or pixels.

## Verification

Run:

    python scripts/verify_visual_director.py
    pytest -q --confcutdir=tests/hermes tests/hermes/test_visual_director.py
    python scripts/verify_v2_core_freeze.py

Exact pinned Hermes structured-output compatibility is verified by scripts/verify_hermes_visual_director.py in the Visual Director workflow.
