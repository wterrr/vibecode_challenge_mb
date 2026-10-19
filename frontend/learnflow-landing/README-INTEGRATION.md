# LearnFlow — integrated React FE + existing FastAPI backend (V3-96)

This replaces the uploaded FE's **local storyboard simulation** with real backend job actions. The supplied Gemini introduction, product movie, four mascots, theme, and interactives remain intact. The historical LearnFlow app/backend repository is **not** included in this ZIP and is not overwritten by these files.

## A. Development (two processes, one API origin to browser)

1. Clone/open the existing private LearnFlow repository at `wterrr/vibecode_challenge_mb`, at the verified V3-96 branch `chatgpt/v3-96-real-browser-gpt-ui-proof` (or a reviewed descendant). Start backend exactly as documented by that repository. Example:

   ```bash
   cd /path/to/vibecode_challenge_mb
   # use your existing backend virtual environment and install requirements
   LEARNFLOW_PIPELINE_MODE=demo uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

2. Start this frontend (Node >=20):

   ```bash
   cd /path/to/learnflow-landing
   npm install
   npm run dev
   ```

   Open `http://localhost:5173/`. Vite transparently proxies `/api/*` and `/healthz` to port 8000. **Do not put any Gemini or OpenRouter key in VITE_* variables**.

3. Type a prompt and click the arrow: the browser creates `POST /api/jobs`, polls `GET /api/jobs/{id}`, and shows `GET /api/jobs/{id}/video` if and only if published by backend. The `#library` section lists real jobs and can open or delete terminal jobs. The job ID persists in localStorage to recover after a reload.

4. To test **real legacy generation**, use `LEARNFLOW_PIPELINE_MODE=real` and configure a valid server-side `GEMINI_API_KEY`. Without it, the backend will reject the planner stage; the FE will expose the failed job rather than invent a video. Demo mode requires the demo-supported topics listed in the backend repo. **V3-96 GPT is not the normal `/api/jobs` pipeline**.

## B. Single website on FastAPI port 8000

Build the frontend and install it into the backend checkout (install script changes only `app/main.py`, adds `app/web/react_landing.py`, and copies `dist` to `app/static/landing`):

```bash
cd /path/to/learnflow-landing
npm install
npm run build
python backend_bridge/install_into_backend.py --backend /path/to/vibecode_challenge_mb --dry-run
python backend_bridge/install_into_backend.py --backend /path/to/vibecode_challenge_mb
cd /path/to/vibecode_challenge_mb
LEARNFLOW_REACT_LANDING=1 LEARNFLOW_PIPELINE_MODE=demo uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Visit `http://127.0.0.1:8000/`: new React website with native `/api` calls, served from the backend's existing `/static` mount. Existing server pages `/create`, `/library`, `/jobs/{id}` remain available, but new React landing has an integrated library. If `LEARNFLOW_REACT_LANDING` is unset or `0`, the original backend Jinja homepage is served. The original `app/main.py` is backed up to `app/main.py.before-react-landing` on first install. When updating the FE, rebuild and rerun the install script. Built files should be installed in your deployment image; Vite/npm are not required at runtime.

## C. V3-96 local GPT developer preview (explicit paid mode only)

This is an **opt-in separate backend endpoint**. It is not a general video generator. Its known supported question family is *3 × 4 ↔ 4 × 3, 12 persistent squares*, in English. For local-only development:

Backend environment:

```bash
LEARNFLOW_PIPELINE_MODE=demo
LEARNFLOW_V3_GPT_ARRAY_PREVIEW=true
OPENROUTER_API_KEY=<set-on-server-only>
# Backend environment must be development/test, request must come from loopback.
```

Frontend `.env.local`:

```
VITE_ENABLE_LOCAL_GPT_PREVIEW=true
```

Refresh FE, open **Tùy chọn bài học**, choose GPT preview mode, enter a supported English prompt of at least 35 characters, explicitly check *paid consent*, then submit **once**. The browser calls `POST /api/v3/ai/array-preview` and plays a verified private MP4 only on HTTP success. The backend reserves at most one provider attempt **per process**, not a durable worldwide billing limit. The FE must not silently fallback or retry after timeout. Changing backend mode, restarting the server, or redeploying can reset backend limits. Not for public production traffic.

## Contracts and scope

- `GET /healthz` is only a connectivity check, not evidence that the model provider or renderer is configured.
- `POST /api/jobs` accepts `{topic, audience, language: "vi"|"en", target_duration_seconds: 60|90|120, visual_style: "clean"}`, returns HTTP 202 + `job_id`.
- `GET /api/jobs/{id}` has `status`, `stage`, `progress_percent`, `error`, `video_url`.
- `GET /api/jobs?limit=30` returns actual stored jobs; `DELETE /api/jobs/{id}` only allows terminal jobs.
- The landing's Gemini product movie and interactive showcases are illustrative. They are **not** passed off as newly generated job videos.
- This frontend does not add authentication, ownership checks, per-user quota, rate limiting, queue persistence, user payments, arbitrary V3 research capability or human pedagogical approval. **Do not expose these job endpoints publicly without production security review.**
- Public release and 3Blue1Brown-level equivalence remain **not verified**. Existing production constraints and separate V3 developer gates stay intact.
