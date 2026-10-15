"""V3-79 preregistered generic composition/font/compiler hostile mutations."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_candidate_acceptance import accept,mock_candidate_bytes
from learnflow_v3.creative_scene_fixtures import fixtures
from learnflow_v3.creative_scene_graph import manim
from learnflow_v3.v377_extent_aware_comparison import refine
from learnflow_v3.v379_visual_hierarchy import compact,COMPARISON_ABS_X
from learnflow_v3.v375_creative_native_gate import preflight
from scripts.run_v3_54_model_candidate_quality import ROOT,NAMES,case_run

REG=ROOT/"benchmarks/learnflowbench/v3/v3_79_visual_hierarchy_preregister.json"

def accepted(case):
    result,diag=accept(mock_candidate_bytes(fixtures()[case]))
    assert result is not None,diag
    return result

def fframes(story):
    return [120]*len(story.beats)

def composition(case):
    d=accepted(case)
    story=d["storyboard"]
    coords,v377=refine(story,d["layout"])
    mapped,proof=compact(story,coords)
    return d,story,coords,mapped,proof


def test_prereg_and_production_boundary():
    r=json.loads(REG.read_text())
    assert r["checkpoint"]=="V3-79"
    assert r["kind"]=="FIRST_CHILD_PREREG_BEFORE_CODE"
    assert r["parent"]["draft_pr"]==115
    assert r["parent"]["sha"]=="de011bad4e76c7dd15110ac0085384fbd931e3b9"
    assert r["baseline"]["artifact_id"]==11943953684
    assert r["restrictions"]["model_api_calls"]==0
    assert r["restrictions"]["production"]=="BLOCKED"
    assert r["restrictions"]["no_original_video_overwrite"] if "no_original_video_overwrite" in r["restrictions"] else r["restrictions"]["no_frozen_v3_59_v3_61_v3_77_v3_78_media_overwrites"]

@pytest.mark.parametrize("case",list(NAMES.values()))
def test_frozen_creative_layout_preserves_ids_and_strict_geometry(case):
    d,story,old,new,proof=composition(case)
    assert set(old)==set(new)
    assert len(proof["scenes"])==sum(s.layout=="COMPARISON" for s in story.scenes)
    for s in story.scenes:
        assert set(old[s.id])==set(new[s.id])
        if s.layout=="COMPARISON":
            for n in s.nodes:
                x,y=new[s.id][n.id]
                assert abs(x)==COMPARISON_ABS_X
                assert y==old[s.id][n.id][1]
        else:
            assert old[s.id]==new[s.id]
    assert preflight(story,d["facts"],new,fframes(story))["status"]=="PASS_DECLARED_CREATIVE_SCENE_RESERVATIONS"
    assert proof["evidence_claims_modified"] is False
    assert proof["beat_actions_modified"] is False

@pytest.mark.parametrize("case",list(NAMES.values()))
def test_default_manims_identical_and_typographic_profile_actually_compiles(case):
    d,story,old,new,proof=composition(case)
    sec=[10.0]*len(story.beats)
    baseline=manim(story,d["facts"],d["graphs"],old,sec)
    identical=manim(story,d["facts"],d["graphs"],old,sec,hierarchy_v379=False)
    assert baseline==identical
    fresh=manim(story,d["facts"],d["graphs"],new,sec,hierarchy_v379=True)
    assert fresh.startswith("# V3-51 GENERIC HOST COMPILED SOURCE NEVER MODEL PYTHON")
    assert "font_size=30" in fresh
    assert "font_size=27" in fresh
    assert "width=1.20" in fresh
    assert "width=.85,height=" in baseline
    assert "font_size=22" in baseline
    assert "scale_factor=1.07" in fresh
    assert "ReplacementTransform(" not in fresh
    assert "# BEAT_" not in fresh or fresh.count("# BEAT_")==len(story.beats)
    compile(fresh,"<host-manuscript>","exec")

def test_reflow_refuses_moving_non_v377_columns():
    d,story,old,new,proof=composition("tokens_as_network")
    mutated=deepcopy(old)
    target=next(s for s in story.scenes if s.layout=="COMPARISON")
    n=target.nodes[0]
    x,y=mutated[target.id][n.id]
    mutated[target.id][n.id]=(x*.7,y)
    with pytest.raises(Blocked,match="V379_UNRECOGNIZED_OLD_COMPARISON_COLUMN"):
        compact(story,mutated)

def test_missing_node_identity_cannot_launder_native_source():
    d,story,old,new,proof=composition("tokens_as_network")
    mutated=deepcopy(old)
    scene=next(s for s in story.scenes if s.layout=="COMPARISON")
    del mutated[scene.id][scene.nodes[0].id]
    with pytest.raises(Blocked,match="V379_SCENE_OBJECT_IDENTITY_DRIFT"):
        compact(story,mutated)

def test_nan_comparison_x_or_y_rejected():
    d,story,old,new,proof=composition("tokens_as_network")
    scene=next(s for s in story.scenes if s.layout=="COMPARISON")
    for t in [0,1]:
        mutated=deepcopy(old)
        x,y=mutated[scene.id][scene.nodes[0].id]
        mutated[scene.id][scene.nodes[0].id]=(float("nan"),y) if t==0 else (x,float("inf"))
        with pytest.raises(Blocked,match="V379_NONFINITE_SOURCE_COORD"):
            compact(story,mutated)

def test_unknown_scene_id_fails_closed():
    d,story,old,new,proof=composition("tokens_as_network")
    scene=next(s for s in story.scenes if s.layout=="COMPARISON")
    mutated=deepcopy(old)
    del mutated[scene.id]
    with pytest.raises(Blocked,match="V379_MISSING_COMPARISON_SCENE"):
        compact(story,mutated)

def test_heldout_no_comparison_declared_noop():
    d,story,old,new,proof=composition("heldout_symbolic_rewrite")
    assert old==new
    assert proof["status"]=="NO_COMPARISON_IDENTITY_NOOP"

def test_host_source_never_branches_on_case_ids_or_math_values():
    src=(ROOT/"learnflow_v3/v379_visual_hierarchy.py").read_text()
    assert "REQUIRED_MARGIN" in src and "_line_hit" in src
    for marker in ["mock_token_network","score_comparison","board:caption:text",
                   "0.330","0.670","weightright","context","3blue1brown"]:
        assert marker not in src

def test_integration_opt_in_before_v375_manims_and_no_automatic_base_change():
    src=(ROOT/"scripts/run_v3_54_model_candidate_quality.py").read_text()
    assert "hierarchy_v379:bool=False" in src
    assert "V379_REQUIRES_EXISTING_STRICT_V377_AND_V376" in src
    assert src.index("layout,hierarchy_receipt=compact")<src.index("v375_preflight=preflight")
    assert src.index("layout,hierarchy_receipt=compact")<src.index("host_code=manim")
    assert 'hierarchy_v379=hierarchy_v379' in src
    assert "v379_visual_hierarchy_source" in src

def test_new_runner_native_audio_mp4_sha_and_3_real_fixtures():
    src=(ROOT/"scripts/run_v3_79_pedagogical_hierarchy.py").read_text()
    assert "strict_v375=True,runtime_v376=True" in src
    assert "reflow_v377=True,hierarchy_v379=True" in src
    assert "inspect(movie,telemetry,receipt" in src
    assert 'physical["native_movie_sha256"]!=receipt["native_mp4_sha256"]' in src
    assert '"provider_model_api_calls":0' in src
    assert '"final_visual_quality":"NOT_PASS_PENDING_HUMAN_REVIEW"' in src
    assert 'V379_FRESH_DIR_REQUIRED' in src
