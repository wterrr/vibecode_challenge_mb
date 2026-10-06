"""Video-level critic orchestration for LearnFlow V2 CP2.14."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any, Protocol

from pydantic import ValidationError

from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.videoqa.errors import (
    VideoCriticInvalidInputError,
    VideoCriticProviderError,
    VideoCriticProviderQuotaError,
    VideoCriticProviderUnavailableError,
)
from learnflow_v2.videoqa.schema import (
    VideoCriticFailurePolicy,
    VideoCriticGateState,
    VideoCriticRequest,
    VideoCriticResponse,
    VideoCriticResult,
    VideoCriticStatus,
    validate_video_critic_response_scope,
)


class VideoCriticProvider(Protocol):
    def critique_video(self, request: VideoCriticRequest) -> VideoCriticResponse | Mapping[str, Any]: ...


def compute_video_critic_request_hash(request: VideoCriticRequest) -> str:
    if not isinstance(request, VideoCriticRequest):
        raise VideoCriticInvalidInputError("request must be VideoCriticRequest")
    validated = VideoCriticRequest.model_validate(request.model_dump(mode="json"))
    return hashlib.sha256(canonical_json(validated).encode("utf-8")).hexdigest()


def _failure_result(
    request: VideoCriticRequest,
    failure_policy: VideoCriticFailurePolicy,
    state: VideoCriticGateState,
    warning: str,
) -> VideoCriticResult:
    return VideoCriticResult(
        video_id=request.video_id,
        request=request,
        request_hash=compute_video_critic_request_hash(request),
        failure_policy=failure_policy,
        state=state,
        response=None,
        approved=failure_policy == VideoCriticFailurePolicy.CONTINUE,
        warnings=(warning,),
    )


def run_video_critic(
    *,
    request: VideoCriticRequest,
    provider: VideoCriticProvider | None,
    failure_policy: VideoCriticFailurePolicy = VideoCriticFailurePolicy.CONTINUE,
) -> VideoCriticResult:
    """Run optional video-level critique after all scene-level quality gates pass."""
    if not isinstance(request, VideoCriticRequest):
        raise VideoCriticInvalidInputError("request must be VideoCriticRequest")
    request = VideoCriticRequest.model_validate(request.model_dump(mode="json"))
    if not isinstance(failure_policy, VideoCriticFailurePolicy):
        raise VideoCriticInvalidInputError("failure_policy must be VideoCriticFailurePolicy")
    if provider is None:
        return _failure_result(request, failure_policy, VideoCriticGateState.UNAVAILABLE, "video_critic_unavailable: provider_not_configured")

    try:
        raw_response = provider.critique_video(request)
    except VideoCriticProviderQuotaError:
        return _failure_result(request, failure_policy, VideoCriticGateState.QUOTA_EXCEEDED, "video_critic_unavailable: quota_exceeded")
    except VideoCriticProviderUnavailableError:
        return _failure_result(request, failure_policy, VideoCriticGateState.UNAVAILABLE, "video_critic_unavailable: provider_unavailable")
    except TimeoutError:
        return _failure_result(request, failure_policy, VideoCriticGateState.TIMEOUT, "video_critic_unavailable: timeout")
    except VideoCriticProviderError:
        return _failure_result(request, failure_policy, VideoCriticGateState.PROVIDER_ERROR, "video_critic_unavailable: provider_error")
    except Exception as exc:
        return _failure_result(
            request,
            failure_policy,
            VideoCriticGateState.PROVIDER_ERROR,
            f"video_critic_unavailable: unexpected_provider_error:{type(exc).__name__}",
        )

    try:
        if isinstance(raw_response, VideoCriticResponse):
            response = VideoCriticResponse.model_validate(raw_response.model_dump(mode="json"))
        elif isinstance(raw_response, Mapping):
            response = VideoCriticResponse.model_validate(dict(raw_response))
        else:
            raise VideoCriticInvalidInputError("video critic provider must return structured mapping/VideoCriticResponse; prose is rejected")
        validate_video_critic_response_scope(response, request)
    except (ValidationError, VideoCriticInvalidInputError):
        return _failure_result(request, failure_policy, VideoCriticGateState.INVALID_RESPONSE, "video_critic_unavailable: invalid_structured_response")

    state = VideoCriticGateState.PASS if response.status == VideoCriticStatus.PASS else VideoCriticGateState.REVIEW_REQUIRED
    return VideoCriticResult(
        video_id=request.video_id,
        request=request,
        request_hash=compute_video_critic_request_hash(request),
        failure_policy=failure_policy,
        state=state,
        response=response,
        approved=response.status == VideoCriticStatus.PASS,
        warnings=(),
    )
