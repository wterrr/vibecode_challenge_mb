"""V3-46 visual-quality harness and opt-in shared style adversarial controls.

These are design/layout CONTRACT checks. Native pixel evidence is separately
exercised in the V3-46 CI with actual MP4s and frozen baseline artifacts.
Human ratings remain blank by definition and cannot be fabricated by CI.
"""
from __future__ import annotations

import ast
from copy import deepcopy
import csv
import json
import os
from pathlib import Path

import pytest

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.semantic_scene_offline_fixtures import fixture_cases
from learnflow_v3.semantic_scene_wire import decode_model_facing_scene,compile_scene
from learnflow_v3.visual_quality_system import (
    safe_rectangles,caption_max_width,frame_lines,panel_lines,
    beat_focus_lines,text_style_lines,style_receipt,
    SAFE_HORIZONTAL,SAFE_VERTICAL
)
from scripts.run_v3_46_visual_quality import _descriptors,_rubric,RATINGS

ROOT=Path(__file__).resolve().parents[2]


def test_preregister_is_immutable_and_stacked_after_v345_fix():
    p=json.loads((ROOT/"benchmarks/learnflowbench/v3/v3_46_visual_quality_preregister.json").read_text())
    assert p["checkpoint"]=="V3-46" and p["registered_before_implementation"] is True
    assert p["parent_pr"]==79 and p["parent_sha"]=="646a82c021b17400aafa1dfd30a0a157c930ec10"
    assert p["model_http_calls"]==0 and p["production"]=="BLOCKED"
    assert p["visual_quality_rubric"]["human_acceptance"].startswith("Requires independent human")
    assert len(p["visual_quality_rubric"]["dimensions"])==6


@pytest.mark.parametrize("fixture",fixture_cases().keys())
def test_two_families_have_same_compiler_semantics_and_opt_in_presentation(fixture):
    scene=decode_model_facing_scene(fixture_cases()[fixture])
    durations=[8.666667,8.466667,8.533333,8.533333]
    before=compile_scene(scene,durations)
    after=compile_scene(scene,durations,visual_quality=True)
    assert before!=after
    assert "V346 SHARED_VISUAL_SYSTEM" not in before
    assert "V346 SHARED_VISUAL_SYSTEM" in after
    assert "LEARNFLOW  /" in after
    assert "CMU Serif" in after
    assert "v346_beats[3]" in after
    assert "v346_rule" in after
    assert "v346_footrule" in after
    assert "FadeIn(" in after
    assert "self.wait(.8)" in after or "self.wait(0.80000)" in after
    assert "__import__" not in after and "subprocess" not in after
    compile(after,"<v346_untrusted_model_data_host_compiled_only>","exec")
    if scene.family=="ordered_process":
        assert "process" in fixture
        assert "Line(edge_start_verify.get_start(),edge_start_verify.get_end())" in after
        assert "buff=0" in after
        assert "caption = Text(" in after
        assert "TransformFromCopy" not in after
    else:
        assert "TransformFromCopy" in after
        assert "v346_panel_0" in after and "v346_panel_1" in after
        assert "(1×2)/(2×2) = 2/4" in after


def test_design_colors_and_safe_metadata_hierarchy_are_bounded():
    r=style_receipt()
    assert r["font"]=="CMU Serif" and r["node_caption_inside_inset"]>=.22
    assert r["content_safe_x"]<7 and r["header_rule"]>3
    assert r["provenance"]=="HOST_OWNED_VISUAL_SYSTEM_NO_PROVIDER_AUTHORED_CODE"
    for family in ("fraction_equivalence","ordered_process"):
        chrome="\n".join(frame_lines(family))
        assert "v346_eyebrow" in chrome
        assert "v346_footrule" in chrome
        assert "v346_beats = VGroup()" in chrome
        assert ".set_z_index" not in chrome
        assert all(len(beat_focus_lines(i))==2 for i in range(4))


@pytest.mark.parametrize("bad",["unsupported_family","tiny_caption","text_outside_safe_area",
                                 "panel_outside","unsupported_label_kind","invalid_beat_number"])
def test_visual_contract_rejects_bad_layout_without_repair(bad):
    scene=decode_model_facing_scene(fixture_cases()["v345-synthetic-process"])
    if bad=="unsupported_family":
        with pytest.raises(Blocked):
            frame_lines("arbitrary_scene")
    elif bad=="tiny_caption":
        with pytest.raises(Blocked,match="CAPTION_WIDTH_INSUFFICIENT"):
            caption_max_width(.6)
    elif bad=="text_outside_safe_area":
        bad_scene=scene.model_copy(deep=True)
        label=next(x for x in bad_scene.graphics if x.kind=="label")
        label.x=5.6
        label.text="An extremely long public title with no space at the frame side"
        with pytest.raises(Blocked,match="OUTSIDE_SAFE_CONTENT_RECT"):
            safe_rectangles(scene.family,bad_scene.graphics)
    elif bad=="panel_outside":
        with pytest.raises(Blocked,match="PANEL_OUT_OF_SAFE_AREA"):
            panel_lines([-5.,2.])
    elif bad=="unsupported_label_kind":
        with pytest.raises(Blocked):
            text_style_lines("title","hidden_python", "Hello",0,0,"#fff",3)
    else:
        with pytest.raises(Blocked,match="INVALID_BEAT_INDEX"):
            beat_focus_lines(5)


def test_both_synthetic_scene_label_bounds_pass_without_rewriting_claims():
    for raw in fixture_cases().values():
        scene=decode_model_facing_scene(raw)
        checked=safe_rectangles(scene.family,scene.graphics)
        assert checked["safe_area_pass"] is True
        assert len(checked["bounds"])>=2
        assert all(abs(x["x"])+x["width_budget"]/2<SAFE_HORIZONTAL for x in checked["bounds"])
    assert SAFE_VERTICAL<4


def test_human_rubric_is_empty_and_no_fake_preference_or_scores(tmp_path):
    rubric=_rubric(tmp_path)
    with rubric.open() as stream:
        rows=list(csv.DictReader(stream))
    assert len(rows)==2*len(RATINGS)
    assert all(r["review_status"]=="AWAITING_INDEPENDENT_HUMAN" for r in rows)
    assert all(not r["v346_score_1to5"] and not r["baseline_score_1to5"] for r in rows)
    assert not any(r["blind_reviewer_id"] for r in rows)


def test_sample_metrics_are_descriptive_not_human_quality_pass():
    import numpy as np
    sample=np.zeros((12,180,320,3),dtype=np.uint8)
    sample[0,42:122,50:210]=220
    sample[1:,45:125,52:212]=210
    outcome=_descriptors(sample)
    assert outcome["sample_count"]==12
    assert outcome["bright_boundary_pixel_max"]==0
    assert outcome["foreground_occupancy_mean"]>0
    assert "cannot establish continuous motion" in outcome["sample_index_note"]


def test_ci_artifacts_and_two_source_frozen_baselines_no_keys():
    wf=(ROOT/".github/workflows/v3-46-visual-quality-benchmark.yml").read_text()
    runner=(ROOT/"scripts/run_v3_46_visual_quality.py").read_text()
    assert "38198567269" in wf
    assert "v3-45-two-FAMILY-OFFLINE-MP4-NOT-MODEL" in wf
    assert "run_v3_46_visual_quality.py" in wf
    assert "v3_46_visual_quality_receipt.json" in wf
    assert "OPENROUTER_API_KEY" not in wf
    assert "Pillow" in wf
    assert "model_requests" in runner
    assert "V3_46=NATIVE_LAYOUT_QA_PASS_HUMAN_VISUAL_QUALITY_PENDING" in runner
    assert "human_visual_quality_status" in runner
    assert "same_audio_beats_and_model_facing_wire" in runner
