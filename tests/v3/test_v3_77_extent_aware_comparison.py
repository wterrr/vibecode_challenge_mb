"""V3-77 source-level extent-aware COMPARISON geometry: prereg mutations.

No internet/model. The real Docker H264/AAC, native glyph contrast and native
pixel claims belong to the separate Actions physical render step.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from learnflow_v3.creative_candidate_acceptance import accept,mock_candidate_bytes
from learnflow_v3.creative_scene_fixtures import fixtures
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.v375_creative_native_gate import preflight,box,SIZE,REQUIRED_MARGIN
from learnflow_v3.v377_extent_aware_comparison import (
    reflow_comparison,refine,CONTENT_BOTTOM,CONTENT_TOP,
    MIN_SAME_COL_SEPARATION,
)
from scripts.run_v3_54_model_candidate_quality import ROOT,NAMES

REG=ROOT/"benchmarks/learnflowbench/v3/v3_77_extent_aware_comparison_preregister.json"

def accepted(which):
    out,meta=accept(mock_candidate_bytes(fixtures()[which]))
    assert meta["status"]=="ACCEPTED_OFFLINE_CONTRACT_ONLY"
    assert out
    return out

def fixture_scene(kinds=("CHART","CHART","MATH","SHAPE","MATH","MATH")):
    return SimpleNamespace(id="heldout_permuted_kinds",layout="COMPARISON",
        nodes=[SimpleNamespace(id=f"n{i}",kind=kind) for i,kind in enumerate(kinds)],
        relations=[])

def frames(story):
    return [120]*len(story.beats)

def test_first_child_preregister_before_code_and_original_hashes_frozen():
    d=json.loads(REG.read_text())
    assert d["kind"]=="FIRST_CHILD_PREREG_BEFORE_IMPLEMENTATION"
    assert d["parent"]["draft_pr"]==113
    assert d["parent"]["sha"]=="06508f48299fc3098d2f81e8042c4a3a9ce1f20c"
    assert d["baseline"]["artifact"]==11884427679
    assert d["baseline"]["model_calls"]==0
    assert d["boundaries"]["no_merge_main"] and d["boundaries"]["no_historical_media_overwrite"]

def test_reproduce_original_token_comparison_collision_then_fix():
    doc=accepted("tokens_as_network")
    story=doc["storyboard"];original=doc["layout"]
    with pytest.raises(Blocked,match="V373_VISUAL_COLLISION:weightright:context"):
        preflight(story,doc["facts"],original,frames(story))
    repaired,report=refine(story,original)
    assert report["status"]=="GENERATED_GEOMETRY_CERTIFIED"
    assert repaired!=original
    result=preflight(story,doc["facts"],repaired,frames(story))
    assert result["status"]=="PASS_DECLARED_CREATIVE_SCENE_RESERVATIONS"
    mix=next(s for s in story.scenes if s.id=="mixture")
    obj={n.id:n for n in mix.nodes}
    a=box(obj["weightright"],repaired["mixture"]["weightright"])
    b=box(obj["context"],repaired["mixture"]["context"])
    assert a.bottom+REQUIRED_MARGIN<=b.top or b.bottom+REQUIRED_MARGIN<=a.top

@pytest.mark.parametrize("case",list(NAMES.values()))
def test_reuse_three_frozen_stories_and_preserve_identity(case):
    doc=accepted(case)
    original=doc["layout"];story=doc["storyboard"]
    revised,receipt=refine(story,original)
    assert len(receipt["scenes"])>=1
    assert set(revised)==set(original)
    for s in story.scenes:
        assert set(revised[s.id])==set(original[s.id])
        if s.layout!="COMPARISON":
            assert revised[s.id]==original[s.id]
    assert preflight(story,doc["facts"],revised,frames(story))["status"]==(
        "PASS_DECLARED_CREATIVE_SCENE_RESERVATIONS"
    )

@pytest.mark.parametrize("kinds",[
    ("CHART","SHAPE","MATH","MATH"),
    ("SHAPE","CHART","TEXT","EQUATION","MATH"),
    ("CHART","CHART","MATH","SHAPE","MATH","MATH"),
    ("MATH","TEXT","CHART","SHAPE","MATH","EQUATION"),
])
def test_unseen_kind_permutations_have_no_self_collisions(kinds):
    s=fixture_scene(kinds)
    result,evidence=reflow_comparison(s)
    assert len(result)==len(kinds)
    assert evidence["reserved_height_world"]<=CONTENT_TOP-CONTENT_BOTTOM
    assert min(evidence["row_clearances_world"],default=MIN_SAME_COL_SEPARATION)>0
    for i,a in enumerate(s.nodes):
        for b in s.nodes[i+1:]:
            x=box(a,result[a.id]);y=box(b,result[b.id])
            assert (x.right+REQUIRED_MARGIN<=y.left or
                    y.right+REQUIRED_MARGIN<=x.left or
                    x.bottom+REQUIRED_MARGIN<=y.top or
                    y.bottom+REQUIRED_MARGIN<=x.top)

def test_impossible_six_high_charts_fails_closed_not_clips():
    with pytest.raises(Blocked,match="V377_CONTENT_BUDGET_EXCEEDED"):
        reflow_comparison(fixture_scene(("CHART",)*6))

def test_unknown_kind_no_exporter_cannot_pass():
    with pytest.raises(Blocked,match="V377_UNEXPORTED_RENDERER_KIND"):
        reflow_comparison(fixture_scene(("SHAPE","SHAPE","NEW_KIND")))

def test_duplicate_node_ids_rejected():
    s=fixture_scene()
    s.nodes[1].id=s.nodes[0].id
    with pytest.raises(Blocked,match="V377_DUPLICATE_NODE_IDS"):
        reflow_comparison(s)

@pytest.mark.parametrize("number",[0,1,2,7,10])
def test_unsupported_count_rejected(number):
    kinds=["SHAPE"]*number
    with pytest.raises(Blocked,match="V377_UNSUPPORTED_NODE_COUNT"):
        reflow_comparison(fixture_scene(kinds))

def test_wrong_layout_cannot_be_reflowed_silently():
    s=fixture_scene()
    s.layout="GRID"
    with pytest.raises(Blocked,match="V377_UNSUPPORTED_LAYOUT"):
        reflow_comparison(s)

def test_route_to_missing_identity_fails_closed():
    s=fixture_scene()
    s.relations=[SimpleNamespace(id="e",source="n0",target="missing")]
    with pytest.raises(Blocked,match="V377_RELATION_LOST_ENDPOINT"):
        reflow_comparison(s)

def test_legacy_default_path_remains_original_and_new_is_explicit_optin():
    s=(ROOT/"scripts/run_v3_54_model_candidate_quality.py").read_text()
    assert "reflow_v377:bool=False" in s
    assert 'if reflow_v377:' in s
    assert s.index("layout,reflow_receipt=refine")<s.index("_docker_manim(folder,source)")
    assert s.index("layout,reflow_receipt=refine")<s.index("v375_preflight=preflight")
    assert "V377_NEEDS_BOTH_STRICT_NATIVE_QUALITY_GATES" in s
    assert "v377_generated_extent_aware_comparison" in s

def test_source_solver_never_branches_on_fixture_or_topic_words():
    s=(ROOT/"learnflow_v3/v377_extent_aware_comparison.py").read_text()
    for forbidden in ["mock_token_network","weightright","context","score_comparison",
                      "Attention source","V376_NATIVE_TEXT_COLOR_CONTRAST_LT_4P5"]:
        assert forbidden not in s
    assert "SIZE" in s and "_edge_route" in s and "_line_hit" in s

def test_new_native_output_preserves_strict_a3_and_frozen_sha_requirements():
    src=(ROOT/"scripts/run_v3_77_native_comparison_layout.py").read_text()
    assert "strict_v375=True,runtime_v376=True,reflow_v377=True" in src
    assert 'V377_FRESH_VERSIONED_DIRECTORY_REQUIRED' in src
    assert '"source":"FROZEN_HOST_SYNTHETIC_NOT_REAL_MODEL"' in src
    assert '"model_api_calls":0' in src
    assert '"human_viewer_quality":"NOT_PASS_PENDING_FRESH_REVIEW"' in src
    assert 'proof["native_mp4_sha256"]!=sha256(movie.read_bytes()).hexdigest()' in src
