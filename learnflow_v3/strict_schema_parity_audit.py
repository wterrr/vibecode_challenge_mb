"""V3-40 OFFLINE-only candidate schema audit. No inference, credentials or model call.

The historical V3-35/37/39 strict_wire_schema() and one-shot request stay
unchanged. This module projects every wire-expressible host bound from the
actual Pydantic models; non-local semantic guards remain host-owned.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from learnflow_v3.creative_manim_ablation import Blocked, CreativeScene
from learnflow_v3.structured_scene_authoring import strict_wire_schema, verify_schema

PREREG = "benchmarks/learnflowbench/v3/v3_40_strict_schema_parity_preregister.json"
PARENT_HEAD = "f5dd06a0dcb8b1cfd0398ea17c196c50aabaa0b5"
KEYWORDS = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
            "minItems", "maxItems", "minLength", "maxLength", "pattern")
# These are not claimed to be enforced by the provider JSON Schema:
HOST_ONLY = (
    "Graphic.consistent: reserved/unsafe Python identifiers",
    "Graphic.consistent: text-versus-shape condition, visible maths and control characters",
    "Motion.action_contract: wait/move/non-move conditional target and coordinates",
    "LectureBeat.grounded: allowlisted spoken numbers and F2-specific semantics",
    "CreativeScene.whole_plan: distinct IDs, visual diversity, claim coverage",
    "CreativeScene.whole_plan: show-before-use, no repeated show, visible state budget",
    "CreativeScene.whole_plan: narration minimum spoken word count",
    "normalize_wire: placeholder action fields must be exactly zero or empty",
    "provider support: strict enforcement of bounds/regex/minItems by the actual endpoint is NOT authenticated",
)


def _unbox(node: dict, defs: dict, path: str) -> dict:
    """Resolve Pydantic refs and optional-null field wrappers for wire projection."""
    for _ in range(8):
        if "$ref" in node:
            ref = node["$ref"]
            prefix = "#/$defs/"
            if not isinstance(ref, str) or not ref.startswith(prefix):
                raise Blocked("V340_UNSUPPORTED_REFERENCE:" + path)
            node = defs[ref[len(prefix):]]
        elif "anyOf" in node:
            options = [part for part in node["anyOf"] if part.get("type") != "null"]
            if len(options) != 1 or len(node["anyOf"]) != 2:
                raise Blocked("V340_UNSUPPORTED_UNION:" + path)
            node = options[0]
        else:
            return node
    raise Blocked("V340_REFERENCE_LOOP:" + path)


def _walk(candidate: dict, host_node: dict, defs: dict, path: str,
          constraints: list, *, project: bool) -> None:
    host = _unbox(host_node, defs, path)
    kind = candidate.get("type")
    if kind != host.get("type"):
        raise Blocked("V340_TYPE_DRIFT:" + path)
    if "enum" in host or "enum" in candidate:
        if host.get("enum") != candidate.get("enum"):
            raise Blocked("V340_ENUM_DRIFT:" + path)

    for key in KEYWORDS:
        expected = host.get(key)
        if project:
            if key in host:
                candidate[key] = expected
            else:
                candidate.pop(key, None)
        if candidate.get(key) != expected or ((key in candidate) != (key in host)):
            raise Blocked("V340_BOUND_DRIFT:" + path + "." + key)
        if key in host:
            constraints.append({"field": path, "keyword": key, "value": expected})

    if kind == "object":
        if candidate.get("additionalProperties") is not False:
            raise Blocked("V340_EXTRA_PROPERTIES_ALLOWED:" + path)
        host_fields = set(host.get("properties", {}))
        # model_author is injected from provider provenance by the trusted host.
        if path == "root":
            host_fields.discard("model_author")
        wire_fields = set(candidate.get("properties", {}))
        if host_fields != wire_fields or set(candidate.get("required", [])) != wire_fields:
            raise Blocked("V340_FIELD_DRIFT:" + path)
        for field, child in candidate["properties"].items():
            _walk(child, host["properties"][field], defs, path + "." + field,
                  constraints, project=project)
    elif kind == "array":
        _walk(candidate["items"], host["items"], defs, path + "[]",
              constraints, project=project)


def candidate_schema() -> dict:
    """Derive a separate candidate from Pydantic, never mutate historical wire."""
    wire = deepcopy(strict_wire_schema())
    host = CreativeScene.model_json_schema()
    _walk(wire, host, host.get("$defs", {}), "root", [], project=True)
    verify_schema(wire)
    return wire


def assert_parity(schema: dict) -> list[dict]:
    """Fail on any host field/type/enum/bound drift; return an inventory."""
    host = CreativeScene.model_json_schema()
    constraints = []
    _walk(schema, host, host.get("$defs", {}), "root", constraints, project=False)
    verify_schema(schema)
    return constraints


def audit(root: Path) -> tuple[dict, dict]:
    prereg = json.loads((root / PREREG).read_text(encoding="utf-8"))
    if (prereg.get("checkpoint") != "V3-40" or
        prereg.get("preregistered_before_implementation") is not True or
        prereg.get("frozen_parent_head") != PARENT_HEAD or
        prereg.get("model_http_posts_allowed") != 0):
        raise Blocked("V340_PREREGISTRATION_DRIFT")
    candidate = candidate_schema()
    inventory = assert_parity(candidate)
    if not inventory or len(inventory) < 20:
        raise Blocked("V340_INCOMPLETE_BOUND_COVERAGE")
    historical = strict_wire_schema()
    if historical["properties"]["objects"]["items"]["properties"]["height"].get("maximum") is not None:
        raise Blocked("V340_HISTORICAL_WIRE_MODIFIED")
    if historical["properties"]["beats"]["items"]["properties"]["claim_ids"].get("minItems") is not None:
        raise Blocked("V340_HISTORICAL_WIRE_MODIFIED")
    digest = sha256(json.dumps(candidate, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    report = {
        "checkpoint": "V3-40",
        "status": "OFFLINE_WIRE_EXPRESSIBLE_PARITY_PASS_NOT_ENDPOINT_CERTIFICATION",
        "historical_v339_one_shot": "CONSUMED_NO_RETRY",
        "host_model": "CreativeScene",
        "schema_sha256": digest,
        "wire_expressible_constraints": inventory,
        "host_only_conditions": list(HOST_ONLY),
        "json_schema_local_validation": "MUST_BE_TESTED_SEPARATELY_IN_CI",
        "provider_native_strict_bounds_enforcement": "NOT_VERIFIED",
        "model_inference_http_posts": 0,
        "real_model_mp4": "NOT_OBTAINED",
        "educational_quality": "NOT_ASSESSED",
        "production": "BLOCKED",
    }
    return candidate, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    candidate, report = audit(root)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "v3_40_bounded_candidate_schema.json").write_text(
        json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "v3_40_schema_parity_audit.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("V3_40=OFFLINE_WIRE_EXPRESSIBLE_PARITY_PASS_NOT_ENDPOINT_CERTIFICATION", flush=True)


if __name__ == "__main__":
    main()
