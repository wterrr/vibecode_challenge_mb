"""V3-42: ONE-POST genuine GPT-6 Luna portable strict-output decoding.

Separately authorized and preregistered; never called from ordinary CI. V3-39
wire/response path remains frozen. No retry/fallback, no raw output in artifacts.
"""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from jsonschema import Draft202012Validator
from pydantic import ValidationError

from learnflow_v3.compatible_scene_protocol import (
    candidate_request_body, decode_portable_wire, portable_wire_schema)
from learnflow_v3.creative_manim_ablation import Blocked, CreativeScene
from learnflow_v3.creative_manim_runner import API, MODEL


def _write_failure(out: Path, *, code: str, attempts: int, response_sha: str | None,
                   errors: list[dict] | None = None, usage: dict | None = None) -> None:
    (out / "v3_42_portable_model_failure.json").write_text(
        json.dumps({
            "checkpoint": "V3-42", "state": "BLOCKED",
            "code": code, "model": MODEL, "model_request_attempts": attempts,
            "model_response_sha256": response_sha,
            "validation_error_shapes": errors or [],
            "provider_reported_usage": usage,
            "raw_model_text_saved": False, "retry_count": 0,
            "provider_fallback": False, "production": "BLOCKED"
        }, indent=2) + "\n", encoding="utf-8")


def one_shot_portable(key: str, out: Path, *, sender=None) -> tuple[dict, dict]:
    if not out.is_dir() or any(out.iterdir()):
        raise Blocked("V342_OUTPUT_NONEMPTY")
    if not isinstance(key, str) or len(key) < 10:
        _write_failure(out, code="V342_API_KEY_NOT_CONFIGURED",
                       attempts=0, response_sha=None)
        raise Blocked("V342_API_KEY_NOT_CONFIGURED")
    body = candidate_request_body()
    schema = portable_wire_schema()
    if (body.get("model") != MODEL or body.get("max_tokens") != 6500
        or "temperature" in body or
        body.get("provider") != {"allow_fallbacks": False, "require_parameters": True}
        or body.get("response_format", {}).get("json_schema", {}).get("strict") is not True
        or body["response_format"]["json_schema"]["schema"] != schema):
        raise Blocked("V342_PREREGISTERED_WIRE_DRIFT")
    request = Request(API, method="POST", data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json",
                 "HTTP-Referer": "https://github.com/wterrr/vibecode_challenge_mb",
                 "X-Title": "LearnFlow V3-42 single portable genuine creative lesson"})
    (out / "v3_42_request_attempt.json").write_text(json.dumps({
        "checkpoint": "V3-42", "model": MODEL, "attempted_http_requests": 1,
        "temperature_parameter_sent": False,
        "provider_require_parameters": True,
        "provider_allow_fallbacks": False, "provider_retries": 0,
        "response_format": "json_schema_strict",
        "wire_schema_sha256": sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest(),
    }, indent=2) + "\n", encoding="utf-8")
    try:
        with (sender or urlopen)(request, timeout=125) as conn:
            wire = conn.read(220_000)
    except HTTPError as exc:
        code = "V342_HTTP_" + str(exc.code)
        _write_failure(out, code=code, attempts=1, response_sha=None)
        raise Blocked(code) from None
    except (URLError, TimeoutError, OSError):
        _write_failure(out, code="V342_PROVIDER_TRANSPORT_ERROR",
                       attempts=1, response_sha=None)
        raise Blocked("V342_PROVIDER_TRANSPORT_ERROR") from None
    # Envelope parsing never trusts the provider text as model attribution.
    try:
        envelope = json.loads(wire.decode("utf-8"))
        choices = envelope["choices"]
        if not isinstance(choices, list) or len(choices) != 1:
            raise Blocked("V342_PROVIDER_AMBIGUOUS_CHOICES")
        choice = choices[0]
        if choice.get("finish_reason") != "stop":
            raise Blocked("V342_PROVIDER_TRUNCATED")
        content = choice["message"]["content"]
        if not isinstance(content, str) or len(content) > 45000:
            raise Blocked("V342_PROVIDER_BAD_CONTENT")
        received_model = envelope.get("model")
        if received_model is not None and received_model != MODEL:
            raise Blocked("V342_PROVIDER_MODEL_MISMATCH")
    except (KeyError, TypeError, IndexError, ValueError, UnicodeError) as exc:
        code = str(exc) if isinstance(exc, Blocked) else "V342_PROVIDER_BAD_ENVELOPE"
        _write_failure(out, code=code, attempts=1, response_sha=None)
        raise Blocked(code) from None
    response_sha = sha256(content.encode("utf-8")).hexdigest()
    usage = envelope.get("usage")
    if not isinstance(usage, dict):
        usage = {}
    try:
        raw = json.loads(content)
    except (ValueError, TypeError):
        _write_failure(out, code="V342_PROVIDER_BAD_JSON", attempts=1,
                       response_sha=response_sha, usage=usage)
        raise Blocked("V342_PROVIDER_BAD_JSON") from None
    errors = list(Draft202012Validator(schema).iter_errors(raw))
    if errors:
        shapes = [{"path": ".".join(str(part) for part in err.absolute_path)[:100],
                   "type": "jsonschema_" + err.validator}
                  for err in errors[:60]]
        _write_failure(out, code="V342_PROVIDER_WIRE_SCHEMA_REJECT",
                       attempts=1, response_sha=response_sha,
                       errors=shapes, usage=usage)
        raise Blocked("V342_PROVIDER_WIRE_SCHEMA_REJECT")
    try:
        normalized = decode_portable_wire(raw)
        plan = CreativeScene.model_validate({**normalized, "model_author": MODEL})
    except (ValidationError, Blocked):
        _write_failure(out, code="V342_PROVIDER_HOST_SEMANTIC_REJECT",
                       attempts=1, response_sha=response_sha, usage=usage)
        raise Blocked("V342_PROVIDER_HOST_SEMANTIC_REJECT") from None
    canonical = plan.model_dump(mode="json")
    receipt = {
        "stage": "REAL_MODEL_SCHEMA_CONSTRAINED_SCENE", "model": MODEL,
        "actual_provider_requests": 1, "no_retry": True, "no_fallback": True,
        "provider_require_parameters": True, "temperature_parameter_sent": False,
        "model_response_sha256": response_sha,
        "strict_json_schema_sha256": sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest(),
        "validated_plan_canonical_sha256": sha256(json.dumps(
            canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "provider_response_id_sha256": sha256(str(envelope.get("id", "")).encode()).hexdigest(),
        "protocol": "V3-42_PREREGISTERED_V3-41_PORTABLE",
        "normalization_only_transport_placeholders": True,
        "usage": usage,
    }
    (out / "v3_42_portable_provider_receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return canonical, receipt
