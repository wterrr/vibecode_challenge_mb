"""Content hashing, cache reuse, and dependency traversal for CP2.13."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from typing import Any, Iterable

from pydantic import BaseModel

from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.repair.errors import RepairDependencyError, RepairNonDeterminismError
from learnflow_v2.repair.schema import ArtifactInputHash, ArtifactKind, ArtifactRecord


def compute_content_hash(payload: Any) -> str:
    """Return a deterministic SHA-256 digest for artifact content."""
    if isinstance(payload, BaseModel):
        rendered = canonical_json(payload)
        json.loads(rendered, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(f"non-finite JSON constant {token}")))
        tagged = "model\n" + rendered
    elif isinstance(payload, (dict, list, tuple)):
        rendered = canonical_json(payload)
        json.loads(rendered, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(f"non-finite JSON constant {token}")))
        tagged = "json\n" + rendered
    elif isinstance(payload, bytes):
        return hashlib.sha256(b"bytes\n" + payload).hexdigest()
    elif isinstance(payload, str):
        tagged = "text\n" + payload
    else:
        raise TypeError(f"unsupported artifact payload type for hashing: {type(payload).__name__}")
    return hashlib.sha256(tagged.encode("utf-8")).hexdigest()


def input_hashes_from(records: Iterable[ArtifactRecord]) -> tuple[ArtifactInputHash, ...]:
    validated_records: list[ArtifactRecord] = []
    for record in records:
        if not isinstance(record, ArtifactRecord):
            raise RepairDependencyError("artifact inputs must be ArtifactRecord instances")
        validated_records.append(ArtifactRecord.model_validate(record.model_dump(mode="json")))
    items = [ArtifactInputHash(artifact_id=record.artifact_id, content_hash=record.content_hash) for record in validated_records]
    ids = [item.artifact_id for item in items]
    if len(ids) != len(set(ids)):
        raise RepairDependencyError("input records cannot contain duplicate artifact IDs")
    return tuple(sorted(items, key=lambda item: item.artifact_id))


def make_artifact_record(
    *,
    artifact_id: str,
    kind: ArtifactKind,
    payload: Any,
    created_by_phase: str,
    compiler_version: str,
    inputs: Iterable[ArtifactRecord] = (),
    scene_id: str | None = None,
    transition_id: str | None = None,
    from_scene_id: str | None = None,
    to_scene_id: str | None = None,
) -> ArtifactRecord:
    return ArtifactRecord(
        artifact_id=artifact_id,
        kind=kind,
        content_hash=compute_content_hash(payload),
        input_hashes=input_hashes_from(inputs),
        created_by_phase=created_by_phase,
        compiler_version=compiler_version,
        scene_id=scene_id,
        transition_id=transition_id,
        from_scene_id=from_scene_id,
        to_scene_id=to_scene_id,
    )


class ArtifactIndex:
    """In-memory deterministic provenance index; payload bytes remain external."""

    def __init__(self) -> None:
        self._records: dict[str, ArtifactRecord] = {}

    @property
    def records(self) -> tuple[ArtifactRecord, ...]:
        return tuple(sorted(self._records.values(), key=lambda record: record.artifact_id))

    def add(self, record: ArtifactRecord, *, validate_inputs: bool = True) -> None:
        if not isinstance(record, ArtifactRecord):
            raise RepairDependencyError("ArtifactIndex.add requires an ArtifactRecord")
        record = ArtifactRecord.model_validate(record.model_dump(mode="json"))
        existing = self._records.get(record.artifact_id)
        if existing is not None:
            if existing != record:
                raise RepairDependencyError(f"artifact_id '{record.artifact_id}' is already registered with different provenance")
            return
        if validate_inputs:
            for input_ref in record.input_hashes:
                parent = self._records.get(input_ref.artifact_id)
                if parent is None:
                    raise RepairDependencyError(
                        f"artifact '{record.artifact_id}' references unknown input '{input_ref.artifact_id}'"
                    )
                if parent.content_hash != input_ref.content_hash:
                    raise RepairDependencyError(
                        f"artifact '{record.artifact_id}' input hash for '{input_ref.artifact_id}' is stale"
                    )
        self._records[record.artifact_id] = record
        try:
            self._assert_acyclic()
        except Exception:
            self._records.pop(record.artifact_id, None)
            raise

    def get(self, artifact_id: str) -> ArtifactRecord:
        try:
            return self._records[artifact_id]
        except KeyError as exc:
            raise RepairDependencyError(f"unknown artifact_id '{artifact_id}'") from exc

    def find(
        self,
        *,
        kind: ArtifactKind | None = None,
        scene_id: str | None = None,
        transition_id: str | None = None,
    ) -> tuple[ArtifactRecord, ...]:
        results = []
        for record in self._records.values():
            if kind is not None and record.kind != kind:
                continue
            if scene_id is not None and record.scene_id != scene_id:
                continue
            if transition_id is not None and record.transition_id != transition_id:
                continue
            results.append(record)
        return tuple(sorted(results, key=lambda record: record.artifact_id))

    def find_reusable(
        self,
        *,
        kind: ArtifactKind,
        inputs: Iterable[ArtifactRecord],
        created_by_phase: str,
        compiler_version: str,
        scene_id: str | None = None,
        transition_id: str | None = None,
    ) -> ArtifactRecord | None:
        expected_inputs = input_hashes_from(inputs)
        candidates = [
            record
            for record in self._records.values()
            if record.kind == kind
            and record.input_hashes == expected_inputs
            and record.created_by_phase == created_by_phase
            and record.compiler_version == compiler_version
            and record.scene_id == scene_id
            and record.transition_id == transition_id
        ]
        if not candidates:
            return None
        distinct_hashes = {record.content_hash for record in candidates}
        if len(distinct_hashes) > 1:
            raise RepairNonDeterminismError(
                f"same deterministic inputs/compiler produced multiple {kind.value} content hashes"
            )
        return sorted(candidates, key=lambda record: record.artifact_id)[0]

    def downstream_closure(self, root_ids: Iterable[str], *, include_roots: bool = True) -> tuple[str, ...]:
        roots = tuple(sorted(set(root_ids)))
        for root in roots:
            if root not in self._records:
                raise RepairDependencyError(f"unknown invalidation root '{root}'")
        reverse: dict[str, list[str]] = defaultdict(list)
        for record in self._records.values():
            for input_ref in record.input_hashes:
                reverse[input_ref.artifact_id].append(record.artifact_id)
        for children in reverse.values():
            children.sort()
        seen = set(roots if include_roots else ())
        queue = deque(roots)
        while queue:
            current = queue.popleft()
            for child in reverse.get(current, ()):  # deterministic child ordering
                if child not in seen:
                    seen.add(child)
                    queue.append(child)
        if not include_roots:
            seen.difference_update(roots)
        return tuple(sorted(seen))

    def _assert_acyclic(self) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(artifact_id: str) -> None:
            if artifact_id in visiting:
                raise RepairDependencyError("artifact dependency graph must be acyclic")
            if artifact_id in visited:
                return
            visiting.add(artifact_id)
            record = self._records[artifact_id]
            for input_ref in record.input_hashes:
                if input_ref.artifact_id in self._records:
                    visit(input_ref.artifact_id)
            visiting.remove(artifact_id)
            visited.add(artifact_id)

        for artifact_id in sorted(self._records):
            visit(artifact_id)
