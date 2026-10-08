"""OpenRouter live-model capability and availability probe for V2D."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from openrouter_policy import require_free_openrouter_model


LIVE_MODEL_CANDIDATES = (
    "google/gemma-4-31b-it:free",
    "poolside/laguna-s-2.1:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "apodex/apodex-1.1-mini:free",
)

_RESPONSE_FORMAT_MODELS = (
    "google/gemma-4-",
    "apodex/apodex-",
)

_SPECIALIST_PROBE_OBJECT = {
    "sources": [
        {
            "title": "OpenRouter",
            "locator": "https://openrouter.ai/",
        }
    ],
    "claims": [
        {
            "statement": "Probe claim.",
            "source_indexes": [0],
            "confidence": 1.0,
        }
    ],
    "misconceptions": [
        {
            "statement": "Probe misconception.",
            "correction": "Probe correction.",
            "claim_indexes": [0],
        }
    ],
    "examples": [
        {
            "description": "Probe example.",
            "claim_indexes": [0],
        }
    ],
}

OPENROUTER_CHAT_COMPLETIONS = "https://openrouter.ai/api/v1/chat/completions"


@dataclass(frozen=True)
class ModelProbeResult:
    model: str
    passed: bool
    status: str
    detail: str = ""
    request_count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelSelection:
    selected_model: str
    probes: tuple[ModelProbeResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_model": self.selected_model,
            "probes": [item.to_dict() for item in self.probes],
        }


class ModelProbeError(RuntimeError):
    def __init__(self, message: str, probes: Iterable[ModelProbeResult]) -> None:
        super().__init__(message)
        self.probes = tuple(probes)


def _safe_detail(value: Any) -> str:
    text = str(value).replace("\n", " ").strip()
    return text[-500:]


def _safe_http_error_detail(raw: str) -> str:
    """Keep diagnostic HTTP error fields without persisting account/header metadata."""

    try:
        payload = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return "non_json_http_error"

    error = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error, dict):
        return "unstructured_http_error"

    safe_error: dict[str, Any] = {}
    message = error.get("message")
    if isinstance(message, str) and message.strip():
        safe_error["message"] = _safe_detail(message)
    code = error.get("code")
    if isinstance(code, (int, float, str)) and not isinstance(code, bool):
        safe_error["code"] = code

    metadata = error.get("metadata")
    if isinstance(metadata, dict):
        safe_metadata = {}
        for key in ("limit_source", "provider_name", "remedy_hint"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                safe_metadata[key] = _safe_detail(value)
        if safe_metadata:
            safe_error["metadata"] = safe_metadata

    return json.dumps(
        {"error": safe_error},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _extract_text(message: Any) -> str:
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts)
    return ""


def _probe_sampling_parameters(model: str) -> dict[str, Any]:
    """Do not send unsupported sampling knobs to strict OpenRouter endpoints.

    GPT-6 Luna does not advertise the 'temperature' parameter. Under
    provider.require_parameters=True, including it causes a routing HTTP 404
    before tools or structured-output capability can be evaluated.
    """
    if model == "openai/gpt-6-luna":
        return {}
    return {"temperature": 0}


def _probe_one(*, api_key: str, model: str, timeout_seconds: float = 30.0) -> ModelProbeResult:
    """Probe both native function calling and structured specialist JSON.

    A model only passes when, under the same auto tool-selection surface used by
    pinned Hermes, it emits a real OpenAI-compatible tool_calls entry, consumes the
    tool result, and then returns the exact specialist-shaped JSON.
    Serializing a fake {"calls": ...} object in assistant text is not sufficient.
    """

    tool_definition = {
        "type": "function",
        "function": {
            "name": "probe_noop",
            "description": "Capability probe. Call exactly once with an empty object.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    }

    def _send(payload: dict[str, Any], *, request_count: int):
        request = Request(
            OPENROUTER_CHAT_COMPLETIONS,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/wterrr/vibecode_challenge_mb",
                "X-Title": "LearnFlow Live V2D Probe",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8")), None
        except HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")
            except Exception:
                detail = str(exc)
            return None, ModelProbeResult(
                model=model,
                passed=False,
                status=f"http_{exc.code}",
                detail=_safe_http_error_detail(detail),
                request_count=request_count,
            )
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            return None, ModelProbeResult(
                model=model,
                passed=False,
                status="transport_error",
                detail=_safe_detail(exc),
                request_count=request_count,
            )

    tool_prompt = (
        "Capability probe. Call the probe_noop function exactly once with an empty "
        "JSON object {}. Do not describe the call and do not return a JSON imitation "
        "of a tool call in assistant text."
    )
    tool_payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": tool_prompt}],
        "max_tokens": 4096,
        **_probe_sampling_parameters(model),
        "tools": [tool_definition],
        # Match pinned Hermes ChatCompletionsTransport: expose tools but do not
        # force tool_choice. Passing a forced function here rejects otherwise
        # usable OpenRouter free endpoints that Hermes itself can call.
        "provider": {"require_parameters": True},
    }
    if model.startswith("google/gemma-4-"):
        tool_payload["reasoning_effort"] = "medium"

    body, error = _send(tool_payload, request_count=1)
    if error is not None:
        return error

    try:
        message = body["choices"][0]["message"]
        tool_calls = message["tool_calls"]
        if not isinstance(tool_calls, list) or len(tool_calls) != 1:
            raise ValueError("expected exactly one native tool call")
        tool_call = tool_calls[0]
        function = tool_call["function"]
        if function.get("name") != "probe_noop":
            raise ValueError(f"unexpected tool name {function.get('name')!r}")
        arguments = function.get("arguments", "{}")
        parsed_arguments = (
            json.loads(arguments)
            if isinstance(arguments, str)
            else arguments
        )
        if parsed_arguments != {}:
            raise ValueError(
                f"probe_noop arguments must be empty object, got {parsed_arguments!r}"
            )
        tool_call_id = str(tool_call["id"])
        if not tool_call_id:
            raise ValueError("native tool call is missing id")
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        safe_prefix = ""
        try:
            safe_prefix = _extract_text(body["choices"][0].get("message", {}))[:240]
        except Exception:
            pass
        return ModelProbeResult(
            model=model,
            passed=False,
            status="native_tool_call_missing",
            detail=_safe_detail(
                f"{type(exc).__name__}: {exc}; response_prefix={safe_prefix!r}"
            ),
            request_count=1,
        )

    assistant_message = {
        "role": "assistant",
        "content": message.get("content"),
        "tool_calls": tool_calls,
    }
    final_prompt = (
        "The tool call succeeded. Return ONLY the following JSON object exactly, "
        "with the same keys, nesting, arrays, indexes, strings, and numbers. JSON: "
        + json.dumps(
            _SPECIALIST_PROBE_OBJECT,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    final_payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "user", "content": tool_prompt},
            assistant_message,
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": json.dumps({"ok": True}, separators=(",", ":")),
            },
            {"role": "user", "content": final_prompt},
        ],
        "max_tokens": 4096,
        **_probe_sampling_parameters(model),
        "provider": {"require_parameters": True},
    }
    if model.startswith(_RESPONSE_FORMAT_MODELS):
        final_payload["response_format"] = {"type": "json_object"}
    if model.startswith("google/gemma-4-"):
        final_payload["reasoning_effort"] = "medium"

    body, error = _send(final_payload, request_count=2)
    if error is not None:
        return error

    try:
        choice = body["choices"][0]
        final_message = choice["message"]
        text = _extract_text(final_message)
        parsed = json.loads(text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        finish_reason = None
        try:
            finish_reason = body["choices"][0].get("finish_reason")
        except Exception:
            pass
        safe_prefix = ""
        try:
            safe_prefix = _extract_text(body["choices"][0].get("message", {}))[:240]
        except Exception:
            pass
        return ModelProbeResult(
            model=model,
            passed=False,
            status="invalid_probe_response",
            detail=_safe_detail(
                f"{type(exc).__name__}: {exc}; "
                f"finish_reason={finish_reason!r}; "
                f"response_prefix={safe_prefix!r}"
            ),
            request_count=2,
        )

    if parsed != _SPECIALIST_PROBE_OBJECT:
        return ModelProbeResult(
            model=model,
            passed=False,
            status="schema_mismatch",
            detail=_safe_detail(parsed),
            request_count=2,
        )
    return ModelProbeResult(
        model=model,
        passed=True,
        status="pass",
        request_count=2,
    )


def select_live_model(
    *,
    api_key: str,
    candidates: Iterable[str] = LIVE_MODEL_CANDIDATES,
) -> ModelSelection:
    probes: list[ModelProbeResult] = []
    seen: set[str] = set()
    for raw in candidates:
        model = require_free_openrouter_model(str(raw).strip())
        if not model or model in seen:
            continue
        seen.add(model)
        result = _probe_one(api_key=api_key, model=model)
        probes.append(result)
        if result.passed:
            return ModelSelection(selected_model=model, probes=tuple(probes))
    raise ModelProbeError("no live model passed the OpenRouter capability probe", probes)
