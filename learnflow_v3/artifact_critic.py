"""V3-13 bounded Artifact Critic: actual decoded pixel inputs, strict scoped issues.

Only a *candidate reviewer adapter*, not a deployed or independently validated
VLM. Reuses V2 critic taxonomy and V3-10/11 byte/source replay; no arbitrary
code, geometry writes, remote calls, or V3-12 publication permission.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Callable, Literal

from PIL import Image
from pydantic import Field, field_validator, model_validator

from learnflow_v2.repair import compute_content_hash
from .models import SemanticContractError, V3Model
from .sequence_renderer import SequenceRenderProfile
from .temporal_demo_renderer import _decode_exact_frame, verify_temporal_render
from .beat_grounding import verify_binary_beat_video
from .publication_gate import review_binary_publication, review_geometry_publication

VERSION="v3-13-artifact-critic-v1"
MAX_FRAME_SAMPLES=8
MAX_ISSUES=8
CATEGORY_OWNER={
    "VISUAL_LEGIBILITY":"VISUAL_DIRECTOR",
    "PEDAGOGICAL_ALIGNMENT":"PEDAGOGY_AGENT",
    "FACTUAL_SOURCE_MISMATCH":"RESEARCH_ORCHESTRATION",
    "SCRIPT_CUE_MISMATCH":"SCRIPT_AGENT",
    "SEMANTIC_VISUAL_MISMATCH":"VISUAL_DIRECTOR",
    "TEMPORAL_OCCLUSION":"CORE_REPAIR",
    "STYLE_INCONSISTENCY":"VISUAL_DIRECTOR",
}
SEVERITIES=("LOW","MEDIUM","HIGH","CRITICAL")


def _deny(reason):
    raise SemanticContractError("V3_13_"+reason)


class FrameEvidence(V3Model):
    frame_index:int=Field(strict=True,ge=0)
    timestamp_ms:int=Field(strict=True,ge=0)
    rgb_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    rgb_width:int=Field(strict=True,ge=320)
    rgb_height:int=Field(strict=True,ge=180)


class ArtifactReviewRequest(V3Model):
    version:Literal["v3-13-artifact-critic-v1"]=VERSION
    subject:Literal["CERTIFIED_BINARY_SEARCH","TEMPORAL_GEOMETRY_DEMO"]
    source_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    video_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    video_frame_count:int=Field(strict=True,gt=0)
    fps:int=Field(strict=True,ge=12,le=30)
    frame_samples:tuple[FrameEvidence,...]=Field(min_length=2,max_length=MAX_FRAME_SAMPLES)
    allowed_object_ids:tuple[str,...]=Field(min_length=1)
    approved_claim_ids:tuple[str,...]=()
    allowed_beat_ids:tuple[str,...]=()
    prior_deterministic_pass:Literal[True]=True
    actual_review_cost_usd:Literal[0.0]=0.0
    max_review_calls:Literal[1]=1
    source_replay_verified:Literal[True]=True

    @model_validator(mode="after")
    def _full(self):
        if sorted({x.frame_index for x in self.frame_samples})!=[x.frame_index for x in self.frame_samples]:
            raise ValueError("V3_13_FRAME_SAMPLE_DUPLICATE_OR_UNSORTED")
        if any(x.frame_index>=self.video_frame_count or
               x.timestamp_ms!=round(x.frame_index*1000/self.fps) for x in self.frame_samples):
            raise ValueError("V3_13_FRAME_TIME_MISMATCH")
        for seq in (self.allowed_object_ids,self.approved_claim_ids,self.allowed_beat_ids):
            if len(seq)!=len(set(seq)) or any(not x or not x.strip() for x in seq):
                raise ValueError("V3_13_SCOPE_IDENTITY_INVALID")
        return self


class ArtifactIssue(V3Model):
    issue_id:str=Field(min_length=1,max_length=80,pattern=r"^[a-z][a-z0-9_-]*$")
    category:Literal[
        "VISUAL_LEGIBILITY","PEDAGOGICAL_ALIGNMENT","FACTUAL_SOURCE_MISMATCH",
        "SCRIPT_CUE_MISMATCH","SEMANTIC_VISUAL_MISMATCH","TEMPORAL_OCCLUSION",
        "STYLE_INCONSISTENCY",
    ]
    severity:Literal["LOW","MEDIUM","HIGH","CRITICAL"]
    first_frame:int=Field(strict=True,ge=0)
    last_frame:int=Field(strict=True,ge=0)
    object_ids:tuple[str,...]=Field(min_length=1,max_length=10)
    evidence_frame_indices:tuple[int,...]=Field(min_length=1,max_length=MAX_FRAME_SAMPLES)
    evidence_rgb_sha256:tuple[str,...]=Field(min_length=1,max_length=MAX_FRAME_SAMPLES)
    claim_id:str|None=None
    beat_id:str|None=None
    confidence:float=Field(ge=0.0,le=1.0)
    rationale:str=Field(min_length=12,max_length=600)
    repair_route:Literal[
        "VISUAL_DIRECTOR","PEDAGOGY_AGENT","RESEARCH_ORCHESTRATION",
        "SCRIPT_AGENT","CORE_REPAIR",
    ]

    @field_validator("confidence",mode="before")
    @classmethod
    def _finite(cls,v):
        if type(v) not in (int,float) or not math.isfinite(v):
            raise ValueError("V3_13_CONFIDENCE_MUST_BE_FINITE")
        return float(v)

    @model_validator(mode="after")
    def _shape(self):
        if self.first_frame>self.last_frame:
            raise ValueError("V3_13_REVERSED_TIME_RANGE")
        if self.repair_route!=CATEGORY_OWNER[self.category]:
            raise ValueError("V3_13_REPAIR_ROUTE_MISMATCH")
        if len(self.evidence_frame_indices)!=len(self.evidence_rgb_sha256):
            raise ValueError("V3_13_FRAME_HASH_CARDINALITY")
        if len(self.object_ids)!=len(set(self.object_ids)):
            raise ValueError("V3_13_DUPLICATE_OBJECT_REF")
        if sorted(set(self.evidence_frame_indices))!=list(self.evidence_frame_indices):
            raise ValueError("V3_13_UNORDERED_EVIDENCE")
        if any(not s or not s.strip() for s in self.object_ids):
            raise ValueError("V3_13_BLANK_OBJECT")
        if self.confidence<0.5:
            raise ValueError("V3_13_BELOW_REVIEW_CONFIDENCE_FLOOR")
        return self


class ProposedCriticResponse(V3Model):
    request_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    issues:tuple[ArtifactIssue,...]=Field(default_factory=tuple,max_length=MAX_ISSUES)
    summary:str=Field(min_length=5,max_length=300)

    @model_validator(mode="after")
    def _identity(self):
        if len({i.issue_id for i in self.issues})!=len(self.issues):
            raise ValueError("V3_13_DUPLICATE_ISSUE_ID")
        return self


class CriticReviewResult(V3Model):
    version:Literal["v3-13-artifact-critic-v1"]=VERSION
    request_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    video_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    status:Literal[
        "CRITIC_UNAVAILABLE","CRITIC_REVIEW_REQUIRED","CRITIC_NO_ISSUES_UNVERIFIED",
        "CRITIC_REJECTED","DETERMINISTIC_QA_BLOCKED",
    ]
    reason:str=Field(min_length=1,max_length=120)
    findings:tuple[ArtifactIssue,...]=()
    reviewer_calls:int=Field(strict=True,ge=0,le=1)
    external_model_cost_usd:Literal[0.0]=0.0
    critic_pass_certified:Literal[False]=False
    publication_blocked:Literal[True]=True
    independent_human_quality:Literal["UNMEASURED"]="UNMEASURED"
    review_hash:str=Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _hash(self):
        if self.review_hash!=compute_content_hash(
            self.model_dump(mode="json",exclude={"review_hash"})
        ):
            raise ValueError("V3_13_REVIEW_CHECKSUM_INVALID")
        if self.findings and self.status!="CRITIC_REVIEW_REQUIRED":
            raise ValueError("V3_13_FINDINGS_WITHOUT_REVIEW")
        return self


def _make_result(*,request:ArtifactReviewRequest,status:str,reason:str,
                 findings=(),calls=0)->CriticReviewResult:
    fields={
        "version":VERSION,"request_sha256":compute_content_hash(request.model_dump(mode="json")),
        "video_sha256":request.video_sha256,"status":status,"reason":reason,
        "findings":tuple(i.model_dump(mode="json") for i in findings),
        "reviewer_calls":calls,"external_model_cost_usd":0.0,
        "critic_pass_certified":False,"publication_blocked":True,
        "independent_human_quality":"UNMEASURED",
    }
    fields["review_hash"]=compute_content_hash(fields)
    return CriticReviewResult.model_validate(fields)


def _validate_response(response:ProposedCriticResponse,request:ArtifactReviewRequest):
    if response.request_sha256!=compute_content_hash(request.model_dump(mode="json")):
        _deny("FOREIGN_OR_STALE_REVIEW_REQUEST")
    samples={s.frame_index:s.rgb_sha256 for s in request.frame_samples}
    objects=set(request.allowed_object_ids)
    claims=set(request.approved_claim_ids)
    beats=set(request.allowed_beat_ids)
    for issue in response.issues:
        if issue.last_frame>=request.video_frame_count:
            _deny("ISSUE_OUTSIDE_VIDEO")
        if not set(issue.object_ids).issubset(objects):
            _deny("INVENTED_OBJECT_ID")
        if issue.claim_id is not None and issue.claim_id not in claims:
            _deny("UNAPPROVED_CLAIM")
        if issue.beat_id is not None and issue.beat_id not in beats:
            _deny("INVENTED_BEAT_ID")
        for frame,sha in zip(issue.evidence_frame_indices,issue.evidence_rgb_sha256,strict=True):
            if not issue.first_frame<=frame<=issue.last_frame:
                _deny("EVIDENCE_OUTSIDE_ISSUE_WINDOW")
            if samples.get(frame)!=sha:
                _deny("INVENTED_FRAME_OR_RGB_HASH")
        if issue.category in ("FACTUAL_SOURCE_MISMATCH","SCRIPT_CUE_MISMATCH") and issue.claim_id is None:
            _deny("FACT_OR_CUE_ISSUE_MISSING_CLAIM")
    return response.issues


def _sample_indices(frame_count:int)->tuple[int,...]:
    return tuple(sorted({0,frame_count//5,2*frame_count//5,
                         3*frame_count//5,4*frame_count//5,frame_count-1}))


def _extract_video_frames(video_path:Path,profile:SequenceRenderProfile,frame_count:int):
    frames=[]
    for idx in _sample_indices(frame_count):
        rgb=_decode_exact_frame(video_path,idx,profile)
        frames.append(FrameEvidence(
            frame_index=idx,timestamp_ms=round(idx*1000/profile.fps),
            rgb_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(),
            rgb_width=profile.width,rgb_height=profile.height,
        ))
    return tuple(frames)


def _file_hash(path:Path)->str:
    if not path.is_file() or path.is_symlink():
        _deny("MISSING_OR_SYMLINK_VIDEO")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binary_request(*,trace,plan,pattern,ledger,registry,script,storyboard,scenegraph,
                   manifest,video_evidence,video_path:str|Path,profile)->ArtifactReviewRequest:
    verified=verify_binary_beat_video(
        trace=trace,plan=plan,pattern=pattern,ledger=ledger,registry=registry,
        script=script,storyboard=storyboard,scenegraph=scenegraph,
        manifest=manifest,video_evidence=video_evidence,video_path=video_path,profile=profile)
    if verified.status!="RENDERED_SYNTHETIC_BEAT_GROUNDING_PASS":
        _deny("BINARY_REPLAY_NOT_PASS")
    objects=tuple(sorted({object_id for b in manifest.beats
                          for object_id in b.target_object_ids}))
    claims=tuple(sorted({claim for b in manifest.beats for claim in b.claim_refs}))
    return ArtifactReviewRequest(
        subject="CERTIFIED_BINARY_SEARCH",source_sha256=manifest.manifest_sha256,
        video_sha256=_file_hash(Path(video_path)),video_frame_count=manifest.frame_count,
        fps=profile.fps,frame_samples=_extract_video_frames(Path(video_path),profile,manifest.frame_count),
        allowed_object_ids=objects,approved_claim_ids=claims,
        allowed_beat_ids=tuple(b.beat_id for b in manifest.beats),
    )


def geometry_request(*,plan,certificate,evidence,video_path:str|Path)->ArtifactReviewRequest:
    verify_temporal_render(plan=plan,certificate=certificate,
                           evidence=evidence,video_path=video_path)
    profile=SequenceRenderProfile(width=plan.width,height=plan.height,fps=plan.fps)
    return ArtifactReviewRequest(
        subject="TEMPORAL_GEOMETRY_DEMO",source_sha256=certificate.source_hash,
        video_sha256=_file_hash(Path(video_path)),video_frame_count=plan.frame_count,
        fps=plan.fps,frame_samples=_extract_video_frames(Path(video_path),profile,plan.frame_count),
        allowed_object_ids=tuple(t.object_id for t in plan.tracks),
    )


def run_artifact_critic(
    request:ArtifactReviewRequest,*,reviewer:Callable[[ArtifactReviewRequest],object]|None=None
)->CriticReviewResult:
    """Offline reviewer interface, one call max; never a real model trust claim.

    A reviewer may propose issues only. Even 0 issues never becomes CRITIC_PASS.
    Exceptions/malformed/out-of-scope findings make status REJECTED, not PASS.
    """
    if reviewer is None:
        return _make_result(request=request,status="CRITIC_UNAVAILABLE",
                            reason="NO_CONNECTED_AUTHORIZED_ARTIFACT_REVIEWER")
    try:
        raw=reviewer(request)
        parsed=ProposedCriticResponse.model_validate(raw)
        issues=_validate_response(parsed,request)
    except (TimeoutError, ConnectionError, OSError):
        return _make_result(request=request,status="CRITIC_UNAVAILABLE",
                            reason="REVIEWER_OUTAGE_OR_TIMEOUT",calls=1)
    except Exception:
        return _make_result(request=request,status="CRITIC_REJECTED",
                            reason="UNTRUSTED_REVIEWER_EXCEPTION_OR_INVALID_SCOPE",calls=1)
    return _make_result(request=request,
        status="CRITIC_REVIEW_REQUIRED" if issues else "CRITIC_NO_ISSUES_UNVERIFIED",
        reason="BOUNDED_REVIEWER_FINDINGS_NOT_INDEPENDENTLY_VALIDATED",findings=issues,calls=1)


def run_video_artifact_critic(
    request:ArtifactReviewRequest,*,video_path:str|Path,
    reviewer:Callable[[ArtifactReviewRequest,tuple[tuple[int,Image.Image],...]],object]|None=None,
)->CriticReviewResult:
    """Supply ACTUAL decoded image samples to a future authorized reviewer.

    Revalidates SHA and each RGB pixel buffer at review time. The request
    itself must first be constructed by binary_request / geometry_request
    after exact V3-10/11 source replay. Reviewer controls no release action.
    """
    if reviewer is None:
        return run_artifact_critic(request)
    try:
        video=Path(video_path)
        if _file_hash(video)!=request.video_sha256:
            _deny("VIDEO_CHANGED_SINCE_SOURCE_REPLAY")
        profile=SequenceRenderProfile(
            width=request.frame_samples[0].rgb_width,
            height=request.frame_samples[0].rgb_height,fps=request.fps,
        )
        decoded=[]
        for sample in request.frame_samples:
            if sample.rgb_width!=profile.width or sample.rgb_height!=profile.height:
                _deny("MIXED_FRAME_DIMENSIONS")
            img=_decode_exact_frame(video,sample.frame_index,profile)
            if hashlib.sha256(img.tobytes()).hexdigest()!=sample.rgb_sha256:
                _deny("PIXEL_CHANGED_SINCE_REQUEST")
            decoded.append((sample.frame_index,img))
    except Exception:
        return _make_result(
            request=request,status="CRITIC_REJECTED",
            reason="VIDEO_BYTES_OR_PIXELS_NO_LONGER_MATCH_APPROVED_REQUEST",
        )
    return run_artifact_critic(
        request,
        reviewer=lambda bound:reviewer(
            bound,tuple((idx,frame.copy()) for idx,frame in decoded),
        ),
    )


def verify_critic_review(*,candidate:CriticReviewResult,request:ArtifactReviewRequest,
                         reviewer:Callable|None=None)->None:
    fresh=run_artifact_critic(request,reviewer=reviewer)
    if candidate.model_dump(mode="json")!=fresh.model_dump(mode="json"):
        _deny("STALE_OR_FORGED_REVIEW")


class SeededLabel(V3Model):
    """Author-seeded test labels, NOT independent human quality annotations."""
    case_id:str=Field(min_length=1)
    expected_issue_ids:tuple[str,...]
    label_origin:Literal["AUTHOR_SEEDED_SYNTHETIC"]="AUTHOR_SEEDED_SYNTHETIC"


class BoundedFixtureMetrics(V3Model):
    fixture_count:int
    positive_fixtures:int
    expected_total:int
    predicted_total:int
    true_positive:int
    false_positive:int
    false_negative:int
    precision:float
    recall:float
    human_labeled_precision:Literal["UNMEASURED"]="UNMEASURED"
    human_labeled_recall:Literal["UNMEASURED"]="UNMEASURED"
    improvement_vs_v2_percent_points:Literal["NOT_ESTABLISHED"]="NOT_ESTABLISHED"


def evaluate_seeded_labels(
    gold:tuple[SeededLabel,...],predictions:dict[str,tuple[str,...]]
)->BoundedFixtureMetrics:
    if len({g.case_id for g in gold})!=len(gold) or set(predictions)!={g.case_id for g in gold}:
        _deny("SEED_FIXTURE_IDENTITY_MISMATCH")
    tp=fp=fn=0
    for g in gold:
        expect=set(g.expected_issue_ids)
        got=set(predictions[g.case_id])
        if len(got)!=len(predictions[g.case_id]):
            _deny("DUPLICATE_PREDICTED_ISSUE")
        tp+=len(expect & got)
        fp+=len(got-expect)
        fn+=len(expect-got)
    return BoundedFixtureMetrics(
        fixture_count=len(gold),positive_fixtures=sum(bool(x.expected_issue_ids) for x in gold),
        expected_total=tp+fn,predicted_total=tp+fp,true_positive=tp,
        false_positive=fp,false_negative=fn,
        precision=tp/(tp+fp) if tp+fp else 0.0,
        recall=tp/(tp+fn) if tp+fn else 0.0,
    )
