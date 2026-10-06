"""Deterministic assembly of validated Hermes specialist research outputs."""

from __future__ import annotations

import json
from typing import Any, Iterable

from agent_contracts import AgentContractError

from .merge import merge_specialist_findings
from .models import (
    ConceptResearchFindings,
    EvidenceResearchFindings,
    MisconceptionResearchFindings,
    ResearchOrchestrationPlan,
    ResearchOrchestrationResult,
    ResearchRole,
)


_ROLE_MODELS = {
    ResearchRole.CONCEPT: ConceptResearchFindings,
    ResearchRole.EVIDENCE: EvidenceResearchFindings,
    ResearchRole.MISCONCEPTION: MisconceptionResearchFindings,
}


def _extract_json_object(text: str) -> dict[str, Any]:
    """Extract one JSON object from a specialist summary without trusting prose wrappers."""

    raw = str(text or "").strip()
    if not raw:
        raise AgentContractError("specialist summary is empty")

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(raw):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(raw[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise AgentContractError("specialist summary does not contain a JSON object")


def _index_results(
    results: Iterable[dict[str, Any]],
    *,
    expected_count: int,
) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    rows = list(results)
    if len(rows) != expected_count:
        raise AgentContractError(
            f"expected exactly {expected_count} specialist results; got {len(rows)}"
        )

    for entry in rows:
        if not isinstance(entry, dict):
            raise AgentContractError("specialist result entry must be an object")
        task_index = entry.get("task_index")
        if not isinstance(task_index, int) or isinstance(task_index, bool):
            raise AgentContractError("specialist result task_index must be an integer")
        if task_index < 0 or task_index >= expected_count:
            raise AgentContractError(f"unexpected specialist task_index {task_index!r}")
        if task_index in indexed:
            raise AgentContractError(f"duplicate specialist task_index {task_index}")
        indexed[task_index] = entry

    if set(indexed) != set(range(expected_count)):
        raise AgentContractError("specialist result indexes are incomplete")
    return indexed


def assemble_specialist_delegation_results(
    *,
    plan: ResearchOrchestrationPlan,
    brief_id: str,
    topic: str,
    delegation_payload: dict[str, Any],
) -> ResearchOrchestrationResult:
    """Fail closed on every leaf, then assemble final research artifacts in host code."""

    if plan.brief_id != brief_id:
        raise AgentContractError(
            f"research plan brief_id {plan.brief_id!r} does not match {brief_id!r}"
        )
    if len(plan.specialist_tasks) != 3:
        raise AgentContractError(
            "deterministic research assembly requires exactly three specialists"
        )

    raw_results = delegation_payload.get("results")
    if not isinstance(raw_results, list):
        raise AgentContractError("Hermes delegation payload is missing results")

    indexed = _index_results(
        raw_results,
        expected_count=len(plan.specialist_tasks),
    )
    parsed_by_role: dict[ResearchRole, Any] = {}

    for task_index, specialist_task in enumerate(plan.specialist_tasks):
        entry = indexed[task_index]
        if entry.get("status") != "completed":
            raise AgentContractError(
                f"{specialist_task.role.value} failed: "
                f"{entry.get('error') or entry.get('status')!r}"
            )
        if bool(entry.get("truncated")):
            raise AgentContractError(f"{specialist_task.role.value} was truncated")
        if entry.get("schema_valid") is not True:
            errors = entry.get("schema_errors") or ()
            raise AgentContractError(
                f"{specialist_task.role.value} failed output schema validation: "
                f"{errors!r}"
            )

        model_type = _ROLE_MODELS[specialist_task.role]
        payload = _extract_json_object(str(entry.get("summary") or ""))
        parsed_by_role[specialist_task.role] = model_type.model_validate(payload)

    expected_roles = set(_ROLE_MODELS)
    if set(parsed_by_role) != expected_roles:
        missing = sorted(
            role.value for role in expected_roles - set(parsed_by_role)
        )
        raise AgentContractError(
            f"missing specialist roles after validation: {missing!r}"
        )

    return merge_specialist_findings(
        pack_id=f"research:{brief_id}",
        graph_id=f"evidence:{brief_id}",
        topic=topic,
        concept_findings=parsed_by_role[ResearchRole.CONCEPT],
        evidence_findings=parsed_by_role[ResearchRole.EVIDENCE],
        misconception_findings=parsed_by_role[ResearchRole.MISCONCEPTION],
    )
