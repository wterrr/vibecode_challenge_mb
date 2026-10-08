"""V3-12 no-bypass publication gate: real MP4 replay and adversarial mutations."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from learnflow_v3.models import SemanticContractError
from learnflow_v3.sequence_renderer import SequenceRenderProfile
from learnflow_v3.temporal_geometry import certify_temporal_layout
from learnflow_v3.temporal_demo_renderer import render_certified_temporal_demo
from learnflow_v3.publication_gate import (
    CriticObservation, PublicationPolicy, PublicationReview,
    DeterministicStatus, CriticStatus, GateStatus,
    publish,review_binary_publication,review_geometry_publication,
    verify_publication_review,
)
from scripts.verify_v3_beat_grounding import generate_verified_case
from scripts.verify_v3_temporal_geometry import demo_layout


@pytest.fixture(scope="module")
def binary(tmp_path_factory):
    p=tmp_path_factory.mktemp("v3_12_binary")
    profile=SequenceRenderProfile(width=640,height=360,fps=12,seconds_per_step=.75)
    bundle,trace,manifest,render,beat,video=generate_verified_case(
        directory=p,case="duplicate",profile=profile)
    args=dict(trace=trace,manifest=manifest,video_evidence=render,
              video_path=video,profile=profile,
              **{k:v for k,v in bundle.items() if k!="verified_trace_refs"})
    return args,beat


@pytest.fixture(scope="module")
def geometry(tmp_path_factory):
    p=tmp_path_factory.mktemp("v3_12_geometry")
    plan=demo_layout()
    cert=certify_temporal_layout(plan)
    output=p/"geometry.mp4"
    evidence=render_certified_temporal_demo(plan=plan,certificate=cert,output_path=output)
    return dict(plan=plan,certificate=cert,evidence=evidence,video_path=output)


def test_real_binary_component_pass_is_never_publish_pass(binary):
    args,beat=binary
    review=review_binary_publication(**args)
    assert review.deterministic_status==DeterministicStatus.DETERMINISTIC_PASS
    assert review.critic_status==CriticStatus.CRITIC_UNAVAILABLE
    assert review.publication_status=="PUBLISH_BLOCKED"
    assert review.production_release_executed is False
    assert review.release_quality_tier=="NO_RELEASE_GRADE"
    assert review.video_sha256==hashlib.sha256(args["video_path"].read_bytes()).hexdigest()
    assert [x.key for x in review.requirements if x.status==GateStatus.PASS]==[
        "CERTIFIED_SOURCE","RENDERED_PIXELS","BEAT_VISUAL_ALIGNMENT"]
    assert "AUDIO" not in review.release_quality_tier
    assert "LESSON_WIDE_TEMPORAL_GEOMETRY" in review.blocked_reasons
    verify_publication_review(candidate=review,replay=lambda:review_binary_publication(**args))


def test_real_geometry_component_not_confused_with_full_lesson(geometry):
    review=review_geometry_publication(**geometry)
    assert review.deterministic_status==DeterministicStatus.DETERMINISTIC_PASS
    assert review.publication_status=="PUBLISH_BLOCKED"
    assert [x.key for x in review.requirements if x.status==GateStatus.PASS]==[
        "CERTIFIED_SOURCE","RENDERED_PIXELS"]
    assert "BEAT_VISUAL_ALIGNMENT" in review.blocked_reasons
    assert "LESSON_WIDE_TEMPORAL_GEOMETRY" in review.blocked_reasons


@pytest.mark.parametrize("outcome,expected",[
    ("NOT_RUN",CriticStatus.CRITIC_UNAVAILABLE),
    ("UNAVAILABLE",CriticStatus.CRITIC_UNAVAILABLE),
    ("PASS_UNVERIFIED",CriticStatus.CRITIC_UNAVAILABLE),
    ("FAIL",CriticStatus.CRITIC_FAIL),
    ("ERROR",CriticStatus.QA_ERROR),
])
def test_critic_fault_matrix_never_promotes_raw_result(binary,outcome,expected):
    args,_=binary
    c=CriticObservation(outcome=outcome)
    r=review_binary_publication(**args,critic=c)
    assert r.critic_status==expected
    assert r.publication_status=="PUBLISH_BLOCKED"
    assert "VERIFIED_ARTIFACT_CRITIC" in r.blocked_reasons
    assert r.lifecycle[-2].stage=="CRITIC_STATUS"
    assert r.lifecycle[-1].stage=="PUBLISH_BLOCKED"


@pytest.mark.parametrize("field,value",[
    ("enable_publication",True),
    ("allow_unverified_deterministic_only",True),
    ("require_verified_critic",False),
    ("dry_run_only",False),
    ("retry_llm",True),
])
def test_untrusted_publish_flags_cannot_override_policy(field,value):
    with pytest.raises(ValidationError):
        PublicationPolicy.model_validate({field:value})
    with pytest.raises(SemanticContractError,match="PUBLICATION_DISABLED"):
        publish()


def test_stale_render_cache_fails_even_when_subject_claims_success(binary):
    args,_=binary
    broken=dict(args)
    broken["video_evidence"]=args["video_evidence"].model_copy(
        update={"video_sha256":"0"*64})
    r=review_binary_publication(**broken)
    assert r.deterministic_status==DeterministicStatus.DETERMINISTIC_FAIL
    assert r.publication_status=="PUBLISH_BLOCKED"
    assert r.requirements[0].status==GateStatus.FAIL
    assert r.lifecycle[-3].stage=="DETERMINISTIC_FAIL"
    assert r.video_sha256==hashlib.sha256(args["video_path"].read_bytes()).hexdigest()


def test_invalid_beat_cue_broken_renderer_manifest(binary):
    args,_=binary
    m=args["manifest"].model_dump(mode="json")
    m["beats"][0]["beat_id"]="beat-unknown"
    from learnflow_v3.beat_grounding import BeatGroundingManifest
    altered=BeatGroundingManifest.model_validate(m)
    r=review_binary_publication(**{**args,"manifest":altered})
    assert r.deterministic_status==DeterministicStatus.DETERMINISTIC_FAIL
    assert r.publication_status=="PUBLISH_BLOCKED"


def test_unrecognized_algorithm_representation_blocked(binary):
    args,_=binary
    model=args["pattern"].model_dump(mode="json")
    model["renderer_requirement"]="MATH"
    fake=type(args["pattern"]).model_validate(model)
    r=review_binary_publication(**{**args,"pattern":fake})
    assert r.deterministic_status==DeterministicStatus.DETERMINISTIC_FAIL


def test_unknown_concept_identity_blocked(binary):
    args,_=binary
    model=args["pattern"].model_dump(mode="json")
    model["concept_refs"][0]["concept_id"]="unregistered-concept"
    fake=type(args["pattern"]).model_validate(model)
    r=review_binary_publication(**{**args,"pattern":fake})
    assert r.deterministic_status==DeterministicStatus.DETERMINISTIC_FAIL


def test_partial_scene_missing_script_segment_blocked(binary):
    args,_=binary
    d=args["script"].model_dump(mode="json")
    d["segments"]=d["segments"][:-1]
    changed=type(args["script"]).model_validate(d)
    r=review_binary_publication(**{**args,"script":changed})
    assert r.deterministic_status==DeterministicStatus.DETERMINISTIC_FAIL
    assert r.publication_status=="PUBLISH_BLOCKED"


def test_actual_video_missing_and_altered_bytes_block(binary,tmp_path):
    args,_=binary
    missing=tmp_path/"missing.mp4"
    a=review_binary_publication(**{**args,"video_path":missing})
    assert a.deterministic_status==DeterministicStatus.DETERMINISTIC_FAIL
    copied=tmp_path/"altered.mp4"
    copied.write_bytes(args["video_path"].read_bytes()+b"POSTPROCESS")
    b=review_binary_publication(**{**args,"video_path":copied})
    assert b.deterministic_status==DeterministicStatus.DETERMINISTIC_FAIL
    assert a.publication_status==b.publication_status=="PUBLISH_BLOCKED"


def test_geometry_stale_cache_and_changed_keyframe_block(geometry):
    bad=geometry["evidence"].model_copy(update={"video_sha256":"f"*64})
    r=review_geometry_publication(**{**geometry,"evidence":bad})
    assert r.deterministic_status==DeterministicStatus.DETERMINISTIC_FAIL
    data=geometry["plan"].model_dump(mode="json")
    data["tracks"][1]["keyframes"][-1]["box"]["x"]=243
    changed=type(geometry["plan"]).model_validate(data)
    r=review_geometry_publication(**{**geometry,"plan":changed})
    assert r.deterministic_status==DeterministicStatus.DETERMINISTIC_FAIL


def test_unexpected_internal_verifier_exception_is_qa_error(binary,monkeypatch):
    import learnflow_v3.publication_gate as gate
    def explode(**kwargs):
        raise RuntimeError("simulated QA provider outage")
    monkeypatch.setattr(gate,"verify_binary_beat_video",explode)
    r=review_binary_publication(**binary[0])
    assert r.deterministic_status==DeterministicStatus.QA_ERROR
    assert r.publication_status=="PUBLISH_BLOCKED"
    assert r.lifecycle[-3].stage=="QA_ERROR"


def test_audit_chain_and_rehashed_tamper_cannot_promote(binary):
    args,_=binary
    r=review_binary_publication(**args)
    data=r.model_dump(mode="json")
    data["publication_status"]="PUBLISH_CANDIDATE"
    from learnflow_v2.repair import compute_content_hash
    data["review_sha256"]=compute_content_hash({k:v for k,v in data.items() if k!="review_sha256"})
    with pytest.raises(ValidationError):
        PublicationReview.model_validate(data)
    data=r.model_dump(mode="json")
    data["requirements"][0]["reason"]="LLM says pass"
    data["review_sha256"]=compute_content_hash({k:v for k,v in data.items() if k!="review_sha256"})
    modified=PublicationReview.model_validate(data)
    with pytest.raises(SemanticContractError,match="STALE_OR_REHASHED_REVIEW"):
        verify_publication_review(candidate=modified,replay=lambda:review_binary_publication(**args))
    data=r.model_dump(mode="json")
    data["lifecycle"][0]["reason"]="fraud"
    data["review_sha256"]=compute_content_hash({k:v for k,v in data.items() if k!="review_sha256"})
    with pytest.raises(ValidationError,match="AUDIT_CHAIN_TAMPERED"):
        PublicationReview.model_validate(data)


def test_critic_pass_and_release_grade_cannot_be_forged(binary):
    data=review_binary_publication(**binary[0]).model_dump(mode="json")
    data["critic_status"]="CRITIC_PASS"
    data["release_quality_tier"]="PRODUCTION"
    from learnflow_v2.repair import compute_content_hash
    data["review_sha256"]=compute_content_hash({k:v for k,v in data.items() if k!="review_sha256"})
    with pytest.raises(ValidationError):
        PublicationReview.model_validate(data)
