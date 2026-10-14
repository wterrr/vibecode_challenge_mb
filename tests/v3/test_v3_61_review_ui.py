"""V3-61 offline UI package integrity. Test files are NOT human ratings."""
import json
import re
from pathlib import Path

import pytest

from scripts import build_v3_61_review_ui as ui


def simulated_source(tmp_path, monkeypatch):
    manifest = ui.preregistered()
    src = tmp_path / "SIMULATED_CLIPS_NOT_EVIDENCE"
    src.mkdir()
    for name in manifest["masked_clips_sha256"]:
        (src / name).write_bytes(b"TEST_ONLY_NOT_A_VIDEO")
    monkeypatch.setattr(ui, "verify_packet", lambda *_args, **_kw:
                        {"media_integrity":"PASS_NATIVE_MASKED"})
    monkeypatch.setattr(ui, "sha", lambda p: manifest["masked_clips_sha256"][p.name])
    return src


def test_preregistered_before_interface_and_frozen_parent():
    d = ui.preregistered()
    assert d["registered_before_implementation"]
    assert d["parent_pr"] == 96
    assert d["source_native_artifact_id"] == 11863660782
    assert len(d["masked_clips_sha256"]) == 9
    assert d["frozen_acceptance"]["pedagogical_quality"] == "UNRATED_NO_REVIEWERS"
    assert d["frozen_acceptance"]["learning_gain"] == "NOT_MEASURED"


def test_three_counterbalanced_local_html_and_exact_masked_clips(tmp_path, monkeypatch):
    src = simulated_source(tmp_path, monkeypatch)
    dest = tmp_path / "review_ui"
    receipt = ui.build(src, dest)
    assert receipt["gate"] == "PACKAGED_OFFLINE_MASKED"
    assert receipt["rater_count"] == 0 and receipt["production"] == "BLOCKED"
    assert len(list((dest/"media").glob("*.mp4"))) == 9
    pages = sorted(dest.glob("reviewer_*.html"))
    assert len(pages) == 3
    configs = []
    for page in pages:
        content = page.read_text()
        assert "Content-Security-Policy" in content
        assert "connect-src 'none'" in content
        assert 'type="application/json"' in content
        match = re.search(r'<script type="application/json" id="frozen-configuration">(.*?)</script>', content)
        assert match
        config = json.loads(match.group(1))
        assert len(config["clips"]) == 9
        configs.append(tuple(x["clip_id"] for x in config["clips"]))
        for forbidden in ui.FORBIDDEN:
            assert forbidden not in content
    assert len(set(configs)) == 3
    for page in (dest/"v361_reviewer.js", dest/"v361.css"):
        assert page.exists()
        for forbidden in ui.FORBIDDEN:
            assert forbidden not in page.read_text()
    assert not any("admin" in x.name.lower() for x in dest.iterdir())


def test_no_unaudited_source_or_replaced_kit(tmp_path, monkeypatch):
    media = simulated_source(tmp_path, monkeypatch)
    output = tmp_path / "out"
    output.mkdir()
    with pytest.raises(ValueError, match="OUTPUT_EXISTS"):
        ui.build(media, output)
    output.rmdir()
    (media/"fraction_equivalence_A.mp4").unlink()
    with pytest.raises(ValueError, match="SOURCE_CLIP_MISSING"):
        ui.build(media, output)
    assert not output.exists()


def test_sha_failure_fails_without_partial_package(tmp_path, monkeypatch):
    source = simulated_source(tmp_path, monkeypatch)
    monkeypatch.setattr(ui, "sha", lambda _p: "0"*64)
    destination = tmp_path / "out"
    with pytest.raises(ValueError, match="PACKAGED_SHA_DRIFT"):
        ui.build(source, destination)
    # Package is not complete nor valid; must not be distributed.
    assert not (destination/"START_HERE.txt").exists()
