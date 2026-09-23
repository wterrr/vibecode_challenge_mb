# LearnFlow AI — AI Learning Video Studio

LearnFlow AI transforms educational questions and learning topics into concise, structured, narrated videos with synchronized concept cards, process diagrams, comparisons, and illustrations.

## Current Status
- **V1 Baseline**: Frozen at CP10 (Local Submission Readiness).
  - All 202 tests passing (`pytest -q`).
  - Production `PORT` contract and preflight capabilities verified.
  - Deterministic downstream baseline verified via `python scripts/capture_v1_baseline.py`.
  - V1 code remains the active production runtime path under `app/`.
- **V2.1 Development**: Active side-by-side architecture development.
  - Source of truth: `PLAN_V2.md` (frozen V1 source of truth remains `PLAN.md`).
  - Isolated package namespace: `learnflow_v2/`.
  - V2 is completely isolated from production runtime and FastAPI until the V2 Core Gate passes.
- **Implemented Milestones**:
  - **CP0**: Runtime configuration, capability detection, preflight diagnostics, and healthz.
  - **CP1**: SQLite schema, Job entity lifecycle, atomic repository, and transactional storage.
  - **CP2**: Job creation API, async queue worker, Web UI, and artifact storage using `FakePipeline`.
  - **CP3**: Structured lesson planning via Gemini Interactions API, JSON schema validation, and repair loops.
  - **CP4**: Edge TTS voice synthesis, audio metadata extraction, and audio-first timeline synchronization.
  - **CP5**: Deterministic Pillow + FFmpeg visual renderers (`ConceptCard`, `ProcessDiagram`, `Comparison`, `Illustration`), typography line fitting, long-token wrapping, and progressive state allocation.
  - **CP6**: Optional Gemini image generation (`GeminiImageProvider`, `gemini-3.1-flash-image`), aspect-ratio preserving composition, and robust deterministic illustration fallback.
  - **CP7**: Real learning video pipeline (`RealVideoPipeline`) orchestrating planning, validation, TTS synthesis, visual rendering, assembly, and quality validation.
  - **CP8**: Quality Gate (`QualityGate`) verifying candidate video artifacts via `ffprobe` metadata checks, atomic publication (`publish_final()`), and safe video download endpoint.
  - **CP9**: Calm, restrained human-centric design system: single-prompt learning landing, honest demo mode notice, 6-stage linear lesson preparation progression, 16:9 native HTML5 video player, inline title renaming, accessible native delete dialog, and complete Vietnamese microcopy.
  - **CP10**: Local submission readiness, production startup honoring `$PORT` without reload, preflight filesystem & SQLite probe hardening, explicit runtime mode validation, and deployment documentation.


## Architecture

The production pipeline follows an audio-first, deterministic rendering and assembly flow:
```text
topic
→ planning (Gemini structured planner or Demo planner)
→ validation (plan semantic & pedagogical rules)
→ TTS (Edge TTS narration audio synthesis)
→ audio-first timeline (ResolvedTimeline with padding & subtitle cues)
→ rendering (CP5 deterministic visual renderers for each scene)
→ assembly (VideoAssembler concatenating visuals, audio & subtitles into final.pending.mp4)
→ QualityGate (ffprobe verification: duration, dimensions, stream codecs, file integrity)
→ atomic final publication (rename final.pending.mp4 -> final.mp4)
```

## Runtime Modes

LearnFlow AI supports exactly three pipeline modes (`LEARNFLOW_PIPELINE_MODE`):

1. **REAL (`LEARNFLOW_PIPELINE_MODE=real`, default)**:
   - Gemini planner for structured lesson generation.
   - If `GEMINI_API_KEY` is absent or unconfigured, server starts normally and jobs fail safely with `planner_not_configured` at the `PLANNING` stage. No silent fallback to demo or fake mode.
   - Edge TTS for natural multi-language voice narration.
   - Real visual renderers (Pillow + FFmpeg).
   - Real video assembler with burned subtitles.
   - Real Quality Gate verification.
   - Produces authenticated `final.mp4` artifact.

2. **DEMO (`LEARNFLOW_PIPELINE_MODE=demo`)**:
   - Explicitly selected via `LEARNFLOW_PIPELINE_MODE=demo`.
   - Prevalidated supported lesson plans (e.g. TCP 3-way handshake, Photosynthesis, RAM vs SSD).
   - Unsupported arbitrary topics strictly raise `demo_topic_not_available` (no synthetic hallucinated plans).
   - **NO** Gemini API key or external LLM calls required.
   - Real TTS synthesis, real audio-first timeline, real deterministic visual renderers, real FFmpeg video assembly, and real Quality Gate verification.
   - Produces authenticated `final.mp4` artifact.

3. **FAKE (`LEARNFLOW_PIPELINE_MODE=fake`)**:
   - Explicitly selected via `LEARNFLOW_PIPELINE_MODE=fake`.
   - CP2 lifecycle and queue progression testing only.
   - No real media generation or FFmpeg processing.
   - *Fake mode is NOT the production product pipeline.*

## FFmpeg Requirements

LearnFlow AI rendering and video assembly require FFmpeg and ffprobe binaries on the host system:
- **ffmpeg**: 4.4+ with H.264 (`libx264`) encoder support.
- **ffprobe**: Installed and discoverable in `PATH`.
- **DejaVu Sans font**: Or equivalent TrueType sans-serif font for Vietnamese Unicode subtitle & text rendering.

## Setup & Local Development

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   # Set GEMINI_API_KEY if running in REAL mode, or set LEARNFLOW_PIPELINE_MODE=demo
   ```

4. Run the development server with live reload:
   ```bash
   npm run dev
   # Runs: uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
   ```

## Production Start

Production startup strictly honors the hosting platform's `$PORT` environment variable (falling back to port 8000) and disables auto-reload:

```bash
npm start
# Runs: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Or directly via Uvicorn:
```bash
PORT=8000 uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Verify service liveness (does not require external API keys or video generation):
```bash
curl http://127.0.0.1:8000/healthz
# Response: {"status":"ok"}
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8000` | Port for production server binding |
| `LEARNFLOW_PIPELINE_MODE` | `real` | Runtime pipeline mode (`real`, `demo`, `fake`) |
| `LEARNFLOW_DB_PATH` | `learnflow.db` | Path to SQLite database file |
| `ARTIFACTS_DIR` | `artifacts` | Directory for storing job artifacts and video outputs |
| `GEMINI_API_KEY` | `""` | Google Gemini API key for structured lesson planning |
| `GEMINI_PLANNER_MODEL` | `gemini-3.8-flash` | Gemini model for lesson planning |
| `SPEECH_PROVIDER` | `edge` | Voice synthesis provider (`edge`) |
| `TTS_VOICE_VI` | `vi-VN-NamMinhNeural` | Edge TTS Vietnamese voice identifier |
| `TTS_VOICE_EN` | `en-US-GuyNeural` | Edge TTS English voice identifier |
| `ENABLE_IMAGE_GENERATION` | `false` | Enable AI illustration generation |
| `IMAGE_PROVIDER` | `none` | Image provider (`none` or `gemini`) |
| `GEMINI_IMAGE_MODEL` | `gemini-3.1-flash-image` | Gemini model for image generation |
| `RENDER_PROFILE` | `production` | Render profile (`production` for 1080p, `test` for fast 360p) |

## Preflight Verification

Run the local environment diagnostics:
```bash
python scripts/preflight.py
```
Preflight validates Python runtime, required packages, FFmpeg, ffprobe, libx264, writable artifacts directory, SQLite operations, and Vietnamese font rendering using clean isolated probes. It never makes automated paid API calls or network calls.

Optional manual Gemini connectivity check (only when key is set):
```bash
python scripts/preflight.py --check-gemini
```

## Local Submission Verification

Before packaging for submission, run the test suite and build verification:
```bash
# Run all automated tests
pytest -q

# Run build verification harness
npm run build

# Run local environment preflight check
python scripts/preflight.py
```

## Post-submission VibeHost validation

> **Important**: The real VibeHost environment is only available after submission. VibeHost capabilities are not verified until after submission. Do not claim persistent filesystem guaranteed, FFmpeg guaranteed, or background worker guaranteed before actual deployment.

The following checklist must be validated on the deployed VibeHost instance post-submission:

- [ ] `NOT VERIFIED`: FFmpeg available?
- [ ] `NOT VERIFIED`: ffprobe available?
- [ ] `NOT VERIFIED`: libx264 available?
- [ ] `NOT VERIFIED`: Gemini outbound HTTPS works?
- [ ] `NOT VERIFIED`: Edge TTS outbound HTTPS works?
- [ ] `NOT VERIFIED`: SQLite survives restart?
- [ ] `NOT VERIFIED`: artifacts survive restart?
- [ ] `NOT VERIFIED`: background worker survives a full ~60-second lesson?
- [ ] `NOT VERIFIED`: real final.mp4 plays/downloads?
- [ ] `NOT VERIFIED`: mobile UI works on deployed URL?
