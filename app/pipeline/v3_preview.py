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

    async def preview_narrated_binary_search(
        self,*,values:tuple[int,...],target:int,family:str="WORKED_EXAMPLE_BOARD",
        event_aligned:bool=False,
    )->dict:
        decision=select_renderer(family)
        if decision.status!="SELECTED_BY_INTEGRATION_ADAPTER":
            raise V3PreviewRejected(
                f"{decision.status}: {decision.reason}; no CONCEPT_CARD fallback"
            )
        if (
            not isinstance(target,int) or isinstance(target,bool) or
            any(not isinstance(v,int) or isinstance(v,bool) for v in values)
            or not 3<=len(values)<=12 or
            any(abs(v)>1000000 for v in values) or
            abs(target)>1000000 or tuple(sorted(values))!=values
        ):
            raise V3PreviewRejected("INVALID_BINARY_SOURCE: sorted bounded integers required")
        async with self._preview_lock:
            return await asyncio.to_thread(self._narrated_sync,values=values,target=target,
                                           event_aligned=event_aligned)

    def _narrated_sync(self,*,values:tuple[int,...],target:int,
                       event_aligned:bool=False)->dict:
        # Uses existing app ArtifactStore and explicit private preview owner;
        # never publishes final.mp4 or changes a durable legacy job status.
        from learnflow_v3.narrated_lesson import build_narrated_lesson
        token="v3narrated"+uuid.uuid4().hex
        base=self.artifacts.get_job_dir(token,create=True)
        try:
            source=build_binary_lesson_source(values=values,target=target)
            receipt=build_narrated_lesson(source=source,out=base,event_aware=event_aligned)
            video=base/"narrated_binary_lesson.mp4"
            if not video.is_file() or video.is_symlink() or (
                hashlib.sha256(video.read_bytes()).hexdigest()!=receipt.video_sha256
            ):
                raise RuntimeError("V3_19_NARRATED_MP4_NOT_VERIFIED")
            if not (base/"narrated_binary_lesson.receipt.json").is_file():
                raise RuntimeError("V3_19_NARRATED_RECEIPT_MISSING")
            if event_aligned:
                from learnflow_v3.narrated_lesson import verify_narrated_lesson
                verify_narrated_lesson(source=source,folder=base,receipt=receipt)
                if not (base/"narrated_binary_lesson.event_proof.json").is_file():
                    raise RuntimeError("V3_20_EVENT_BOUNDARY_PROOF_MISSING")
            return {
                "event_boundary_alignment":receipt.event_boundary_alignment,
                "event_proof_sha256":receipt.event_proof_sha256,
                "semantic_event_count":len(receipt.segments) if event_aligned else None,
                "lexical_transcript_as_heard":"UNMEASURED",
                "status":("OFFLINE_EVENT_ALIGNED_QA_PASS_NOT_PUBLISHED" if event_aligned
                          else "OFFLINE_NARRATED_PREVIEW_QA_PASS_NOT_PUBLISHED"),
                "preview_id":token,"renderer_family":"STATEFUL_SEQUENCE_BINARY_SEARCH",
                "source_trace_sha256":receipt.source_trace_sha256,
                "manifest_sha256":receipt.report_sha256,
                "video_sha256":receipt.video_sha256,
                "subtitle_sha256":receipt.subtitle_sha256,
                "duration_seconds":receipt.duration_seconds,
                "frame_count":receipt.total_frames,
                "scene_count":len(receipt.segments),
                "scene_ids":[s["scene_id"] for s in receipt.segments],
                "beat_ids":[s["beat_id"] for s in receipt.segments],
                "claim_ids":["claim-01"],"object_ids":["array-01"],
                "audio_codec":receipt.audio_codec,
                "video_codec":receipt.video_codec,
                "audio_origin":receipt.speech_origin,
                "segment_alignment":receipt.segment_alignment,
                "word_alignment":receipt.word_alignment,
                "human_quality":"UNMEASURED",
                "publication":"PUBLISH_BLOCKED",
                "public_video_url":None,
            }
        except Exception:
            shutil.rmtree(base,ignore_errors=True)
            raise


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
