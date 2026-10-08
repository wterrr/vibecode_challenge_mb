"""V3 Integration Closure: real OFFLINE source → route → render → assemble → QA.

Integrates the existing certified Binary Search renderer with a real timeline
and H264 assembler. NO golden scripts, tests, LLM calls, TTS, live service
routing, production publication, or claim of a complete voiced lesson.

V3-04's honest SELECTED_UNRENDERABLE means its *own* boundary is semantic
only; this adapter is a distinct, explicit, source-replayed dispatch proof.
Other families ABSTAIN, no CONCEPT_CARD fallback.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Literal

from pydantic import Field,model_validator

from learnflow_v2.repair import compute_content_hash
from .beat_grounding import compile_binary_beat_manifest,verify_binary_beat_video
from .binary_search_trace import certify_and_route_binary_search
from .models import RepresentationType,SemanticContractError,V3Model
from .offline_lesson_source import BinaryLessonSource
from .publication_gate import review_binary_publication
from .sequence_renderer import SequenceRenderProfile,render_certified_binary_search_video
from .signal_preservation import audit_signal_preservation
from .release_gate import _rgb_stream_sha256

VERSION="v3-integration-closure-v1"
SUPPORTED={"WORKED_EXAMPLE_BOARD":"STATEFUL_SEQUENCE_BINARY_SEARCH"}
UNCONNECTED=frozenset(("PROCESS_FLOW","EQUATION_GRAPH","STATE_MACHINE",
                        "CONCEPT_CARD","CODE_WALKTHROUGH","FUNCTION_GRAPH",
                        "EQUATION_DERIVATION","TEMPORAL_GEOMETRY_DEMO"))


def _block(msg):
    raise SemanticContractError("V3_INTEGRATION_"+msg)


class DispatchDecision(V3Model):
    version:Literal["v3-integration-closure-v1"]=VERSION
    family:str
    status:Literal["SELECTED_BY_INTEGRATION_ADAPTER","ABSTAIN_UNCONNECTED_FAMILY",
                   "ABSTAIN_INVALID_TOPOLOGY"]
    renderer:Literal["STATEFUL_SEQUENCE_BINARY_SEARCH"]|None=None
    fallback_to_card:Literal[False]=False
    production_registered:Literal[False]=False
    reason:str

    @model_validator(mode="after")
    def _coherent(self):
        if self.status=="SELECTED_BY_INTEGRATION_ADAPTER":
            if self.renderer!=SUPPORTED.get(self.family):
                raise ValueError("INTEGRATION_FORGED_RENDERER_SELECTED")
        elif self.renderer is not None:
            raise ValueError("INTEGRATION_ABSTENTION_CANNOT_RENDER")
        return self


class IntegratedClipReceipt(V3Model):
    version:Literal["v3-integration-closure-v1"]=VERSION
    status:Literal["OFFLINE_BOUND_BINARY_CLIP_NOT_PRODUCTION"]="OFFLINE_BOUND_BINARY_CLIP_NOT_PRODUCTION"
    representation:Literal["WORKED_EXAMPLE_BOARD"]="WORKED_EXAMPLE_BOARD"
    selected_variant:Literal["TRACE_SPOTLIGHT","TRACE_COMPACT"]
    renderer_family:Literal["STATEFUL_SEQUENCE_BINARY_SEARCH"]="STATEFUL_SEQUENCE_BINARY_SEARCH"
    route_status_at_v3_04:Literal["SELECTED_UNRENDERABLE"]="SELECTED_UNRENDERABLE"
    scene_id:str
    lesson_id:str
    source_hashes:dict[str,str]
    trace_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    route_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    source_beat_manifest_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    source_signal_audit_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    deferred_signals:tuple[str,...]
    downstream_claim_refs:tuple[str,...]
    downstream_object_ids:tuple[str,...]
    downstream_beat_ids:tuple[str,...]
    timeline:tuple[dict,...]
    stages:tuple[str,...]
    scene_video_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    assembled_video_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    decoded_scene_rgb_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    decoded_assembly_rgb_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    frame_count:int=Field(gt=0)
    width:int=Field(gt=0)
    height:int=Field(gt=0)
    fps:int=Field(gt=0)
    output_name:str
    audio:Literal["NOT_GENERATED"]="NOT_GENERATED"
    real_narration_alignment:Literal["UNMEASURED"]="UNMEASURED"
    global_visual_signal_consumption:Literal["PARTIAL_DECLARED_DEFERRED"]="PARTIAL_DECLARED_DEFERRED"
    qa:Literal["BOUNDED_SOURCE_AND_DECODED_PIXEL_PASS"]="BOUNDED_SOURCE_AND_DECODED_PIXEL_PASS"
    publication:Literal["PUBLISH_BLOCKED"]="PUBLISH_BLOCKED"
    web_pipeline_connected:Literal[False]=False
    independent_human_review:Literal["UNMEASURED"]="UNMEASURED"
    report_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _hash(self):
        if self.decoded_scene_rgb_sha256!=self.decoded_assembly_rgb_sha256:
            raise ValueError("INTEGRATION_ASSEMBLED_PIXELS_CHANGED")
        if self.report_sha256!=compute_content_hash(
            self.model_dump(mode="json",exclude={"report_sha256"})):
            raise ValueError("INTEGRATION_RECEIPT_HASH_CHANGED")
        if not self.deferred_signals:
            raise ValueError("INTEGRATION_CANNOT_CLAIM_ALL_SIGNALS_CONSUMED")
        if self.stages!=(
            "SOURCE_ORACLE_CERTIFIED","V3_SEMANTIC_SIGNAL_AUDITED",
            "V3_PATTERN_ROUTED","INTEGRATION_RENDERER_DISPATCHED",
            "SCENE_H264_RENDERED","BEAT_FRAME_QA_REPLAYED",
            "TIMELINE_ASSEMBLED","ALL_ASSEMBLED_RGB_PIXELS_MATCHED",
            "V3_PUBLICATION_REVIEW_BLOCKED",
        ):
            raise ValueError("INTEGRATION_STAGE_ORDER_DRIFT")
        return self


def select_renderer(family:str|RepresentationType,*,scenegraph=None)->DispatchDecision:
    """The only connected renderer is binary sequence, NOT a universal factory."""
    name=family.value if isinstance(family,RepresentationType) else str(family)
    if name in SUPPORTED:
        return DispatchDecision(family=name,status="SELECTED_BY_INTEGRATION_ADAPTER",
                                renderer=SUPPORTED[name],
                                reason="BOUNDED_BINARY_SOURCE_AND_TRACE_REQUIRED")
    if name=="PROCESS_FLOW" and scenegraph is not None:
        # Reuse V3-07 DAG predicate to avoid a V3-04 router/renderer cycle mismatch.
        from .code_process_renderer import layout_process
        try:
            layout_process(scenegraph)
        except SemanticContractError:
            return DispatchDecision(family=name,status="ABSTAIN_INVALID_TOPOLOGY",
                                    reason="V3_07_PROCESS_TOPOLOGY_CANNOT_RENDER")
    return DispatchDecision(family=name,status="ABSTAIN_UNCONNECTED_FAMILY",
                            reason="NO_INTEGRATED_RENDERER_NOT_CONCEPT_CARD")


def _run_ffmpeg(args:list[str],reason:str)->None:
    try:
        p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=80)
    except (OSError,subprocess.TimeoutExpired) as exc:
        _block(reason+"_TOOL_FAILED")
    if p.returncode:
        _block(reason+"_FFMPEG_FAILED")


def _sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_source_consumption(*,source:BinaryLessonSource,beats,signal):
    """Declares partial source consumption, with strict visual-critical fields."""
    plan=source.plan
    if len(plan.sections)!=1 or plan.sections[0].hero_candidate:
        _block("HERO_BUDGET_UNIMPLEMENTED")
    if plan.constraints.cognitive_load_tier!="MEDIUM":
        _block("COGNITIVE_LOAD_TIER_UNIMPLEMENTED")
    if tuple(b.beat_id for b in plan.beats)!=tuple(x.beat_id for x in beats.beats):
        _block("BEAT_ID_LOST")
    if tuple({z for x in plan.beats for z in x.claim_refs}) and not set(
        z for x in plan.beats for z in x.claim_refs
    )<=set(z for x in beats.beats for z in x.claim_refs):
        _block("CLAIM_LOST")
    if tuple(o.object_id for o in source.pattern.semantic_objects)!=beats.beats[0].target_object_ids:
        _block("OBJECT_ID_LOST")
    if not signal.declared_unconsumed_paths:
        _block("DEFERRED_VISUAL_SIGNALS_MUST_BE_AUDITED")
    # The legacy semantic-gate-only V3-03 is NOT magically "render_ready".
    if signal.render_ready:
        _block("FALSE_GLOBAL_RENDER_READY")
    return tuple(sorted(signal.declared_unconsumed_paths))


def run_integrated_binary_clip(*,source:BinaryLessonSource,out_dir:Path,
                              profile:SequenceRenderProfile,
                              adapter_enabled:bool=True,
                              fault_inject:str|None=None)->IntegratedClipReceipt|DispatchDecision:
    """Exactly one offline scene, explicit video-only assembly (no fake narration).

    Atomic link-to-final after all source replays; any failure removes only
    this execution's temp files; preexisting final/receipt never overwritten.
    """
    out=Path(out_dir)
    if not out.is_dir() or out.is_symlink():_block("OUTPUT_DIRECTORY_UNSAFE")
    final=out/"integrated_binary_lesson.mp4"
    receipt_file=out/"integrated_binary_lesson.receipt.json"
    if final.exists() or final.is_symlink() or receipt_file.exists() or receipt_file.is_symlink():
        _block("DESTINATION_EXISTS_NO_CLOBBER")
    if not adapter_enabled:
        return DispatchDecision(family="WORKED_EXAMPLE_BOARD",
                                status="ABSTAIN_UNCONNECTED_FAMILY",
                                reason="INTEGRATION_ADAPTER_NOT_REGISTERED")
    decision=select_renderer(source.pattern.pattern_type)
    if decision.status!="SELECTED_BY_INTEGRATION_ADAPTER":return decision
    # Independently certify trace/ledger, ALL V2 & V3 cross-artifact relations.
    proof=certify_and_route_binary_search(trace=source.trace,**source.params())
    route=proof.route
    if route.status.value!="SELECTED_UNRENDERABLE" or route.selected_variant not in (
        "TRACE_SPOTLIGHT","TRACE_COMPACT"
    ) or route.representation!=source.pattern.pattern_type:
        _block("V3_04_ROUTE_NOT_CERTIFIED")
    signal=audit_signal_preservation(
        **source.params(),verified_trace_refs=(source.trace.query.source_ref,)
    )
    beat_manifest=compile_binary_beat_manifest(
        trace=source.trace,**source.params(),profile=profile)
    deferred=_assert_source_consumption(source=source,beats=beat_manifest,signal=signal)
    stages=(
        "SOURCE_ORACLE_CERTIFIED","V3_SEMANTIC_SIGNAL_AUDITED",
        "V3_PATTERN_ROUTED","INTEGRATION_RENDERER_DISPATCHED",
        "SCENE_H264_RENDERED","BEAT_FRAME_QA_REPLAYED",
        "TIMELINE_ASSEMBLED","ALL_ASSEMBLED_RGB_PIXELS_MATCHED",
        "V3_PUBLICATION_REVIEW_BLOCKED",
    )
    with tempfile.TemporaryDirectory(prefix=".v3-integration-",dir=out) as sandbox:
        work=Path(sandbox)
        scene=work/"certified_scene.mp4"
        assembled=work/"assembled.mp4"
        render=render_certified_binary_search_video(
            trace=source.trace,**source.params(),profile=profile,output_path=scene)
        verified=verify_binary_beat_video(
            trace=source.trace,**source.params(),manifest=beat_manifest,
            video_evidence=render,video_path=scene,profile=profile)
        if verified.observable_coverage!=1.0:
            _block("BEAT_COVERAGE_FAILED")
        if fault_inject=="AFTER_SCENE_CREATED":
            _block("INJECTED_FAILURE_AFTER_SCENE")
        # 1-scene start=0 to end=frame_count; remux through genuine FFmpeg
        # assembly rather than equating standalone render with final output.
        _run_ffmpeg([
            "ffmpeg","-nostdin","-hide_banner","-v","error","-y",
            "-i",str(scene),"-map","0:v:0","-c:v","copy","-an",
            "-map_metadata","-1","-movflags","+faststart",str(assembled),
        ],"ASSEMBLY")
        if fault_inject=="AFTER_ASSEMBLY_CREATED":
            _block("INJECTED_FAILURE_AFTER_ASSEMBLY")
        count=beat_manifest.frame_count
        scene_rgb=_rgb_stream_sha256(
            video=scene,width=profile.width,height=profile.height,count=count)
        final_rgb=_rgb_stream_sha256(
            video=assembled,width=profile.width,height=profile.height,count=count)
        if scene_rgb!=final_rgb:_block("ASSEMBLED_FRAME_STREAM_NOT_IDENTICAL")
        pub=review_binary_publication(
            trace=source.trace,**source.params(),manifest=beat_manifest,
            video_evidence=render,video_path=scene,profile=profile)
        if (pub.publication_status!="PUBLISH_BLOCKED" or
            pub.deterministic_status.value!="DETERMINISTIC_PASS" or
            pub.production_release_executed):
            _block("PUBLICATION_GUARD_NOT_REPLAYED")
        source_hashes=signal.source_hashes|{
            "trace":source.trace.trace_sha256,
            "beat_manifest":beat_manifest.manifest_sha256,
            "renderer_scene":render.video_sha256,
            "review":pub.review_sha256,
        }
        contents=dict(
            version=VERSION,status="OFFLINE_BOUND_BINARY_CLIP_NOT_PRODUCTION",
            representation="WORKED_EXAMPLE_BOARD",selected_variant=route.selected_variant,
            renderer_family=decision.renderer,
            route_status_at_v3_04=route.status.value,
            scene_id=source.scenegraph.scene_id,lesson_id=source.plan.lesson_id,
            source_hashes=source_hashes,
            trace_sha256=source.trace.trace_sha256,route_sha256=route.decision_hash,
            source_beat_manifest_sha256=beat_manifest.manifest_sha256,
            source_signal_audit_sha256=signal.audit_hash,
            deferred_signals=deferred,
            downstream_claim_refs=tuple(dict.fromkeys(
                claim for b in beat_manifest.beats for claim in b.claim_refs)),
            downstream_object_ids=beat_manifest.beats[0].target_object_ids,
            downstream_beat_ids=tuple(b.beat_id for b in beat_manifest.beats),
            timeline=tuple({
                "beat_id":b.beat_id,"script_segment_id":b.script_segment_ref,
                "claim_refs":list(b.claim_refs),
                "object_ids":list(b.target_object_ids),
                "start_frame":b.frame_start,"end_frame_exclusive":b.frame_end_exclusive,
            } for b in beat_manifest.beats),
            stages=stages,scene_video_sha256=render.video_sha256,
            assembled_video_sha256=_sha(assembled),
            decoded_scene_rgb_sha256=scene_rgb,decoded_assembly_rgb_sha256=final_rgb,
            frame_count=count,width=profile.width,height=profile.height,fps=profile.fps,
            output_name=final.name,
        )
        # Populate all immutable safety defaults before computing hash.
        preliminary=IntegratedClipReceipt.model_construct(**contents)
        data=preliminary.model_dump(mode="json",exclude={"report_sha256"})
        receipt=IntegratedClipReceipt.model_validate(
            data|{"report_sha256":compute_content_hash(data)})
        staged=work/"receipt.json"
        staged.write_text(json.dumps(receipt.model_dump(mode="json"),
                                      indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        created=False
        try:
            os.link(assembled,final)
            created=True
            if fault_inject=="AFTER_FINAL_VIDEO_LINKED":
                _block("INJECTED_FAILURE_AFTER_LINK")
            os.link(staged,receipt_file)
        except Exception:
            if created:final.unlink(missing_ok=True)
            raise
    return receipt


def verify_integrated_binary_clip(*,source:BinaryLessonSource,
                                  out_dir:Path,
                                  profile:SequenceRenderProfile,
                                  receipt:IntegratedClipReceipt)->None:
    """Independent source QA and full decoded pixel replay of final video."""
    out=Path(out_dir)
    f=out/receipt.output_name
    if not f.is_file() or f.is_symlink() or _sha(f)!=receipt.assembled_video_sha256:
        _block("STALE_OR_MUTATED_ASSEMBLED_VIDEO")
    if receipt.source_hashes["trace"]!=source.trace.trace_sha256:
        _block("STALE_SOURCE_TRACE")
    route=certify_and_route_binary_search(trace=source.trace,**source.params()).route
    if route.decision_hash!=receipt.route_sha256:
        _block("STALE_SOURCE_ROUTE")
    beat=compile_binary_beat_manifest(trace=source.trace,**source.params(),profile=profile)
    if beat.manifest_sha256!=receipt.source_beat_manifest_sha256:
        _block("STALE_BEAT_OR_CLAIM")
    audit=audit_signal_preservation(**source.params(),
        verified_trace_refs=(source.trace.query.source_ref,))
    if audit.audit_hash!=receipt.source_signal_audit_sha256:
        _block("STALE_SEMANTIC_SIGNAL")
    if (tuple(b.beat_id for b in beat.beats)!=receipt.downstream_beat_ids or
        beat.beats[0].target_object_ids!=receipt.downstream_object_ids or
        tuple(dict.fromkeys(c for b in beat.beats for c in b.claim_refs))!=receipt.downstream_claim_refs):
        _block("BOUND_IDENTITIES_LOST")
    if _rgb_stream_sha256(video=f,width=profile.width,height=profile.height,
                          count=beat.frame_count)!=receipt.decoded_assembly_rgb_sha256:
        _block("STALE_DECODED_PIXEL_EVIDENCE")
    disk=IntegratedClipReceipt.model_validate_json(
        (out/"integrated_binary_lesson.receipt.json").read_text(encoding="utf-8"))
    if disk!=receipt:_block("MUTATED_RECEIPT_ON_DISK")
