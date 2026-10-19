"""V3-14 deterministic typed local track restore, rollback and real MP4 QA."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v3.models import SemanticContractError
from learnflow_v3.temporal_geometry import certify_temporal_layout,TemporalLayoutPlan
from learnflow_v3.temporal_demo_renderer import render_certified_temporal_demo,verify_temporal_render
from learnflow_v3.artifact_refine import (
    LocalRepairIntent,LocalRefineResult,intent_for_seeded_defect,
    refine_single_track,defer_nonlocal_issue,verify_refine_result,
)
from scripts.verify_v3_temporal_geometry import demo_layout


@pytest.fixture(scope="module")
def certified(tmp_path_factory):
    folder=tmp_path_factory.mktemp("v3_14_trusted_baseline")
    plan=demo_layout()
    cert=certify_temporal_layout(plan)
    path=folder/"last_good.mp4"
    evidence=render_certified_temporal_demo(plan=plan,certificate=cert,output_path=path)
    verify_temporal_render(plan=plan,certificate=cert,evidence=evidence,video_path=path)
    return (plan,cert,evidence,path)


def inject(plan,case):
    data=plan.model_dump(mode="json")
    tracks={t["object_id"]:t for t in data["tracks"]}
    if case=="text":
        tracks["title"]["keyframes"][0]["font_px"]=80
        return "title","TEXT_OVERFLOW",TemporalLayoutPlan.model_validate(data)
    if case=="subtitle":
        tracks["right-explanation"]["keyframes"][-1]["box"]["y"]=273
        return "right-explanation","SUBTITLE_INTRUSION",TemporalLayoutPlan.model_validate(data)
    if case=="clip":
        tracks["left-explanation"]["keyframes"][0]["box"]["x"]=-16
        return "left-explanation","FRAME_CLIPPING",TemporalLayoutPlan.model_validate(data)
    if case=="motion":
        tracks["left-explanation"]["keyframes"].insert(1,{
            "frame":1,"box":{"x":450,"y":132,"width":140,"height":54},
        })
        return "left-explanation","EXCESSIVE_MOTION",TemporalLayoutPlan.model_validate(data)
    if case=="overlap":
        tracks["left-explanation"]["keyframes"][-1]["box"]["y"]=222
        return "left-explanation","TEMPORAL_OCCLUSION",TemporalLayoutPlan.model_validate(data)
    raise AssertionError("unknown synthetic defect")


def apply(case,certified,output):
    plan,cert,evidence,path=certified
    target,category,bad=inject(plan,case)
    intent=intent_for_seeded_defect(
        case_id=case,baseline=plan,candidate=bad,
        target_track_id=target,defect_category=category)
    return refine_single_track(
        intent=intent,baseline=plan,baseline_certificate=cert,
        baseline_evidence=evidence,baseline_video_path=path,
        candidate=bad,output_path=output,
    )


@pytest.mark.parametrize("case",["text","subtitle","clip","motion","overlap"])
def test_single_track_local_repair_replays_real_mp4_with_original_preserved(case,certified,tmp_path):
    plan,cert,evidence,original=certified
    original_hash=hashlib.sha256(original.read_bytes()).hexdigest()
    out=tmp_path/f"repaired-{case}.mp4"
    report=apply(case,certified,out)
    assert report.status=="LOCAL_REPAIR_VERIFIED"
    assert report.publication_blocked is True
    assert report.production_patch_applied is False
    assert report.rollback_original_preserved is True
    assert report.attempts==1
    assert report.full_video_reencoded is True
    assert report.frame_count_reencoded==plan.frame_count
    assert report.verified_output_plan_sha256==report.baseline_plan_sha256
    assert len(report.altered_track_ids)==1
    assert len(report.untouched_track_ids)==len(plan.tracks)-1
    assert "V3_12_PUBLICATION_REVIEW" in report.invalidated_downstream
    assert hashlib.sha256(out.read_bytes()).hexdigest()==report.repaired_video_sha256
    assert hashlib.sha256(original.read_bytes()).hexdigest()==original_hash
    assert original.exists()
    assert out.stat().st_size>1000


def test_result_reproducible_and_no_mutation_of_source(certified,tmp_path):
    a=apply("text",certified,tmp_path/"a.mp4")
    b=apply("text",certified,tmp_path/"b.mp4")
    assert a.model_dump(mode="json")==b.model_dump(mode="json")
    verify_refine_result(candidate=a,replay=b)


def test_other_track_changed_is_rejected_before_any_render(certified,tmp_path):
    plan,cert,evidence,orig=certified
    _,category,bad=inject(plan,"text")
    data=bad.model_dump(mode="json")
    data["tracks"][1]["keyframes"][0]["box"]["x"]+=4
    other=TemporalLayoutPlan.model_validate(data)
    intent=intent_for_seeded_defect(
        case_id="multiple",baseline=plan,candidate=other,target_track_id="title",
        defect_category=category)
    out=tmp_path/"never.mp4"
    with pytest.raises(SemanticContractError,match="SILENT_NOOP_OR_MULTI_TRACK_MUTATION"):
        refine_single_track(intent=intent,baseline=plan,
            baseline_certificate=cert,baseline_evidence=evidence,
            baseline_video_path=orig,candidate=other,output_path=out)
    assert not out.exists()


def test_semantic_global_field_mutation_cannot_hide_in_local_patch(certified,tmp_path):
    plan,cert,evidence,orig=certified
    _,category,bad=inject(plan,"clip")
    modified=bad.model_copy(update={"source_ref":"different-source-semantic"})
    intent=intent_for_seeded_defect(
        case_id="semantic",baseline=plan,candidate=modified,
        target_track_id="left-explanation",defect_category=category)
    with pytest.raises(SemanticContractError,match="GLOBAL_SEMANTIC_OR_LAYOUT_DRIFT"):
        refine_single_track(intent=intent,baseline=plan,
            baseline_certificate=cert,baseline_evidence=evidence,
            baseline_video_path=orig,candidate=modified,output_path=tmp_path/"not.mp4")


def test_noop_and_unproven_good_candidate_are_blocked(certified,tmp_path):
    plan,cert,evidence,orig=certified
    from learnflow_v2.repair import compute_content_hash
    original_track=next(t for t in plan.tracks if t.object_id=="title")
    intent=LocalRepairIntent(
        case_id="no-op",defect_category="TEXT_OVERFLOW",
        target_track_id="title",baseline_plan_sha256=compute_content_hash(plan.model_dump(mode="json")),
        candidate_plan_sha256=compute_content_hash(plan.model_dump(mode="json")),
        expected_bad_track_sha256=compute_content_hash(original_track.model_dump(mode="json")))
    with pytest.raises(SemanticContractError,match="SILENT_NOOP_OR_MULTI_TRACK_MUTATION"):
        refine_single_track(intent=intent,baseline=plan,
            baseline_certificate=cert,baseline_evidence=evidence,
            baseline_video_path=orig,candidate=plan,output_path=tmp_path/"no.mp4")


def test_wrong_defect_class_and_stale_patch_hash_fails_closed(certified,tmp_path):
    plan,cert,evidence,orig=certified
    target,category,bad=inject(plan,"text")
    valid=intent_for_seeded_defect(case_id="wrong",baseline=plan,candidate=bad,
                                  target_track_id=target,defect_category=category)
    invalid=valid.model_copy(update={"defect_category":"FRAME_CLIPPING"})
    with pytest.raises(SemanticContractError,match="DEFECT_CATEGORY_NOT_PROVEN"):
        refine_single_track(intent=invalid,baseline=plan,
            baseline_certificate=cert,baseline_evidence=evidence,
            baseline_video_path=orig,candidate=bad,output_path=tmp_path/"wrong.mp4")
    forged=valid.model_copy(update={"candidate_plan_sha256":"f"*64})
    with pytest.raises(SemanticContractError,match="STALE_PLAN_FINGERPRINT"):
        refine_single_track(intent=forged,baseline=plan,
            baseline_certificate=cert,baseline_evidence=evidence,
            baseline_video_path=orig,candidate=bad,output_path=tmp_path/"stale.mp4")


def test_stale_last_good_video_not_trusted(certified,tmp_path):
    plan,cert,evidence,orig=certified
    target,category,bad=inject(plan,"clip")
    intent=intent_for_seeded_defect(case_id="bad-baseline",baseline=plan,
                                   candidate=bad,target_track_id=target,defect_category=category)
    modified=tmp_path/"untrusted.mp4"
    modified.write_bytes(orig.read_bytes()+b"tampered")
    with pytest.raises(SemanticContractError):
        refine_single_track(intent=intent,baseline=plan,
            baseline_certificate=cert,baseline_evidence=evidence,
            baseline_video_path=modified,candidate=bad,output_path=tmp_path/"never.mp4")


def test_preexisting_output_and_original_destination_are_never_overwritten(certified,tmp_path):
    plan,cert,evidence,orig=certified
    target,category,bad=inject(plan,"clip")
    intent=intent_for_seeded_defect(case_id="overwrite",baseline=plan,
                                   candidate=bad,target_track_id=target,defect_category=category)
    already=tmp_path/"existing.mp4"
    already.write_bytes(b"must-stay")
    for output in (already,orig):
        with pytest.raises(SemanticContractError,match="OUTPUT_DESTINATION_UNSAFE"):
            refine_single_track(intent=intent,baseline=plan,
                baseline_certificate=cert,baseline_evidence=evidence,
                baseline_video_path=orig,candidate=bad,output_path=output)
    assert already.read_bytes()==b"must-stay"


def test_dependent_renderer_failure_rolls_back_without_publication(certified,tmp_path,monkeypatch):
    import learnflow_v3.artifact_refine as ar
    plan,cert,evidence,orig=certified
    target,category,bad=inject(plan,"clip")
    intent=intent_for_seeded_defect(case_id="encode-fault",baseline=plan,
                                   candidate=bad,target_track_id=target,defect_category=category)
    orig_hash=hashlib.sha256(orig.read_bytes()).hexdigest()
    def fail_render(**kwargs):
        raise RuntimeError("injected ffmpeg codec crash")
    monkeypatch.setattr(ar,"render_certified_temporal_demo",fail_render)
    output=tmp_path/"failed.mp4"
    outcome=refine_single_track(intent=intent,baseline=plan,
        baseline_certificate=cert,baseline_evidence=evidence,
        baseline_video_path=orig,candidate=bad,output_path=output)
    assert outcome.status=="ROLLBACK_BLOCKED"
    assert not outcome.full_video_reencoded
    assert outcome.repaired_video_sha256 is None
    assert outcome.publication_blocked
    assert not output.exists()
    assert hashlib.sha256(orig.read_bytes()).hexdigest()==orig_hash


def test_defect_owner_routes_nonlocal_issues_without_auto_change():
    cases={
        "FACTUAL_SOURCE_MISMATCH":"RESEARCH_ORCHESTRATION",
        "SCRIPT_CUE_MISMATCH":"SCRIPT_AGENT",
        "PEDAGOGICAL_ALIGNMENT":"PEDAGOGY_AGENT",
        "SEMANTIC_VISUAL_MISMATCH":"VISUAL_DIRECTOR",
        "STYLE_INCONSISTENCY":"VISUAL_DIRECTOR",
        "VISUAL_LEGIBILITY":"VISUAL_DIRECTOR",
    }
    for category,owner in cases.items():
        result=defer_nonlocal_issue(category)
        assert result.owner==owner and result.publication_blocked
        assert result.geometry_patch_applied is False
    with pytest.raises(SemanticContractError):
        defer_nonlocal_issue("EXECUTE_LLM_PYTHON")
    with pytest.raises(ValidationError):
        LocalRepairIntent.model_validate({
            "case_id":"unsafe","defect_category":"TEXT_OVERFLOW","target_track_id":"title",
            "operation":"EXECUTE_PYTHON","baseline_plan_sha256":"a"*64,
            "candidate_plan_sha256":"b"*64,"expected_bad_track_sha256":"c"*64,
        })


def test_deceptive_success_or_rehashed_audit_does_not_validate(certified,tmp_path):
    r=apply("text",certified,tmp_path/"safe.mp4")
    from learnflow_v2.repair import compute_content_hash
    d=r.model_dump(mode="json")
    d["publication_blocked"]=False
    d["result_sha256"]=compute_content_hash({k:v for k,v in d.items() if k!="result_sha256"})
    with pytest.raises(ValidationError):
        LocalRefineResult.model_validate(d)
    forged=r.model_copy(update={"reason":"LLM claims verified"})
    with pytest.raises(SemanticContractError,match="REHASHED_OR_STALE"):
        verify_refine_result(candidate=forged,replay=r)


def test_renderer_partial_write_then_exception_is_fully_cleaned(certified,tmp_path,monkeypatch):
    """Regression: an encoder may fail AFTER producing a partial MP4."""
    import learnflow_v3.artifact_refine as ar
    baseline,cert,evidence,original=certified
    target,category,bad=inject(baseline,"clip")
    intent=intent_for_seeded_defect(
        case_id="partial-write-fault",baseline=baseline,candidate=bad,
        target_track_id=target,defect_category=category)
    initial_sha=hashlib.sha256(original.read_bytes()).hexdigest()

    def crash_after_creating_partial(**kwargs):
        Path(kwargs["output_path"]).write_bytes(b"partial-h264-before-encoder-crash")
        raise RuntimeError("injected partial output failure")

    monkeypatch.setattr(ar,"render_certified_temporal_demo",
                        crash_after_creating_partial)
    destination=tmp_path/"partial.mp4"
    result=refine_single_track(
        intent=intent,baseline=baseline,baseline_certificate=cert,
        baseline_evidence=evidence,baseline_video_path=original,
        candidate=bad,output_path=destination)
    assert result.status=="ROLLBACK_BLOCKED"
    assert result.publication_blocked
    assert not destination.exists()
    assert list(tmp_path.iterdir())==[]
    assert hashlib.sha256(original.read_bytes()).hexdigest()==initial_sha
