"""V3 integration vertical slice: true ffmpeg MP4, no golden-script calls.

No production API/gemini; the user-facing application remains unchanged.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v2.scenegraph import SceneGraph
from learnflow_v3.models import SemanticContractError,VisualTeachingPlan
from learnflow_v3.offline_lesson_source import build_binary_lesson_source
from learnflow_v3.integration_slice import (
    DispatchDecision,IntegratedClipReceipt,select_renderer,
    run_integrated_binary_clip,verify_integrated_binary_clip,
)
from learnflow_v3.sequence_renderer import SequenceRenderProfile
from scripts.audit_v3_reachability import build_inventory


PROFILE=SequenceRenderProfile(width=640,height=360,fps=12,seconds_per_step=.75)


@pytest.fixture(scope="module")
def source():
    return build_binary_lesson_source(
        values=(1,3,5,7,9,12,12,14,18),target=12)


@pytest.fixture(scope="module")
def actual_video(tmp_path_factory,source):
    path=tmp_path_factory.mktemp("v3_integrated_no_golden")
    receipt=run_integrated_binary_clip(source=source,out_dir=path,profile=PROFILE)
    return path,receipt


def test_real_vertical_slice_mp4_after_route_remux_pixel_qa(actual_video,source):
    path,receipt=actual_video
    assert isinstance(receipt,IntegratedClipReceipt)
    verify_integrated_binary_clip(source=source,out_dir=path,profile=PROFILE,
                                  receipt=receipt)
    assert receipt.qa=="BOUNDED_SOURCE_AND_DECODED_PIXEL_PASS"
    assert receipt.route_status_at_v3_04=="SELECTED_UNRENDERABLE"
    assert receipt.selected_variant.startswith("TRACE_")
    assert receipt.renderer_family=="STATEFUL_SEQUENCE_BINARY_SEARCH"
    assert receipt.frame_count==PROFILE.frames_per_step()*len(source.trace.steps)
    assert receipt.decoded_scene_rgb_sha256==receipt.decoded_assembly_rgb_sha256
    assert len(receipt.timeline)==len(source.trace.steps)
    assert all(entry["end_frame_exclusive"]>entry["start_frame"]
               for entry in receipt.timeline)
    assert receipt.stages[-1]=="V3_PUBLICATION_REVIEW_BLOCKED"
    assert receipt.publication=="PUBLISH_BLOCKED"
    assert receipt.audio=="NOT_GENERATED"
    assert receipt.web_pipeline_connected is False
    assert receipt.independent_human_review=="UNMEASURED"
    assert (path/"integrated_binary_lesson.mp4").stat().st_size>1000
    assert set(p.name for p in path.iterdir())=={
        "integrated_binary_lesson.mp4",
        "integrated_binary_lesson.receipt.json",
    }


def test_canonical_claim_object_beat_identity_carried_to_receipt(actual_video,source):
    _,receipt=actual_video
    assert receipt.downstream_claim_refs==("claim-01",)
    assert receipt.downstream_object_ids==tuple(x.object_id for x in source.pattern.semantic_objects)
    assert receipt.downstream_beat_ids==tuple(x.beat_id for x in source.plan.beats)
    assert [b["script_segment_id"] for b in receipt.timeline]==[
        s.segment_id for s in source.script.segments
    ]
    assert all(b["claim_refs"]==["claim-01"] for b in receipt.timeline)


def test_missing_renderer_returns_explicit_abstention_no_clip(tmp_path,source):
    result=run_integrated_binary_clip(
        source=source,out_dir=tmp_path,profile=PROFILE,adapter_enabled=False)
    assert isinstance(result,DispatchDecision)
    assert result.status=="ABSTAIN_UNCONNECTED_FAMILY"
    assert result.renderer is None and not result.fallback_to_card
    assert list(tmp_path.iterdir())==[]


@pytest.mark.parametrize("family",[
    "PROCESS_FLOW","EQUATION_GRAPH","STATE_MACHINE","CODE_WALKTHROUGH",
    "CONCEPT_CARD","FUNCTION_GRAPH","EQUATION_DERIVATION",
])
def test_unconnected_families_are_not_masquerading_as_working(family):
    result=select_renderer(family)
    assert result.status=="ABSTAIN_UNCONNECTED_FAMILY"
    assert result.renderer is None and result.production_registered is False


def test_cyclic_process_network_is_explicitly_abstained_not_flattened():
    graph=SceneGraph.model_validate({
        "scene_id":"cyclic-process","purpose":"EXPLAIN",
        "layout_intent":{"type":"PROCESS","reading_direction":"LEFT_TO_RIGHT"},
        "nodes":[{"id":"a","kind":"CONCEPT","label":"A"},
                 {"id":"b","kind":"CONCEPT","label":"B"}],
        "relations":[{"id":"ab","kind":"FLOW","source":"a","target":"b"},
                     {"id":"ba","kind":"FLOW","source":"b","target":"a"}],
    })
    result=select_renderer("PROCESS_FLOW",scenegraph=graph)
    assert result.status=="ABSTAIN_INVALID_TOPOLOGY"
    assert result.renderer is None and not result.fallback_to_card


def test_declared_not_rendered_signals_are_not_silently_claimed_consumed(actual_video):
    _,receipt=actual_video
    assert receipt.global_visual_signal_consumption=="PARTIAL_DECLARED_DEFERRED"
    assert len(receipt.deferred_signals)>0
    assert any("visual_teaching_goal" in x for x in receipt.deferred_signals)
    with pytest.raises(ValidationError):
        IntegratedClipReceipt.model_validate({
            **receipt.model_dump(mode="json"),
            "global_visual_signal_consumption":"COMPLETE",
        })


def test_unimplemented_hero_cannot_silently_be_ignored(tmp_path,source):
    p=source.plan.model_dump(mode="json")
    p["sections"][0]["hero_candidate"]=True
    mutation=replace(source,plan=VisualTeachingPlan.model_validate(p))
    with pytest.raises(SemanticContractError,match="HERO_BUDGET_UNIMPLEMENTED"):
        run_integrated_binary_clip(source=mutation,out_dir=tmp_path,profile=PROFILE)
    assert not list(tmp_path.iterdir())


def test_stale_script_binding_fails_before_creating_clip(tmp_path,source):
    script=source.script.model_dump(mode="json")
    script["segments"][0]["spoken_text"]="Binary search for 8 in [1, 3, 5]."
    mutated=replace(source,script=type(source.script).model_validate(script))
    with pytest.raises(SemanticContractError):
        run_integrated_binary_clip(source=mutated,out_dir=tmp_path,profile=PROFILE)
    assert not list(tmp_path.iterdir())


def test_stale_claim_or_beat_id_fails_before_video(tmp_path,source):
    plan=source.plan.model_dump(mode="json")
    plan["beats"][0]["claim_refs"]=["fabricated-claim"]
    mutated=replace(source,plan=VisualTeachingPlan.model_validate(plan))
    with pytest.raises(SemanticContractError):
        run_integrated_binary_clip(source=mutated,out_dir=tmp_path,profile=PROFILE)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("fault",[
    "AFTER_SCENE_CREATED","AFTER_ASSEMBLY_CREATED","AFTER_FINAL_VIDEO_LINKED",
])
def test_fault_injection_never_leaves_partial_final_and_never_publishes(
    tmp_path,source,fault
):
    with pytest.raises(SemanticContractError,match="INJECTED_FAILURE"):
        run_integrated_binary_clip(
            source=source,out_dir=tmp_path,profile=PROFILE,fault_inject=fault)
    assert list(tmp_path.iterdir())==[]


def test_existing_final_is_not_overwritten_even_by_success(tmp_path,source):
    final=tmp_path/"integrated_binary_lesson.mp4"
    final.write_bytes(b"leave-this-alone")
    with pytest.raises(SemanticContractError,match="DESTINATION_EXISTS_NO_CLOBBER"):
        run_integrated_binary_clip(source=source,out_dir=tmp_path,profile=PROFILE)
    assert final.read_bytes()==b"leave-this-alone"


def test_mutated_final_mp4_and_receipt_rejected(tmp_path,actual_video,source):
    previous,r=actual_video
    target=tmp_path/"integrated_binary_lesson.mp4"
    receipt=tmp_path/"integrated_binary_lesson.receipt.json"
    target.write_bytes((previous/target.name).read_bytes()+b"container-tamper")
    receipt.write_bytes((previous/receipt.name).read_bytes())
    with pytest.raises(SemanticContractError,match="STALE_OR_MUTATED_ASSEMBLED_VIDEO"):
        verify_integrated_binary_clip(source=source,out_dir=tmp_path,
                                      profile=PROFILE,receipt=r)


def test_modified_source_changes_hash_and_replay_is_blocked(actual_video,source):
    path,receipt=actual_video
    p=source.plan.model_dump(mode="json")
    p["sections"][0]["visual_teaching_goal"]="Different teaching goal is not rendered"
    changed=replace(source,plan=VisualTeachingPlan.model_validate(p))
    with pytest.raises(SemanticContractError,match="STALE_"):
        verify_integrated_binary_clip(source=changed,out_dir=path,profile=PROFILE,
                                      receipt=receipt)


def test_receipt_rehash_does_not_enable_publishing(actual_video):
    _,receipt=actual_video
    d=receipt.model_dump(mode="json")
    d["publication"]="PUBLISH_ALLOWED"
    from learnflow_v2.repair import compute_content_hash
    d["report_sha256"]=compute_content_hash({k:v for k,v in d.items()
                                            if k!="report_sha256"})
    with pytest.raises(ValidationError):
        IntegratedClipReceipt.model_validate(d)


def test_reachability_inventory_separates_product_from_offline_and_names_api():
    a=build_inventory()
    by_name={x["module"]:x for x in a["rows"]}
    assert "learnflow_v3.sequence_renderer" in by_name
    assert "learnflow_v3.integration_slice" in by_name
    assert "learnflow_v3.evaluation_pilot" in by_name
    assert by_name["learnflow_v3.integration_slice"]["status"]!="PRODUCTION_REFERENCED_REQUIRES_RUNTIME_PROOF"
    assert by_name["learnflow_v3.evaluation_pilot"]["status"]=="INTENTIONALLY_OFFLINE_SAFETY_GATE"
    assert not a["production_v3_imports_found"]
    assert any(x["name"]=="run_integrated_binary_clip" for x in
               by_name["learnflow_v3.integration_slice"]["public_api"])
    assert a["scope_files_scanned"]>200
    assert a["module_count"]>=20
