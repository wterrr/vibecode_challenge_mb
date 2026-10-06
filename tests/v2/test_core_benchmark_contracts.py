from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from benchmarks.v2.static_quality import score_frame


def test_frozen_benchmark_spec_matches_v1_baseline_and_metric_weights():
    spec = json.loads(Path("benchmarks/specs/v2_core_gate_v1.json").read_text(encoding="utf-8"))
    baseline = json.loads(Path("benchmarks/baselines/v1/baseline.json").read_text(encoding="utf-8"))

    assert spec["benchmark_id"] == "v2-core-gate-v1"
    assert spec["lesson_keys"] == sorted(baseline["lessons"].keys())
    assert spec["render_profile"] == {
        "width": 640,
        "height": 360,
        "fps": 12,
        "scene_duration_seconds": 2.0,
        "transition_duration_seconds": 0.5,
        "repetitions": 2,
    }
    weights = spec["static_quality_metric"]["weights"]
    assert abs(sum(weights.values()) - 1.0) < 1e-12
    assert spec["repair_cases"]["expected_case_count"] == 9
    assert spec["freeze_rule"].startswith("Spec and metric formula must not change")


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

    assert runner.SPEC_PATH.name == "v2_core_gate_v1.json"
    assert callable(runner._run_v2_once)
    assert callable(runner._repair_benchmark)
