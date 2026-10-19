"""V3-95 explicitly enabled, local-only paid GPT educational VIDEO preview.

A separate developer endpoint intentionally does NOT silently replace
/api/jobs, does not create durable production jobs and never publishes final.mp4.
Single paid consent for each request plus one process-wide attempt permit.
"""
from __future__ import annotations
import logging
from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field

router=APIRouter(prefix="/api/v3/ai",tags=["v3-gpt-developer-only"])
log=logging.getLogger(__name__)

class GptArrayPreviewRequest(BaseModel):
    query:str=Field(min_length=35,max_length=300)
    language:str=Field(default="en",pattern="^en$")
    paid_consent:bool=False

def dev_guard(request:Request):
    st=request.app.state.settings
    if (not st.v3_gpt_array_preview_enabled or
        st.environment.strip().lower() not in ("test","development")):
        raise HTTPException(status_code=404,detail="V3 GPT preview disabled")
    host=request.client.host if request.client else None
    if host not in ("testclient","127.0.0.1","::1","localhost"):
        raise HTTPException(status_code=403,detail="Local developer only")
    from app.pipeline.v3_preview import V3OfflinePreviewPipeline
    pipeline=request.app.state.pipeline
    if not isinstance(pipeline,V3OfflinePreviewPipeline):
        raise HTTPException(status_code=503,detail="V3 preview pipeline not enabled")
    return pipeline

@router.post("/array-preview",status_code=200)
async def create_array_video(payload:GptArrayPreviewRequest,request:Request)->dict:
    pipeline=dev_guard(request)
    from app.pipeline.v3_preview import V3PreviewRejected
    try:
        return await pipeline.preview_gpt_array(
            query=payload.query,paid_consent=payload.paid_consent)
    except V3PreviewRejected as exc:
        # 422/409 distinguish out-of-topic vs already-spent process permit.
        msg=str(exc)
        code=409 if "ATTEMPT_PER_PROCESS" in msg else 422
        raise HTTPException(status_code=code,detail=msg) from None
    except Exception as exc:
        log.error("V395 local GPT native preview denied (%s)",type(exc).__name__)
        raise HTTPException(status_code=502,detail=
            "V395 provider/semantic/media verification failed; no video published") from None

@router.get("/array-preview/{preview_id}/video")
def get_array_video(preview_id:str,request:Request)->FileResponse:
    pipeline=dev_guard(request)
    if len(preview_id)!=39 or not preview_id.startswith("v395gpt"):
        raise HTTPException(status_code=404,detail="Unknown private preview")
    try:
        movie=pipeline.get_gpt_preview_video(preview_id)
    except Exception:
        movie=None
    if movie is None:
        raise HTTPException(status_code=404,detail="No verified developer video")
    return FileResponse(movie,media_type="video/mp4",filename="learnflow-v395-preview.mp4")
