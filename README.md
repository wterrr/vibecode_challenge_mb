# LearnFlow AI — AI Learning Video Studio

LearnFlow AI transforms educational questions and learning topics into concise, structured, narrated videos with synchronized concept cards, process diagrams, comparisons, and illustrations.

## Current Status
- **Phase**: Implemented through CP6 — Optional Gemini Image Provider + Illustration Fallback.
- **Implemented**:
  - CP0: Runtime configuration, capability detection, preflight diagnostics, and healthz.
  - CP1: SQLite schema, Job entity lifecycle, atomic repository, and transactional storage.
  - CP2: Job creation API, async queue worker, Web UI, and artifact storage using `FakePipeline`.
  - CP3: Structured lesson planning via Gemini Interactions API, JSON schema validation, and repair loops.
  - CP4: Edge TTS voice synthesis, audio metadata extraction, and audio-first timeline synchronization.
  - CP5: Deterministic Pillow + FFmpeg visual renderers (`ConceptCard`, `ProcessDiagram`, `Comparison`, `Illustration`), typography line fitting, long-token wrapping, and progressive state allocation.
  - CP6: Optional Gemini image generation (`GeminiImageProvider`, `gemini-3.1-flash-image`), aspect-ratio preserving composition, and robust deterministic illustration fallback.
- **Application Pipeline**: The FastAPI application and background worker currently run with `FakePipeline` (CP2 behavior preserved). Real pipeline wiring is deferred to CP7.
- **Deferred to Later Checkpoints**: Quality Gate & Live Pipeline Assembly (CP7-CP8).

## System Requirements
- **Python**: 3.11+
- **FFmpeg**: 4.4+ with H.264 (`libx264`) encoder
- **FFprobe**: Installed and available in `PATH`
- **Pillow**: With DejaVu Sans or safe system sans font
- **Manim**: Optional (not required for critical path)

## Setup & Installation

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
   # Edit .env to set GEMINI_API_KEY if testing Gemini connectivity
   ```

## Running Preflight Verification

Run the environment diagnostics:
```bash
python scripts/preflight.py
```

To optionally test Gemini API connectivity (if `GEMINI_API_KEY` is configured):
```bash
python scripts/preflight.py --check-gemini
```

## Running the Server

Start the development server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify health check:
```bash
curl http://127.0.0.1:8000/healthz
# Response: {"status":"ok"}
```

## Running Tests

Run the test suite:
```bash
pytest -q
```

## Roadmap & Architecture
See `PLAN.md` for the authoritative implementation plan and checkpoints CP0–CP11.
