"""V3-18 guarded developer-only HTTP *receipt* API.

No MP4 endpoint is exposed. All requests use the SAME app.state.pipeline built
by the established app.pipeline.factory and wrapped behind OFF-by-default flag.
No job SUCCEEDED, no public final.mp4, no model/TTS network service called.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field,StrictInt


log=logging.getLogger(__name__)
router=APIRouter(prefix="/api/v3/offline",tags=["v3-offline-preview"])


class BinaryPreviewInput(BaseModel):
    family:str=Field(default="WORKED_EXAMPLE_BOARD",min_length=3,max_length=36)
    values:tuple[StrictInt,...]=Field(min_length=3,max_length=12)
    target:StrictInt


@router.post("/binary-search",status_code=200)
async def offline_binary_search(payload:BinaryPreviewInput,request:Request)->dict:
    settings=request.app.state.settings
    if (not settings.v3_binary_preview_enabled or
        settings.environment.strip().lower() not in ("test","development")):
        raise HTTPException(status_code=404,detail="V3 offline preview is disabled")
    client_host=request.client.host if request.client else None
    if client_host not in ("testclient","127.0.0.1","::1","localhost"):
        raise HTTPException(status_code=403,detail="Local developer request required")
    # Delay V3 renderer imports until AFTER all OFF/nonlocal gates.
    from app.pipeline.v3_preview import V3OfflinePreviewPipeline,V3PreviewRejected
    pipeline=request.app.state.pipeline
    if not isinstance(pipeline,V3OfflinePreviewPipeline):
        raise HTTPException(status_code=503,detail="V3 adapter not installed")
    try:
        return await pipeline.preview_binary_search(
            family=payload.family,values=payload.values,target=payload.target
        )
    except V3PreviewRejected as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from None
    except Exception as exc:
        # Fail closed: no renderer stacktrace/paths or capability escalation.
        log.error("V3 preview failed closed (%s)",type(exc).__name__)
        raise HTTPException(
            status_code=500,
            detail="V3 preview was rejected by source/renderer/QA; nothing published",
        ) from None


@router.post("/binary-search-lesson",status_code=200)
async def offline_narrated_binary_lesson(payload:BinaryPreviewInput,request:Request)->dict:
    """Developer-only narrated lesson. Never registers a public video URL."""
    settings=request.app.state.settings
    if (not settings.v3_binary_preview_enabled or
        not settings.v3_narrated_lesson_enabled or
        settings.environment.strip().lower() not in ("test","development")):
        raise HTTPException(status_code=404,detail="V3 narrated lesson disabled")
    client_host=request.client.host if request.client else None
    if client_host not in ("testclient","127.0.0.1","::1","localhost"):
        raise HTTPException(status_code=403,detail="Local developer request required")
    from app.pipeline.v3_preview import V3OfflinePreviewPipeline,V3PreviewRejected
    pipeline=request.app.state.pipeline
    if not isinstance(pipeline,V3OfflinePreviewPipeline):
        raise HTTPException(status_code=503,detail="V3 adapter unavailable")
    try:
        return await pipeline.preview_narrated_binary_search(
            values=payload.values,target=payload.target,family=payload.family)
    except V3PreviewRejected as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from None
    except Exception as exc:
        log.error("V3-19 narrated QA fail-closed (%s)",type(exc).__name__)
        raise HTTPException(
            status_code=500,
            detail="V3 narrated preview was blocked by source/audio/timeline/QA; not published",
        ) from None



@router.post("/binary-search-event-aligned",status_code=200)
async def offline_event_aligned_binary_lesson(payload:BinaryPreviewInput,request:Request)->dict:
    """Explicit local developer V3-20 route with physical utterance boundaries.

    Returns *only* checked receipt, never video bytes/URL or publication.
    """
    settings=request.app.state.settings
    if (not settings.v3_binary_preview_enabled or
        not settings.v3_narrated_lesson_enabled or
        not settings.v3_event_alignment_enabled or
        settings.environment.strip().lower() not in ("test","development")):
        raise HTTPException(status_code=404,detail="V3-20 local event alignment disabled")
    client_host=request.client.host if request.client else None
    if client_host not in ("testclient","127.0.0.1","::1","localhost"):
        raise HTTPException(status_code=403,detail="Local developer request required")
    from app.pipeline.v3_preview import V3OfflinePreviewPipeline,V3PreviewRejected
    pipeline=request.app.state.pipeline
    if not isinstance(pipeline,V3OfflinePreviewPipeline):
        raise HTTPException(status_code=503,detail="V3 adapter unavailable")
    try:
        return await pipeline.preview_narrated_binary_search(
            values=payload.values,target=payload.target,
            family=payload.family,event_aligned=True)
    except V3PreviewRejected as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from None
    except Exception as exc:
        log.error("V3-20 event alignment failed closed (%s)",type(exc).__name__)
        raise HTTPException(
            status_code=500,
            detail="V3-20 source/speech/event/video QA blocked; nothing published",
        ) from None
