"""V3-71: actual frozen masked ZIP plus hostile TEST_ONLY archive mutations.

No fake review submissions or simulated learning outcomes; the source ZIP is a
real native V3-61 artifact and is only used for physical media validation.
"""
from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path

import pytest

from scripts.run_v3_60_independent_review import ReviewBlocked
from scripts import run_v3_71_masked_native_preflight as v371


def frozen_zip() -> Path:
    value = os.getenv("V371_KIT_ZIP")
    assert value, "V371_KIT_ZIP required: original V3-61 media artifact"
    f = Path(value)
    assert f.is_file(), f
    return f


def changed_zip(tmp_path: Path, *, drop: str = "", extra: str = "",
                corrupt: str = "", append: bytes = b"") -> Path:
    dest = tmp_path / "TEST_ONLY_MUTATED_NOT_REVIEWER_MEDIA.zip"
    with zipfile.ZipFile(frozen_zip()) as original, zipfile.ZipFile(
        dest, "w", compression=zipfile.ZIP_DEFLATED
    ) as rewritten:
        for name in original.namelist():
            if name == drop:
                continue
            raw = original.read(name)
            if name == corrupt:
                raw += append
            rewritten.writestr(name, raw)
        if extra:
            rewritten.writestr(extra, b"TEST_ONLY_NOT_HUMAN_REVIEW")
    return dest


def test_genuine_original_masked_native_kit_matches_prereg():
    r = v371.verify_kit(frozen_zip(), full_decode=False)
    assert r["source_artifact_id"] == 11863189967
    assert r["gate"] == "NATIVE_MASKED_REVIEW_PACKET_PASS"
    assert r["video_shas_verified"] == 9
    assert r["assigned_blinded_forms"] == 3
    assert r["independent_real_reviewers"] == 0
    assert r["pedagogical_quality"] == "UNRATED"
    assert r["production"] == "BLOCKED"


@pytest.mark.parametrize("mutate,error", [
    ({"drop": "media/fraction_equivalence_B.mp4"},
     "ZIP_FILE_INVENTORY_OR_ADMIN_LEAK"),
    ({"extra": "admin_treatment_key.json"},
     "ZIP_FILE_INVENTORY_OR_ADMIN_LEAK"),
    ({"extra": "../fake_admin.json"},
     "ZIP_FILE_INVENTORY_OR_ADMIN_LEAK"),
    ({"corrupt": "media/fraction_equivalence_A.mp4", "append": b"TEST_ONLY"},
     "CLIP_SHA256_DRIFT"),
    ({"corrupt": "reviewer_01.html", "append": b"https://tracker.test/"},
     "UI_NETWORK_OR_TREATMENT_LEAK"),
    ({"corrupt": "MASKED_MANIFEST.json", "append": b"{}"},
     "INVALID_OR_UNREADABLE_ZIP"),
])
def test_mutation_refused_without_human_score(tmp_path, mutate, error):
    archive = changed_zip(tmp_path, **mutate)
    with pytest.raises((ReviewBlocked, json.JSONDecodeError), match=error if error !=
                       "INVALID_OR_UNREADABLE_ZIP" else None):
        v371.verify_kit(archive, full_decode=False)


def test_no_placeholder_or_absent_archive(tmp_path):
    with pytest.raises(ReviewBlocked, match="KIT_ZIP_MISSING"):
        v371.verify_kit(tmp_path / "does-not-exist.zip")


def test_prereg_no_human_efficacy_claim():
    p = json.loads(v371.REG.read_text())
    assert p["scope"] == "RESEARCH_ONLY_OFFLINE_NO_EXTERNAL_REVIEWERS"
    assert p["limits"]["real_human_reviewers"] == 0
    assert p["limits"]["human_quality"] == "UNRATED"
    assert p["prohibitions"]["model_post"] == 0
    assert p["prohibitions"]["masked_video_changes"] == 0
