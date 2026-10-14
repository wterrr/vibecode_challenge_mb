#!/usr/bin/env python3
"""V3-71 offline physical reviewer-kit validation, never human scoring.

Reuses the exact V3-60 native media verification and V3-61 masked UI
preregistration. No provider/model network or treatment-key access.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_v3_60_independent_review import (
    ReviewBlocked, spec, template_rows, verify_packet
)
from scripts.build_v3_61_review_ui import preregistered

REG = ROOT / "benchmarks/learnflowbench/v3/v3_71_native_preflight_preregister.json"
STATIC = {"MASKED_MANIFEST.json", "START_HERE.txt", "v361.css",
          "v361_reviewer.js", "reviewer_01.html", "reviewer_02.html",
          "reviewer_03.html"}
FORBIDDEN = ("admin_treatment_key", "original_motion", "causal_reveal",
             "static_end_state", "https://", "http://", "fetch(",
             "XMLHttpRequest", "WebSocket", "sendBeacon")


def require(ok: bool, reason: str):
    if not ok:
        raise ReviewBlocked("V371_" + reason)


def verify_kit(zip_path: Path, *, full_decode: bool = False) -> dict:
    prereg = json.loads(REG.read_text(encoding="utf-8"))
    require(prereg.get("checkpoint") == "V3-71" and
            prereg.get("parent", {}).get("sha") ==
            "4f12f5a5b093b2d44719dc1ddb02733a70444267",
            "PREREG_DRIFT")
    source = spec()
    v361 = preregistered()
    require(source["masked_clips_sha256"] == v361["masked_clips_sha256"],
            "FROZEN_MEDIA_DRIFT")
    expected = STATIC | {"media/" + name
                         for name in source["masked_clips_sha256"]}
    require(zip_path.is_file() and not zip_path.is_symlink(), "KIT_ZIP_MISSING")
    require(0 < zip_path.stat().st_size <= 80_000_000, "KIT_ZIP_OVERSIZE")
    try:
        with zipfile.ZipFile(zip_path) as z:
            infos = z.infolist()
            names = [x.filename for x in infos]
            require(len(names) == len(expected) and len(set(names)) == len(names) and
                    set(names) == expected, "ZIP_FILE_INVENTORY_OR_ADMIN_LEAK")
            require(sum(x.file_size for x in infos) <= 80_000_000,
                    "EXPANDED_KIT_OVERSIZE")
            for info in infos:
                mode = (info.external_attr >> 16)
                require(not info.is_dir() and
                        not stat.S_ISLNK(mode) and
                        not info.filename.startswith("/") and
                        ".." not in Path(info.filename).parts and
                        info.file_size <= 10_000_000,
                        "ZIP_ENTRY_UNSAFE")
            with tempfile.TemporaryDirectory(prefix="v371-masked-") as td:
                root = Path(td)
                z.extractall(root)
                manifest = json.loads((root / "MASKED_MANIFEST.json").read_text(
                    encoding="utf-8"))
                require(manifest.get("clips") ==
                        source["masked_clips_sha256"] and
                        manifest.get("treatment_mapping") == "WITHHELD" and
                        manifest.get("reviewer_count") == 0 and
                        manifest.get("human_quality") == "UNRATED",
                        "MANIFEST_SCOPE_OR_HASH_DRIFT")
                for path in (root / "v361_reviewer.js", root / "v361.css"):
                    content = path.read_text(encoding="utf-8")
                    require(not any(x in content for x in FORBIDDEN),
                            "UI_NETWORK_OR_TREATMENT_LEAK")
                for i in (1, 2, 3):
                    content = (root / f"reviewer_{i:02d}.html").read_text(
                        encoding="utf-8")
                    require(not any(x in content for x in FORBIDDEN),
                            "UI_NETWORK_OR_TREATMENT_LEAK")
                    require("connect-src 'none'" in content, "MISSING_CSP")
                    match = re.search(
                        r'<script type="application/json" id="frozen-configuration">(.*?)</script>',
                        content, flags=re.S)
                    require(match is not None, "FORM_CONFIGURATION_MISSING")
                    config = json.loads(match.group(1))
                    frozen = template_rows(source, i - 1)
                    require(config.get("checkpoint") == "V3-61" and
                            config.get("form_number") == i and
                            [v["clip_id"] for v in config.get("clips", [])] ==
                            [v["clip_id"] for v in frozen],
                            "FORM_ORDER_DRIFT")
                verified = verify_packet(root / "media", decode=full_decode)
                require(verified["media_integrity"] == "PASS_NATIVE_MASKED" and
                        len(verified["clips"]) == 9, "NATIVE_MEDIA_GATE")
                return {
                    "checkpoint": "V3-71",
                    "gate": "NATIVE_MASKED_REVIEW_PACKET_PASS",
                    "source_artifact_id": 11863189967,
                    "files_verified": 16,
                    "video_shas_verified": 9,
                    "assigned_blinded_forms": 3,
                    "full_decode": "PASS" if full_decode else "NOT_REQUESTED",
                    "AAC_and_frame_parity": "PASS",
                    "admin_treatment_mapping": "WITHHELD",
                    "independent_real_reviewers": 0,
                    "pedagogical_quality": "UNRATED",
                    "learner_gain": "NOT_MEASURED",
                    "model_creativity": "NOT_TESTED",
                    "production": "BLOCKED",
                }
    except (zipfile.BadZipFile, OSError) as exc:
        raise ReviewBlocked("V371_INVALID_OR_UNREADABLE_ZIP") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit-zip", type=Path, required=True)
    parser.add_argument("--full-decode", action="store_true")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    receipt = verify_kit(args.kit_zip, full_decode=args.full_decode)
    if args.receipt is not None:
        require(not args.receipt.exists(), "OUTPUT_ALREADY_EXISTS")
        args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) +
                                "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
