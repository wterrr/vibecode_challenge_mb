"""V3-41 provider-portable finite schema for a future separately authorized trial.

This module only builds schemas and validates LOCAL JSON data. It never imports
any HTTP client or API key. V3-39's strict_wire_schema and historical one-shot
sender are unchanged. A valid wire object is still NOT automatically a valid
pedagogical or temporally coherent scene: host validators remain authoritative.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import json

from jsonschema import Draft202012Validator
from pydantic import ValidationError

from learnflow_v3.creative_manim_ablation import Blocked, CreativeScene, Graphic, Motion
from learnflow_v3.structured_scene_authoring import (
    CLAIMS, normalize_wire, strict_wire_schema, verify_schema,
)
from learnflow_v3.strict_schema_parity_audit import candidate_schema

VERSION = "v3-41-provider-portable-enum-slots-v1"
ALLOWED_KEYWORDS = {
    "type", "properties", "required", "additionalProperties",
    "enum", "items", "description",
}
REQUIRED_BEATS = ("beat_1", "beat_2", "beat_3", "beat_4")
CLAIM_SLOTS = ("claim_primary", "claim_secondary", "claim_tertiary")
MAX_TOTAL_ENUM_VALUES = 1000


def _finite_numbers(node: dict, step: str, *, default: object = None) -> list[float]:
    """Generate a deterministic finite grid INSIDE host limits, without clipping."""
    if node.get("type") != "number" or "minimum" not in node or "maximum" not in node:
        raise Blocked("V341_UNBOUNDED_PYDANTIC_GEOMETRY")
    low = Decimal(str(node["minimum"]))
    high = Decimal(str(node["maximum"]))
    delta = Decimal(step)
    if low >= high or delta <= 0:
        raise Blocked("V341_INVALID_GEOMETRY_DOMAIN")
    begin = int((low / delta).to_integral_value(rounding=ROUND_CEILING))
    end = int((high / delta).to_integral_value(rounding=ROUND_FLOOR))
    values = {low, high}
    values.update(Decimal(n) * delta for n in range(begin, end + 1))
    if default is not None:
        d = Decimal(str(default))
        if d < low or d > high:
            raise Blocked("V341_PYDANTIC_DEFAULT_OUTSIDE_LIMITS")
        values.add(d)
    if low <= 0 <= high:
        values.add(Decimal(0))
    return [float(x) for x in sorted(values)]


def _forbid_unsupported(schema: dict) -> int:
    """Exact documented portable keyword allowlist; enforce enum+schema budgets."""
    total = 0

    def walk(node: dict, path: str, depth: int) -> None:
        nonlocal total
        if depth > 10 or set(node) - ALLOWED_KEYWORDS:
            raise Blocked("V341_UNSUPPORTED_PROVIDER_SCHEMA_KEYWORD:" + path)
        if node.get("type") == "object":
            props = node.get("properties", {})
            if (node.get("additionalProperties") is not False or
                set(node.get("required", [])) != set(props)):
                raise Blocked("V341_NONSTRICT_OBJECT:" + path)
            for name, child in props.items():
                walk(child, path + "." + name, depth + 1)
        elif node.get("type") == "array":
            walk(node["items"], path + "[]", depth + 1)
        elif node.get("type") not in ("string", "number", "integer", "boolean"):
            raise Blocked("V341_UNSUPPORTED_TYPE:" + path)
        if "enum" in node:
            choices = node["enum"]
            if not isinstance(choices, list) or not choices:
                raise Blocked("V341_EMPTY_ENUM:" + path)
            total += len(choices)
    walk(schema, "root", 1)
    if total > MAX_TOTAL_ENUM_VALUES:
        raise Blocked("V341_ENUM_BUDGET_EXCEEDED")
    Draft202012Validator.check_schema(schema)
    return total


def portable_wire_schema() -> dict:
    """No maximum/minimum/minItems: use host-derived numeric enums and required slots."""
    bounded = candidate_schema()  # Pydantic-derived source of truth.
    wire = deepcopy(strict_wire_schema())
    graphic = wire["properties"]["objects"]["items"]["properties"]
    bounded_graphic = bounded["properties"]["objects"]["items"]["properties"]
    motion = wire["properties"]["beats"]["items"]["properties"]["actions"]["items"]["properties"]
    bounded_motion = bounded["properties"]["beats"]["items"]["properties"]["actions"]["items"]["properties"]

    for name in ("x", "y", "width", "height", "radius"):
        grid = "0.1" if name in ("x", "y") else "0.05"
        graphic[name]["enum"] = _finite_numbers(
            bounded_graphic[name], grid, default=(None if Graphic.model_fields[name].is_required()
                                                 else Graphic.model_fields[name].default))
    for name in ("x", "y"):
        motion[name]["enum"] = _finite_numbers(
            bounded_motion[name], "0.2", default=Motion.model_fields[name].default)

    beat = wire["properties"]["beats"]["items"]
    props = beat["properties"]
    del props["claim_ids"]
    # A nonempty primary factual claim is mandatory at *wire decoding time*.
    # Empty extras are explicitly authored transport placeholders, NOT facts.
    props["claim_primary"] = {
        "type": "string", "enum": list(CLAIMS),
        "description": "Required first approved claim, never empty."}
    for key in CLAIM_SLOTS[1:]:
        props[key] = {
            "type": "string", "enum": [""] + list(CLAIMS),
            "description": "Extra claim ID or empty string for NO extra claim."}
    beat["required"] = list(props)
    # Required beat_1..beat_4 makes 'four beats' structural, not minItems.
    wire["properties"]["beats"] = {
        "type": "object", "additionalProperties": False,
        "properties": {name: deepcopy(beat) for name in REQUIRED_BEATS},
        "required": list(REQUIRED_BEATS),
        "description": "Exactly four ordered authored teaching beats."}
    verify_schema(wire)
    _forbid_unsupported(wire)
    return wire


def decode_portable_wire(raw: dict) -> dict:
    """Fail closed, never clamp geometry, invent claims or repair actions.

    Only a lossless mapping of the model's three declared claim slots into an
    ordered claim_ids list, and four required beat names into ordered beats.
    """
    schema = portable_wire_schema()
    try:
        Draft202012Validator(schema).validate(raw)
    except Exception:
        # No user-controlled Pydantic or provider text in failure messages.
        raise Blocked("V341_WIRE_SCHEMA_REJECTED") from None
    legacy = {
        "title": raw["title"],
        "learning_objective": raw["learning_objective"],
        "objects": deepcopy(raw["objects"]),
        "beats": [],
    }
    for name in REQUIRED_BEATS:
        beat = raw["beats"][name]
        claims = [beat["claim_primary"]]
        claims += [beat[k] for k in CLAIM_SLOTS[1:] if beat[k] != ""]
        if len(claims) == 0:
            raise Blocked("V341_EMPTY_MODEL_CLAIM")
        legacy["beats"].append({
            "claim_ids": claims,
            "narration": beat["narration"],
            "visual_goal": beat["visual_goal"],
            "actions": deepcopy(beat["actions"]),
        })
    normalized = normalize_wire(legacy)
    try:
        CreativeScene.model_validate(normalized)
    except ValidationError:
        raise Blocked("V341_HOST_SEMANTIC_REJECTED") from None
    return normalized


def offline_synthetic_wire_fixture() -> dict:
    """Convert the EXISTING explicit host fixture, never a claimed model result."""
    from learnflow_v3.creative_manim_ablation import fixture_plan
    canonical = fixture_plan().model_dump(mode="json", exclude={"model_author"})
    result = {
        "title": canonical["title"],
        "learning_objective": canonical["learning_objective"],
        "objects": deepcopy(canonical["objects"]),
        "beats": {},
    }
    for name, beat in zip(REQUIRED_BEATS, canonical["beats"], strict=True):
        claims = beat["claim_ids"]
        if not 1 <= len(claims) <= 3:
            raise Blocked("V341_INVALID_SYNTHETIC_CLAIM_FIXTURE")
        encoded = {
            "claim_primary": claims[0],
            "claim_secondary": claims[1] if len(claims) >= 2 else "",
            "claim_tertiary": claims[2] if len(claims) >= 3 else "",
            "narration": beat["narration"],
            "visual_goal": beat["visual_goal"],
            "actions": deepcopy(beat["actions"]),
        }
        for action in encoded["actions"]:
            for k in ("x", "y"):
                if action.get(k) is None:
                    action[k] = 0.0
            if action.get("target") is None:
                action["target"] = ""
        result["beats"][name] = encoded
    return result


def audit_protocol() -> dict:
    wire = portable_wire_schema()
    fixture = offline_synthetic_wire_fixture()
    normalized = decode_portable_wire(fixture)
    import hashlib
    digest = hashlib.sha256(json.dumps(wire, sort_keys=True).encode()).hexdigest()
    return {
        "checkpoint": "V3-41",
        "status": "OFFLINE_COMPATIBLE_SCHEMA_LOCAL_PASS_PROVIDER_NOT_VERIFIED",
        "protocol": VERSION,
        "strict_portable_keywords": sorted(ALLOWED_KEYWORDS),
        "enum_value_count": _forbid_unsupported(wire),
        "schema_sha256": digest,
        "synthetic_fixture_host_valid": bool(CreativeScene.model_validate(normalized)),
        "model_inference_http_posts": 0,
        "model_authored_mp4": "NOT_OBTAINED",
        "strict_endpoint_native_enforcement": "NOT_VERIFIED",
        "pedagogical_quality": "NOT_ASSESSED",
        "production": "BLOCKED",
    }


def candidate_request_body() -> dict:
    """Pure deterministic future request preview; NO transport or credentials."""
    from learnflow_v3.creative_manim_runner import MODEL, prompt
    domain_prompt = deepcopy(prompt())
    # Old V3-34 hint describes legacy claim_ids/wire and model_author field.
    # It is only a hint, not an instruction in the V3-41 protocol.
    domain_prompt.pop("schema", None)
    domain_prompt["output_protocol"] = VERSION
    domain_prompt["wire_rules"] = [
        "Return exactly four ordered beat_1..beat_4 objects.",
        "Each beat MUST select its own claim_primary F1/F2/F3. Optional secondary/tertiary slots are empty strings or model-chosen approved claim IDs.",
        "Do not emit claim_ids arrays. Never leave claim_primary empty.",
        "Use ONLY the offered numeric enums for x,y,width,height,radius; do not round or clip after the response.",
        "Keep graphic IDs unique and show each target before any move/emphasize/remove.",
        "Every action requires target,x,y; set unused x/y to 0 and wait target to an empty string.",
        "Do not emit model_author or executable Python.",
        "Four beats together must cover all approved factual claim IDs.",
    ]
    return {
        "model": MODEL,
        "max_tokens": 6500,
        "provider": {"allow_fallbacks": False, "require_parameters": True},
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "learnflow_creative_scene_v341",
                "strict": True,
                "schema": portable_wire_schema(),
            },
        },
        "messages": [
            {"role": "system", "content":
             "Author an original fact-grounded educational Manim storyboard in JSON data only; no executable code. The schema is mandatory. Do not fabricate factual sources."},
            {"role": "user", "content": json.dumps(domain_prompt, ensure_ascii=False)},
        ],
    }


def offline_fake_provider_exchange(sender) -> tuple[dict, dict]:
    """One injected LOCAL callback; no URL, key, HTTP, retries or model proof.

    Rehearses the OpenRouter chat envelope and exact schema/semantic decoder.
    Never treat the returned hash as a real provider response SHA.
    """
    from hashlib import sha256
    if not callable(sender):
        raise Blocked("V341_MOCK_SENDER_REQUIRED")
    response = sender(candidate_request_body())
    if not (isinstance(response, dict) and
            isinstance(response.get("choices"), list) and
            len(response["choices"]) == 1):
        raise Blocked("V341_MOCK_BAD_ENVELOPE")
    choice = response["choices"][0]
    if not isinstance(choice, dict) or choice.get("finish_reason") != "stop":
        raise Blocked("V341_MOCK_TRUNCATED_OR_FILTERED")
    message = choice.get("message")
    raw = message.get("content") if isinstance(message, dict) else None
    if not isinstance(raw, str) or len(raw) > 45_000:
        raise Blocked("V341_MOCK_BAD_CONTENT")
    try:
        wire = json.loads(raw)
    except (ValueError, TypeError):
        raise Blocked("V341_MOCK_BAD_JSON") from None
    plan = decode_portable_wire(wire)
    return plan, {
        "stage": "SYNTHETIC_INJECTED_ENVELOPE_ONLY",
        "model_request_attempts": 0,
        "mock_only_content_sha256": sha256(raw.encode("utf-8")).hexdigest(),
        "real_model_response_sha256": None,
        "no_retry": True,
        "provider_fallback": False,
        "production": "BLOCKED",
    }
