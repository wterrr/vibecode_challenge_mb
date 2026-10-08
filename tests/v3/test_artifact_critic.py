"""V3-13 pixel-bound issue schema, fault matrix and seeded-label limitations."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v2.repair import compute_content_hash
from learnflow_v3.models import SemanticContractError
from learnflow_v3.sequence_renderer import SequenceRenderProfile
from learnflow_v3.temporal_geometry import certify_temporal_layout
from learnflow_v3.temporal_demo_renderer import render_certified_temporal_demo
from learnflow_v3.publication_gate import review_binary_publication
from learnflow_v3.artifact_critic import (
    ArtifactIssue,ArtifactReviewRequest,ProposedCriticResponse,CriticReviewResult,
    SeededLabel,evaluate_seeded_labels,binary_request,geometry_request,
    run_artifact_critic,verify_critic_review,
)
from scripts.verify_v3_beat_grounding import generate_verified_case
from scripts.verify_v3_temporal_geometry import demo_layout


@pytest.fixture(scope="module")
def binary(tmp_path_factory):
    path=tmp_path_factory.mktemp("v3_13_binary")
    prof=SequenceRenderProfile(width=640,height=360,fps=12,seconds_per_step=.75)
    bundle,trace,manifest,renderer,_,video=generate_verified_case(
        directory=path,case="duplicate",profile=prof,
    )
    inputs={
        **{k:v for k,v in bundle.items() if k!="verified_trace_refs"},
        "trace":trace,"manifest":manifest,"video_evidence":renderer,
        "video_path":video,"profile":prof,
    }
    return inputs,binary_request(**inputs)


@pytest.fixture(scope="module")
def geometry(tmp_path_factory):
    p=tmp_path_factory.mktemp("v3_13_geometry")
    plan=demo_layout()
    cert=certify_temporal_layout(plan)
    video=p/"geometry.mp4"
    evidence=render_certified_temporal_demo(plan=plan,certificate=cert,output_path=video)
    kwargs=dict(plan=plan,certificate=cert,evidence=evidence,video_path=video)
    return kwargs,geometry_request(**kwargs)


def make_issue(request,*,issue_id="contrast-risk",category="VISUAL_LEGIBILITY",
               object_id=None,frame=None,confidence=.83,**other):
    from learnflow_v3.artifact_critic import CATEGORY_OWNER
    s=request.frame_samples[1] if frame is None else next(x for x in request.frame_samples
                                                      if x.frame_index==frame)
    args=dict(issue_id=issue_id,category=category,severity="MEDIUM",
              first_frame=s.frame_index,last_frame=s.frame_index,
              object_ids=(object_id or request.allowed_object_ids[0],),
              evidence_frame_indices=(s.frame_index,),
              evidence_rgb_sha256=(s.rgb_sha256,),confidence=confidence,
              rationale="Author-injected perceptual concern, requires independent review",
              repair_route=CATEGORY_OWNER[category])
    args.update(other)
    return args


def reviewer_for(request,issues=()):
    return {"request_sha256":compute_content_hash(request.model_dump(mode="json")),
            "issues":list(issues),"summary":"Offline developer-injected issue proposal"}


def test_real_binary_decode_and_scoped_source_grounding(binary):
    inputs,request=binary
    assert request.prior_deterministic_pass
    assert request.video_sha256==hashlib.sha256(inputs["video_path"].read_bytes()).hexdigest()
    assert len(request.frame_samples)==6
    assert len(request.allowed_object_ids)>0
    assert request.allowed_beat_ids
    assert all(len(sample.rgb_sha256)==64 for sample in request.frame_samples)
    assert request.frame_samples[-1].frame_index==request.video_frame_count-1
    assert len({x.rgb_sha256 for x in request.frame_samples})>1


def test_real_temporal_geometry_pixels_and_zero_audio_claim(geometry):
    inputs,request=geometry
    assert request.subject=="TEMPORAL_GEOMETRY_DEMO"
    assert request.frame_samples[-1].frame_index==48
    assert not request.approved_claim_ids and not request.allowed_beat_ids
    assert request.allowed_object_ids==tuple(x.object_id for x in inputs["plan"].tracks)


def test_no_provider_reports_unavailable_not_pass(binary):
    _,request=binary
    report=run_artifact_critic(request)
    assert report.status=="CRITIC_UNAVAILABLE"
    assert report.reviewer_calls==0
    assert report.publication_blocked is True
    assert report.critic_pass_certified is False
    assert report.independent_human_quality=="UNMEASURED"
    verify_critic_review(candidate=report,request=request)


def test_empty_reviewer_issues_cannot_be_critic_pass(binary):
    _,request=binary
    report=run_artifact_critic(request,reviewer=lambda r:reviewer_for(r))
    assert report.status=="CRITIC_NO_ISSUES_UNVERIFIED"
    assert report.critic_pass_certified is False
    assert report.publication_blocked is True
    assert report.reviewer_calls==1


def test_actual_video_scoped_issue_and_typed_owner(binary):
    _,request=binary
    issue=make_issue(request)
    reviewer=lambda r:reviewer_for(r,(issue,))
    response=run_artifact_critic(request,reviewer=reviewer)
    assert response.status=="CRITIC_REVIEW_REQUIRED"
    assert response.findings[0].category=="VISUAL_LEGIBILITY"
    assert response.findings[0].repair_route=="VISUAL_DIRECTOR"
    assert response.publication_blocked and not response.critic_pass_certified
    verify_critic_review(candidate=response,request=request,reviewer=reviewer)
    with pytest.raises(SemanticContractError,match="STALE_OR_FORGED"):
        forged=response.model_copy(update={"reason":"Critical automated publish PASS"})
        verify_critic_review(candidate=forged,request=request,reviewer=reviewer)


@pytest.mark.parametrize("tamper",[
    lambda d:d.update(request_sha256="0"*64),
    lambda d:d["issues"][0].update(object_ids=["invented_object"]),
    lambda d:d["issues"][0].update(evidence_rgb_sha256=["f"*64]),
    lambda d:d["issues"][0].update(evidence_frame_indices=[42]),
    lambda d:d["issues"][0].update(beat_id="missing-beat"),
    lambda d:d["issues"][0].update(claim_id="unapproved-claim"),
    lambda d:d["issues"][0].update(first_frame=1000,last_frame=1001),
    lambda d:d["issues"][0].update(repair_route="RESEARCH_ORCHESTRATION"),
    lambda d:d["issues"][0].update(confidence=.24),
    lambda d:d["issues"][0].update(rationale="exec(anything)"),
    lambda d:d["issues"][0].update(issue_id="not valid spaces"),
])
def test_hallucinated_or_malformed_reviewer_proposals_fail_closed(binary,tamper):
    _,request=binary
    from copy import deepcopy
    data=reviewer_for(request,(make_issue(request),))
    tamper(data)
    review=run_artifact_critic(request,reviewer=lambda _:data)
    assert review.status=="CRITIC_REJECTED"
    assert not review.findings and review.publication_blocked


def test_executable_and_raw_geometry_are_not_part_of_issue_schema(binary):
    _,request=binary
    data=make_issue(request)
    data["python_code"]="import os; os.system('oops')"
    with pytest.raises(ValidationError):
        ArtifactIssue.model_validate(data)
    data=make_issue(request)
    data["x"]=100
    with pytest.raises(ValidationError):
        ArtifactIssue.model_validate(data)
    data=make_issue(request)
    data["patch_code"]="fix video automatically"
    with pytest.raises(ValidationError):
        ArtifactIssue.model_validate(data)


def test_unbounded_duplicate_and_conflicting_findings_rejected(binary):
    _,request=binary
    data=reviewer_for(request,[make_issue(request,issue_id="dup")]*2)
    assert run_artifact_critic(request,reviewer=lambda _:data).status=="CRITIC_REJECTED"
    data=reviewer_for(request,[make_issue(request,issue_id=f"issue-{i}") for i in range(9)])
    assert run_artifact_critic(request,reviewer=lambda _:data).status=="CRITIC_REJECTED"
    calls=[]
    def reject(_):
        calls.append(1)
        raise RuntimeError("provider outage")
    result=run_artifact_critic(request,reviewer=reject)
    assert result.status=="CRITIC_REJECTED" and result.reviewer_calls==1
    assert len(calls)==1


def test_unsupported_time_and_source_scope_rejected(binary):
    _,request=binary
    tamper=request.model_dump(mode="json")
    tamper["frame_samples"][0]["timestamp_ms"]=10000
    with pytest.raises(ValidationError):
        ArtifactReviewRequest.model_validate(tamper)
    tamper=request.model_dump(mode="json")
    tamper["allowed_object_ids"]=[]
    with pytest.raises(ValidationError):
        ArtifactReviewRequest.model_validate(tamper)


def test_hard_deterministic_failure_before_any_critic(binary,tmp_path):
    args,_=binary
    bad=dict(args)
    bad["video_path"]=tmp_path/"non-existent.mp4"
    with pytest.raises(SemanticContractError):
        binary_request(**bad)
    bad=dict(args)
    bad["video_evidence"]=args["video_evidence"].model_copy(update={"video_sha256":"0"*64})
    with pytest.raises(SemanticContractError):
        binary_request(**bad)


def test_real_v3_12_publication_gate_stays_blocked_with_critic_findings(binary):
    args,request=binary
    scoped=run_artifact_critic(
        request,reviewer=lambda r:reviewer_for(r,(make_issue(r),)))
    assert scoped.status=="CRITIC_REVIEW_REQUIRED"
    review=review_binary_publication(**args)
    assert review.publication_status=="PUBLISH_BLOCKED"
    assert "VERIFIED_ARTIFACT_CRITIC" in review.blocked_reasons


def test_wrong_video_for_geometry_refused(geometry,tmp_path):
    args,_=geometry
    fake=tmp_path/"wrong.mp4"
    fake.write_bytes(args["video_path"].read_bytes()+b"stale")
    with pytest.raises(SemanticContractError):
        geometry_request(**{**args,"video_path":fake})


def test_invalid_reviewer_result_cannot_grant_external_publication(binary):
    _,request=binary
    result=run_artifact_critic(request)
    tampered=result.model_dump(mode="json")
    tampered["critic_pass_certified"]=True
    tampered["publication_blocked"]=False
    tampered["review_hash"]=compute_content_hash({k:v for k,v in tampered.items() if k!="review_hash"})
    with pytest.raises(ValidationError):
        CriticReviewResult.model_validate(tampered)


def test_bounded_author_seeded_metrics_not_labeled_human(binary):
    _,request=binary
    # Transparent injected fixture labels: never call these HUMAN-LABELED.
    gold=(
        SeededLabel(case_id="contrast",expected_issue_ids=("contrast-risk",)),
        SeededLabel(case_id="static",expected_issue_ids=()),
        SeededLabel(case_id="occluded",expected_issue_ids=("occlusion-risk",)),
        SeededLabel(case_id="hallucination",expected_issue_ids=()),
    )
    predictions={
        "contrast":("contrast-risk",),
        "static":(),
        "occluded":("occlusion-risk",),
        "hallucination":("false-alarm",),
    }
    metrics=evaluate_seeded_labels(gold,predictions)
    assert metrics.fixture_count==4
    assert metrics.true_positive==2 and metrics.false_positive==1
    assert metrics.false_negative==0
    assert metrics.precision==pytest.approx(2/3)
    assert metrics.recall==1.0
    assert metrics.human_labeled_precision=="UNMEASURED"
    assert metrics.human_labeled_recall=="UNMEASURED"
    assert metrics.improvement_vs_v2_percent_points=="NOT_ESTABLISHED"


def test_seeded_evaluation_fails_on_case_leakage_and_duplicate_predictions():
    labels=(SeededLabel(case_id="a",expected_issue_ids=("x",)),)
    with pytest.raises(SemanticContractError):
        evaluate_seeded_labels(labels,{"other":("x",)})
    with pytest.raises(SemanticContractError):
        evaluate_seeded_labels(labels,{"a":("x","x")})
