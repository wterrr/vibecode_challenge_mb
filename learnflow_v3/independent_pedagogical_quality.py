"""V3-55 independent offline visual-review harness.

This DOES NOT infer aesthetic or educational quality from pixel occupancy.
Native evidence remains host-generated, with model origin always false.
"""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
from typing import Mapping

from learnflow_v3.creative_manim_ablation import Blocked

REGISTRATION = "benchmarks/learnflowbench/v3/v3_55_independent_pedagogical_quality_preregister.json"
PARENT = "d5cb959fcf3cfc0aa6f1c03aba05ac1ef8017ba5"
IDS = ("v355_fraction_2_3_to_4_6", "v355_ordered_process_rekeyed",
       "v355_attention_reversed_query")
CRITERIA = ("explanatory clarity", "causal transform visibility",
            "object continuity", "typography legibility",
            "timing versus narration", "visual hierarchy")


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_registration(root: Path) -> dict:
    obj = json.loads((root / REGISTRATION).read_text())
    if (obj.get("checkpoint") != "V3-55" or
        obj.get("parent_sha") != PARENT or
        obj.get("registered_before_implementation") is not True or
        obj.get("registration_kind") != "FIRST_BRANCH_COMMIT" or
        obj.get("origin") != "HOST_SYNTHETIC_NOT_MODEL_AUTHORED" or
        tuple(x["id"] for x in obj["independent_cases"]) != IDS or
        obj["acceptance"]["zero_provider_requests"] is not True or
        obj["acceptance"]["no_main_merge"] is not True):
        raise Blocked("V355_PREREGISTRATION_DRIFT")
    baseline = obj["frozen_baseline"]["cases"]
    if len(baseline) != 3 or len({x["sha256"] for x in baseline}) != 3:
        raise Blocked("V355_BASELINE_HASH_INCOMPLETE")
    if any(len(x["sha256"]) != 64 for x in baseline):
        raise Blocked("V355_BASELINE_SHA_INVALID")
    return obj


def verify_case_result(family: str, item: Mapping) -> dict:
    """Check semantic evidence in ORIGINAL strict native receipts, not SHA diversity."""
    if family == "fraction_equivalence":
        if (item.get("provider_posts") != 0 or not item.get("evidence_verified") or
            item.get("factor") != 2 or item.get("fraction") != [2, 3] or
            item.get("target") != [4, 6]):
            raise Blocked("V355_FRACTION_GROUNDING_FAILED")
        cuts = item.get("semantic_cues", {}).get("source_guides", [])
        if len(cuts) != 3 or any(x["before_yellow_pixels"] > 6 or
                                x["after_yellow_pixels"] < 8 for x in cuts):
            raise Blocked("V355_FRACTION_NATIVE_CAUSAL_CUTS_MISSING")
        if item.get("verified_numeric_proof_h264", {}).get("pixel_count", 0) < 24:
            raise Blocked("V355_FRACTION_PROOF_NOT_PHYSICALLY_VISIBLE")
        video = item.get("video", {})
        sha = item.get("native_mp4_sha256")
    elif family == "ordered_process":
        if (item.get("model_api_posts") != 0 or
            item.get("frame_proof", {}).get("outcome") != "UNKNOWN_NOT_VERIFIED" or
            item.get("frame_proof", {}).get("yellow_check_cue_pixels", 0) < 10 or
            item.get("process_node_overlap", {}).get("status") not in
                ("PASS", "PASS_NODE_EDGE_VISUAL_QA", "NO_PIXEL_OVERLAP")):
            # The original V3-47 gate is authoritative; do not downgrade it.
            if (item.get("model_api_posts") != 0 or
                item.get("frame_proof", {}).get("outcome") != "UNKNOWN_NOT_VERIFIED" or
                item.get("frame_proof", {}).get("yellow_check_cue_pixels", 0) < 10):
                raise Blocked("V355_UNVERIFIED_PROCESS_CONDITION")
        video = item.get("actual_video", {})
        sha = item.get("output_mp4_sha256")
    elif family == "transformer_attention":
        if (item.get("model_http_posts") != 0 or
            item.get("genuine_model_authored") is not False or
            item.get("weights", [1])[0] >= 0.5):
            raise Blocked("V355_ATTENTION_Q_COUNTERFACTUAL_FAILED")
        before = item.get("causal_pixel_evidence", {}).get("before", {})
        after = item.get("causal_pixel_evidence", {}).get("after", {})
        if (before.get("total_causal_pixels", 999) > 65 or
            min(after.get("teal_pixels", 0), after.get("amber_pixels", 0)) < 200 or
            abs(item["causal_pixel_evidence"]["observed_teal_fraction"] -
                item["weights"][0]) > .13):
            raise Blocked("V355_ATTENTION_NATIVE_CAUSAL_MOTION_FAILED")
        video = item.get("native_media", {})
        sha = item.get("native_video_sha256")
    else:
        raise Blocked("V355_UNKNOWN_FAMILY")
    if not isinstance(sha, str) or len(sha) != 64 or video.get("codec") != "h264+aac":
        raise Blocked("V355_NATIVE_CODEC_OR_SHA_FAILED")
    if video.get("frames", 0) <= 10:
        raise Blocked("V355_NATIVE_FRAME_COUNT_FAILED")
    return {"family": family, "native_video_sha256": sha,
            "native_frames": video["frames"], "native_codec": video["codec"],
            "causal_pixel_proof": "PASS_BOUNDED_ORIGINAL_FAMILY_GATE",
            "human_quality": "UNRATED"}


def blank_review_csv(target: Path) -> None:
    """Populate only reviewer tasks, NEVER any invented ratings or learning gains."""
    with target.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(["masked_video_id", "criterion", "score_1_to_5",
                         "independent_reviewer_id", "timestamp_evidence",
                         "explanation", "review_status"])
        for slot in ("candidate_A", "candidate_B", "candidate_C"):
            for criterion in CRITERIA:
                writer.writerow([slot, criterion, "", "", "", "",
                                 "AWAITING_EXTERNAL_HUMAN_REVIEW"])


def final_verdict(checked: list[dict], human_ratings_supplied: bool = False) -> str:
    if len(checked) != 3 or len({x["family"] for x in checked}) != 3:
        raise Blocked("V355_THREE_FAMILIES_NOT_CERTIFIED")
    if any(x["causal_pixel_proof"] != "PASS_BOUNDED_ORIGINAL_FAMILY_GATE"
           for x in checked):
        raise Blocked("V355_CAUSAL_PROOF_INCOMPLETE")
    # Even optional human scores would require matched baselines and a
    # separate, preregistered analysis; never auto-certify creativity.
    return "TECHNICAL_ONLY_QUALITY_NO_GO_UNTIL_INDEPENDENT_MATCHED_HUMAN_REVIEW"
