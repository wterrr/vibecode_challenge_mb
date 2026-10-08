#!/usr/bin/env python3
"""V3-00 offline audit inventory verifier; never loads providers or remote content."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "reports" / "v3_00_reuse_inventory.json"
REPORT = ROOT / "reports" / "v3_00_baseline_merge_gate.md"
CLASSES = {"KEEP","EXPERIMENTAL","SUPERSEDED","EXCLUDE"}
def main() -> int:
    try:
        doc=json.loads(PATH.read_text(encoding="utf-8"))
        assert REPORT.is_file()
        assert doc["schema_version"] == "v3-00-baseline-inventory-v1"
        assert doc["scope"] == "AUDIT_ONLY"
        assert doc["main_sha"] == "29fab1d5738ccb060502c8ae82e2e31f00360811"
        assert doc["pilot_sha"] == "a1e4e8b72f4e63e9cde0ffd4351df9a936900d9a"
        assert doc["merge_base_sha"] == doc["main_sha"]
        assert doc["ahead"] == 27 and doc["behind"] == 0
        files,commits,capabilities,upstreams=(doc[k] for k in ("files","commits","capabilities","upstream"))
        assert len(files) == 23 and len({x["path"] for x in files}) == 23
        assert len(commits) == 27 and len({x["sha"] for x in commits}) == 27
        assert all(x["decision"] in CLASSES and x["rationale"] for x in files)
        assert all(x["decision"] in CLASSES and x["summary"] for x in commits)
        assert not any(x["path"].startswith("learnflow_v2/") for x in files)
        assert {x["id"] for x in capabilities} == {f"C{i}" for i in range(1,13)}
        assert all(x["internal"] and x["upstream_ref"] and x["proposed_test"] for x in capabilities)
        for cap in capabilities:
            for token in cap["proposed_test"].split():
                if token.endswith(".py"):
                    assert (ROOT / token).is_file(), f"missing proposed baseline test: {token}"
        assert len(upstreams) == 4 and all(len(x["sha"]) == 40 for x in upstreams)
        algogen=next(x for x in upstreams if x["repository"] == "MAC-AutoML/ALGOGEN-lab")
        assert algogen["decision"] == "STUDY_ONLY_NO_COPY"
        assert "NO LICENSE" in algogen["license"]
        assert doc["gate"]["straight_fast_forward"] == "NO_GO"
        assert doc["gate"]["paid_api_calls"] == 0
        assert doc["gate"]["frozen_core_paths_changed"] == 0
        assert doc["gate"]["post_v3_build_authorized"] is False
        text=REPORT.read_text(encoding="utf-8")
        assert all(x in text for x in ("27-commit inventory","23-file inventory","No Manim dependency was installed","V3-00B"))
        print("V3_00_BASELINE=PASS commits=27 files=23 capabilities=12")
        return 0
    except (AssertionError, KeyError, OSError, ValueError, StopIteration) as e:
        print(f"V3_00_BASELINE=FAIL {type(e).__name__}: {e}")
        return 1
if __name__ == "__main__":
    raise SystemExit(main())
