"""V3-72 original-defect reproduction + exhaustive source-geometry regression.

All tests are structural and native rendering only. No fabricated human data.
"""
from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path

from PIL import ImageChops, ImageStat
import pytest

from learnflow_v3.pedagogical_storytelling_slice import (
    WIDTH, HEIGHT, FPS, facts, plan
)
import learnflow_v3.v372_timeline_safe_renderer as safe
from scripts.run_v3_72_native_collision_repair import timeline_boundaries, run


def frozen_expected():
    return json.loads(
        (Path(__file__).resolve().parents[2] /
         "benchmarks/learnflowbench/v3/v3_72_collision_repair_preregister.json"
        ).read_text())


def test_prereg_before_new_video_generation_and_source_shas():
    reg = frozen_expected()
    assert reg["parent"]["sha"] == "67738eb4ea9d007841da53ab204157972b8328c0"
    assert reg["scope"].startswith("Research-only versioned")
    assert reg["restrictions"]["model_post_count"] == 0
    assert reg["restrictions"]["frozen_study_media_mutations"] == 0
    assert len(reg["original_physical_sources"]["attention_reversed_query"]["sha256"]) == 64


def test_mutation_reproduces_user_attention_source_defect():
    # Exact original V3-57 bar A spans 365..411, while score B title starts
    # at anchor y=399. Old code never measured these intersections.
    broken = replace(safe.SAFE_LAYOUT, score_a_y=365,
                     score_b_label_y=399)
    with pytest.raises(safe.VisualCollision,
                       match="ATTENTION_SCORE_TEXT_BAR_COLLISION"):
        safe.frame_geometry("attention_reversed_query", 3, .5, broken)
    repaired = safe.frame_geometry("attention_reversed_query", 3, .5)
    for label in repaired["score_labels"]:
        for bar in repaired["score_bars"]:
            assert not safe.overlap(label, bar, 6)


def test_mutation_reproduces_user_process_marker_inside_action():
    # Frozen V3-59 source endpoint center=540, ACTION begins at x=510.
    # Even with radius-only 13, overlap is 43px of rightmost extent.
    broken = replace(safe.SAFE_LAYOUT, action_marker_endpoint_x=540)
    assert 540 + 13 - 510 == 43
    with pytest.raises(safe.VisualCollision,
                       match="PROCESS_MARKER_PENETRATES_ACTION"):
        safe.frame_geometry("process_heldout_unknown", 2, 1.0, broken)


def test_intermediate_collision_mutation_caught_not_only_endpoint():
    # Starts on clear external edge, penetrates the node during travel.
    wrong = replace(safe.SAFE_LAYOUT, action_marker_endpoint_x=525)
    assert safe.frame_geometry("process_heldout_unknown", 2, 0, wrong)
    with pytest.raises(safe.VisualCollision,
                       match="PROCESS_MARKER_PENETRATES_ACTION"):
        safe.verify_entire_timeline("process_heldout_unknown",
                                    [0, 50, 100, 150, 200, 250],
                                    wrong)


@pytest.mark.parametrize("case,nframes", [
    ("attention_reversed_query", 355),
    ("process_heldout_unknown", 344),
])
def test_all_real_native_frame_times_safe_on_all_five_beats(case, nframes):
    raw = frozen_expected()["original_physical_sources"][case]["beats_s"]
    boundaries = [0] + [round(v[1]*FPS) for v in raw[:-1]] + [nframes]
    audit = safe.verify_entire_timeline(case, boundaries)
    assert audit["validated_frames"] == nframes
    assert audit["all_frames_no_overlap"]
    for beat in range(5):
        for t in (0, .001, .19, .53, .58, .91, 1):
            data = safe.frame_geometry(case, beat, t)
            assert data["timeline_geometry"] == "CLEAR"
            image = safe.render_safe_frame(plan(case), beat, t)
            assert image.size == (WIDTH, HEIGHT)


def test_process_end_reaches_external_edge_not_interior_and_unknown():
    at_end = safe.frame_geometry("process_heldout_unknown", 2, 1)
    assert at_end["center_x"] == 488
    assert at_end["rightmost_stroked_px"] == 504
    assert at_end["gap_px"] >= 6
    assert at_end["center_y"] == 337
    assert at_end["action_active"] is True
    assert at_end["condition"] == "UNKNOWN_NOT_VERIFIED"
    assert not safe.frame_geometry("process_heldout_unknown", 2, .5)["action_active"]
    assert facts("process_heldout_unknown")["success_claim"] is False


def test_image_before_during_after_is_real_semantic_visual_difference():
    p = plan("process_heldout_unknown")
    before = safe.render_safe_frame(p, 2, 0)
    middle = safe.render_safe_frame(p, 2, .48)
    after = safe.render_safe_frame(p, 2, 1)
    roi = (372, 320, 508, 354)
    assert before.crop(roi).tobytes() != middle.crop(roi).tobytes()
    assert middle.crop(roi).tobytes() != after.crop(roi).tobytes()
    # Actual ACTION region changes only after arrival; not an invented PASS.
    assert before.getpixel((641, 303)) == middle.getpixel((641, 303))
    assert after.getpixel((641, 303)) != middle.getpixel((641, 303))


@pytest.mark.parametrize("field,value", [
    ("score_b_label_y", 390),
    ("score_a_y", 389),
    ("score_b_y", 387),
    ("geometry_clearance", 0),
])
def test_text_bar_collision_and_false_clearance_mutations(field, value):
    g = replace(safe.SAFE_LAYOUT, **{field: value})
    with pytest.raises(safe.VisualCollision, match="V372_"):
        safe.frame_geometry("attention_reversed_query", 3, .65, g)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -0.1, 1.1])
def test_nonfinite_or_out_of_range_progress_rejected(bad):
    with pytest.raises(safe.VisualCollision,
                       match="NONFINITE_OR_OUT_OF_RANGE_TIME"):
        safe.frame_geometry("process_heldout_unknown", 2, bad)


def test_unregistered_case_cannot_generate_false_safe_result():
    with pytest.raises(safe.VisualCollision, match="CASE_OR_BEAT"):
        safe.frame_geometry("fraction_equivalence", 2, .5)


def test_no_existing_study_media_or_release_result_baked_in():
    assert frozen_expected()["claims"]["human_quality"] == "UNRATED"
    assert frozen_expected()["claims"]["release"] == "BLOCKED"
    assert safe.PROCESS_MARKER_ENDPOINT < safe.ACTION_RECT[0]
