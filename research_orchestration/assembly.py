"""Deterministic assembly of validated Hermes specialist research outputs."""

from __future__ import annotations

import json
from typing import Any, Iterable
from urllib.parse import urlparse

from agent_contracts import (
    AgentContractError,
    EvidenceEdge,
    EvidenceNodeKind,
    EvidenceRelation,
    ResearchClaim,
    ResearchExample,
    ResearchMisconception,
    SourceRecord,
)

from .merge import merge_specialist_findings
from .models import (
    ConceptResearchFindings,
    EvidenceResearchFindings,
    MisconceptionResearchFindings,
    ResearchOrchestrationPlan,
    ResearchOrchestrationResult,
    ResearchRole,
)


_PLACEHOLDER_HOSTS = {
    "example.com",
    "www.example.com",
    "example.org",
    "www.example.org",
    "example.net",
    "www.example.net",
    "example.test",
    "localhost",
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


def _require_object_keys(
    payload: dict[str, Any],
    *,
    required: set[str],
    optional: set[str] | None = None,
    label: str,
) -> None:
    optional = optional or set()
    actual = set(payload)
    missing = sorted(required - actual)
    unknown = sorted(actual - required - optional)
    if missing:
        raise AgentContractError(f"{label} is missing required fields {missing!r}")
    if unknown:
        raise AgentContractError(f"{label} has unexpected fields {unknown!r}")


def _validate_wire_shape(role: ResearchRole, payload: dict[str, Any]) -> None:
    if role == ResearchRole.CONCEPT:
        _require_object_keys(
            payload,
            required={"concepts"},
            optional={"open_questions"},
            label="concept specialist output",
        )
        return

    _require_object_keys(
        payload,
        required=(
            {"sources", "claims"}
            if role == ResearchRole.EVIDENCE
            else {"sources", "claims", "misconceptions", "examples"}
        ),
        label=f"{role.value} output",
    )

    sources = _require_list(payload, "sources")
    for index, row in enumerate(sources):
        if not isinstance(row, dict):
            raise AgentContractError(f"sources[{index}] must be an object")
        _require_object_keys(
            row,
            required={"title", "locator"},
            optional={"source_type", "publisher", "authors"},
            label=f"sources[{index}]",
        )

    claims = _require_list(payload, "claims")
    for index, row in enumerate(claims):
        if not isinstance(row, dict):
            raise AgentContractError(f"claims[{index}] must be an object")
        _require_object_keys(
            row,
            required={"statement", "source_indexes", "confidence"},
            label=f"claims[{index}]",
        )

    if role == ResearchRole.MISCONCEPTION:
        for field in ("misconceptions", "examples"):
            rows = _require_list(payload, field)
            for index, row in enumerate(rows):
                if not isinstance(row, dict):
                    raise AgentContractError(f"{field}[{index}] must be an object")
                required = (
                    {"statement", "correction", "claim_indexes"}
                    if field == "misconceptions"
                    else {"description", "claim_indexes"}
                )
                _require_object_keys(
                    row,
                    required=required,
                    label=f"{field}[{index}]",
                )


def validate_specialist_summary(
    role: ResearchRole,
    summary: str,
):
    """Strictly validate one specialist wire result with host-owned semantics."""

    payload = _extract_json_object(summary)
    _validate_wire_shape(role, payload)
    return _parse_role_payload(role, payload)


def _require_list(payload: dict[str, Any], field: str) -> list[Any]:
    value = payload.get(field)
    if not isinstance(value, list) or not value:
        raise AgentContractError(f"{field} must be a non-empty array")
    return value


def _validated_indexes(
    raw: Any,
    *,
    upper_bound: int,
    field_name: str,
) -> tuple[int, ...]:
    if not isinstance(raw, list) or not raw:
        raise AgentContractError(f"{field_name} must be a non-empty index array")
    values: list[int] = []
    for item in raw:
        if not isinstance(item, int) or isinstance(item, bool):
            raise AgentContractError(f"{field_name} entries must be integers")
        if item < 0 or item >= upper_bound:
            raise AgentContractError(
                f"{field_name} index {item} is outside 0..{upper_bound - 1}"
            )
        values.append(item)
    if len(values) != len(set(values)):
        raise AgentContractError(f"{field_name} indexes must be unique")
    return tuple(values)


def _validate_locator(locator: str) -> str:
    locator = str(locator or "").strip()
    if not locator:
        raise AgentContractError("source locator cannot be blank")
    parsed = urlparse(locator)
    if parsed.scheme in {"http", "https"}:
        host = (parsed.hostname or "").lower()
        if host in _PLACEHOLDER_HOSTS or host.endswith(".invalid"):
            raise AgentContractError(
                f"placeholder source locator is forbidden: {locator!r}"
            )
    return locator


def _sources_from_wire(
    payload: dict[str, Any],
    *,
    prefix: str,
) -> tuple[SourceRecord, ...]:
    rows = _require_list(payload, "sources")
    sources: list[SourceRecord] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise AgentContractError("source entry must be an object")
        source_payload = {
            "source_id": f"{prefix}.S{index:03d}",
            "title": row.get("title"),
            "locator": _validate_locator(str(row.get("locator") or "")),
        }
        for optional in ("source_type", "publisher", "authors"):
            if optional in row:
                source_payload[optional] = row[optional]
        sources.append(SourceRecord.model_validate(source_payload))
    return tuple(sources)


def _claims_and_edges_from_wire(
    payload: dict[str, Any],
    *,
    prefix: str,
    sources: tuple[SourceRecord, ...],
) -> tuple[tuple[ResearchClaim, ...], tuple[EvidenceEdge, ...]]:
    rows = _require_list(payload, "claims")
    claims: list[ResearchClaim] = []
    edges: list[EvidenceEdge] = []
    edge_number = 1
    for claim_number, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise AgentContractError("claim entry must be an object")
        indexes = _validated_indexes(
            row.get("source_indexes"),
            upper_bound=len(sources),
            field_name=f"claims[{claim_number - 1}].source_indexes",
        )
        claim_id = f"{prefix}.C{claim_number:03d}"
        source_ids = tuple(sources[index].source_id for index in indexes)
        claims.append(
            ResearchClaim(
                claim_id=claim_id,
                statement=row.get("statement"),
                source_ids=source_ids,
                confidence=row.get("confidence"),
            )
        )
        for source_index in indexes:
            edges.append(
                EvidenceEdge(
                    edge_id=f"{prefix}.E{edge_number:03d}",
                    from_kind=EvidenceNodeKind.SOURCE,
                    from_id=sources[source_index].source_id,
                    to_claim_id=claim_id,
                    relation=EvidenceRelation.SUPPORTS,
                )
            )
            edge_number += 1
    return tuple(claims), tuple(edges)


def _evidence_from_wire(payload: dict[str, Any]) -> EvidenceResearchFindings:
    sources = _sources_from_wire(payload, prefix="evidence")
    claims, edges = _claims_and_edges_from_wire(
        payload,
        prefix="evidence",
        sources=sources,
    )
    return EvidenceResearchFindings(
        sources=sources,
        claims=claims,
        evidence_edges=edges,
    )


def _misconception_from_wire(payload: dict[str, Any]) -> MisconceptionResearchFindings:
    sources = _sources_from_wire(payload, prefix="misconception")
    claims, edges = _claims_and_edges_from_wire(
        payload,
        prefix="misconception",
        sources=sources,
    )

    misconception_rows = _require_list(payload, "misconceptions")
    misconceptions: list[ResearchMisconception] = []
    for index, row in enumerate(misconception_rows, start=1):
        if not isinstance(row, dict):
            raise AgentContractError("misconception entry must be an object")
        claim_indexes = _validated_indexes(
            row.get("claim_indexes"),
            upper_bound=len(claims),
            field_name=f"misconceptions[{index - 1}].claim_indexes",
        )
        misconceptions.append(
            ResearchMisconception(
                misconception_id=f"misconception.M{index:03d}",
                statement=row.get("statement"),
                correction=row.get("correction"),
                claim_ids=tuple(claims[i].claim_id for i in claim_indexes),
            )
        )

    example_rows = _require_list(payload, "examples")
    examples: list[ResearchExample] = []
    for index, row in enumerate(example_rows, start=1):
        if not isinstance(row, dict):
            raise AgentContractError("example entry must be an object")
        claim_indexes = _validated_indexes(
            row.get("claim_indexes"),
            upper_bound=len(claims),
            field_name=f"examples[{index - 1}].claim_indexes",
        )
        examples.append(
            ResearchExample(
                example_id=f"misconception.X{index:03d}",
                description=row.get("description"),
                claim_ids=tuple(claims[i].claim_id for i in claim_indexes),
            )
        )

    return MisconceptionResearchFindings(
        sources=sources,
        claims=claims,
        evidence_edges=edges,
        misconceptions=tuple(misconceptions),
        examples=tuple(examples),
    )


def _parse_role_payload(
    role: ResearchRole,
    payload: dict[str, Any],
):
    if role == ResearchRole.CONCEPT:
        return ConceptResearchFindings.model_validate(payload)
    if role == ResearchRole.EVIDENCE:
        return _evidence_from_wire(payload)
    if role == ResearchRole.MISCONCEPTION:
        return _misconception_from_wire(payload)
    raise AgentContractError(f"unsupported research role {role!r}")


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

        parsed_by_role[specialist_task.role] = validate_specialist_summary(
            specialist_task.role,
            str(entry.get("summary") or ""),
        )

    expected_roles = {
        ResearchRole.CONCEPT,
        ResearchRole.EVIDENCE,
        ResearchRole.MISCONCEPTION,
    }
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
