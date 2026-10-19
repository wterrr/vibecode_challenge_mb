"""V3-05 typed binary search with independently replayed, leftmost-policy oracle.

Production runs only locally. No generated code, external provider or renderer.
A V3 VERIFIED_TRACE ref alone is never treated as algorithmic proof.
"""
from __future__ import annotations

from bisect import bisect_left
import re
from typing import Literal

from pydantic import Field, StrictInt, model_validator

from learnflow_v2.repair import compute_content_hash
from .models import (
    ObjectKind, ObjectState, LedgerStep, SemanticContractError,
    StateLedger, StateSourceKind, V3Model, VisualPatternSpec,
)
from .pattern_router import VisualPatternRoute, route_visual_pattern

BINARY_SEARCH_ORACLE_VERSION = "v3-05-leftmost-inclusive-v1"
MAX_ARRAY_ITEMS = 4096


class BinarySearchInput(V3Model):
    values: tuple[StrictInt, ...] = Field(max_length=MAX_ARRAY_ITEMS)
    target: StrictInt
    duplicate_policy: Literal["LEFTMOST"] = "LEFTMOST"

    @model_validator(mode="after")
    def _sorted(self):
        if any(a > b for a, b in zip(self.values, self.values[1:])):
            raise ValueError("UNSORTED_BINARY_SEARCH_INPUT")
        return self


class SearchStep(V3Model):
    phase: Literal["COMPARE", "COMPLETE"]
    low: StrictInt
    high: StrictInt
    mid: StrictInt | None = None
    observed: StrictInt | None = None
    action: Literal["DISCARD_LEFT", "KEEP_LEFT", "RECORD_CANDIDATE", "FOUND", "NOT_FOUND"]
    next_low: StrictInt | None = None
    next_high: StrictInt | None = None
    candidate_index: StrictInt | None = None

    @model_validator(mode="after")
    def _shape(self):
        if self.phase == "COMPARE":
            if self.mid is None or self.observed is None or self.next_low is None or self.next_high is None:
                raise ValueError("COMPARE_STEP_MISSING_STATE")
            if self.action not in ("DISCARD_LEFT", "KEEP_LEFT", "RECORD_CANDIDATE"):
                raise ValueError("COMPARE_INVALID_ACTION")
        elif self.phase == "COMPLETE":
            if any(x is not None for x in (self.mid, self.observed, self.next_low, self.next_high)):
                raise ValueError("COMPLETE_STEP_HAS_COMPARISON_STATE")
            if self.action not in ("FOUND", "NOT_FOUND"):
                raise ValueError("COMPLETE_INVALID_ACTION")
        return self


class BinarySearchTrace(V3Model):
    schema_version: Literal["3.0"] = "3.0"
    oracle_version: Literal["v3-05-leftmost-inclusive-v1"] = BINARY_SEARCH_ORACLE_VERSION
    source_ref: str
    query: BinarySearchInput
    steps: tuple[SearchStep, ...] = Field(min_length=1, max_length=MAX_ARRAY_ITEMS + 2)
    result_index: StrictInt | None
    trace_sha256: str

    @model_validator(mode="after")
    def _syntax(self):
        if not self.source_ref.startswith("trace:") or len(self.source_ref) <= 6:
            raise ValueError("INVALID_TRACE_REF")
        if not self.trace_sha256 or len(self.trace_sha256) != 64:
            raise ValueError("INVALID_TRACE_HASH_FORMAT")
        return self


class VerifiedBinarySearchProof(V3Model):
    oracle_version: Literal["v3-05-leftmost-inclusive-v1"] = BINARY_SEARCH_ORACLE_VERSION
    trace_ref: str
    trace_sha256: str
    oracle_index: StrictInt | None
    step_count: StrictInt
    assurance: Literal["REPLAYED_EVERY_STEP_AND_BISECT_LEFT"] = "REPLAYED_EVERY_STEP_AND_BISECT_LEFT"


class VerifiedBinarySearchRoute(V3Model):
    proof: VerifiedBinarySearchProof
    ledger_sha256: str
    route: VisualPatternRoute
    render_ready: Literal[False] = False


def _trace_payload(ref: str, query: BinarySearchInput, steps: tuple[SearchStep, ...], result: int | None) -> dict:
    return {
        "schema_version": "3.0", "oracle_version": BINARY_SEARCH_ORACLE_VERSION,
        "source_ref": ref, "query": query.model_dump(mode="json"),
        "steps": [step.model_dump(mode="json") for step in steps],
        "result_index": result,
    }


def make_binary_search_trace(*, values: tuple[int, ...], target: int, source_ref: str) -> BinarySearchTrace:
    """Deterministic producer. Verification below does not trust this producer."""
    query = BinarySearchInput(values=values, target=target)
    low, high, candidate = 0, len(query.values) - 1, None
    steps: list[SearchStep] = []
    while low <= high:
        mid = low + (high - low) // 2
        item = query.values[mid]
        if item < target:
            new_low, new_high, action = mid + 1, high, "DISCARD_LEFT"
        elif item == target:
            candidate = mid
            new_low, new_high, action = low, mid - 1, "RECORD_CANDIDATE"
        else:
            new_low, new_high, action = low, mid - 1, "KEEP_LEFT"
        steps.append(SearchStep(
            phase="COMPARE", low=low, high=high, mid=mid, observed=item,
            action=action, next_low=new_low, next_high=new_high,
            candidate_index=candidate,
        ))
        low, high = new_low, new_high
    result = candidate
    steps.append(SearchStep(
        phase="COMPLETE", low=low, high=high,
        action="FOUND" if candidate is not None else "NOT_FOUND",
        candidate_index=result,
    ))
    payload = _trace_payload(source_ref, query, tuple(steps), result)
    return BinarySearchTrace(**payload, trace_sha256=compute_content_hash(payload))


def verify_binary_search_trace(trace: BinarySearchTrace) -> VerifiedBinarySearchProof:
    """Fail-closed replay of *every* step, plus independent stdlib bisect oracle.

    Neither supplied source_ref nor recomputed checksum is accepted as proof
    without checking the comparison, invariant and bounds at each transition.
    """
    query = trace.query
    payload = _trace_payload(trace.source_ref, query, trace.steps, trace.result_index)
    if compute_content_hash(payload) != trace.trace_sha256:
        raise SemanticContractError("BINARY_SEARCH_TRACE_HASH_MISMATCH")
    oracle_insert = bisect_left(query.values, query.target)
    oracle = oracle_insert if (
        oracle_insert < len(query.values) and query.values[oracle_insert] == query.target
    ) else None
    low, high, candidate = 0, len(query.values) - 1, None
    comparisons = 0
    if trace.steps[-1].phase != "COMPLETE":
        raise SemanticContractError("BINARY_SEARCH_TERMINAL_MISSING")
    for position, step in enumerate(trace.steps[:-1]):
        if step.phase != "COMPARE":
            raise SemanticContractError(f"BINARY_SEARCH_NONTERMINAL_PHASE position={position}")
        if low > high:
            raise SemanticContractError("BINARY_SEARCH_EXTRA_COMPARISON")
        midpoint = low + (high - low) // 2
        actual = query.values[midpoint]
        if actual < query.target:
            next_low, next_high, action = midpoint + 1, high, "DISCARD_LEFT"
        elif actual > query.target:
            next_low, next_high, action = low, midpoint - 1, "KEEP_LEFT"
        else:
            candidate = midpoint
            next_low, next_high, action = low, midpoint - 1, "RECORD_CANDIDATE"
        required = (low, high, midpoint, actual, action, next_low, next_high, candidate)
        observed = (step.low, step.high, step.mid, step.observed, step.action,
                    step.next_low, step.next_high, step.candidate_index)
        if required != observed:
            raise SemanticContractError(f"BINARY_SEARCH_STEP_MISMATCH position={position}")
        low, high = next_low, next_high
        comparisons += 1
    if low <= high:
        raise SemanticContractError("BINARY_SEARCH_EARLY_TERMINATION")
    terminal = trace.steps[-1]
    if (
        terminal.low != low or terminal.high != high
        or terminal.candidate_index != candidate
        or terminal.action != ("FOUND" if candidate is not None else "NOT_FOUND")
        or trace.result_index != candidate
    ):
        raise SemanticContractError("BINARY_SEARCH_TERMINAL_MISMATCH")
    if candidate != oracle:
        raise SemanticContractError("BINARY_SEARCH_INDEPENDENT_ORACLE_MISMATCH")
    return VerifiedBinarySearchProof(
        trace_ref=trace.source_ref, trace_sha256=trace.trace_sha256,
        oracle_index=oracle, step_count=len(trace.steps),
    )


def to_binary_search_state_ledger(
    *,
    trace: BinarySearchTrace,
    pattern: VisualPatternSpec,
    beat_refs: tuple[str, ...],
) -> StateLedger:
    """Adapt only an independently verified trace to V3-02's typed StateLedger."""
    proof = verify_binary_search_trace(trace)
    if pattern.state_source.kind != StateSourceKind.VERIFIED_TRACE or pattern.state_source.ref != proof.trace_ref:
        raise SemanticContractError("BINARY_SEARCH_PATTERN_SOURCE_MISMATCH")
    if proof.trace_ref not in pattern.source_refs:
        raise SemanticContractError("BINARY_SEARCH_MISSING_PATTERN_PROVENANCE")
    if pattern.pattern_type.value != "WORKED_EXAMPLE_BOARD" or pattern.renderer_requirement != "STATEFUL_SEQUENCE":
        raise SemanticContractError("BINARY_SEARCH_UNSUPPORTED_PATTERN")
    if len(beat_refs) != proof.step_count or len(set(beat_refs)) != len(beat_refs):
        raise SemanticContractError("BINARY_SEARCH_BEAT_ALIGNMENT_MISMATCH")
    if not any(o.kind == ObjectKind.SEQUENCE for o in pattern.semantic_objects):
        raise SemanticContractError("BINARY_SEARCH_SEQUENCE_OBJECT_REQUIRED")
    if any(o.kind not in (ObjectKind.SEQUENCE, ObjectKind.POINTER) for o in pattern.semantic_objects):
        raise SemanticContractError("BINARY_SEARCH_UNSUPPORTED_OBJECT_KIND")
    ledger_steps: list[LedgerStep] = []
    for ordinal, (step, beat_ref) in enumerate(zip(trace.steps, beat_refs, strict=True)):
        props = {
            "visible": True, "values": list(trace.query.values),
            "target": trace.query.target, "low": step.low, "high": step.high,
            "mid": step.mid, "observed": step.observed, "action": step.action,
            "candidate_index": step.candidate_index, "result_index": (
                trace.result_index if step.phase == "COMPLETE" else None
            ), "phase": step.phase,
        }
        obj_states = tuple(ObjectState(object_id=obj.object_id, properties=dict(props))
                           for obj in pattern.semantic_objects)
        ledger_steps.append(LedgerStep(
            step_id=f"binary-step-{ordinal:04d}", beat_ref=beat_ref,
            object_states=obj_states,
        ))
    return StateLedger(
        ledger_id=f"binary-ledger-{proof.trace_sha256[:20]}",
        pattern_ref=pattern.pattern_id, source_ref=proof.trace_ref,
        steps=tuple(ledger_steps),
    )


def verify_binary_search_ledger(
    *,
    trace: BinarySearchTrace,
    pattern: VisualPatternSpec,
    ledger: StateLedger,
    beat_refs: tuple[str, ...],
) -> VerifiedBinarySearchProof:
    """Reject drifted/faked ledger even with a valid trace source marker."""
    proof = verify_binary_search_trace(trace)
    expected = to_binary_search_state_ledger(trace=trace, pattern=pattern, beat_refs=beat_refs)
    if ledger.model_dump(mode="json") != expected.model_dump(mode="json"):
        raise SemanticContractError("BINARY_SEARCH_STATE_LEDGER_MISMATCH")
    return proof


def _explicit_binary_search_example(value: str) -> BinarySearchInput | None:
    """Parse one bounded, unambiguous explicit teaching example; never infer."""
    if "binary search for" not in value.casefold():
        return None
    expression = re.compile(
        r"\bbinary\s+search\s+for\s+(-?\d+)\s+in\s+\[([^\]]*)\]",
        re.IGNORECASE,
    )
    matches = expression.findall(value)
    if len(matches) != 1:
        raise SemanticContractError("BINARY_SEARCH_EXAMPLE_AMBIGUOUS_OR_MALFORMED")
    target, raw_values = matches[0]
    parts = [s.strip() for s in raw_values.split(",")] if raw_values.strip() else []
    if any(not re.fullmatch(r"-?\d+", x) for x in parts):
        raise SemanticContractError("BINARY_SEARCH_EXAMPLE_INVALID_INTEGER")
    try:
        return BinarySearchInput(values=tuple(int(x) for x in parts), target=int(target))
    except ValueError as exc:
        raise SemanticContractError("BINARY_SEARCH_EXAMPLE_INVALID_INPUT") from exc


def verify_binary_search_teaching_binding(*, trace: BinarySearchTrace, pattern: VisualPatternSpec,
                                          registry, script, storyboard) -> None:
    """Require actual matching array/target in script AND storyboard.

    Neither correctness of the algorithm alone nor an LLM's verified flag
    can prove that the taught example is the same as the trace input.
    """
    source_ids = {s.removeprefix("script:") for s in pattern.source_refs if s.startswith("script:")}
    script_examples = []
    for segment in script.segments:
        if segment.segment_id in source_ids:
            for value in (segment.spoken_text, segment.subtitle_text):
                parsed = _explicit_binary_search_example(value)
                if parsed is not None:
                    script_examples.append(parsed)
    storyboard_examples = []
    for scene in storyboard.scenes:
        if scene.scene_id == pattern.scene_id:
            parsed = _explicit_binary_search_example(scene.visual_intent)
            if parsed is not None:
                storyboard_examples.append(parsed)
    if not script_examples or not storyboard_examples:
        raise SemanticContractError("BINARY_SEARCH_CANONICAL_INPUT_UNGROUNDED")
    registry_examples = []
    for ref in pattern.concept_refs:
        try:
            label = registry.get(ref.concept_id).label
        except Exception as exc:
            raise SemanticContractError("BINARY_SEARCH_CONCEPT_REF_UNKNOWN") from exc
        parsed = _explicit_binary_search_example(label)
        if parsed is not None:
            registry_examples.append(parsed)
    if any(candidate != trace.query for candidate in (
        *script_examples, *storyboard_examples, *registry_examples
    )):
        raise SemanticContractError("BINARY_SEARCH_SEMANTIC_INPUT_MISMATCH")


def certify_and_route_binary_search(
    *,
    trace: BinarySearchTrace,
    plan,
    pattern: VisualPatternSpec,
    ledger: StateLedger,
    registry,
    script,
    storyboard,
    scenegraph,
) -> VerifiedBinarySearchRoute:
    """Trust boundary: no caller-asserted verified_trace_refs accepted here."""
    beat_refs = tuple(b.beat_id for b in plan.beats)
    proof = verify_binary_search_ledger(
        trace=trace, pattern=pattern, ledger=ledger, beat_refs=beat_refs,
    )
    verify_binary_search_teaching_binding(
        trace=trace, pattern=pattern, registry=registry,
        script=script, storyboard=storyboard,
    )
    route = route_visual_pattern(
        plan=plan, pattern=pattern, ledger=ledger,
        registry=registry, script=script, storyboard=storyboard, scenegraph=scenegraph,
        verified_trace_refs=(proof.trace_ref,),
    )
    return VerifiedBinarySearchRoute(
        proof=proof, ledger_sha256=compute_content_hash(ledger),
        route=route,
    )
