# V3-97 — Upload-backed original React FE integration

The original uploaded frontend (including the **four mascot PNGs**, **Gemini product film** and **opening MP4**) is *not* present in this source branch yet. Do not describe the PR as a complete website until it has been imported, built, committed and browser-tested.

The source artifact is learnflow_FE_BE_integrated_V3-96.zip (SHA256 66a11a7348811337b236c33fe37497fa6a28b0a30ae588c86e8e445cff1b4aa7). The import tool refuses other ZIPs, zip-slip, symlinks, duplicates, decompression bombs and overwriting existing content.

1. Put the provided ZIP into the checkout and run:

   `python scripts/import_v3_97_frontend_zip.py --zip /path/to/learnflow_FE_BE_integrated_V3-96.zip`

2. `cd frontend/learnflow-landing && npm install && npm run test:contract && npm run build && cd ../..`
3. `python scripts/import_v3_97_frontend_zip.py --install-dist`
4. Local development only: `LEARNFLOW_REACT_LANDING=1 LEARNFLOW_PIPELINE_MODE=demo uvicorn app.main:app --host 127.0.0.1 --port 8000`.
5. Test `http://127.0.0.1:8000/`, `/healthz`, `POST /api/jobs`, job status polling and the MP4 player. The normal `/api/jobs` pipeline uses existing backend routes. The **V3-96 GPT-6** endpoint is developer-only and **OFF by default**; use explicit paid consent in its separately guarded form. **No automatic fallback/retry**.

The new React landing is opt-in and disabled outside `development` and `test`. When disabled, the historical Jinja site and API remain unchanged. No `main` merge or production deploy. No new model requests in this change.

**Gate:** bridge code can PASS independently. FE commit/build/E2E remains **BLOCKED** until the real uploaded FE source/media reach the repository and CI confirms they function together. Human pedagogical quality remains UNRATED.
