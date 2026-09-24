"""Canonical, deterministic JSON serialization for LearnFlow V2 semantic models."""

import json
from typing import Any
from pydantic import BaseModel


def _canonicalize_value(val: Any) -> Any:
    """Recursively normalize data structure for canonical ordering.

    Normalizes non-semantic collections into stable canonical sort order:
    - ConceptRegistry.concepts -> sorted by concept_id
    - SceneGraph.nodes -> sorted by id
    - SceneGraph.relations -> sorted by id
    - SceneGraph.groups -> sorted by id
    - Set-like symbolic string lists: aliases, style_refs, member_ids, keep_near, keep_apart -> sorted
    Does NOT sort narrative sequences, steps, points, scenes, or preferred_order data.
    """
    if isinstance(val, dict):
        normalized: dict[str, Any] = {}
        for k, v in val.items():
            if k == "concepts" and isinstance(v, list) and all(isinstance(x, dict) and "concept_id" in x for x in v):
                # Sort concepts deterministically by concept_id
                normalized[k] = sorted(
                    [_canonicalize_value(item) for item in v],
                    key=lambda x: str(x.get("concept_id", "")),
                )
            elif k == "nodes" and isinstance(v, list) and all(isinstance(x, dict) and "id" in x for x in v):
                # Sort scene nodes deterministically by id
                normalized[k] = sorted(
                    [_canonicalize_value(item) for item in v],
                    key=lambda x: str(x.get("id", "")),
                )
            elif k == "relations" and isinstance(v, list) and all(isinstance(x, dict) and "id" in x for x in v):
                # Sort scene relations deterministically by id
                normalized[k] = sorted(
                    [_canonicalize_value(item) for item in v],
                    key=lambda x: str(x.get("id", "")),
                )
            elif k == "groups" and isinstance(v, list) and all(isinstance(x, dict) and "id" in x for x in v):
                # Sort scene groups deterministically by id
                normalized[k] = sorted(
                    [_canonicalize_value(item) for item in v],
                    key=lambda x: str(x.get("id", "")),
                )
            elif k == "boxes" and isinstance(v, list) and all(isinstance(x, dict) and "node_id" in x for x in v):
                # Sort layout boxes deterministically by node_id
                normalized[k] = sorted(
                    [_canonicalize_value(item) for item in v],
                    key=lambda x: str(x.get("node_id", "")),
                )
            elif k == "candidates" and isinstance(v, list) and all(isinstance(x, dict) and "candidate_id" in x for x in v):
                # Sort layout candidates deterministically by candidate_id
                normalized[k] = sorted(
                    [_canonicalize_value(item) for item in v],
                    key=lambda x: str(x.get("candidate_id", "")),
                )
            elif k in ("aliases", "style_refs", "member_ids", "keep_near", "keep_apart") and isinstance(v, list) and all(isinstance(x, str) for x in v):
                # Sort set-like symbolic string collections
                normalized[k] = sorted(v)
            else:
                normalized[k] = _canonicalize_value(v)
        return normalized
    elif isinstance(val, list):
        return [_canonicalize_value(item) for item in val]
    return val


def canonical_json(data: BaseModel | dict[str, Any] | list[Any]) -> str:
    """Serialize a model or data structure into canonical, deterministic JSON.

    Guarantees:
    - Deterministic key ordering (sort_keys=True)
    - Normalized collection ordering for non-semantic collections (nodes, relations, groups, concepts, aliases, style_refs)
    - Normalized UTF-8 text (ensure_ascii=False)
    - Stable formatting without timestamp insertion or process randomness
    - Round-trip parseable JSON
    """
    if isinstance(data, BaseModel):
        raw_payload = data.model_dump(mode="json")
    elif isinstance(data, (dict, list)):
        raw_payload = data
    else:
        raise TypeError(f"canonical_json requires BaseModel, dict, or list, got {type(data)}")

    canonical_payload = _canonicalize_value(raw_payload)

    return json.dumps(
        canonical_payload,
        sort_keys=True,
        ensure_ascii=False,
        indent=2,
        separators=(",", ": "),
    )
