# V3-18 — Product Pipeline Integration, source-bound Binary Search HTTP preview

**Scope:** Stacked PR #52 on PR #51 exact parent 749861073f26cc0367ec101c7c63eaecef4e0d1b. Never merge main, frozen V2 Core unchanged. Local developer-only HTTP/MP4 proof; no paid model, human participant, deployment or video publication. Final-head CI pending.

## Audited entrypoint and selected seam

- Existing normal route: app/main.py create_app → app/pipeline/factory.py create_pipeline → app.state.pipeline → app/runner/job_runner.py; /api/jobs creates durable jobs and requires published final.mp4 for successful real runs. Publishing an unauthorized V3 clip here would violate V3-12 and V3-17.
- Other active V2D route: lesson_pipeline/coordinator.py → lesson_pipeline/core.py CapabilityCoreGateway → frozen V2. This route is left untouched to avoid parallel live orchestration or bypassing protected Core.
- V3-18 instead wraps the original LearningVideoPipeline ONLY with explicit developer feature flag enabled. The wrapped process(job,on_stage) delegates directly to original FakePipeline/RealVideoPipeline; app.state.runner.pipeline IS app.state.pipeline, with unchanged legacy jobs/retries. The same factory instance offers preview_binary_search() as a guarded capability. There is no second queue or live model orchestration. The developer-only HTTP route POST /api/v3/offline/binary-search uses that same app.state.pipeline. No video-serving/download URL is exposed.
- LEARNFLOW_V3_BINARY_PREVIEW defaults OFF; no expensive V3 imports on the OFF request path. Only environment=test/development can enable; production flag is fatal, remote clients denied. Feature flag is NOT permission for public publishing.

## Actual intended source→pixel proof (not a golden script)

HTTP JSON family WORKED_EXAMPLE_BOARD, bounded sorted values and target → learnflow_v3.offline_lesson_source.build_binary_lesson_source(values,target) → existing V3-05 oracle and V2/V3 canonical source contracts → V3-03 explicit source/deferred signal audit → V3-04 original semantic-only route SELECTED_UNRENDERABLE → V3 Integration Closure explicit binary renderer adapter → V3-06 genuine H264 scene → V3-10 decoded pixel beat QA → real FFmpeg video-only one-scene assembly → full decoded RGB parity → V3-12 PUBLISH_BLOCKED source replay. Receipt covers hashes for original trace, route, beat/claim/object IDs, full decoded stream, output H264 and stated deferred semantic signals. Unsupported family (Process, Code, Math, State Machine or Concept Card) ABSTAINS HTTP 422; never substitutes a card.

Pipeline uses existing ArtifactStore root for an opaque local preview ID. It never writes final.mp4 or final.pending.mp4, never invokes ArtifactStore.publish_final(), never marks a job SUCCEEDED and never adds a public playback route. HTTP response contains only machine-readable QA/source/video hashes and no path or URL. On source/render/QA failure, cleanup deletes only private preview directory; staged renderer output remains no-clobber.

## Changed files and verification

- app/config.py, app/pipeline/factory.py: opt-in guarded decorator of original pipeline; OFF legacy factory unchanged.
- app/pipeline/v3_preview.py: V3 preview capability on existing pipeline object with async thread offload, bounded input, full-source MP4 QA and failure cleanup; process(job,on_stage) remains V2.
- app/api/v3_offline.py, app/main.py: localhost/test-only first-party FastAPI route with strict guarded status and source inputs. Rejects unsupported/untrusted, hides errors and never serves video.
- tests/v3/test_product_pipeline_integration.py: real TestClient invoking create_app and actual factory, actual H264/ffprobe/receipt, flag OFF vs ON, original job API, production denial, remote peer rejection, unsupported family, malformed input, late partial writes, forged source mutation and no-public-video claim.
- scripts/verify_v3_product_pipeline.py: posts a distinct array and target via actual HTTP entrypoint and independently replays the generated source, H264 and receipt. CI artifact includes MP4 + verified JSON only; private SQLite and preview cache deleted.
- .github/workflows/v3-product-pipeline-integration.yml: full V3 tests and original app/CRUD/fake/real pipeline regressions, frozen V2/Hermes/prereg/Bench/Core Freeze plus real HTTP MP4 evidence.

## Explicit NO-CLAIM and remaining work

This is a single ~3-second silent Binary Search developer preview. It is NOT the normal /api/jobs publishing route, a full 60/90/120 second learner video, narrated/TTS-aligned multi-scene timeline, real model planner, entire Code/Math/Process/State Machine registry, human quality study, C6/C7 real efficacy proof or authenticated production release. It proves product HTTP entrypoint reaches the same app pipeline factory and V3's offline renderer behind a default-OFF developer guard, not production readiness. The Hermes V2D coordinator is deliberately not altered. Keep PUBLISH_BLOCKED, no V2 Core or main merge. Exact code-head CI and final artifact evidence will be appended after measured execution.
