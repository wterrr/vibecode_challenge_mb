"""V3-15 frozen-demand state-machine expansion: real MP4 and adversarial semantics."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_bench import load_corpus
from learnflow_v3.models import SemanticContractError
from learnflow_v3.sequence_renderer import SequenceRenderProfile
from learnflow_v3.state_machine_renderer import (
    StateMachineLesson,StateMachineRenderEvidence,certify_source,draw_state_frame,
    stable_layout,render_state_machine,verify_state_machine_video,
)
from scripts.verify_v3_pattern_coverage import curated_spec,run,PROFILE
from scripts.verify_v3_benchmark_protocol import PROTOCOL_PATH,validate

LOOKUP={topic.topic_id:topic for topic in load_corpus().topics}


@pytest.fixture(scope="module")
def real_mp4s(tmp_path_factory):
    path=tmp_path_factory.mktemp("v3_15_real_goldens")
    result=run(path)
    return path,result


def _good(topic_id="lfb-006-cs"):
    return curated_spec(LOOKUP[topic_id])


def _alter(spec,fn):
    d=spec.model_dump(mode="json")
    fn(d)
    return StateMachineLesson.model_validate(d)


def _invalid(topic_id,change,match=None):
    d=_good(topic_id).model_dump(mode="json")
    change(d)
    with pytest.raises(ValidationError,match=match):
        StateMachineLesson.model_validate(d)


def test_demand_pre_registered_exact_two_of_twelve(real_mp4s):
    directory,data=real_mp4s
    validate(json.loads(PROTOCOL_PATH.read_text()))
    assert data["prereg_topics_total"]==12
    assert data["candidate_evidence_count"]==2 and data["not_candidate_evidence_count"]==10
    assert data["new_candidate_families"]==["STATE_MACHINE"]
    assert data["frozen_pilot_unmodified"] is True
    assert data["c5_seventy_percent_usage"]=="UNMEASURED"
    assert data["production_router_registered"] is False
    assert all(c["status"]=="NOT_PRODUCTION_ROUTED" for c in data["topic_demand_audit"])
    assert [c["topic_id"] for c in data["topic_demand_audit"] if
        c["decision"]=="AUTHOR_CURATED_STATE_MACHINE_CANDIDATE"]==[
            "lfb-006-cs","lfb-016-cs"]


@pytest.mark.parametrize("topic_id",["lfb-006-cs","lfb-016-cs"])
def test_real_decoded_h264_golden_semantic_motion_and_hashes(real_mp4s,topic_id):
    directory,data=real_mp4s
    video=directory/f"state_machine_{topic_id}.mp4"
    payload=next(x for x in data["real_golden_clips"] if x["topic_id"]==topic_id)
    evidence=StateMachineRenderEvidence.model_validate(payload["render_evidence"])
    spec=StateMachineLesson.model_validate(payload["lesson_source_model"])
    assert spec.renderer_family=="STATE_MACHINE"
    assert spec.no_concept_card_fallback
    assert spec.registered_in_v3_04_router is False
    assert evidence.publication_blocked is True
    assert evidence.audio_sync=="UNMEASURED"
    assert evidence.frame_count==PROFILE.frames_per_step()*len(spec.beats)
    assert evidence.video_sha256==hashlib.sha256(video.read_bytes()).hexdigest()
    assert set(evidence.stable_node_centers)=={s.state_id for s in spec.states}
    assert min(evidence.decoded_state_roi_delta)>0.5
    assert min(evidence.decoded_within_beat_motion)>0.06
    verify_state_machine_video(
        spec=spec,topic=LOOKUP[topic_id],video_path=video,
        evidence=evidence,profile=PROFILE)


@pytest.mark.parametrize("topic_id",["lfb-006-cs","lfb-016-cs"])
def test_cycles_or_branch_are_genuinely_present(topic_id):
    spec=_good(topic_id)
    directed={(e.source_id,e.target_id) for e in spec.transitions}
    if topic_id=="lfb-006-cs":
        assert ("sent","waiting") in directed and ("retry","sent") in directed
        assert ("waiting","retry") in directed
    else:
        assert ("waiting","retry") in directed and ("retry","waiting") in directed
    assert any(sum(e.source_id==s.state_id for e in spec.transitions)>1 for s in spec.states)
    assert len(set(spec.beats))==len(spec.beats)


def test_unique_render_centers_stable_if_state_declaration_order_mutated():
    spec=_good()
    changed=_alter(spec,lambda d:d["states"].reverse())
    assert stable_layout(spec,PROFILE)==stable_layout(changed,PROFILE)


@pytest.mark.parametrize("topic_id",["lfb-006-cs","lfb-016-cs"])
def test_all_state_boxes_clear_header_and_footer_bands(topic_id):
    spec=_good(topic_id)
    centers=stable_layout(spec,PROFILE)
    # The drawn header divider is y=103/540*height; the footer starts at y=476/540*height.
    y_divider=103*PROFILE.height/540
    footer=476*PROFILE.height/540
    half_h=26*PROFILE.height/540
    for x,y in centers.values():
        assert y-half_h > y_divider+8
        assert y+half_h < footer-8
        assert x-77*PROFILE.width/960 > 10
        assert x+77*PROFILE.width/960 < PROFILE.width-10


def test_hidden_concept_card_variant_and_prod_router_claim_rejected():
    _invalid("lfb-006-cs",lambda d:d.update(renderer_family="CONCEPT_CARD"))
    _invalid("lfb-006-cs",lambda d:d.update(no_concept_card_fallback=False))
    _invalid("lfb-006-cs",lambda d:d.update(registered_in_v3_04_router=True))
    _invalid("lfb-006-cs",lambda d:d.update(independent_factual_verification=True))


def test_bad_trace_transition_or_trigger_rejected():
    _invalid("lfb-006-cs",lambda d:d["beats"][1].update(via_transition_id="wrong"))
    _invalid("lfb-006-cs",lambda d:d["beats"][1].update(trigger="fake"))
    _invalid("lfb-006-cs",lambda d:d["beats"][1].update(state_id="retry"))
    _invalid("lfb-006-cs",lambda d:d["beats"][0].update(via_transition_id="send",trigger="send"))
    _invalid("lfb-006-cs",lambda d:d["beats"][-1].update(state_id="waiting"))


def test_duplicate_graph_identity_rejected():
    _invalid("lfb-006-cs",lambda d:d["states"][1].update(state_id=d["states"][0]["state_id"]))
    _invalid("lfb-006-cs",lambda d:d["transitions"][1].update(transition_id=d["transitions"][0]["transition_id"]))
    _invalid("lfb-006-cs",lambda d:d["beats"][1].update(beat_id=d["beats"][0]["beat_id"]))


def test_guarded_branch_and_terminal_semantics_fail_closed():
    _invalid("lfb-016-cs",lambda d:d["transitions"][0].update(target_id="invented"))
    _invalid("lfb-016-cs",lambda d:d["transitions"][0].update(source_id="commit"))
    _invalid("lfb-016-cs",lambda d:next(x for x in d["states"] if x["state_id"]=="commit").update(terminal=False))
    _invalid("lfb-016-cs",lambda d:d["transitions"].append({
        "transition_id":"extra","source_id":"commit","target_id":"prepare","trigger":"undo"}))
    _invalid("lfb-016-cs",lambda d:d["transitions"].append({
        "transition_id":"cycle_self","source_id":"waiting","target_id":"waiting","trigger":"retry"}))


def test_source_identity_rehash_after_frozen_query_mutation_rejected():
    spec=_good()
    altered=spec.model_copy(update={"topic_query_sha256":"0"*64})
    with pytest.raises(SemanticContractError,match="FROZEN_QUERY_DRIFT"):
        certify_source(altered,topic=LOOKUP["lfb-006-cs"])
    with pytest.raises(SemanticContractError,match="FROZEN_DEMAND_TOPIC_MISMATCH"):
        certify_source(spec,topic=LOOKUP["lfb-016-cs"])
    with pytest.raises(ValueError,match="ABSTAIN"):
        curated_spec(LOOKUP["lfb-019-math"])


def test_stale_video_and_rehashed_pixel_evidence_rejected(real_mp4s,tmp_path):
    directory,data=real_mp4s
    payload=data["real_golden_clips"][0]
    spec=StateMachineLesson.model_validate(payload["lesson_source_model"])
    evidence=StateMachineRenderEvidence.model_validate(payload["render_evidence"])
    path=directory/"state_machine_lfb-006-cs.mp4"
    altered=tmp_path/"modified.mp4"
    altered.write_bytes(path.read_bytes()+b"appended-tail")
    with pytest.raises(SemanticContractError,match="VIDEO_OR_SOURCE_FINGERPRINT_MISMATCH"):
        verify_state_machine_video(spec=spec,topic=LOOKUP[spec.topic_id],
                                  video_path=altered,evidence=evidence,profile=PROFILE)
    forged=evidence.model_copy(update={"decoded_state_roi_delta":tuple(100 for _ in evidence.decoded_state_roi_delta)})
    with pytest.raises(SemanticContractError,match="FORGED_VISIBLE_STATE_DELTA"):
        verify_state_machine_video(spec=spec,topic=LOOKUP[spec.topic_id],
                                  video_path=path,evidence=forged,profile=PROFILE)


def test_renderer_refuses_to_overwrite_trusted_mp4(real_mp4s):
    directory,_=real_mp4s
    p=directory/"state_machine_lfb-006-cs.mp4"
    h=hashlib.sha256(p.read_bytes()).hexdigest()
    with pytest.raises(SemanticContractError,match="UNSAFE_VIDEO_DESTINATION"):
        render_state_machine(spec=_good(),topic=LOOKUP["lfb-006-cs"],
                             output_path=p,profile=PROFILE)
    assert hashlib.sha256(p.read_bytes()).hexdigest()==h


def test_cyclic_is_not_rewritten_as_process_dag_or_any_card():
    spec=_good("lfb-016-cs")
    from learnflow_v3.code_process_renderer import layout_process
    from learnflow_v2.scenegraph import SceneGraph
    graph=SceneGraph.model_validate({
        "scene_id":"negative-cyclic-process",
        "purpose":"EXPLAIN",
        "layout_intent":{"type":"PROCESS","reading_direction":"LEFT_TO_RIGHT"},
        "nodes":[{"id":s.state_id,"kind":"CONCEPT","label":s.label}
                 for s in spec.states],
        "relations":[{"id":e.transition_id,"kind":"FLOW",
                      "source":e.source_id,"target":e.target_id} for e in spec.transitions],
    })
    with pytest.raises(SemanticContractError,match="CYCLIC_GRAPH"):
        layout_process(graph,PROFILE)
    assert spec.renderer_family=="STATE_MACHINE"
    assert spec.no_concept_card_fallback


def test_no_claim_of_real_audio_or_human_gains():
    spec=_good()
    for item in ({"real_audio_sync_verified":True},
                 {"independent_factual_verification":True},
                 {"source_origin":"MODEL_ASSERTED"}):
        _invalid("lfb-006-cs",lambda d:d.update(item))
