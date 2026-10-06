from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from benchmarks.v2.static_quality import score_frame


def test_corrected_frozen_benchmark_spec_matches_v1_baseline_and_preserves_invalidated_v1():
    legacy = json.loads(Path("benchmarks/specs/v2_core_gate_v1.json").read_text(encoding="utf-8"))
    spec = json.loads(Path("benchmarks/specs/v2_core_gate_v2.json").read_text(encoding="utf-8"))
    baseline = json.loads(Path("benchmarks/baselines/v1/baseline.json").read_text(encoding="utf-8"))

    assert legacy["benchmark_id"] == "v2-core-gate-v1"
    assert spec["benchmark_id"] == "v2-core-gate-v2"
    assert spec["supersedes_invalid_run"]["benchmark_id"] == "v2-core-gate-v1"
    assert len(spec["supersedes_invalid_run"]["reason"]) >= 2
    assert spec["lesson_keys"] == sorted(baseline["lessons"].keys())
    assert spec["render_profile"] == {
        "width": 640,
        "height": 360,
        "fps": 12,
        "scene_duration_seconds": 2.0,
        "transition_duration_seconds": 0.5,
        "repetitions": 2,
    }
    assert spec["rendered_text_contract"]["font_size_px"] == 18
    assert spec["rendered_text_contract"]["overflow_policy"] == "REJECT_RENDER"
    assert "pre-subtitle scene clip" in spec["static_quality_metric"]["sample"]
    assert spec["static_quality_metric"]["v1_source"].startswith("retained V1 scenes/")
    assert spec["deterministic_qa"]["min_font_size_px"] == 18
    assert "burned subtitles derived from lesson narration" in spec["product_parity"]["required_from_v1"]
    assert "benchmark-only metadata" in spec["product_parity"]["subtitle_policy"]
    weights = spec["static_quality_metric"]["weights"]
    assert abs(sum(weights.values()) - 1.0) < 1e-12
    assert spec["repair_cases"]["expected_case_count"] == 9
    assert spec["evidence_policy"]["ephemeral_actions_artifact_alone_is_not_sufficient"] is True
    assert spec["freeze_rule"].startswith("After the first VALID")


def test_static_quality_metric_is_deterministic(tmp_path: Path):
    path = tmp_path / "frame.png"
    image = Image.new("RGB", (320, 180), (15, 17, 22))
    draw = ImageDraw.Draw(image)
    draw.rectangle((80, 45, 240, 135), fill=(70, 110, 160))
    draw.text((120, 80), "LearnFlow", fill=(245, 245, 245))
    image.save(path)

    first = score_frame(path)
    second = score_frame(path)
    assert first == second
    assert 0.0 <= first.total <= 100.0


def test_benchmark_runner_imports_without_executing():
    import scripts.run_v2_core_benchmark as runner

    assert runner.SPEC_PATH.name == "v2_core_gate_v2.json"
    assert callable(runner._run_v2_once)
    assert callable(runner._repair_benchmark)
    assert callable(runner._scene_qa_report)
