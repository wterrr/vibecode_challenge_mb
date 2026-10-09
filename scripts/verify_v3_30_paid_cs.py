#!/usr/bin/env python3
"""V3-30 source/check/opt-in paid Luna runner. NO fixture can count as live."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learnflow_v3.paid_cs_lesson import Blocked, MODEL, fetch_source, run_one


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("source-check", "live-paid"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=False)
    if args.mode == "source-check":
        try:
            result = fetch_source()
            # Do not persist copyrighted entire source paragraphs in source-only evidence.
            result = {k: v for k, v in result.items() if k != "spans"}
            (output / "v3_30_official_python_source.json").write_text(json.dumps(result, indent=2)+"\n")
            print("V3_30_SOURCE=PASS official Python docs, quotes verified, not independent fact review")
            return 0
        except (Blocked, OSError, ValueError) as error:
            (output / "v3_30_official_python_source.json").write_text(json.dumps({
                "status": "BLOCKED", "error": type(error).__name__,
                "independent_fact_review": "NOT_RUN"}, indent=2)+"\n")
            print("V3_30_SOURCE=BLOCKED", flush=True)
            return 2
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        (output / "v3_30_live_receipt.json").write_text(json.dumps({
            "status": "NOT_RUN_NO_SECRET", "model": MODEL, "paid_calls": 0,
            "video": "NOT_RUN", "production": "BLOCKED"}, indent=2)+"\n")
        print("V3_30_PAID_LIVE=NOT_RUN_NO_SECRET")
        return 2
    try:
        result = run_one(root=ROOT, out=output, key=key)
        print("V3_30_PAID_LIVE=" + result["status"], flush=True)
        return 0
    except (Blocked, OSError, ValueError, RuntimeError) as error:
        (output / "v3_30_live_failure.json").write_text(json.dumps({
            "status": "BLOCKED_NO_LIVE_PASS", "error_type": type(error).__name__,
            "error_code": str(error)[:130] if isinstance(error, Blocked) else "RENDER_OR_GATE_BLOCKED",
            "model": MODEL, "max_paid_calls": 2,
            "human_quality": "NOT_RUN", "production": "BLOCKED"}, indent=2)+"\n")
        print("V3_30_PAID_LIVE=BLOCKED_NO_LIVE_PASS", flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
