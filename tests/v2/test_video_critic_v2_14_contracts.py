from __future__ import annotations

import math
import pytest

from learnflow_v2.videoqa import (
    REQUIRED_VIDEO_CRITIC_DIMENSIONS,
    VideoCriticDimension,
    VideoCriticInvalidInputError,
    VideoCriticIssue,
    VideoCriticRecommendation,
    VideoCriticRequest,
    VideoCriticResponse,
    VideoCriticStatus,
    VideoIssueSeverity,
    VideoIssueType,
    VideoRecommendationOp,
    VideoSceneSummary,
    VisualModality,
    compute_video_critic_request_hash,
)
from tests.v2.video_critic_v2_14_helpers import assessments, make_request, make_review_response


def test_request_requires_all_five_video_dimensions():
    request = make_request()
    assert request.dimensions == REQUIRED_VIDEO_CRITIC_DIMENSIONS
    payload = request.model_dump(mode="json")
    payload["dimensions"] = [VideoCriticDimension.PACING.value]
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticRequest.model_validate(payload)


def test_request_requires_every_scene_quality_approved():
    request = make_request()
    payload = request.model_dump(mode="json")
    payload["scenes"][1]["scene_quality_approved"] = False
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticRequest.model_validate(payload)


def test_scene_ordinals_must_be_contiguous_and_unique():
    payload = make_request().model_dump(mode="json")
    payload["scenes"][2]["ordinal"] = 5
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticRequest.model_validate(payload)


def test_transitions_must_exactly_cover_adjacent_scenes():
    payload = make_request().model_dump(mode="json")
    payload["transitions"] = payload["transitions"][:1]
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticRequest.model_validate(payload)


def test_total_duration_must_equal_scene_plus_transition_durations():
    payload = make_request().model_dump(mode="json")
    payload["total_duration"] = 10.5
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticRequest.model_validate(payload)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0, True])
def test_request_rejects_invalid_total_duration(bad):
    payload = make_request().model_dump(mode="json")
    payload["total_duration"] = bad
    with pytest.raises(Exception):
        VideoCriticRequest.model_validate(payload)


def test_scene_summary_collections_are_canonical_and_immutable():
    request = make_request()
    scene = request.scenes[1]
    assert scene.concept_keys == ("concept:loss", "concept:prediction")
    with pytest.raises(TypeError):
        scene.concept_keys[0] = "x"


def test_review_issue_must_point_to_specific_scenes():
    with pytest.raises(Exception):
        VideoCriticIssue(
            issue_id="x", issue_type=VideoIssueType.PACING, severity=VideoIssueSeverity.HIGH,
            scene_ids=(), reason="Too fast",
        )


def test_cross_scene_issue_types_require_multiple_scenes():
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticIssue(
            issue_id="x", issue_type=VideoIssueType.VISUAL_REPETITION, severity=VideoIssueSeverity.MEDIUM,
            scene_ids=("s1",), reason="repetition",
        )


def test_transition_continuity_issue_requires_two_scenes_and_one_transition():
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticIssue(
            issue_id="x", issue_type=VideoIssueType.TRANSITION_CONTINUITY, severity=VideoIssueSeverity.HIGH,
            scene_ids=("s1", "s2"), reason="continuity",
        )


def test_only_change_visual_modality_can_set_suggested_modality():
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticRecommendation(
            recommendation_id="x", op=VideoRecommendationOp.ADJUST_PACING, scene_ids=("s1",),
            rationale="slow down", suggested_modality=VisualModality.ILLUSTRATION,
        )


def test_pass_response_cannot_hide_issues():
    review = make_review_response()
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticResponse(status=VideoCriticStatus.PASS, dimension_assessments=assessments(), issues=review.issues, recommendations=review.recommendations)


def test_review_response_requires_issues_and_recommendations():
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticResponse(status=VideoCriticStatus.REVIEW_REQUIRED, dimension_assessments=assessments(VideoCriticDimension.PACING), issues=(), recommendations=())


def test_response_recommendation_must_touch_implicated_scene():
    issue = VideoCriticIssue(
        issue_id="i", issue_type=VideoIssueType.PACING, severity=VideoIssueSeverity.MEDIUM,
        scene_ids=("s1",), reason="pace",
    )
    rec = VideoCriticRecommendation(
        recommendation_id="r", op=VideoRecommendationOp.ADJUST_PACING,
        scene_ids=("s3",), rationale="slow",
    )
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticResponse(status=VideoCriticStatus.REVIEW_REQUIRED, dimension_assessments=assessments(VideoCriticDimension.PACING), issues=(issue,), recommendations=(rec,))


def test_canonical_roundtrip_and_hash_are_stable():
    request = make_request()
    assert VideoCriticRequest.from_canonical_json(request.to_canonical_json()) == request
    assert compute_video_critic_request_hash(request) == compute_video_critic_request_hash(request)
    review = make_review_response()
    assert VideoCriticResponse.from_canonical_json(review.to_canonical_json()) == review


def test_direct_model_construct_bypass_is_revalidated_by_hash_boundary():
    forged = VideoCriticRequest.model_construct(
        schema_version="2.1", video_id="v", final_video_ref="v", video_artifact_hash="a"*64, lesson_goal="x", lesson_objective_ids=(),
        total_duration=1.0, dimensions=(VideoCriticDimension.PACING,), scenes=(), transitions=(),
    )
    with pytest.raises(Exception):
        compute_video_critic_request_hash(forged)


def test_issue_and_recommendation_dimension_maps_are_immutable():
    from learnflow_v2.videoqa import ISSUE_DIMENSION, RECOMMENDATION_DIMENSION
    with pytest.raises(TypeError):
        ISSUE_DIMENSION[VideoIssueType.PACING] = VideoCriticDimension.STYLE
    with pytest.raises(TypeError):
        RECOMMENDATION_DIMENSION[VideoRecommendationOp.ADJUST_PACING] = VideoCriticDimension.STYLE


def test_recommendation_dimension_must_match_issue_dimension_on_same_scene():
    issue = VideoCriticIssue(
        issue_id="style", issue_type=VideoIssueType.STYLE_INCONSISTENCY,
        severity=VideoIssueSeverity.MEDIUM, scene_ids=("s1", "s2"), reason="style mismatch",
    )
    rec = VideoCriticRecommendation(
        recommendation_id="pace", op=VideoRecommendationOp.ADJUST_PACING,
        scene_ids=("s1",), rationale="slow down",
    )
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticResponse(status=VideoCriticStatus.REVIEW_REQUIRED, dimension_assessments=assessments(VideoCriticDimension.STYLE), issues=(issue,), recommendations=(rec,))


def test_request_requires_artifact_hash_provenance_and_unique_frame_refs():
    payload = make_request().model_dump(mode="json")
    payload["video_artifact_hash"] = "bad"
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticRequest.model_validate(payload)

    payload = make_request().model_dump(mode="json")
    payload["scenes"][1]["quality_artifact_hash"] = "bad"
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticRequest.model_validate(payload)

    payload = make_request().model_dump(mode="json")
    payload["scenes"][1]["representative_frame_ref"] = payload["scenes"][0]["representative_frame_ref"]
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticRequest.model_validate(payload)


def test_request_requires_style_and_pedagogical_evidence():
    payload = make_request().model_dump(mode="json")
    payload["scenes"][0]["style_signature"] = []
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticRequest.model_validate(payload)

    payload = make_request().model_dump(mode="json")
    payload["scenes"][0]["learning_objective_ids"] = []
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticRequest.model_validate(payload)

    payload = make_request().model_dump(mode="json")
    payload["lesson_objective_ids"] = ["obj:1", "obj:2", "obj:missing"]
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticRequest.model_validate(payload)


def test_request_rejects_unordered_container_types_instead_of_hash_ordering_them():
    payload = make_request().model_dump(mode="json")
    payload["dimensions"] = set(payload["dimensions"])
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticRequest.model_validate(payload)


def test_response_requires_exact_dimension_assessment_coverage():
    review = make_review_response().model_dump(mode="json")
    review["dimension_assessments"] = review["dimension_assessments"][:-1]
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticResponse.model_validate(review)


def test_response_failed_dimensions_must_match_issue_dimensions():
    review = make_review_response().model_dump(mode="json")
    # Mark pacing failed although there is no pacing issue.
    for assessment in review["dimension_assessments"]:
        if assessment["dimension"] == "PACING":
            assessment["passed"] = False
    with pytest.raises(VideoCriticInvalidInputError):
        VideoCriticResponse.model_validate(review)
