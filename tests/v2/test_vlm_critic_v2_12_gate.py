from __future__ import annotations

import pytest

from learnflow_v2.qa import (
    CriticFailurePolicy,
    CriticGateState,
    CriticProviderError,
    CriticProviderQuotaError,
    CriticProviderUnavailableError,
    CriticStatus,
    QualityMode,
    run_quality_gate,
)
from tests.v2.critic_v2_12_helpers import FakeProvider, fail_report, good_request, pass_report, pass_response, repair_response


def test_deterministic_mode_makes_zero_provider_calls_even_if_provider_given():
    provider = FakeProvider()
    result = run_quality_gate(
        deterministic_report=pass_report(),
        quality_mode=QualityMode.DETERMINISTIC,
        provider=provider,
    )
    assert provider.calls == 0
    assert result.approved is True
    assert result.critic_state == CriticGateState.NOT_REQUESTED


def test_deterministic_failure_blocks_critic_and_zero_provider_calls():
    provider = FakeProvider(result=pass_response())
    result = run_quality_gate(
        deterministic_report=fail_report(),
        quality_mode=QualityMode.CRITIC,
        critic_request=None,
        provider=provider,
    )
    assert provider.calls == 0
    assert result.approved is False
    assert result.critic_state == CriticGateState.SKIPPED_DETERMINISTIC_FAIL


def test_critic_pass_approves_after_deterministic_pass():
    provider = FakeProvider(result=pass_response())
    result = run_quality_gate(
        deterministic_report=pass_report(),
        quality_mode=QualityMode.CRITIC,
        critic_request=good_request(),
        provider=provider,
    )
    assert provider.calls == 1
    assert result.approved is True
    assert result.critic_state == CriticGateState.PASS
    assert result.critic_response.status == CriticStatus.PASS


def test_critic_repair_blocks_publish_until_future_repair_engine():
    provider = FakeProvider(result=repair_response())
    result = run_quality_gate(
        deterministic_report=pass_report(),
        quality_mode=QualityMode.CRITIC,
        critic_request=good_request(),
        provider=provider,
    )
    assert result.approved is False
    assert result.critic_state == CriticGateState.REPAIR_REQUIRED


@pytest.mark.parametrize(
    "exc,state",
    [
        (CriticProviderUnavailableError("offline"), CriticGateState.UNAVAILABLE),
        (TimeoutError("slow"), CriticGateState.TIMEOUT),
        (CriticProviderQuotaError("quota"), CriticGateState.QUOTA_EXCEEDED),
        (CriticProviderError("provider"), CriticGateState.PROVIDER_ERROR),
        (RuntimeError("unexpected"), CriticGateState.PROVIDER_ERROR),
    ],
)
def test_provider_failures_continue_deterministic_approved_output_by_default(exc, state):
    result = run_quality_gate(
        deterministic_report=pass_report(),
        quality_mode=QualityMode.CRITIC,
        critic_request=good_request(),
        provider=FakeProvider(exc=exc),
        failure_policy=CriticFailurePolicy.CONTINUE,
    )
    assert result.approved is True
    assert result.critic_state == state
    assert result.critic_response is None
    assert result.warnings and "critic_unavailable" in result.warnings[0]


def test_strict_policy_blocks_on_provider_outage():
    result = run_quality_gate(
        deterministic_report=pass_report(),
        quality_mode=QualityMode.CRITIC,
        critic_request=good_request(),
        provider=FakeProvider(exc=CriticProviderUnavailableError("offline")),
        failure_policy=CriticFailurePolicy.STRICT,
    )
    assert result.approved is False
    assert result.critic_state == CriticGateState.UNAVAILABLE


def test_missing_provider_is_explicit_unavailable_not_implicit_pass():
    result = run_quality_gate(
        deterministic_report=pass_report(),
        quality_mode=QualityMode.CRITIC,
        critic_request=good_request(),
        provider=None,
    )
    assert result.approved is True
    assert result.critic_state == CriticGateState.UNAVAILABLE
    assert result.warnings


def test_prose_provider_response_becomes_invalid_response_state():
    result = run_quality_gate(
        deterministic_report=pass_report(),
        quality_mode=QualityMode.CRITIC,
        critic_request=good_request(),
        provider=FakeProvider(result="looks good"),
    )
    assert result.approved is True
    assert result.critic_state == CriticGateState.INVALID_RESPONSE


def test_malformed_structured_response_becomes_invalid_response_state():
    result = run_quality_gate(
        deterministic_report=pass_report(),
        quality_mode=QualityMode.CRITIC,
        critic_request=good_request(),
        provider=FakeProvider(result={"status": "PASS", "prose": "looks good"}),
    )
    assert result.critic_state == CriticGateState.INVALID_RESPONSE


def test_unknown_target_in_critic_response_is_invalid_not_actionable():
    payload = repair_response().model_dump(mode="json")
    payload["issues"][0]["targets"] = [{"kind": "NODE", "target_id": "ghost"}]
    payload["patches"][0]["targets"] = [{"kind": "NODE", "target_id": "ghost"}]
    result = run_quality_gate(
        deterministic_report=pass_report(),
        quality_mode=QualityMode.CRITIC,
        critic_request=good_request(),
        provider=FakeProvider(result=payload),
    )
    assert result.critic_state == CriticGateState.INVALID_RESPONSE
    assert result.approved is True


def test_critic_request_must_match_exact_deterministic_report():
    other = pass_report().model_copy(update={"scene_id": "other"})
    with pytest.raises(Exception):
        run_quality_gate(
            deterministic_report=other,
            quality_mode=QualityMode.CRITIC,
            critic_request=good_request(),
            provider=FakeProvider(),
        )


def test_quality_gate_canonical_replay_is_stable():
    kwargs = dict(
        deterministic_report=pass_report(),
        quality_mode=QualityMode.CRITIC,
        critic_request=good_request(),
        provider=FakeProvider(result=pass_response()),
    )
    one = run_quality_gate(**kwargs)
    kwargs["provider"] = FakeProvider(result=pass_response())
    two = run_quality_gate(**kwargs)
    assert one.to_canonical_json() == two.to_canonical_json()


def test_quality_gate_artifact_rejects_forged_warnings_on_success():
    result = run_quality_gate(
        deterministic_report=pass_report(),
        quality_mode=QualityMode.CRITIC,
        critic_request=good_request(),
        provider=FakeProvider(result=pass_response()),
    )
    data = result.model_dump(mode="json")
    data["warnings"] = ["fake"]
    with pytest.raises(Exception):
        type(result).model_validate(data)


def test_repair_result_cannot_be_forged_as_approved():
    result = run_quality_gate(
        deterministic_report=pass_report(),
        quality_mode=QualityMode.CRITIC,
        critic_request=good_request(),
        provider=FakeProvider(result=repair_response()),
    )
    data = result.model_dump(mode="json")
    data["approved"] = True
    with pytest.raises(Exception):
        type(result).model_validate(data)


def test_strict_policy_blocks_invalid_provider_response():
    result = run_quality_gate(
        deterministic_report=pass_report(),
        quality_mode=QualityMode.CRITIC,
        critic_request=good_request(),
        provider=FakeProvider(result="not structured"),
        failure_policy=CriticFailurePolicy.STRICT,
    )
    assert result.approved is False
    assert result.critic_state == CriticGateState.INVALID_RESPONSE


def test_quality_gate_canonical_round_trip():
    result = run_quality_gate(
        deterministic_report=pass_report(),
        quality_mode=QualityMode.CRITIC,
        critic_request=good_request(),
        provider=FakeProvider(result=pass_response()),
    )
    assert type(result).from_canonical_json(result.to_canonical_json()) == result


def test_provider_returning_bypassed_critic_model_is_revalidated_as_invalid_response():
    from learnflow_v2.qa import CriticIssue, CriticIssueSeverity, CriticIssueType, CriticResponse, CriticTargetKind, CriticTargetRef
    invalid = CriticResponse.model_construct(
        schema_version="2.1",
        status=CriticStatus.PASS,
        issues=(
            CriticIssue(
                issue_id="i",
                issue_type=CriticIssueType.READABILITY,
                severity=CriticIssueSeverity.LOW,
                targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
                reason="should invalidate PASS",
            ),
        ),
        patches=(),
    )
    result = run_quality_gate(
        deterministic_report=pass_report(),
        quality_mode=QualityMode.CRITIC,
        critic_request=good_request(),
        provider=FakeProvider(result=invalid),
    )
    assert result.critic_state == CriticGateState.INVALID_RESPONSE
    assert result.approved is True


def test_quality_gate_result_requires_strict_boolean_approval():
    from learnflow_v2.qa import QualityGateResult
    result = run_quality_gate(
        deterministic_report=pass_report(),
        quality_mode=QualityMode.DETERMINISTIC,
    )
    data = result.model_dump(mode="json")
    data["approved"] = 1
    with pytest.raises(Exception):
        QualityGateResult.model_validate(data)


def test_failure_warnings_are_stable_and_do_not_embed_provider_message():
    result = run_quality_gate(
        deterministic_report=pass_report(),
        quality_mode=QualityMode.CRITIC,
        critic_request=good_request(),
        provider=FakeProvider(exc=CriticProviderUnavailableError("secret-token-should-not-leak")),
    )
    assert result.warnings == ("critic_unavailable: provider_unavailable",)
    assert "secret-token" not in result.to_canonical_json()


def test_critic_mode_rejects_wrong_request_type_explicitly():
    with pytest.raises(Exception):
        run_quality_gate(
            deterministic_report=pass_report(),
            quality_mode=QualityMode.CRITIC,
            critic_request="not-a-request",  # type: ignore[arg-type]
            provider=FakeProvider(),
        )
