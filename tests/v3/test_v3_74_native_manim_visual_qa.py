"""V3-74 research-only regression: actual V3-45 Manim pipeline QA opt-in.

All source fixtures synthetic HOST, never model-authored learner videos.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.semantic_scene_offline_fixtures import (
    synthetic_process_wire, synthetic_fraction_wire
)
from learnflow_v3.semantic_scene_wire import decode_model_facing_scene
from learnflow_v3.v374_native_manim_visual_gate import (
    certify_before_render,traversal_segments,enforce_after_native,
)
from scripts.run_v3_45_semantic_offline import ROOT,run as original_runner
from scripts.run_v3_74_native_integrated import PREREG

BEAT_FRAMES=[130,127,129,128]


@pytest.fixture
def process_scene():
    return decode_model_facing_scene(synthetic_process_wire())


def test_first_child_prereg_was_before_any_code():
    p=json.loads(PREREG.read_text())
    assert p["checkpoint"]=="V3-74" and p["kind"]=="FIRST_CHILD_PREREG_BEFORE_CODE"
    assert p["parent"]["pr"]==109
    assert p["parent"]["sha"]=="0eb88ad7116637799fa662af9ebafbbff6127341"
    assert p["prohibitions"]["model_api_post"]==0
    assert not p["prohibitions"]["merge_main"]


def test_actual_existing_process_compiler_exports_every_traverse_frame(process_scene):
    r=certify_before_render(process_scene,BEAT_FRAMES)
    assert r["checkpoint"]=="V3-74"
    assert r["family"]=="ordered_process"
    assert r["generic_contract"]=="V3-73_VALIDATE_TIMELINE"
    assert len(r["traversal_segments"])==2
    assert r["traversal_frame_count"]>10
    assert all(x["geometry_status"]=="PASS" for x in r["traversal_segments"])
    assert sum(x["v373_geometry_frames_checked"] for x in r["traversal_segments"])==r["traversal_frame_count"]
    assert r["scope"]=="PROCESS_NODES_AND_CURSOR_EXPORTED_ROI_ONLY"


def test_native_process_source_has_pre_and_post_gate_in_correct_order():
    s=(ROOT/"scripts/run_v3_45_semantic_offline.py").read_text()
    assert s.index("temporal_preflight = certify_before_render") < s.index(
        "raw_manim,sandbox=_docker_manim")
    assert s.index("temporal_native = enforce_after_native") > s.index(
        "mux=deterministic_mux")
    assert s.index("temporal_native = enforce_after_native") < s.index(
        "(dest/\"offline_case_receipt.json\").write_text")
    assert 'quality_gate_v374:bool=False' in s
    assert 'V374_UNSUPPORTED_FAMILY_OR_VISUAL_MODE_NO_EXPORTER' in s


@pytest.mark.parametrize("frames",[
    [130,127,129], [130,127,129,-2],
    [130,0,129,128], [130,127,129,True],
])
def test_missing_or_bad_physical_audio_clock_blocks(process_scene,frames):
    with pytest.raises(Blocked,match="V374_AUDIO_CLOCK_UNCERTIFIED"):
        certify_before_render(process_scene,frames)


def test_original_score_marker_mutation_enters_node_mid_animation_and_fails(process_scene):
    # The original bad marker endpoint is at a node centre; a previously
    # accepted geometry-only compiler may silently allow this penetration.
    with pytest.raises(Blocked,match="V374_GENERIC_V373_TIMELINE_REJECTED"):
        certify_before_render(process_scene,BEAT_FRAMES,
                              marker_end_override_world=0.0)


def test_fail_closed_fraction_family_has_no_process_exporter():
    fraction=decode_model_facing_scene(synthetic_fraction_wire())
    with pytest.raises(Blocked,match="V374_NO_EXPORTER_FOR_FAMILY"):
        certify_before_render(fraction,BEAT_FRAMES)


def test_non_horizontal_process_motion_without_exporter_rejected(process_scene):
    # Pydantic construct/update is used ONLY as an adversarial host test;
    # production input must pass strict decode before the export.
    updated=[]
    for obj in process_scene.graphics:
        if obj.id=="verify":
            updated.append(obj.model_copy(update={"y":1.0}))
        else:
            updated.append(obj)
    mutated=process_scene.model_copy(update={"graphics":updated})
    with pytest.raises(Blocked,match="V374_NO_EXPORTER_FOR_NON_HORIZONTAL_OR_REVERSED_PATH"):
        certify_before_render(mutated,BEAT_FRAMES)


def test_reversed_route_without_exporter_blocks(process_scene):
    # Bypass Pydantic semantic validation only inside deliberately corrupted
    # fixture, to exercise native-specific boundary fails.
    mutated=[]
    for obj in process_scene.graphics:
        if obj.id=="edge_start_verify":
            mutated.append(obj.model_copy(update={"src":"verify","dst":"start"}))
        else:
            mutated.append(obj)
    broken=process_scene.model_copy(update={"graphics":mutated})
    with pytest.raises((Blocked,ValueError),match="V374_|V345_"):
        certify_before_render(broken,BEAT_FRAMES)


def test_orphan_traversal_event_preflight_fails(process_scene):
    beats=list(process_scene.beats)
    events=list(beats[1].events)
    i=next(i for i,e in enumerate(events) if e.kind=="traverse_edge")
    events[i]=events[i].model_copy(update={"target":"not_an_edge"})
    beats[1]=beats[1].model_copy(update={"events":events})
    broken=process_scene.model_copy(update={"beats":beats})
    with pytest.raises(Blocked,match="V374_UNCERTIFIED_TRAVERSAL_EDGE"):
        certify_before_render(broken,BEAT_FRAMES)


def test_missing_traversal_or_duplicate_route_blocks(process_scene):
    beats=list(process_scene.beats)
    events=list(beats[2].events)
    events=[x for x in events if x.kind!="traverse_edge"]
    beats[2]=beats[2].model_copy(update={"events":events})
    broken=process_scene.model_copy(update={"beats":beats})
    with pytest.raises(Blocked,match="V374_TRAVERSAL_COVERAGE_INCOMPLETE"):
        certify_before_render(broken,BEAT_FRAMES)


@pytest.mark.parametrize("fake",[
    {"checkpoint":"V3-73","family":"ordered_process","traversal_frame_count":50},
    {"checkpoint":"V3-74","family":"fraction_equivalence","traversal_frame_count":50},
    {"checkpoint":"V3-74","family":"ordered_process","traversal_frame_count":0},
])
def test_native_gate_refuses_unverified_geometry_receipt(process_scene,tmp_path,fake):
    movie=tmp_path/"fake.mp4"
    movie.write_bytes(b"TEST_ONLY fake synthetic bytes not H264")
    with pytest.raises(Blocked,match="V374_MISSING_VALIDATED_UPSTREAM_RECEIPT"):
        enforce_after_native(process_scene,BEAT_FRAMES,movie,fake)


def test_native_gate_refuses_missing_native_video_even_if_geometry_passes(process_scene,tmp_path):
    r=certify_before_render(process_scene,BEAT_FRAMES)
    with pytest.raises(Blocked,match="V374_MISSING_NATIVE_MOVIE"):
        enforce_after_native(process_scene,BEAT_FRAMES,
                             tmp_path/"not_existing.mp4",r)


def test_native_gate_refuses_corrupt_decoded_video(process_scene,tmp_path):
    r=certify_before_render(process_scene,BEAT_FRAMES)
    garbage=tmp_path/"TEST_ONLY_not_a_video.mp4"
    garbage.write_bytes(b"\0"*8000)
    with pytest.raises(Blocked,match="V374_FULL_NATIVE_DECODE_FAILED"):
        enforce_after_native(process_scene,BEAT_FRAMES,garbage,r)


def test_missing_or_wrong_selected_family_is_not_a_no_qa_fallback(tmp_path):
    for requested in (None,{"v345-synthetic-fractions"},
                      {"v345-synthetic-process","v345-synthetic-fractions"}):
        out=tmp_path/f"case_{len(list(tmp_path.iterdir()))}"
        out.mkdir()
        with pytest.raises(Blocked,match="V374_UNSUPPORTED_FAMILY_OR_VISUAL_MODE_NO_EXPORTER"):
            original_runner(ROOT,out,quality_gate_v374=True,selected_fixtures=requested)
        assert not list(out.glob("**/*.mp4"))
    out=tmp_path/"noqa_selection"
    out.mkdir()
    with pytest.raises(Blocked,match="V374_SELECTION_REQUIRES_STRICT_VISUAL_QA"):
        original_runner(ROOT,out,selected_fixtures={"v345-synthetic-process"})
    assert not list(out.glob("**/*.mp4"))


def test_visual_quality_animations_not_instrumented_by_native_exporter(tmp_path):
    out=tmp_path/"unsupported_indicate"
    out.mkdir()
    with pytest.raises(Blocked,match="V374_UNSUPPORTED_FAMILY_OR_VISUAL_MODE_NO_EXPORTER"):
        original_runner(ROOT,out,visual_quality=True,
                        quality_gate_v374=True,
                        selected_fixtures={"v345-synthetic-process"})


def test_default_two_family_v345_source_path_is_retained():
    script=(ROOT/"scripts/run_v3_45_semantic_offline.py").read_text()
    assert 'report={"checkpoint":"V3-74" if quality_gate_v374 else "V3-45"' in script
    assert 'if quality_gate_v374 else cases' in script
    assert '"V345_SYNTHETIC_NOT_REAL_MODEL"' not in script
