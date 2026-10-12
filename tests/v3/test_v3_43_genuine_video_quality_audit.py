"""V3-43 immutable real-video audit and mutation tests. NO network/model.

CI must download archived one-shot V3-42 video, no synthetic substitutes.
"""
from __future__ import annotations
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil

import pytest

from learnflow_v3.genuine_video_quality_audit import (
    AuditRejected, _frame_metrics, _source_timeline, audit_video
)

ROOT = Path(__file__).resolve().parents[2]
PREREG = ROOT / "benchmarks/learnflowbench/v3/v3_43_genuine_video_quality_preregister.json"


@pytest.fixture(scope="module")
def archive():
    path = Path(os.environ["V343_SOURCE_DIR"]).resolve()
    assert path.is_dir(), "V343_SOURCE_DIR must be the real downloaded V3-42 artifact"
    assert (path / "creative_manim_with_audio.mp4").is_file()
    return path


@pytest.fixture(scope="module")
def verified(archive, tmp_path_factory):
    result = audit_video(archive, PREREG, tmp_path_factory.mktemp("v343_complete"))
    return result


def test_preregister_was_independent_and_one_model_request_is_frozen():
    data = json.loads(PREREG.read_text())
    assert data["preregistered_before_implementation"] is True
    assert data["parent_sha"] == "72cb5942ec1f889ddcf79ff57247a3e4d366a24f"
    assert data["source"]["workflow_run_id"] == 38189257163
    assert data["source"]["artifact_id"] == 11721146374
    assert data["source"]["video_sha256"].startswith("f92c47bb")
    assert "any new model POST or paid trial" in data["forbidden"]
    assert data["frozen_quality_flags"]["whole_area_mismatch_warn_ratio"] == .05


def test_real_video_rechecked_not_fake_and_emits_actual_contact_sheet(verified):
    assert verified["technical_provenance"] == "PASS_REVALIDATED"
    assert verified["media_origin"] == "V3-42_REAL_MODEL_AUTHORED_SCENE_REVALIDATED"
    assert verified["duration_seconds"] == 39.333
    assert verified["frame_count"] == 590
    assert verified["model_http_posts_in_audit"] == 0
    assert verified["synthetic_video_substitution"] is False
    assert verified["quality_decision"] == "REQUIRES_VISUAL_AND_PEDAGOGICAL_REDESIGN"


def test_timecoded_beat_level_not_fabricated_word_level(verified):
    expected = [0, 9.2, 19.133, 29.533]
    assert len(verified["beats"]) == 4
    assert [b["start_seconds"] for b in verified["beats"]] == expected
    assert [b["render_actions"] for b in verified["beats"]] == [5,5,4,3]
    assert all(b["alignment_granularity"].startswith("BEAT_ONLY") for b in verified["beats"])
    assert all(80 < b["narration_rate_wpm_approx"] < 260 for b in verified["beats"])


def test_real_decoded_pixels_and_audio_signal_not_only_metadata(verified):
    image = verified["visual_metrics"]
    assert image["sampled_frames"] >= 70
    assert 0 < image["foreground_occupancy_median_pct"] < 100
    assert 0 <= image["low_activity_sample_pairs_fraction"] <= 1
    assert len(verified["sampled_timeline_seconds"]) == 18
    assert len(verified["audio_physical_signal"]) == 4
    assert all(b["rms_normalized"] > .001 for b in verified["audio_physical_signal"])


def test_fraction_ratios_correct_but_equal_whole_illustration_not_precise(verified):
    assert verified["actual_fraction_shaded_ratios"] == {"half":.5,"quarters":.5}
    assert verified["whole_area"]["two_piece"] == 4.68
    assert verified["whole_area"]["four_piece"] == 4.4
    assert verified["whole_area"]["relative_difference_vs_four_piece"] > .05
    assert "V343_DIFFERENT_SIZED_WHOLES" in [i["code"] for i in verified["issues"]]


def test_narration_visual_lag_and_missing_transformation_are_explicit(verified):
    d = verified["claim_to_complete_visual_delay_seconds"]
    assert 5.4 < d["two_piece"] < 5.7
    assert 7.8 < d["four_piece"] < 8.1
    assert verified["explicit_visual_numerator_denominator_times_two"] is False
    codes = {x["code"] for x in verified["issues"]}
    assert codes >= {
        "V343_ARITHMETIC_EXPLANATION_NOT_SHOWN",
        "V343_FIRST_WHOLE_VISUAL_LAG",
        "V343_FOUR_PIECE_REVEAL_LAG",
    }
    assert all(0 <= x["start_seconds"] <= x["end_seconds"] <= 39.34
               for x in verified["issues"])


def test_audit_never_claims_human_quality_or_more_domains(verified):
    assert verified["rubric_coverage"]["human_blinded_quality"] == "NOT_EVALUATED"
    assert verified["rubric_coverage"]["human_learning_gain"] == "NOT_MEASURED"
    assert verified["rubric_coverage"]["full_audio_word_alignment"] == "NOT_MEASURED"
    assert verified["rubric_coverage"]["visual_comparison_3b1b"] == "NOT_CERTIFIED"
    assert verified["production"] == "BLOCKED"


def _clone(archive, tmp_path):
    dest = tmp_path/"mutated"
    shutil.copytree(archive, dest)
    return dest


@pytest.mark.parametrize("mutation,why", [
    ("tamper_video","V343_SOURCE_SHA_MISMATCH:creative_manim_with_audio.mp4"),
    ("tamper_plan","V343_SOURCE_SHA_MISMATCH:scene_plan.json"),
    ("tamper_source","V343_SOURCE_SHA_MISMATCH:generated_host_compiled_manim.py"),
    ("tamper_srt","V343_SOURCE_SHA_MISMATCH:creative_manim.srt"),
    ("tamper_provider","V343_SOURCE_SHA_MISMATCH:v3_42_portable_provider_receipt.json"),
    ("missing_video","V343_MISSING_OR_SYMLINK:creative_manim_with_audio.mp4"),
    ("synthetic_adapter","V343_GENUINE_PROVENANCE_NOT_CERTIFIED"),
    ("wrong_audio_count","V343_NARRATION_RECEIPT_INVALID"),
])
def test_tampering_never_produces_quality_verdict(archive, tmp_path, mutation, why):
    dest = _clone(archive, tmp_path)
    if mutation.startswith("tamper_"):
        fname = {
            "tamper_video":"creative_manim_with_audio.mp4",
            "tamper_plan":"scene_plan.json",
            "tamper_source":"generated_host_compiled_manim.py",
            "tamper_srt":"creative_manim.srt",
            "tamper_provider":"v3_42_portable_provider_receipt.json",
        }[mutation]
        with (dest/fname).open("ab") as f:
            f.write(b"\nTAMPERED\n")
    elif mutation == "missing_video":
        (dest/"creative_manim_with_audio.mp4").unlink()
    else:
        f = dest/"v3_35_ablation_receipt.json"
        obj = json.loads(f.read_text())
        if mutation == "synthetic_adapter":
            obj["model_plan_origin"] = "SYNTHETIC_HOST_FIXTURE_NOT_REAL_MODEL"
        else:
            obj["audio_sampled_beats"] = obj["audio_sampled_beats"][:3]
        f.write_text(json.dumps(obj))
    output = tmp_path / "output"
    with pytest.raises(AuditRejected, match=why):
        audit_video(dest, PREREG, output)
    assert not (output/"v3_43_audit.json").exists()


def test_schema_registration_mutation_is_detected_before_decode(archive,tmp_path):
    m = json.loads(PREREG.read_text())
    m["parent_sha"] = "0"*40
    altered = tmp_path / "registration.json"
    altered.write_text(json.dumps(m))
    with pytest.raises(AuditRejected,match="V343_FROZEN_REGISTRATION_DRIFT"):
        audit_video(archive, altered, tmp_path/"out")


def test_bad_manim_action_schedule_does_not_get_silent_alignment_repair():
    source = "        # BEAT 1 - exact audio-budget duration 2.0s\n" \
             "        self.play(FadeIn(a,scale=.9),run_time=3.0)\n"
    beats = [{"actions":[{"action":"show"}],"start_seconds":0., "end_seconds":2.}]
    with pytest.raises(AuditRejected,match="V343_MANIM_BEAT_COUNT_DRIFT"):
        _source_timeline(source, beats)


def test_ci_downloads_real_artifact_not_synthetic_and_no_model_key():
    code = (ROOT/".github/workflows/v3-43-genuine-video-quality-audit.yml").read_text()
    assert "38189257163" in code
    assert "v3-42-genuine-model-video-or-failclosed-receipt" in code
    assert "actions/download-artifact@v4" in code
    assert "OPENROUTER_API_KEY" not in code
    assert "secrets.OPENROUTER" not in code
    assert "V343_SOURCE_DIR" in code
    assert "creative_evidence_gate" in code
