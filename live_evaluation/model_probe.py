"""OpenRouter live-model capability and availability probe for V2D."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


LIVE_MODEL_CANDIDATES = (
    "nvidia/nemotron-3-super-120b-a12b:free",
    "apodex/apodex-1.1-mini:free",
)

OPENROUTER_CHAT_COMPLETIONS = "https://openrouter.ai/api/v1/chat/completions"


@dataclass(frozen=True)
class ModelProbeResult:
    model: str
    passed: bool
    status: str
    detail: str = ""

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


def _probe_one(*, api_key: str, model: str, timeout_seconds: float = 30.0) -> ModelProbeResult:
    schema = {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean", "const": True},
            "marker": {"type": "string", "const": "live-v2d-probe"},
        },
        "required": ["ok", "marker"],
        "additionalProperties": False,
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Return only this JSON object exactly: "
                    "{\"ok\":true,\"marker\":\"live-v2d-probe\"}. "
                    "Do not call the probe_noop tool."
                ),
            }
        ],
        "max_tokens": 256,
        "temperature": 0,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "probe_noop",
                    "description": "Capability probe only; do not call it.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                },
            }
        ],
        "response_format": {
            "type": "json_object",
        },
        "provider": {"require_parameters": True},
    }
    if model.startswith("nvidia/nemotron-3-super-"):
        # The Super model supports extended thinking. Disable reasoning only for
        # this tiny capability probe so reasoning tokens cannot consume the
        # completion budget before the required JSON object is finished.
        payload["reasoning_effort"] = "none"
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
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = str(exc)
        return ModelProbeResult(
            model=model,
            passed=False,
            status=f"http_{exc.code}",
            detail=_safe_detail(detail),
        )
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        return ModelProbeResult(
            model=model,
            passed=False,
            status="transport_error",
            detail=_safe_detail(exc),
        )

    try:
        choice = body["choices"][0]
        message = choice["message"]
        text = _extract_text(message)
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
        )

    if parsed != {"ok": True, "marker": "live-v2d-probe"}:
        return ModelProbeResult(
            model=model,
            passed=False,
            status="schema_mismatch",
            detail=_safe_detail(parsed),
        )
    return ModelProbeResult(model=model, passed=True, status="pass")


def select_live_model(
    *,
    api_key: str,
    candidates: Iterable[str] = LIVE_MODEL_CANDIDATES,
) -> ModelSelection:
    probes: list[ModelProbeResult] = []
    seen: set[str] = set()
    for raw in candidates:
        model = str(raw).strip()
        if not model or model in seen:
            continue
        seen.add(model)
        result = _probe_one(api_key=api_key, model=model)
        probes.append(result)
        if result.passed:
            return ModelSelection(selected_model=model, probes=tuple(probes))
    raise ModelProbeError("no live model passed the OpenRouter capability probe", probes)
