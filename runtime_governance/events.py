"""Privacy-minimized JSONL metrics/lifecycle audit for runtime governance."""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import RLock
from time import time
from typing import Any

_LOCK = RLock()


def append_event(path: str | Path, event: str, **fields: Any) -> None:
    """Append metadata only; callers must not pass raw prompts, args, or results."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "event": str(event),
        "observed_at": round(time(), 6),
        **fields,
    }
    line = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    with _LOCK:
        with target.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
