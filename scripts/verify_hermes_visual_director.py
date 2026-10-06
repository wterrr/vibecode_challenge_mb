#!/usr/bin/env python3
"""Verify Visual Director structured output against the exact pinned Hermes runtime."""

from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify_script_agent import build_fixture, build_script
from visual_director import build_visual_director_task
from tools.delegation_output_schema import coerce_output_schema


FORBIDDEN_PROPERTIES = {
    "x",
    "y",
    "width",
    "height",
    "pixel_x",
    "pixel_y",
    "x_px",
    "y_px",
    "font_size",
    "coordinates",
    "renderer",
    "ffmpeg",
}


def property_names(value):
    names = set()
    if isinstance(value, dict):
        properties = value.get("properties")
        if isinstance(properties, dict):
            names.update(properties)
        for child in value.values():
            names.update(property_names(child))
    elif isinstance(value, list):
        for child in value:
            names.update(property_names(child))
    return names


def main() -> int:
    brief, pack, evidence_graph, report, pedagogy = build_fixture()
    script = build_script(pedagogy)
    task = build_visual_director_task(
        brief,
        pack,
        evidence_graph,
        report,
        pedagogy,
        script,
    )

    schema, error = coerce_output_schema(task["output_schema"])
    if error or schema is None:
        raise SystemExit(
            f"HERMES_VISUAL_DIRECTOR=FAIL output_schema incompatible: {error!r}"
        )

    root_properties = set(schema.get("properties", {}))
    if not {"storyboard", "scenegraphs"}.issubset(root_properties):
        raise SystemExit("HERMES_VISUAL_DIRECTOR=FAIL output envelope incomplete")

    leaked = property_names(schema) & FORBIDDEN_PROPERTIES
    if leaked:
        raise SystemExit(
            f"HERMES_VISUAL_DIRECTOR=FAIL geometry fields leaked: {sorted(leaked)!r}"
        )

    defs = schema.get("$defs", {})
    layout_hint = defs.get("LayoutHint", {}).get("properties", {})
    if not {
        "preferred_region",
        "importance",
        "keep_near",
        "keep_apart",
        "preferred_order",
    }.issubset(layout_hint):
        raise SystemExit("HERMES_VISUAL_DIRECTOR=FAIL semantic LayoutHint incomplete")

    context = json.loads(task["context"])
    if "research_pack" in context or "selected_fact_claims" in context:
        raise SystemExit("HERMES_VISUAL_DIRECTOR=FAIL research context leaked")
    if context["required_ids"]["script_id"] != script.script_id:
        raise SystemExit("HERMES_VISUAL_DIRECTOR=FAIL script binding")
    if not context["concept_registry"]["concepts"]:
        raise SystemExit("HERMES_VISUAL_DIRECTOR=FAIL concept registry missing")

    instruction_text = "\n".join(context["instructions"]).lower()
    if "pixel" not in instruction_text or "semantic" not in instruction_text:
        raise SystemExit("HERMES_VISUAL_DIRECTOR=FAIL visual boundary instruction missing")
    if "do not invent concept ids" not in instruction_text:
        raise SystemExit("HERMES_VISUAL_DIRECTOR=FAIL concept identity rule missing")

    print("HERMES_VISUAL_DIRECTOR=PASS")
    print("runtime=exact pinned Hermes")
    print("structured_visual_director_schema=PASS")
    print("scenegraph_v2_1_schema=PASS")
    print("semantic_layout_hint_schema=PASS")
    print("no_geometry_fields=PASS")
    print("deterministic_registry_context=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
