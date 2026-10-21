# Code2Video as a bounded LearnFlow agent tool (experimental)

## Upstream provenance and licensing

The optional image in `integrations/code2video/Dockerfile` clones the actual
[showlab/Code2Video](https://github.com/showlab/Code2Video) MIT source and
checks out exactly `1142d8e14cdc2806df85aedb0fbb5dca474caa0f`
(2026-08-24). Its MIT LICENSE is included in the planner image. **Do not**
copy the research repository into LearnFlow's production FastAPI image.

This first bounded integration uses Code2Video's **upstream `get_prompt3_code`
Coder prompt** and `TeachingScene` base-class definition. It is not yet the
original three-agent Planner/Coder/Critic pipeline: LearnFlow supplies the
storyboard and narration, the worker performs at most **one Coder call**,
and the secretless sandbox renders one Manim scene.

## Isolation and requests

```
LearnFlow paid model ─────> optional probe_code2video_scene (semantic JSON)
LessonPlan accepted ──────> Code2VideoSceneRenderer (authenticated HTTP)
Code2Video planner ───────> OpenRouter (one code-generation POST; no retry)
                     └────> renderer private internal network
Secretless renderer ──────> Python Manim execution under CPU/memory/time limits
                     └────> MP4 bytes
LearnFlow ────────────────> FFmpeg timing/codec normalization
                     └────> motion QA + TTS + final MP4
```

The planner worker does NOT execute generated Python. The renderer worker has
NO OpenRouter keys, application credentials, database connection, shared host
Docker socket, internet-facing ports or general public egress. The renderer
uses an AST preflight **only as defense in depth**: untrusted Python execution
always needs a hardened container/VM boundary. See the separate compose file.
The renderer's internal network still permits communication with the planner,
so add network policies/egress ACLs before trusting truly adversarial input.
This is a **research/pilot sandbox**, not a proven security boundary for
multi-tenant untrusted execution.

## Start the optional workers

1. Set the three variables in a private non-committed environment file
   (example content below) named `integrations/code2video/worker.env`:
   ```env
   CODE2VIDEO_OPENROUTER_API_KEY=<dedicated low-limit OpenRouter key>
   CODE2VIDEO_MODEL=openai/gpt-6-luna
   CODE2VIDEO_WORKER_TOKEN=<random at least 24 character shared secret>
   ```
2. Run the optional pinned-source worker from the repository root:
   ```sh
   docker compose -f integrations/code2video/compose.yaml \
     --env-file integrations/code2video/worker.env up --build
   ```
   The Coder/planner port is bound to localhost 8765. Do not expose it
   publicly without private TLS, authentication and allowlisted network access.
   The renderer is only on the internal compose network, uses a non-root user,
   memory/CPU/pids quotas, tmpfs and read-only root filesystem.
3. On LearnFlow, enable ONLY after this private worker is reachable:
   ```env
   LEARNFLOW_AGENTIC_VISUAL_TOOLS=true
   LEARNFLOW_CODE2VIDEO_ENABLED=true
   LEARNFLOW_CODE2VIDEO_WORKER_URL=http://code2video-planner:8765
   LEARNFLOW_CODE2VIDEO_WORKER_TOKEN=<same random secret>
   ```
   This HTTP address works only when LearnFlow can resolve the private service
   on the same Docker network. Otherwise use a private **HTTPS** gateway.
   Do not try to deploy both workers through the existing VibeHost single-app
   Dockerfile or set the worker URL to a public HTTP endpoint.

## Limits and acceptance

- Worker mode is off by default; existing production jobs remain unchanged.
- One Code2Video scene per lesson maximum. A semantic probe is available only
  when enabled; model-generated code is NEVER accepted in API JSON.
- The worker uses one extra paid LLM request per Code2Video scene, in addition
  to LearnFlow's planner and optional tool-discovery POST.
- Rendering: 150-second subprocess limit, bounded video size, dedicated
  CPU/memory/file limits, normalized MP4 and decoded-motion verification.
- There is no automatic loop of 10 code fixes or repeated paid Critic calls.
- Current integration does not run a VLM Critic or verify the factual accuracy
  of new free-form diagrams. Manual review of MP4 remains necessary.
- Running GitHub CI tests the host adapter using an actual H264 clip and mocked
  transport; it does NOT build the optional upstream worker or spend paid keys.
  Worker-build compatibility, live model/API behavior, physical sandbox
  isolation and teaching quality are unverified until separately exercised.
- Do not enable on a production VibeHost site until a private worker service
  and security review exist. Failure to connect must fail the job explicitly,
  never fallback to executing code in FastAPI.

## Why this is different from extending the slide template

Code2Video may synthesize genuinely new Manim geometry rather than choosing a
fixed `concept_card/process_diagram` family. LearnFlow still owns the final
script, media quality gate, audio timing and publication authorization.
The worker is a **bounded creative fallback** for mechanisms the verified
math/algorithm/physics renderer families cannot demonstrate.

