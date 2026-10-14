"""V3-73 adversarial generative geometry and native diagnostic contract tests.

Only deterministic synthetic render fixtures. Zero model calls, no human ratings.
"""
from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path

import pytest

from learnflow_v3.generalized_temporal_visual_qa import (
    Frame, Rect, Object, Edge, VisualQAError, make_text, marker,
    validate_frame, validate_timeline, render_frame
)
from scripts.run_v3_73_generalized_visual_qa import (
    REG, BLUEPRINTS, heldout_frames, v372_generic_adapter_audit
)


@pytest.fixture
def frames():
    return heldout_frames("h731_math_numberline")


def replace_object(frame: Frame, name: str, fn) -> Frame:
    return replace(frame, objects=tuple(fn(x) if x.object_id == name else x
                                        for x in frame.objects))


def test_frozen_prereg_prior_to_implementation_and_research_only():
    data = json.loads(REG.read_text())
    assert data["parent"]["pr"] == 108
    assert data["parent"]["sha"] == "149fb7eccdf860eb7ccf9b7b0cf04a493026c0f7"
    assert data["registration"] == "FIRST_CHILD_BEFORE_IMPLEMENTATION"
    assert data["boundaries"]["no_existing_mp4_replacement"] is True
    assert data["boundaries"]["no_model_api"] is True
    assert len(data["locked_holdouts"]) == 3
    assert {v["domain"] for v in data["locked_holdouts"]} == {
        "Mathematics", "Biology", "Computer Science"}


@pytest.mark.parametrize("case", list(BLUEPRINTS))
def test_three_unseen_domain_scenes_all_forty_five_frames(case):
    frames = heldout_frames(case)
    r = validate_timeline(frames, expected_frames=45)
    assert r["geometry"] == "PASS" and r["continuity"] == "PASS"
    assert r["checked_frames"] == 45 and r["max_observed_step_px"] <= 24
    assert render_frame(frames[0]).size == (1280, 720)
    assert render_frame(frames[22]).tobytes() != render_frame(frames[0]).tobytes()
    assert render_frame(frames[44]).tobytes() != render_frame(frames[22]).tobytes()


def test_original_v372_both_cases_are_covered_by_generalized_adapter():
    r = v372_generic_adapter_audit()
    assert r["original_attention_frames_covered"] == 355
    assert r["original_process_frames_covered"] == 344
    assert r["full_exported_ROI_frames_covered"] == 699
    assert r["QA_SCOPE"] == "EXPORTED_ROI_NOT_WHOLE_MP4"


def test_score_label_bar_overlap_rejected_on_generic_unknown_scene(frames):
    f = frames[20]
    # This is NOT "attention" -- directly reproduce collision generically.
    box = next(o for o in f.objects if o.object_id == "node_0")
    corrupted = replace(f, objects=f.objects + (
        make_text("unrelated_label", "score B = 0.707",
                  int(box.rect.left + 10), 320, fontsize=25),))
    with pytest.raises(VisualQAError, match="VISUAL_COLLISION"):
        validate_frame(corrupted)


@pytest.mark.parametrize("index", [1, 15, 21, 31, 44])
def test_circle_penetration_fails_at_intermediate_and_last_frame(frames, index):
    f = frames[index]
    target = next(o for o in f.objects if o.object_id == "node_1")
    broken = replace_object(f, "one_point", lambda o: marker(
        o.object_id, target.rect.left + 7, 344, o.edge_id, radius=12))
    with pytest.raises(VisualQAError, match="MARKER_PENETRATES_NODE"):
        validate_frame(broken)


def test_allow_only_declared_contained_box_text_not_arbitrary_parent(frames):
    f = frames[11]
    good_label = next(o for o in f.objects if o.object_id == "node_0_label")
    assert good_label.parent_id == "node_0"
    bad = replace_object(f, "node_0_label",
                         lambda o: replace(o, parent_id="node_1"))
    with pytest.raises(VisualQAError, match="IMPROPER_PARENT_CONTAINMENT"):
        validate_frame(bad)
    misuse = replace_object(f, "one_point",
                            lambda o: replace(o, parent_id="node_1"))
    with pytest.raises(VisualQAError, match="IMPROPER_PARENT_CONTAINMENT"):
        validate_frame(misuse)


def test_glyph_metadata_mismatch_rejected_not_trusted(frames):
    f = frames[6]
    corrupt = replace_object(f, "heading",
                             lambda o: replace(o, rect=Rect(
                                 o.rect.left, o.rect.top,
                                 o.rect.right+1, o.rect.bottom)))
    with pytest.raises(VisualQAError, match="UNMEASURED_TEXT_BBOX"):
        validate_frame(corrupt)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -4.0])
def test_bad_numeric_coordinates_fail_closed(frames, bad):
    f = replace_object(frames[0], "node_1", lambda o: replace(
        o, rect=replace(o.rect, left=bad)))
    with pytest.raises(VisualQAError, match="V373_"):
        validate_frame(f)


def test_marker_teleport_mid_timeline_fails_not_just_endpoints(frames):
    bad = list(frames)
    at = bad[22]
    m = next(o for o in at.objects if o.kind == "marker")
    cx = (m.rect.left+m.rect.right)/2+55
    bad[22] = replace_object(at, m.object_id,
                             lambda o: marker(o.object_id, cx, 344, o.edge_id))
    with pytest.raises(VisualQAError, match="MARKER_TELEPORT"):
        validate_timeline(bad, expected_frames=45)


def test_missing_or_reordered_frame_is_rejected(frames):
    with pytest.raises(VisualQAError, match="TIMELINE_INCOMPLETE"):
        validate_timeline(frames[:-1], expected_frames=45)
    broken = list(frames)
    broken[13] = replace(broken[13], index=14)
    with pytest.raises(VisualQAError, match="TIMELINE_GAP_OR_REORDER"):
        validate_timeline(broken, expected_frames=45)


def test_replacing_semantic_identity_mid_timeline_fails(frames):
    bad = list(frames)
    bad[22] = replace_object(bad[22], "one_point",
                             lambda o: replace(o, object_id="new_identity"))
    with pytest.raises(VisualQAError, match="SEMANTIC_IDENTITY_OR_EDGE_DRIFT"):
        validate_timeline(bad, expected_frames=45)


def test_moving_static_label_without_identity_or_style_change_fails(frames):
    bad = list(frames)
    bad[22] = replace_object(bad[22], "heading", lambda o: replace(
        o, at=(o.at[0]+20, o.at[1]),
        rect=Rect(o.rect.left+20, o.rect.top,
                  o.rect.right+20, o.rect.bottom)))
    with pytest.raises(VisualQAError, match="STATIC_OBJECT_JUMP"):
        validate_timeline(bad, expected_frames=45)


def test_orphan_marker_or_altered_edge_fails(frames):
    orphan = replace_object(frames[0], "one_point",
                            lambda o: replace(o, edge_id="fake_edge"))
    with pytest.raises(VisualQAError, match="ORPHAN_MARKER"):
        validate_frame(orphan)
    corrupted = list(frames)
    corrupted[20] = replace(corrupted[20], edges=(
        Edge("new_edge", "node_0", "node_1", 344),))
    with pytest.raises(VisualQAError, match="ORPHAN_MARKER|SEMANTIC_IDENTITY_OR_EDGE_DRIFT"):
        validate_timeline(corrupted, expected_frames=45)


def test_unregistered_kind_or_unbounded_object_count_fails(frames):
    invalid = replace_object(frames[0], "node_1",
                             lambda o: replace(o, kind="unmeasured_shader"))
    with pytest.raises(VisualQAError, match="UNKNOWN_SHAPE_KIND"):
        validate_frame(invalid)
    with pytest.raises(VisualQAError, match="INCOMPLETE_GEOMETRY"):
        validate_frame(Frame(0, frames[0].objects[:2], frames[0].edges))


def test_declared_circle_radius_must_match_actual_bbox(frames):
    bad = replace_object(frames[20], "one_point",
                         lambda o: replace(o, radius=27))
    with pytest.raises(VisualQAError, match="UNCERTIFIED_MOVING_MARKER"):
        validate_frame(bad)


def test_clearance_cannot_be_relaxed_by_callers(frames):
    with pytest.raises(VisualQAError, match="MINIMUM_CLEARANCE"):
        validate_frame(frames[5], clearance=0)


def test_text_cannot_escape_parent_even_when_not_touching_other_objects(frames):
    f = frames[9]
    o = next(x for x in f.objects if x.object_id == "node_0_label")
    fake = replace(o, at=(101, 300),
                   rect=make_text("tmp", o.text, 101, 300,
                                  fontsize=o.fontsize).rect)
    broken = replace_object(f, o.object_id, lambda _: fake)
    with pytest.raises(VisualQAError, match="IMPROPER_PARENT_CONTAINMENT"):
        validate_frame(broken)


def test_heldout_report_does_not_claim_visual_clarity_or_lesson_quality():
    reg = json.loads(REG.read_text())
    assert "silent" in reg["metrics"]["native_mp4_requirement"].lower()
    assert reg["metrics"]["negative_cases_min"] >= 10
    assert reg["metrics"]["min_clearance_px"] == 6
