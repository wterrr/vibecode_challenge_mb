#!/usr/bin/env python3
"""End-to-end offline V3 vertical slice using project-owned source. Not a golden."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v3.offline_lesson_source import build_binary_lesson_source
from learnflow_v3.integration_slice import (
    IntegratedClipReceipt,run_integrated_binary_clip,verify_integrated_binary_clip,
)
from learnflow_v3.sequence_renderer import SequenceRenderProfile
from scripts.audit_v3_reachability import build_inventory


def main(out:Path)->None:
    out.mkdir(parents=True,exist_ok=True)
    source=build_binary_lesson_source(
        values=(1,3,5,7,9,12,12,14,18),target=12)
    profile=SequenceRenderProfile(width=640,height=360,fps=12,seconds_per_step=.75)
    receipt=run_integrated_binary_clip(source=source,out_dir=out,profile=profile)
    if not isinstance(receipt,IntegratedClipReceipt):
        raise AssertionError("V3_INTEGRATION_RENDERER_MISSING")
    verify_integrated_binary_clip(source=source,out_dir=out,
                                  profile=profile,receipt=receipt)
    inventory=build_inventory()
    (out/"v3_integration_dead_code_inventory.json").write_text(
        json.dumps(inventory,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
    )
    assert inventory["module_count"]>=20
    callers={caller for row in inventory["rows"] for caller in row["production_callers"]}
    assert callers=={"app/pipeline/v3_preview.py"}  # sole guarded app entrypoint
    assert receipt.publication=="PUBLISH_BLOCKED"
    assert receipt.web_pipeline_connected is False
    print("V3_INTEGRATION_ROUTE=PASS legacy_router=SELECTED_UNRENDERABLE "
          "adapter=STATEFUL_SEQUENCE_BINARY_SEARCH no_concept_card=True")
    print(f"V3_INTEGRATION_PIXELS=PASS frames={receipt.frame_count} "
          f"scene_rgb_sha={receipt.decoded_scene_rgb_sha256} "
          f"assembly_rgb_sha={receipt.decoded_assembly_rgb_sha256}")
    print("V3_INTEGRATION_ASSEMBLY=PASS real_H264=True one_scene=True "
          "original_audio=NONE publication=BLOCKED")
    print(f"V3_INTEGRATION_INVENTORY=PASS scanned={inventory['scope_files_scanned']} "
          f"modules={inventory['module_count']} "
          f"production_imports={inventory['production_v3_imports_found']}")
    print("V3_INTEGRATION_CLOSURE=BOUNDED_OFFLINE_VERTICAL_SLICE_PASS "
          "production_wiring=NOT_DONE human_quality=UNMEASURED")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    main(p.parse_args().output_dir)
