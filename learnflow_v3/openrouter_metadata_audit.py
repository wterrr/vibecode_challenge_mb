"""V3-38 metadata-only diagnostics, deliberately incapable of inference.

Fixed allowlisted HTTPS GETs only. No dynamic URL, POST, retries, redirects,
raw response persistence, credential echo, management-token operations, or
provider error-body logging. This is NOT proof of chat model entitlements.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, HTTPRedirectHandler, build_opener

MODEL = "openai/gpt-6-luna"
CATALOG_URL = "https://openrouter.ai/api/v1/models/openai/gpt-6-luna/endpoints"
KEY_URL = "https://openrouter.ai/api/v1/key"
MAX_CATALOG_BYTES = 120_000
MAX_KEY_BYTES = 20_000
REQUIRED = frozenset({"response_format", "structured_outputs"})


class NeverFollowRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class MetadataInvalid(Exception):
    pass


def _get(url: str, *, bearer: str | None, sender=None, max_bytes: int) -> tuple[str, object]:
    if url not in (CATALOG_URL, KEY_URL):
        raise MetadataInvalid("NOT_ALLOWLISTED")
    if (url == KEY_URL) != (bearer is not None):
        raise MetadataInvalid("AUTH_ENDPOINT_CONTRACT")
    headers = {"Accept": "application/json", "User-Agent": "LearnFlow-V3-38-GET-only"}
    if bearer is not None:
        headers["Authorization"] = "Bearer " + bearer
    request = Request(url, headers=headers, method="GET")
    if request.get_method() != "GET" or request.data is not None:
        raise MetadataInvalid("NON_GET_REQUEST")
    call = sender or build_opener(NeverFollowRedirect()).open
    try:
        with call(request, timeout=12) as response:
            raw = response.read(max_bytes + 1)
    except HTTPError as exc:
        # Never read or copy an untrusted error body.
        return "HTTP_" + str(exc.code), None
    except (URLError, TimeoutError, OSError, ValueError):
        return "NETWORK_OR_TIMEOUT", None
    if len(raw) > max_bytes:
        return "RESPONSE_TOO_LARGE", None
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError, TypeError):
        return "INVALID_JSON", None
    return "HTTP_200", parsed


def probe_model_endpoints(*, sender=None) -> dict:
    status, body = _get(CATALOG_URL, bearer=None, sender=sender,
                        max_bytes=MAX_CATALOG_BYTES)
    output = {
        "model": MODEL, "http_status": status,
        "model_id_matched": False,
        "endpoint_count": None,
        "schema_advertised_count": None,
        "schema_and_max_tokens_count": None,
        "schema_and_max_completion_tokens_count": None,
        "schema_provider_names": [],
        "inference_requests": 0,
        "account_eligibility_certified": False,
    }
    if status != "HTTP_200":
        output["state"] = "CATALOG_UNVERIFIED"
        return output
    record = body.get("data") if isinstance(body, dict) else None
    if not isinstance(record, dict) or record.get("id") != MODEL:
        output["state"] = "CATALOG_INVALID_MODEL_ID"
        return output
    endpoints = record.get("endpoints")
    if not isinstance(endpoints, list) or len(endpoints) > 200:
        output["state"] = "CATALOG_INVALID_ENDPOINT_LIST"
        return output
    qualified = []
    for entry in endpoints:
        if not isinstance(entry, dict):
            continue
        ps = entry.get("supported_parameters")
        if isinstance(ps, list):
            params = {p for p in ps if isinstance(p, str) and len(p) <= 90}
            if REQUIRED.issubset(params):
                qualified.append((entry, params))
    # Provider names come from public metadata, not user/account details.
    # Fixed vocab prevents arbitrary source strings from reaching CI artifacts.
    known = {"OpenAI", "Azure", "Amazon Bedrock"}
    providers = sorted({entry.get("provider_name") for entry, _ in qualified
                        if entry.get("provider_name") in known})
    output.update({
        "state": "PUBLIC_SCHEMA_ENDPOINTS_ADVERTISED"
                 if qualified else "NO_PUBLIC_SCHEMA_ENDPOINTS",
        "model_id_matched": True,
        "endpoint_count": len(endpoints),
        "schema_advertised_count": len(qualified),
        "schema_and_max_tokens_count": sum("max_tokens" in params for _, params in qualified),
        "schema_and_max_completion_tokens_count": sum("max_completion_tokens" in params for _, params in qualified),
        "schema_provider_names": providers,
    })
    return output


def _positive_limit_state(data: dict) -> str:
    # A missing/unlimited key cap does NOT prove funded account credits.
    lim = data.get("limit")
    rem = data.get("limit_remaining")
    if lim is None:
        return "NO_EXPLICIT_KEY_CAP_REPORTED"
    if type(rem) not in (int, float) or not math.isfinite(rem):
        return "UNKNOWN"
    return "POSITIVE" if rem > 0 else "ZERO_OR_NEGATIVE"


def _expiry_state(value: object) -> str:
    if value is None:
        return "NOT_REPORTED"
    if not isinstance(value, str) or len(value) > 80:
        return "UNKNOWN"
    try:
        expiry = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if expiry.tzinfo is None:
            return "UNKNOWN"
        return "EXPIRED" if expiry < datetime.now(timezone.utc) else "NOT_EXPIRED"
    except ValueError:
        return "UNKNOWN"


def probe_current_key(key: str | None, *, sender=None) -> dict:
    output = {
        "http_status": "NOT_REQUESTED",
        "state": "KEY_NOT_CONFIGURED",
        "key_authenticated": False,
        "key_type": "UNKNOWN",
        "free_tier": "UNKNOWN",
        "key_limit_remaining_state": "UNKNOWN",
        "expiry_state": "UNKNOWN",
        "model_entitlement_verified": False,
        "account_credits_verified": False,
        "workspace_restrictions_verified": False,
        "inference_requests": 0,
    }
    if not key or len(key) < 10:
        return output
    status, body = _get(KEY_URL, bearer=key, sender=sender, max_bytes=MAX_KEY_BYTES)
    output["http_status"] = status
    if status == "HTTP_401":
        output["state"] = "KEY_UNAUTHORIZED"
    elif status in ("HTTP_403", "HTTP_429"):
        output["state"] = "KEY_METADATA_ACCESS_DENIED_OR_RATE_LIMITED"
    elif status != "HTTP_200":
        output["state"] = "KEY_ENDPOINT_UNAVAILABLE"
    else:
        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, dict):
            output["state"] = "KEY_METADATA_INVALID_ENVELOPE"
        else:
            output["state"] = "KEY_AUTHENTICATED_METADATA_ONLY"
            output["key_authenticated"] = True
            role = data.get("is_management_key")
            output["key_type"] = ("MANAGEMENT" if role is True else
                                  "INFERENCE" if role is False else "UNKNOWN")
            tier = data.get("is_free_tier")
            output["free_tier"] = tier if type(tier) is bool else "UNKNOWN"
            output["key_limit_remaining_state"] = _positive_limit_state(data)
            output["expiry_state"] = _expiry_state(data.get("expires_at"))
    return output


def run_audit(key: str | None, *, sender=None) -> dict:
    catalog = probe_model_endpoints(sender=sender)
    auth = probe_current_key(key, sender=sender)
    return {
        "checkpoint": "V3-38",
        "audit_type": "GET_ONLY_METADATA_NO_INFERENCE",
        "model": MODEL,
        "public_catalog": catalog,
        "key_metadata": auth,
        "get_requests_attempted": 1 + int(bool(key and len(key) >= 10)),
        "inference_http_posts": 0,
        "paid_request_authorized": False,
        "historical_v3_37_http_404_root_cause": "UNDETERMINED",
        "routing_compatibility_exact_post": "NOT_TESTED",
        "raw_key_or_account_response_preserved": False,
        "provider_response_body_preserved": False,
        "production": "BLOCKED",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    result = run_audit(os.getenv("OPENROUTER_API_KEY"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("V3_38_CATALOG=" + result["public_catalog"]["state"], flush=True)
    print("V3_38_KEY=" + result["key_metadata"]["state"], flush=True)
    print("V3_38_MODEL_POSTS=0", flush=True)


if __name__ == "__main__":
    main()
