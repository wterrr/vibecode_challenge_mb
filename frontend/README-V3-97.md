# V3-97 — Original React FE integrated with V3-96 FastAPI

All 35 original supplied FE files have been committed: complete React source, four original mascots, two original videos, posters and same-origin API client. See `frontend/learnflow-landing/asset-manifest.sha256` for exact source-byte provenance.

To run one local website:

```bash
cd frontend/learnflow-landing
npm install
npm run test:contract
npm run build
cd ../..
python scripts/import_v3_97_frontend_zip.py --install-dist
LEARNFLOW_REACT_LANDING=1 LEARNFLOW_PIPELINE_MODE=demo uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Visit http://127.0.0.1:8000/. Vite builds into the real FastAPI static directory. React uses real `POST /api/jobs`, `GET /api/jobs/{id}`, `/video`, `GET /api/jobs` for the library, and `DELETE /api/jobs/{id}`. There is no mock storyboard fallback. Original `/create`, `/library`, `/jobs/{id}`, `/healthz` and every backend API remain intact. To restore historical homepage, set `LEARNFLOW_REACT_LANDING=0`.

For development with Vite, run `npm run dev` in FE and FastAPI separately at http://127.0.0.1:8000; Vite proxies backend API paths.

The CI runs: exact asset SHA256, node contract suite, npm production build, comparison of 8 compiled and original assets, FastAPI TestClient tests, real Chromium page and submit to fake pipeline on true same-origin HTTP. Fake means browser UI/BE wiring, **not** AI/model-based lesson creation. V3-96 live GPT proof remains separate and single semantic family only.

**Security:** React route is opt-in in development/test only; never enables paid GPT by itself. Neither this frontend nor backend currently supplies production-grade user auth, job authorization, durable limits or accepted broad-domain pedagogy. Therefore do not expose unauthenticated job endpoints publicly. No main merge or public production acceptance under this checkpoint.
