"""V3-75 creative graph → real Manim QA adversarial / holdout tests.

These tests do NOT fabricate real model results or assert full-frame visual
quality merely from synthetic geometry.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import pytest

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_scene_graph import validate
from learnflow_v3.creative_scene_fixtures import fixtures
from learnflow_v3.v375_creative_native_gate import (
    preflight, native_gate, _line_hit, box, ALLOWED_ACTIONS
)
from learnflow_v3.creative_candidate_acceptance import accept,mock_candidate_bytes
from scripts.run_v3_54_model_candidate_quality import ROOT,NAMES
from scripts.run_v3_75_creative_native_qa import REG


def typed(case):
    o,d=accept(mock_candidate_bytes(fixtures()[case]))
    assert d["status"]=="ACCEPTED_OFFLINE_CONTRACT_ONLY"
    return o


def beatframes(story):
    return [120]*len(story.beats)


def test_preregister_before_code_and_three_frozen_fixture_names():
    r=json.loads(REG.read_text())
    assert r["kind"]=="FIRST_CHILD_BEFORE_IMPLEMENTATION"
    assert r["parent"]["pr"]==110
    assert r["parent"]["sha"]=="daace9c14ad51fc08f150e44692885da2a325fce"
    assert r["case_rules"]["allow_abstain"] is True
    assert r["boundary"]["model_api_post"]==0
    assert r["frozen_cases"]==list(NAMES)
    assert r["metrics"]["minimum_mutations"]>=12


@pytest.mark.parametrize("name",list(NAMES.values()))
def test_creative_real_host_fixtures_either_pass_or_fail_closed(name):
    data=typed(name)
    try:
        q=preflight(data["storyboard"],data["facts"],data["layout"],
                    beatframes(data["storyboard"]))
    except Blocked as e:
        assert str(e).startswith("V375_"),repr(e)
    else:
        assert q["checkpoint"]=="V3-75"
        assert q["status"]=="PASS_DECLARED_CREATIVE_SCENE_RESERVATIONS"
        assert q["all_physical_frame_times_reserved"]==len(data["storyboard"].beats)*120
        assert q["scope"]=="CONSERVATIVE_OBJECT_RESERVATION_NOT_RUNTIME_GLYPH_PIXELS"


@pytest.mark.parametrize("index", [0,1,2])
def test_unsafe_nodes_collision_mutation_detected(index):
    data=typed(list(NAMES.values())[index])
    layout=deepcopy(data["layout"])
    s=data["storyboard"].scenes[0]
    a,b=s.nodes[:2]
    layout[s.id][b.id]=layout[s.id][a.id]
    with pytest.raises(Blocked,match="V375_GENERIC_V373_REJECTED"):
        preflight(data["storyboard"],data["facts"],layout,
                  beatframes(data["storyboard"]))


@pytest.mark.parametrize("family_mutation",["move","hide","replace"])
def test_unexported_dynamic_actions_fail_closed(family_mutation):
    data=typed("tokens_as_network")
    story=data["storyboard"]
    old=story.beats[0]
    action=old.actions[0].model_copy(update={"kind":family_mutation})
    beats=list(story.beats)
    beats[0]=old.model_copy(update={"actions":[action]+list(old.actions[1:])})
    damaged=story.model_copy(update={"beats":beats})
    with pytest.raises(Blocked,match="V375_DYNAMIC_ACTION_NO_COMPLETE_EXPORTER"):
        preflight(damaged,data["facts"],data["layout"],beatframes(story))


@pytest.mark.parametrize("bad", [[120], [120,120,0,120],
                                 [120,120,-8,120], [True,120,120,120]])
def test_missing_or_invalid_physical_frame_clock(bad):
    data=typed("tokens_as_network")
    with pytest.raises(Blocked,match="V375_MISSING_PHYSICAL_BEAT_FRAMES"):
        preflight(data["storyboard"],data["facts"],data["layout"],bad)


def test_underdeclared_object_in_layout_rejected():
    data=typed("tokens_as_network")
    l=deepcopy(data["layout"])
    scene=data["storyboard"].scenes[0]
    del l[scene.id][scene.nodes[0].id]
    with pytest.raises(Blocked,match="V375_UNEXPORTED_SCENE_OBJECT"):
        preflight(data["storyboard"],data["facts"],l,
                  beatframes(data["storyboard"]))


def test_unknown_graphical_object_kind_rejected():
    data=typed("tokens_as_network")
    story=data["storyboard"]
    scenes=list(story.scenes)
    scene=scenes[0]
    old=scene.nodes[0]
    new=old.model_copy(update={"kind":"GPU_SHADER"})
    scenes[0]=scene.model_copy(update={"nodes":[new]+list(scene.nodes[1:])})
    damaged=story.model_copy(update={"scenes":scenes})
    with pytest.raises(Blocked,match="V375_UNKNOWN_RENDERED_OBJECT_KIND"):
        preflight(damaged,data["facts"],data["layout"],beatframes(story))


def test_marker_route_segment_vs_third_party_object_collision():
    from learnflow_v3.generalized_temporal_visual_qa import Rect
    target=Rect(140,140,170,170)
    assert _line_hit((100,150),(200,150),target)
    assert _line_hit((100,100),(200,200),target)
    assert not _line_hit((100,200),(200,200),target)
    assert _line_hit((139,120),(139,190),target,6)


def test_unsupported_gate_cannot_pass_with_missing_mp4(tmp_path):
    with pytest.raises(Blocked,match="V375_MISSING_NATIVE_MOVIE"):
        native_gate(tmp_path/"missing.mp4",513,
                    {"checkpoint":"V3-75","status":"PASS_DECLARED_CREATIVE_SCENE_RESERVATIONS"})


def test_forged_preflight_cannot_pass_actual_movie_gate(tmp_path):
    movie=tmp_path/"fake.mp4"
    movie.write_bytes(b"garbage"*9000)
    with pytest.raises((Blocked,Exception)):
        native_gate(movie,513,{"checkpoint":"V3-74","status":"PASS"})


def test_no_case_name_specific_rules_inside_generic_quality_validator():
    source=(ROOT/"learnflow_v3/v375_creative_native_gate.py").read_text()
    assert "tokens_as_network" not in source
    assert "heldout_symbolic_rewrite" not in source
    assert "scores_as_comparison" not in source
    assert "validate_timeline" in source and "_edge_route" in source


def test_real_creative_runner_pre_and_post_order_and_opt_in():
    src=(ROOT/"scripts/run_v3_54_model_candidate_quality.py").read_text()
    assert "strict_v375:bool=False" in src
    assert src.index("v375_preflight=preflight") < src.index("render,sandbox=_docker_manim")
    assert src.index("v375_native=native_gate") > src.index("mux=deterministic_mux")
    assert src.index("v375_native=native_gate") < src.index('folder/"native_quality_receipt.json"')
    assert "if strict_v375" in src


def test_no_production_or_model_claim_laundered():
    report=(ROOT/"reports/v3_75_creative_native_qa.md")
    # This test runs once report is committed and must keep scope honest.
    txt=report.read_text()
    assert "NOT_CERTIFIED" in txt and "BLOCKED" in txt
