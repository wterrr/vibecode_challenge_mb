# PRD — LearnFlow AI (AI Learning Video Studio)
## Product Requirements Document for VibeCode Challenge

### 1. Overview & Vision
**LearnFlow AI** transforms any learning question or topic into a clear, short, narrated educational video with synchronized visual concept cards, diagrams, and comparisons.

### 2. Core Value Proposition
- **Domain General Planning**: Takes any educational topic (e.g. computer science protocols, biology, hardware architecture, economics).
- **Constrained Visual Primitives**: Uses trusted, deterministic renderers (concept cards, process diagrams, comparisons, illustrations) rather than unconstrained, error-prone code generation.
- **Audio-First Timeline**: Audio narration length drives scene timing for perfectly synchronized pacing.
- **Quality Verification**: Final candidate videos pass rigorous quality gate checks before publication.

### 3. Target Audience & Personas
- Students learning complex topics visually.
- Developers needing quick conceptual refreshers (e.g. TCP Handshake, Concurrency).
- Educators creating modular micro-learning content.

### 4. User Inputs & Configuration
- **Topic** (Required): 3–500 characters.
- **Audience**: Beginner (default), Student, Developer, Professional.
- **Language**: `vi` (Vietnamese, default), `en` (English).
- **Target Duration**: 60s, 90s (default), 120s.
- **Visual Style**: `clean`.

### 5. Technical Requirements (VibeCode CP0-CP11)
- **Runtime**: Single Python 3.11+ runtime with FastAPI.
- **Database**: Local SQLite with WAL mode.
- **Media Engine**: FFmpeg / FFprobe with H.264 (libx264) and AAC encoding.
- **Speech Engine**: Edge-TTS default (remote, no GPU needed).
- **Planning Engine**: Google Gemini structured JSON planning (gemini-3.8-flash).
- **Rendering**: Pure Pillow + FFmpeg composition; optional Manim / Gemini image generation.
- **Client**: Responsive web UI accessible on desktop and mobile (>= 360px).
