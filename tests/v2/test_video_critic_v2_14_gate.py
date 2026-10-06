from __future__ import annotations

import pytest

from learnflow_v2.videoqa import (
    VideoCriticFailurePolicy,
    VideoCriticGateState,
    VideoCriticProviderError,
    VideoCriticProviderQuotaError,
    VideoCriticProviderUnavailableError,
    VideoCriticResponse,
    VideoCriticStatus,
    run_video_critic,
)
from tests.v2.video_critic_v2_14_helpers import assessments, make_request, make_review_response


class Provider:
    def __init__(self, value=None, exc: Exception | None = None):
        self.value = value
        self.exc = exc
        self.calls = 0

    def critique_video(self, request):
        self.calls += 1
        if self.exc is not None:
            raise self.exc
        return self.value


def test_structured_pass_approves_video():
    provider = Provider(VideoCriticResponse(status=VideoCriticStatus.PASS, dimension_assessments=assessments()))
    result = run_video_critic(request=make_request(), provider=provider)
    assert provider.calls == 1
    assert result.state == VideoCriticGateState.PASS
    assert result.approved is True


def test_structured_review_blocks_and_points_to_specific_scenes():
    response = make_review_response()
    result = run_video_critic(request=make_request(), provider=Provider(response))
    assert result.state == VideoCriticGateState.REVIEW_REQUIRED
    assert result.approved is False
    assert result.response is not None
    assert result.response.issues[0].scene_ids


def test_unknown_scene_from_provider_becomes_invalid_response():
    response = make_review_response().model_dump(mode="json")
    response["issues"][0]["scene_ids"] = ["s1", "ghost"]
    result = run_video_critic(request=make_request(), provider=Provider(response))
    assert result.state == VideoCriticGateState.INVALID_RESPONSE
    assert result.approved is True


def test_continuity_issue_must_match_actual_transition_endpoints():
    response = make_review_response().model_dump(mode="json")
    continuity = next(item for item in response["issues"] if item["issue_type"] == "TRANSITION_CONTINUITY")
    continuity["scene_ids"] = ["s1", "s3"]
    result = run_video_critic(request=make_request(), provider=Provider(response))
    assert result.state == VideoCriticGateState.INVALID_RESPONSE


def test_prose_provider_response_is_rejected():
    result = run_video_critic(request=make_request(), provider=Provider("looks good"))
    assert result.state == VideoCriticGateState.INVALID_RESPONSE
    assert result.approved is True


def test_model_construct_invalid_response_is_revalidated():
    forged = VideoCriticResponse.model_construct(schema_version="2.1", status=VideoCriticStatus.PASS, dimension_assessments=assessments(), issues=make_review_response().issues, recommendations=())
    result = run_video_critic(request=make_request(), provider=Provider(forged))
    assert result.state == VideoCriticGateState.INVALID_RESPONSE


@pytest.mark.parametrize(
    "exc,state",
    [
        (VideoCriticProviderUnavailableError("off"), VideoCriticGateState.UNAVAILABLE),
        (VideoCriticProviderQuotaError("quota"), VideoCriticGateState.QUOTA_EXCEEDED),
        (TimeoutError("slow"), VideoCriticGateState.TIMEOUT),
        (VideoCriticProviderError("bad"), VideoCriticGateState.PROVIDER_ERROR),
        (RuntimeError("unexpected"), VideoCriticGateState.PROVIDER_ERROR),
    ],
)
def test_provider_failures_continue_by_default(exc, state):
    result = run_video_critic(request=make_request(), provider=Provider(exc=exc))
    assert result.state == state
    assert result.approved is True
    assert result.warnings


def test_strict_provider_failure_blocks_publish():
    result = run_video_critic(
        request=make_request(), provider=None,
        failure_policy=VideoCriticFailurePolicy.STRICT,
    )
    assert result.state == VideoCriticGateState.UNAVAILABLE
    assert result.approved is False


def test_result_is_bound_to_exact_request_hash():
    request = make_request()
    result = run_video_critic(request=request, provider=Provider(VideoCriticResponse(status=VideoCriticStatus.PASS, dimension_assessments=assessments())))
    from learnflow_v2.videoqa import compute_video_critic_request_hash
    assert result.request_hash == compute_video_critic_request_hash(request)


def test_public_result_rejects_stale_or_forged_request_hash():
    from learnflow_v2.videoqa import VideoCriticResult, compute_video_critic_request_hash
    request = make_request()
    response = VideoCriticResponse(status=VideoCriticStatus.PASS, dimension_assessments=assessments())
    with pytest.raises(Exception):
        VideoCriticResult(
            video_id=request.video_id,
            request=request,
            request_hash="0" * 64,
            failure_policy=VideoCriticFailurePolicy.CONTINUE,
            state=VideoCriticGateState.PASS,
            response=response,
            approved=True,
            warnings=(),
        )
    valid = VideoCriticResult(
        video_id=request.video_id,
        request=request,
        request_hash=compute_video_critic_request_hash(request),
        failure_policy=VideoCriticFailurePolicy.CONTINUE,
        state=VideoCriticGateState.PASS,
        response=response,
        approved=True,
        warnings=(),
    )
    assert valid.request_hash == compute_video_critic_request_hash(request)


def test_public_result_rejects_response_scoped_to_unknown_scene():
    from learnflow_v2.videoqa import (
        VideoCriticIssue, VideoCriticRecommendation, VideoCriticResult,
        VideoIssueSeverity, VideoIssueType, VideoRecommendationOp,
        compute_video_critic_request_hash,
    )
    request = make_request()
    issue = VideoCriticIssue(
        issue_id="i", issue_type=VideoIssueType.PACING, severity=VideoIssueSeverity.MEDIUM,
        scene_ids=("ghost",), reason="pace",
    )
    rec = VideoCriticRecommendation(
        recommendation_id="r", op=VideoRecommendationOp.ADJUST_PACING,
        scene_ids=("ghost",), rationale="slow",
    )
    response = VideoCriticResponse(status=VideoCriticStatus.REVIEW_REQUIRED, dimension_assessments=assessments(__import__("learnflow_v2.videoqa", fromlist=["VideoCriticDimension"]).VideoCriticDimension.PACING), issues=(issue,), recommendations=(rec,))
    with pytest.raises(Exception):
        VideoCriticResult(
            video_id=request.video_id,
            request=request,
            request_hash=compute_video_critic_request_hash(request),
            failure_policy=VideoCriticFailurePolicy.CONTINUE,
            state=VideoCriticGateState.REVIEW_REQUIRED,
            response=response,
            approved=False,
            warnings=(),
        )


def test_pixel_or_renderer_commands_have_no_schema_escape_hatch():
    payload = make_review_response().model_dump(mode="json")
    payload["recommendations"][0]["x"] = 512
    payload["recommendations"][0]["renderer_command"] = "move_to(512, 100)"
    result = run_video_critic(request=make_request(), provider=Provider(payload))
    assert result.state == VideoCriticGateState.INVALID_RESPONSE
