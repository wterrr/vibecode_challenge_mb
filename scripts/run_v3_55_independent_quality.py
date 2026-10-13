#!/usr/bin/env python3
"""V3-55 three independent-family HOST storyboard trials, NOT model inference.

New test composition: V3-49 local rational scene, V3-47 condition/graph,
V3-53 reversed-Q causal attention. Existing finite semantic compilers are
reused unmodified, so any creative-quality improvement remains UNPROVEN.
"""
from __future__ import annotations
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_manim_runner import sha
from learnflow_v3.grounded_fraction_claims import FractionTopic, ground, verify
from learnflow_v3.semantic_scene_offline_fixtures import fixture_cases
from learnflow_v3.semantic_scene_wire import decode_model_facing_scene
from learnflow_v3.pedagogical_visual_grammar import offline_host_plan, validate_transformations
from learnflow_v3.process_edge_visual_qa import _frame
from learnflow_v3.independent_pedagogical_quality import (
    IDS, load_registration, verify_case_result, blank_review_csv, final_verdict)
from scripts.run_v3_49_grounded_claims import _run_case as render_fraction
from scripts.run_v3_47_pedagogical_storytelling import (
    _run_one as render_process, heldout_process)
from scripts.run_v3_53_creative_director import _case as render_attention

FRACTION, PROCESS, ATTENTION = IDS
FAMILIES = ("fraction_equivalence", "ordered_process", "transformer_attention")


def build_new_cases(reg: dict) -> tuple[dict, dict, dict]:
    rows = reg["independent_cases"]
    fr = rows[0]
    fraction = {"id": FRACTION, "role": "preregistered_host_visual_reuse",
                "source": fr["source"], "target": fr["target"],
                "factor": fr["factor"]}
    evidence = ground(FractionTopic(topic_id=FRACTION,
        numerator=fr["source"][0], denominator=fr["source"][1],
        factor=fr["factor"], target_numerator=fr["target"][0],
        target_denominator=fr["target"][1]))
    verify(evidence)

    raw = heldout_process(fixture_cases()["v345-synthetic-process"])
    # Second independent ID namespace, all topology references rebound;
    # not a new real-world condition and must never claim PASS/FAIL.
    graphics = raw["graphics"]
    ids = {g["id"]: "v55_" + g["id"] for g in graphics}
    for graphic in graphics:
        graphic["id"] = ids[graphic["id"]]
        if graphic["kind"] == "edge":
            graphic["src"] = ids[graphic["src"]]
            graphic["dst"] = ids[graphic["dst"]]
    for beat in raw["beats"]:
        for event in beat["events"]:
            if event["target"]: event["target"] = ids[event["target"]]
            if event["source"]: event["source"] = ids[event["source"]]
    process = decode_model_facing_scene(raw)
    validate_transformations(process, offline_host_plan(process))

    attention = {"id": ATTENTION, "role": "reversed_query_new_stage_combination",
                 "query": rows[2]["query"], "emphasis": "network",
                 "stages": ["intro", "compare", "normalize", "transport", "compose"]}
    if attention["query"] != [0, 1]:
        raise Blocked("V355_PREREG_ATTENTION_Q_CHANGED")
    return fraction, raw, attention


def contact_sheet(movie: pathlib.Path, out: pathlib.Path, frames: int):
    # Three native decoded timeline samples for human eyes; not a pixel PASS.
    times = [max(1, min(frames - 2, round(frames * t))) for t in (.12, .50, .88)]
    sheet = Image.new("RGB", (960, 220), (8, 11, 16))
    pen = ImageDraw.Draw(sheet)
    for idx, frame_no in enumerate(times):
        pic = Image.fromarray(_frame(movie, frame_no)).convert("RGB")
        pic.thumbnail((320, 180))
        sheet.paste(pic, (idx * 320, 17))
        pen.text((idx * 320 + 6, 199), f"t={frame_no / 15:.2f}s  frame={frame_no}",
                 fill=(229, 233, 238))
    sheet.save(out, quality=92)
    return {"frames": times, "contact_sha256": sha(out)}


def run(out: pathlib.Path) -> dict:
    reg = load_registration(ROOT)
    if out.exists():
        raise Blocked("V355_FRESH_OUTPUT_REQUIRED")
    out.mkdir(parents=True)
    fraction, process, attention = build_new_cases(reg)
    f = render_fraction(ROOT, out, fraction)
    p = render_process(out, PROCESS, process)
    a = render_attention(attention, out / ATTENTION)

    checks = [verify_case_result(family, item) for family, item
              in zip(FAMILIES, (f, p, a))]
    paths = (
       out / FRACTION / "host_grounded_lesson.mp4",
       out / PROCESS / "storytelling_host_with_audio.mp4",
       out / ATTENTION / "composed_attention_native.mp4"
    )
    review = out / "external_review_packet"
    review.mkdir()
    masked = {}
    for slot, movie, result in zip(("candidate_A","candidate_B","candidate_C"),
                                   paths, checks):
        if not movie.is_file() or sha(movie) != result["native_video_sha256"]:
            raise Blocked("V355_NATIVE_FILE_HASH_MISMATCH")
        dest = review / f"{slot}_timeline.jpg"
        result["review_sheet"] = contact_sheet(movie, dest, result["native_frames"])
        masked[slot] = result["family"]
    # Mapping is separated from the reviewer packet, not presented as blinded A/B.
    (out / "UNBLIND_ONLY_case_mapping.json").write_text(
       json.dumps(masked, indent=2) + "\n")
    blank_review_csv(review / "EXTERNAL_HUMAN_REVIEW_BLANK.csv")

    status = final_verdict(checks)
    result = {
       "checkpoint": "V3-55",
       "parent_sha": reg["parent_sha"],
       "preregistration_sha256": sha(ROOT /
         "benchmarks/learnflowbench/v3/v3_55_independent_pedagogical_quality_preregister.json"),
       "origin": "HOST_SYNTHETIC_NOT_MODEL_AUTHORED",
       "scope": "FRACTION_EXISTING_RATIO_PROCESS_REKEYED_GEOMETRY_ATTENTION_REVERSED_Q",
       "source_case_novelty": "NEW_V355_COMPOSITIONS_NOT_PROOF_OF_UNSEEN_TOPIC_GENERALIZATION",
       "cases": checks,
       "native_video_count": 3,
       "technical_media_family_gates": "PASS_BOUNDED",
       "baseline_relation": "CONTEXT_ONLY_NOT_MATCHED_AB",
       "blinded_packet": "ANONYMIZED_CANDIDATES_ONLY_NO_MATCHED_BASELINE",
       "human_scores": None,
       "creative_visual_quality": "NO_GO_NOT_ESTABLISHED",
       "human_learner_effect": "NOT_MEASURED",
       "genuine_model_authoring": "NOT_TESTED",
       "model_api_posts": 0,
       "main_merge": False,
       "production": "BLOCKED",
       "final_verdict": status,
    }
    (out / "v355_evidence_and_limitations.json").write_text(
       json.dumps(result, indent=2) + "\n")
    print("V3_55=THREE_HOST_NATIVE_FAMILIES_TECHNICAL_PASS_QUALITY_NO_GO", flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    run(parser.parse_args().output_dir)
