from __future__ import annotations

import pytest

from learnflow_v2.qa import QAInvalidInputError, build_critic_overlay, build_critic_request, select_event_aware_frames
from tests.v2.critic_v2_12_helpers import good_layout, good_request, good_schedule, good_scene, pass_report


def test_event_aware_frame_sampling_is_deterministic_and_semantic():
    samples = select_event_aware_frames(good_schedule())
    assert [round(s.timestamp, 2) for s in samples] == [0.0, 0.4, 1.5, 4.45, 5.0]
    assert samples[0].reasons == ("SCENE_START",)
    assert samples[1].reasons == ("AFTER_ENTER:e_enter",)
    assert samples[2].reasons == ("AFTER_TRANSFORM:e_move",)
    assert samples[3].reasons == ("BEFORE_EXIT:e_exit",)
    assert samples[4].reasons == ("SCENE_END",)
    assert select_event_aware_frames(good_schedule()) == samples


def test_sampling_merges_same_timestamp_reasons_without_randomness():
    schedule = good_schedule().model_copy(update={"scene_duration": 4.45})
    # model_copy does not revalidate; build a validated schedule with 5.0 scene end instead.
    samples = select_event_aware_frames(good_schedule(), before_exit_lead_seconds=0.0)
    assert [s.sample_id for s in samples] == [f"sample_{i:03d}" for i in range(len(samples))]
    assert all(tuple(sorted(s.reasons)) == s.reasons for s in samples)


def test_sampling_rejects_nonfinite_or_negative_lead():
    for value in (-0.1, float("nan"), float("inf"), True):
        with pytest.raises(QAInvalidInputError):
            select_event_aware_frames(good_schedule(), before_exit_lead_seconds=value)


def test_overlay_contains_stable_ids_anchors_regions_and_normalized_geometry():
    overlay = build_critic_overlay(good_layout())
    assert [e.element_id for e in overlay.elements] == ["n1", "n2"]
    assert overlay.elements[0].anchor_cell == "C02"
    assert overlay.elements[1].anchor_cell == "D05"
    assert all(e.semantic_region == "CONTENT" for e in overlay.elements)
    assert all(0 <= e.rect.left < e.rect.right <= 1 for e in overlay.elements)
    assert all(0 <= e.rect.top < e.rect.bottom <= 1 for e in overlay.elements)


def test_overlay_canonical_order_independent_of_layout_box_order():
    assert build_critic_overlay(good_layout()) == build_critic_overlay(good_layout(reverse=True))


def test_critic_request_requires_exact_frame_refs():
    schedule = good_schedule()
    samples = select_event_aware_frames(schedule)
    refs = {s.sample_id: f"frame://{s.sample_id}" for s in samples[:-1]}
    with pytest.raises(QAInvalidInputError):
        build_critic_request(
            narration="Narration",
            scene_graph=good_scene(),
            layout_graph=good_layout(),
            motion_schedule=schedule,
            deterministic_report=pass_report(),
            frame_refs=refs,
        )


def test_critic_request_cannot_be_built_from_failed_deterministic_report():
    from tests.v2.critic_v2_12_helpers import fail_report
    schedule = good_schedule()
    refs = {s.sample_id: f"frame://{s.sample_id}" for s in select_event_aware_frames(schedule)}
    with pytest.raises(QAInvalidInputError):
        build_critic_request(
            narration="Narration",
            scene_graph=good_scene(),
            layout_graph=good_layout(),
            motion_schedule=schedule,
            deterministic_report=fail_report(),
            frame_refs=refs,
        )


def test_critic_request_is_canonical_across_layout_input_order():
    assert good_request().to_canonical_json() == good_request(reverse_layout=True).to_canonical_json()


def test_critic_request_contains_no_raw_pixel_geometry_fields():
    payload = good_request().model_dump(mode="json")
    assert "frame_width" not in str(payload)
    assert "frame_height" not in str(payload)
    first_box = payload["layout_boxes"][0]
    assert set(first_box["rect"]) == {"left", "top", "right", "bottom"}


def test_direct_critic_request_rejects_forged_overlay_and_out_of_bounds_frame():
    request = good_request()
    data = request.model_dump(mode="json")
    data["frames"][0]["overlay"]["elements"][0]["anchor_cell"] = "A01"
    with pytest.raises(QAInvalidInputError):
        type(request).model_validate(data)

    data = request.model_dump(mode="json")
    data["frames"][-1]["selection"]["timestamp"] = 999.0
    with pytest.raises(QAInvalidInputError):
        type(request).model_validate(data)


def test_direct_critic_request_rejects_unknown_motion_target():
    request = good_request()
    data = request.model_dump(mode="json")
    data["motion_events"][0]["target"] = "ghost"
    with pytest.raises(QAInvalidInputError):
        type(request).model_validate(data)


def test_direct_critic_request_rejects_missing_scene_start_or_end_samples():
    request = good_request()
    for index in (0, -1):
        data = request.model_dump(mode="json")
        data["frames"].pop(index)
        with pytest.raises(QAInvalidInputError):
            type(request).model_validate(data)


def test_direct_critic_request_rejects_missing_event_aware_sample_or_forged_reason():
    request = good_request()
    data = request.model_dump(mode="json")
    data["frames"] = [f for f in data["frames"] if "AFTER_TRANSFORM:e_move" not in f["selection"]["reasons"]]
    with pytest.raises(QAInvalidInputError):
        type(request).model_validate(data)

    data = request.model_dump(mode="json")
    data["frames"][1]["selection"]["reasons"] = ["SCENE_START"]
    with pytest.raises(QAInvalidInputError):
        type(request).model_validate(data)
