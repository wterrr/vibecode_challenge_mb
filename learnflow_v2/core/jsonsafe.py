"""Generic strict JSON-safe validation helpers for LearnFlow V2.

JSON-safe means values are replayable with RFC-compliant JSON semantics:
None, bool, int, finite float, str, list, and dict[str, JSON-safe].
Tuples/sets/bytes/Path/callables/custom objects and non-finite floats are rejected.
"""

from __future__ import annotations

import math
from typing import Any, Union

JSONSafeValue = Union[
    None,
    bool,
    int,
    float,
    str,
    list["JSONSafeValue"],
    dict[str, "JSONSafeValue"],
]


def validate_json_safe(value: Any, *, path: str = "value") -> None:
    """Raise ValueError if *value* is not strictly JSON-safe.

    This intentionally rejects Python containers that JSON would silently coerce
    (for example tuple -> list) and floats that json.dumps would otherwise emit
    as non-standard NaN/Infinity unless allow_nan is disabled.
    """
    if value is None or isinstance(value, (str, bool)):
        return

    # bool is a subclass of int, so it must be handled before int.
    if isinstance(value, int):
        return

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must be a finite float, got {value!r}")
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            validate_json_safe(item, path=f"{path}[{index}]")
        return

    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} keys must be strings, got {type(key).__name__}")
            validate_json_safe(item, path=f"{path}.{key}")
        return

    raise ValueError(
        f"{path} contains non JSON-safe value of type {type(value).__name__}; "
        "allowed types are null, bool, int, finite float, string, list, and dict[str, JSON-safe]"
    )


def ensure_json_safe_dict(value: dict[str, Any], *, path: str = "metadata") -> dict[str, Any]:
    """Validate and return a strict JSON-safe dict."""
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be a dict[str, JSON-safe value]")
    validate_json_safe(value, path=path)
    return value
