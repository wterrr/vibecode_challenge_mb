# Script Agent

This stage uses Hermes to turn a validated `PedagogyPlan` into a claim-preserving `LessonScript`, then applies a deterministic Visual-Director readiness gate.

## Hermes responsibilities

- write natural spoken narration and subtitle text;
- split narration into ordered `ScriptSegment` records;
- preserve the exact claim IDs selected by Pedagogy Agent;
- map segments to learning objectives;
- assign one `TeachingFunction` to every segment.

## Deterministic responsibilities

- revalidate PedagogyPlan Script-readiness before constructing Hermes context;
- expose only claims selected by the validated PedagogyPlan;
- require the script claim-ID set to equal the PedagogyPlan claim-ID set;
- require every PedagogyPlan objective to be covered by at least one script segment;
- require fact-bearing EXPLAIN / COMPARE / DEMONSTRATE / SUMMARIZE segments to carry claim IDs when the plan contains factual claims;
- reject visual/pixel/renderer/implementation directives before Visual Director.

## Boundary

Script Agent writes narrative structure only. It must not create SceneGraph objects, choose geometry/layout/motion/camera/typography, call renderers, emit FFmpeg commands, or implement Visual Director.
