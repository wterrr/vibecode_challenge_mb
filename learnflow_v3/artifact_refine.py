"""V3-14 bounded, source-certified local ArtifactRefine with fail-closed rollback.

Only restores one compromised renderer-owned *track* from a last-good baseline.
No model/critic/LLM supplies executable code or replacement coordinates.
Reuses V2 content hashes, V3-11 temporal proof and actual decoded H264 QA.
Re-encodes whole clip, so does NOT claim incremental video reuse.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from learnflow_v2.repair import compute_content_hash
from .models import SemanticContractError,V3Model
from .temporal_geometry import (
    TemporalLayoutPlan,TemporalTrack,TemporalGeometryCertificate,
    certify_temporal_layout,verify_temporal_certificate,
)
from .temporal_demo_renderer import (
    TemporalRenderEvidence,render_certified_temporal_demo,verify_temporal_render,
)

VERSION="v3-14-local-track-restore-v1"
DOWNSTREAM=("TEMPORAL_GEOMETRY_CERTIFICATE","RENDERED_H264","DECODED_FRAME_QA","V3_12_PUBLICATION_REVIEW")
NONLOCAL_ROUTES={
    "FACTUAL_SOURCE_MISMATCH":"RESEARCH_ORCHESTRATION",
    "SCRIPT_CUE_MISMATCH":"SCRIPT_AGENT",
    "PEDAGOGICAL_ALIGNMENT":"PEDAGOGY_AGENT",
    "SEMANTIC_VISUAL_MISMATCH":"VISUAL_DIRECTOR",
    "STYLE_INCONSISTENCY":"VISUAL_DIRECTOR",
    "VISUAL_LEGIBILITY":"VISUAL_DIRECTOR",
}


def _hash(model:V3Model)->str:
    return compute_content_hash(model.model_dump(mode="json"))


def _block(reason:str):
    raise SemanticContractError("V3_14_"+reason)


class LocalRepairIntent(V3Model):
    version:Literal["v3-14-local-track-restore-v1"]=VERSION
    case_id:str=Field(min_length=1,max_length=80)
    defect_category:Literal[
        "TEMPORAL_OCCLUSION","SUBTITLE_INTRUSION","FRAME_CLIPPING",
        "TEXT_OVERFLOW","EXCESSIVE_MOTION",
    ]
    target_track_id:str=Field(min_length=1,max_length=80)
    operation:Literal["RESTORE_LAST_CERTIFIED_TRACK"]="RESTORE_LAST_CERTIFIED_TRACK"
    baseline_plan_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    candidate_plan_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    expected_bad_track_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    trusted_source:Literal["AUTHOR_SEEDED_CERTIFIED_SNAPSHOT"]="AUTHOR_SEEDED_CERTIFIED_SNAPSHOT"
    max_attempts:Literal[1]=1
    reviewer_authority:Literal[False]=False
    release_authority:Literal[False]=False


class DeferredRepair(V3Model):
    category:Literal[
        "FACTUAL_SOURCE_MISMATCH","SCRIPT_CUE_MISMATCH",
        "PEDAGOGICAL_ALIGNMENT","SEMANTIC_VISUAL_MISMATCH",
        "STYLE_INCONSISTENCY","VISUAL_LEGIBILITY",
    ]
    owner:Literal[
        "RESEARCH_ORCHESTRATION","SCRIPT_AGENT","PEDAGOGY_AGENT","VISUAL_DIRECTOR"]
    status:Literal["OWNER_REVIEW_REQUIRED"]="OWNER_REVIEW_REQUIRED"
    geometry_patch_applied:Literal[False]=False
    publication_blocked:Literal[True]=True

    @model_validator(mode="after")
    def _route(self):
        if NONLOCAL_ROUTES[self.category]!=self.owner:
            raise ValueError("V3_14_UNSAFE_ROUTING")
        return self


def defer_nonlocal_issue(category:str)->DeferredRepair:
    if category not in NONLOCAL_ROUTES:
        _block("NONLOCAL_CATEGORY_NOT_SUPPORTED")
    return DeferredRepair(category=category,owner=NONLOCAL_ROUTES[category])


class LocalRefineResult(V3Model):
    version:Literal["v3-14-local-track-restore-v1"]=VERSION
    case_id:str
    status:Literal["LOCAL_REPAIR_VERIFIED","ROLLBACK_BLOCKED"]
    reason:str=Field(min_length=1,max_length=140)
    baseline_plan_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    input_plan_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    verified_output_plan_sha256:str|None=None
    initial_video_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    repaired_video_sha256:str|None=None
    altered_track_ids:tuple[str,...]
    untouched_track_ids:tuple[str,...]
    untouched_tracks_stable:Literal[True]=True
    invalidated_downstream:tuple[str,...]
    full_video_reencoded:bool
    frame_count_reencoded:int=Field(strict=True,ge=0)
    attempts:Literal[1]=1
    production_patch_applied:Literal[False]=False
    rollback_original_preserved:Literal[True]=True
    publication_blocked:Literal[True]=True
    real_human_repair_gain:Literal["UNMEASURED"]="UNMEASURED"
    result_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _coherent(self):
        if self.status=="LOCAL_REPAIR_VERIFIED":
            if (self.verified_output_plan_sha256!=self.baseline_plan_sha256 or
                self.repaired_video_sha256 is None or
                not self.full_video_reencoded or self.frame_count_reencoded<=0 or
                len(self.altered_track_ids)!=1 or
                self.invalidated_downstream!=DOWNSTREAM):
                raise ValueError("V3_14_INVALID_SUCCESS_CLAIM")
        else:
            if (self.repaired_video_sha256 is not None or
                self.verified_output_plan_sha256 is not None or
                self.full_video_reencoded or self.frame_count_reencoded):
                raise ValueError("V3_14_BLOCKED_MUST_NOT_CLAIM_RENDER")
        if self.result_sha256!=compute_content_hash(
            self.model_dump(mode="json",exclude={"result_sha256"})
        ):
            raise ValueError("V3_14_RESULT_SHA_FORGED")
        return self


def _result(intent,base,initial,*,success,reason,target=(),stable=(),video=None,frames=0):
    raw={
        "version":VERSION,"case_id":intent.case_id,
        "status":"LOCAL_REPAIR_VERIFIED" if success else "ROLLBACK_BLOCKED",
        "reason":reason,
        "baseline_plan_sha256":_hash(base),
        "input_plan_sha256":_hash(initial),
        "verified_output_plan_sha256":_hash(base) if success else None,
        "initial_video_sha256":"", # set externally from trusted evidence
        "repaired_video_sha256":video if success else None,
        "altered_track_ids":target,"untouched_track_ids":stable,
        "untouched_tracks_stable":True,
        "invalidated_downstream":DOWNSTREAM if success else (),
        "full_video_reencoded":bool(success),
        "frame_count_reencoded":frames if success else 0,
        "attempts":1,"production_patch_applied":False,
        "rollback_original_preserved":True,"publication_blocked":True,
        "real_human_repair_gain":"UNMEASURED",
    }
    return raw


def refine_single_track(*,intent:LocalRepairIntent,baseline:TemporalLayoutPlan,
                        baseline_certificate:TemporalGeometryCertificate,
                        baseline_evidence:TemporalRenderEvidence,
                        baseline_video_path:str|Path,candidate:TemporalLayoutPlan,
                        output_path:str|Path)->LocalRefineResult:
    """Restore ONLY compromised track, then independently certify and H264-decode.

    Original plan/certificate/MP4 are never mutated. We reject ambiguous source
    (multiple changed tracks), forged intent hashes, no-op, missing pristine
    source, and unsafe output. Any post-render failure removes only output we
    just created and remains blocked. No auto-approve.
    """
    orig=Path(baseline_video_path)
    dest=Path(output_path)
    if dest.exists() or dest.is_symlink() or dest.resolve()==orig.resolve():
        _block("OUTPUT_DESTINATION_UNSAFE")
    verify_temporal_render(plan=baseline,certificate=baseline_certificate,
                           evidence=baseline_evidence,video_path=orig)
    original_digest=hashlib.sha256(orig.read_bytes()).hexdigest()
    if (intent.baseline_plan_sha256!=_hash(baseline) or
        intent.candidate_plan_sha256!=_hash(candidate)):
        _block("STALE_PLAN_FINGERPRINT")
    bs={t.object_id:t for t in baseline.tracks}
    cs={t.object_id:t for t in candidate.tracks}
    if set(bs)!=set(cs) or len(bs)!=len(cs):
        _block("OBJECT_IDENTITY_DRIFT")
    if intent.target_track_id not in bs:
        _block("TARGET_NOT_IN_TRUSTED_PLAN")
    if any(getattr(candidate,k)!=getattr(baseline,k) for k in (
        "layout_id","source_ref","width","height","fps","frame_count",
        "edge_inset","subtitle_band","text_padding",
        "max_simultaneously_moving","max_pixels_per_frame")):
        _block("GLOBAL_SEMANTIC_OR_LAYOUT_DRIFT")
    if tuple(t.object_id for t in candidate.tracks)!=tuple(t.object_id for t in baseline.tracks):
        _block("REORDERED_SCENE_OBJECTS")
    target=intent.target_track_id
    if intent.expected_bad_track_sha256!=_hash(cs[target]):
        _block("BAD_TRACK_FINGERPRINT_MISMATCH")
    altered=tuple(k for k in bs if _hash(bs[k])!=_hash(cs[k]))
    if altered!=(target,):
        _block("SILENT_NOOP_OR_MULTI_TRACK_MUTATION")
    stable=tuple(k for k in bs if k!=target)
    if any(_hash(bs[k])!=_hash(cs[k]) for k in stable):
        _block("NON_TARGET_HASH_CHANGED")
    # Prove the bad plan is actually rejected by the original V3-11 oracle.
    try:
        certify_temporal_layout(candidate)
    except (SemanticContractError,ValueError):
        pass
    else:
        _block("CANDIDATE_NOT_PROVEN_DEFECTIVE")
    raw=_result(intent,baseline,candidate,success=False,
                reason="DEPENDENT_QA_OR_RENDER_NOT_COMPLETE",
                target=altered,stable=stable)
    raw["initial_video_sha256"]=original_digest
    created=False
    try:
        data=candidate.model_dump(mode="json")
        replacements={t.object_id:t.model_dump(mode="json") for t in baseline.tracks}
        data["tracks"]=[
            replacements[target] if track["object_id"]==target else track
            for track in data["tracks"]
        ]
        restored=TemporalLayoutPlan.model_validate(data)
        if _hash(restored)!=_hash(baseline):
            _block("LOCAL_RESTORE_NOT_EQUAL_TO_CERTIFIED_SOURCE")
        if any(_hash(x)!=_hash(y) for x,y in zip(restored.tracks,baseline.tracks,strict=True)):
            _block("UNTOUCHED_TRACK_IDENTITY_VIOLATED")
        cert=certify_temporal_layout(restored)
        verify_temporal_certificate(plan=restored,candidate=cert)
        evidence=render_certified_temporal_demo(
            plan=restored,certificate=cert,output_path=dest)
        created=True
        verify_temporal_render(plan=restored,certificate=cert,evidence=evidence,video_path=dest)
        if hashlib.sha256(orig.read_bytes()).hexdigest()!=original_digest:
            _block("ORIGINAL_VIDEO_MODIFIED")
        raw=_result(intent,baseline,candidate,success=True,
                    reason="ONE_TRACK_RESTORED_AND_REPLAY_CERTIFIED",
                    target=altered,stable=stable,
                    video=evidence.video_sha256,frames=restored.frame_count)
        raw["initial_video_sha256"]=original_digest
    except Exception:
        # Only this function's fresh output is eligible for rollback. Never
        # touch the pristine input; never delete any pre-existing destination.
        if created:
            dest.unlink(missing_ok=True)
        if hashlib.sha256(orig.read_bytes()).hexdigest()!=original_digest:
            _block("ORIGINAL_ARTIFACT_INTEGRITY_LOST")
    raw["result_sha256"]=compute_content_hash(raw)
    return LocalRefineResult.model_validate(raw)


def intent_for_seeded_defect(*,case_id:str,baseline:TemporalLayoutPlan,
                             candidate:TemporalLayoutPlan,target_track_id:str,
                             defect_category:str)->LocalRepairIntent:
    target=next((t for t in candidate.tracks if t.object_id==target_track_id),None)
    if target is None:
        _block("UNKNOWN_TRACK")
    return LocalRepairIntent(
        case_id=case_id,defect_category=defect_category,
        target_track_id=target_track_id,
        baseline_plan_sha256=_hash(baseline),
        candidate_plan_sha256=_hash(candidate),
        expected_bad_track_sha256=_hash(target),
    )


def verify_refine_result(*,candidate:LocalRefineResult,
                         replay:LocalRefineResult)->None:
    # Comparison is useful only when replay was independently computed from
    # source files in an isolated fixture run. A self-hash alone is never enough.
    if candidate.model_dump(mode="json")!=replay.model_dump(mode="json"):
        _block("REHASHED_OR_STALE_REPAIR_AUDIT")
