"""V3-18 developer-only guarded adapter on the EXISTING app pipeline instance.

The app's JobRunner and V2 job API still call process() on the original
LearningVideoPipeline. The explicitly enabled local preview route invokes
preview_binary_search() on that SAME pipeline wrapper. No second job queue,
publication, TTS, LLM provider, fallback card, or privileged production path.
"""
from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
import shutil
import uuid

from app.pipeline.base import LearningVideoPipeline,StageCallback
from app.domain.jobs import Job
from app.storage.base import ArtifactStore
from learnflow_v3.integration_slice import (
    IntegratedClipReceipt,select_renderer,run_integrated_binary_clip,
    verify_integrated_binary_clip,
)
from learnflow_v3.offline_lesson_source import build_binary_lesson_source
from learnflow_v3.sequence_renderer import SequenceRenderProfile


class V3PreviewRejected(ValueError):
    """A controlled ABSTAIN or invalid developer-only input; no card fallback."""


class V3OfflinePreviewPipeline(LearningVideoPipeline):
    """Opt-in *wrapper*, not a new production render path or job processor."""

    def __init__(self,*,legacy:LearningVideoPipeline,artifacts:ArtifactStore):
        self.legacy=legacy
        self.artifacts=artifacts
        self.requires_published_artifact=legacy.requires_published_artifact
        self._preview_lock=asyncio.Lock()

    async def process(self,job:Job,on_stage:StageCallback)->None:
        # Preserve the original JobRunner and pipeline lifecycle exactly.
        await self.legacy.process(job,on_stage)

    async def preview_binary_search(
        self,*,values:tuple[int,...],target:int,family:str="WORKED_EXAMPLE_BOARD",
    )->dict:
        decision=select_renderer(family)
        if decision.status!="SELECTED_BY_INTEGRATION_ADAPTER":
            raise V3PreviewRejected(
                f"{decision.status}: {decision.reason}; no CONCEPT_CARD fallback"
            )
        if (
            not isinstance(target,int) or isinstance(target,bool) or
            any(not isinstance(v,int) or isinstance(v,bool) for v in values)
            or not 3<=len(values)<=12
            or any(abs(v)>1000000 for v in values)
            or abs(target)>1000000 or tuple(sorted(values))!=values
        ):
            raise V3PreviewRejected("INVALID_BINARY_SOURCE: sorted bounded integers required")
        async with self._preview_lock:
            return await asyncio.to_thread(
                self._preview_sync,values=values,target=target
            )

    def _preview_sync(self,*,values:tuple[int,...],target:int)->dict:
        # All output remains under the existing Artifacts store. NO final.mp4,
        # no ArtifactStore.publish_final and no public download URL.
        token="v3offline"+uuid.uuid4().hex
        base=self.artifacts.get_job_dir(token,create=True)
        try:
            source=build_binary_lesson_source(values=values,target=target)
            profile=SequenceRenderProfile(
                width=640,height=360,fps=12,seconds_per_step=.75
            )
            receipt=run_integrated_binary_clip(
                source=source,out_dir=base,profile=profile
            )
            if not isinstance(receipt,IntegratedClipReceipt):
                raise V3PreviewRejected("ABSTAIN_NO_RENDERER_NO_FALLBACK")
            verify_integrated_binary_clip(
                source=source,out_dir=base,profile=profile,receipt=receipt
            )
            video=base/receipt.output_name
            if (not video.is_file() or video.is_symlink() or
                hashlib.sha256(video.read_bytes()).hexdigest()!=receipt.assembled_video_sha256):
                raise RuntimeError("V3_PREVIEW_VIDEO_PROOF_FAILED")
            # Validate signed manifest from disk; not just a success return.
            if not (base/"integrated_binary_lesson.receipt.json").is_file():
                raise RuntimeError("V3_PREVIEW_RECEIPT_MISSING")
            assert receipt.publication=="PUBLISH_BLOCKED"
            assert receipt.web_pipeline_connected is False  # still an offline renderer
            assert receipt.audio=="NOT_GENERATED"
            return {
                "status":"OFFLINE_PREVIEW_QA_PASS_NOT_PUBLISHED",
                "preview_id":token,
                "renderer_family":receipt.renderer_family,
                "representation":receipt.representation,
                "frame_count":receipt.frame_count,
                "width":receipt.width,"height":receipt.height,"fps":receipt.fps,
                "source_trace_sha256":receipt.trace_sha256,
                "source_route_sha256":receipt.route_sha256,
                "manifest_sha256":receipt.report_sha256,
                "assembled_video_sha256":receipt.assembled_video_sha256,
                "decoded_rgb_sha256":receipt.decoded_assembly_rgb_sha256,
                "beat_ids":list(receipt.downstream_beat_ids),
                "claim_ids":list(receipt.downstream_claim_refs),
                "object_ids":list(receipt.downstream_object_ids),
                "deferred_signal_count":len(receipt.deferred_signals),
                "qa":receipt.qa,
                "publication":"PUBLISH_BLOCKED",
                "public_video_url":None,
                "human_quality":"UNMEASURED",
                "audio":"NOT_GENERATED",
                "production_renderer_registered":False,
            }
        except Exception:
            # Do not leave stale partially assembled clips or leaked receipts.
            shutil.rmtree(base,ignore_errors=True)
            raise
