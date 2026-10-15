#!/usr/bin/env python3
"""V3-81 four preregistered, host-only cross-topic native Manim witnesses."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_manim_runner import _audio, _docker_manim, _codec_and_pixel_gates, sha
from learnflow_v3.process_edge_visual_qa import _frame
from learnflow_v3.v381_generic_semantic_operators import need, validate_case
from learnflow_v3.v381_finite_manim_compiler import source
from scripts.run_v3_44_semantic_counterfactual import deterministic_mux

REG = ROOT / "benchmarks/learnflowbench/v3/v3_81_domain_agnostic_preregister.json"


def registered():
    raw = REG.read_bytes()
    doc = json.loads(raw)
    need(doc["checkpoint"] == "V3-81" and
         doc["kind"] == "FIRST_CHILD_PREREG_BEFORE_IMPLEMENTATION" and
         doc["parent"]["sha"] == "63135f9e9986b606dfea7b8915b2ea99658066a6" and
         doc["parent"]["pr"] == 117 and
         doc["restrictions"]["model_api_requests"] == 0 and
         doc["restrictions"]["production"] == "BLOCKED", "PREREG_DRIFT")
    cases = doc["cases"]
    need(doc["locked_case_ids"] == [x["id"] for x in cases] and
         len(cases) == doc["acceptance"]["native_cases"] == 4 and
         len({x["id"] for x in cases}) == 4 and
         sum(x["role"] == "heldout" for x in cases) == 1,
         "FROZEN_CASE_SELECTION_CHANGED")
    return doc, sha256(raw).hexdigest()


def native_progress(movie: Path, beat_rows: list[dict], trace: dict):
    need(len(beat_rows) == len(trace["events"]), "PIXEL_BEAT_MISMATCH")
    proofs = []
    for beat, ev in zip(beat_rows, trace["events"], strict=True):
        start = int(beat["frame_start"])
        # The compiler reveals the exact arithmetic result before 3.3 sec.
        early = start + 1
        late = start + 50
        need(late < start + beat["frames"] - 3, "NO_RESULT_WITNESS_BUDGET")
        a = _frame(movie, early)
        b = _frame(movie, late)
        need(a.shape == b.shape == (720, 1280, 3), "DECODED_FRAME_SHAPE")
        # Result text occupies the physical lower center, not the header.
        roi_a = a[450:620, 105:1175].astype("int16")
        roi_b = b[450:620, 105:1175].astype("int16")
        changed = int(np.count_nonzero(np.max(np.abs(roi_a-roi_b), axis=2) > 28))
        need(changed >= 250, "NO_NATIVE_RESULT_VISUAL_TRANSFORMATION")
        proofs.append({
            "operator": ev["kind"], "output": ev["id"],
            "claim_id": ev["claim_id"], "host_output": ev["actual"],
            "early_frame": early, "late_frame": late,
            "actual_changed_lower_canvas_pixels": changed,
            "early_decoded_sha256": sha256(a.tobytes()).hexdigest(),
            "late_decoded_sha256": sha256(b.tobytes()).hexdigest(),
            "scope": "H264_BEFORE_AFTER_NOT_EXACT_GLYPH_OCR_OR_LEARNER_SCORE"
        })
    return proofs


def run(out: Path):
    registration, prereg_sha = registered()
    need(not out.exists(), "OUTPUT_MUST_BE_VERSIONED_AND_FRESH")
    out.mkdir(parents=True)
    receipts = []
    for row in registration["cases"]:
        trace = validate_case(row)
        folder = out / row["id"]
        folder.mkdir()
        (folder / "host_attested_operator_trace.json").write_text(json.dumps(trace, indent=2) + "\n")
        host_story = SimpleNamespace(beats=[
            SimpleNamespace(narration=e["narration"], claim_ids=[e["claim_id"]])
            for e in trace["events"]
        ])
        durations, beat_rows, wav = _audio(folder, host_story)
        manim = source(trace, durations)
        src = folder / "v381_trusted_host_compiler.py"
        src.write_text(manim)
        silent_movie, sandbox = _docker_manim(folder, src)
        movie = folder / "v381_native_semantic.mp4"
        mux = deterministic_mux(silent_movie, wav, movie, beat_rows)
        need(0 <= mux["raw_manim_frames"] - mux["output_h264_frames"] <= 3,
             "UNBOUNDED_MANIM_TO_NARRATION_FRAME_DRIFT")
        av = _codec_and_pixel_gates(movie, beat_rows)
        need(mux["output_h264_frames"] == av["frames"] ==
             sum(int(b["frames"]) for b in beat_rows),
             "H264_AUDIO_FRAME_OR_DURATION_DRIFT")
        pixel = native_progress(movie, beat_rows, trace)
        # Whole H264 decode, not merely sampled frames.
        full = subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(movie),
             "-map", "0:v:0", "-f", "null", "-"],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=160
        )
        need(full.returncode == 0, "FULL_PHYSICAL_H264_DECODE_FAILED")
        report = {
            "id": row["id"], "domain": row["domain"], "role": row["role"],
            "origin": "LOCKED_HOST_SYNTHETIC_NOT_AI_AUTHORED",
            "locked_input_sha256": trace["input_sha256"],
            "operator_sequence": [e["kind"] for e in trace["events"]],
            "math_proven": trace["all_numeric_outputs_verified"],
            "operator_count": len(trace["events"]),
            "native_h264_aac_sha256": sha(movie),
            "native_frames": av["frames"],
            "complete_ffmpeg_decode": "PASS",
            "physical_result_reveals": pixel, "sandbox": sandbox,
            "audio_video_gate": mux, "codec_and_pixel_gate": av,
            "host_python_compiled_sha256": sha(src),
            "model_calls": 0, "human_visual_quality": "UNRATED",
            "learning_gain": "NOT_MEASURED", "production": "BLOCKED",
        }
        (folder / "native_receipt.json").write_text(json.dumps(report, indent=2) + "\n")
        receipts.append(report)
    need(len(receipts) == 4 and len({x["native_h264_aac_sha256"] for x in receipts}) == 4
         and sum(x["role"] == "heldout" for x in receipts) == 1,
         "CROSS_TOPIC_NATIVE_VIDEO_MISSING")
    ops = {k for r in receipts for k in r["operator_sequence"]}
    need(ops == {"SCALE", "ADD", "EQUIVALENT_PARTITION"},
         "OPERATOR_COVERAGE_INCOMPLETE")
    final = {
        "checkpoint": "V3-81", "status": "BOUNDED_FOUR_TOPIC_HOST_NATIVE_EVIDENCE",
        "prereg_sha256": prereg_sha, "cases": receipts, "native_mp4_count": 4,
        "domains": [x["domain"] for x in receipts],
        "operator_families": sorted(ops),
        "all_operator_beats_have_decoded_before_after":
            all(len(x["physical_result_reveals"]) == x["operator_count"] for x in receipts),
        "model_api_requests": 0, "autonomous_model_storyboarding": "NOT_TESTED",
        "scientific_semantics_beyond_arithmetic": "NOT_PROVEN",
        "human_teaching_quality": "UNRATED", "learner_gain": "NOT_MEASURED",
        "universal_cross_domain_generalization": "NOT_PROVEN",
        "final_visual_quality": "NOT_PASS", "production": "BLOCKED",
    }
    (out / "v381_final_receipt.json").write_text(json.dumps(final, indent=2) + "\n")
    return final


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", required=True, type=Path)
    result = run(p.parse_args().output_dir)
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2))
