"""Offline regression for the cross-artifact mismatch in historical Action #181."""
from __future__ import annotations

from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from live_evaluation.semantic_consistency import assert_semantic_consistency, SemanticConsistencyError
from scripts.export_live_v2d_evidence import export_evidence


def action181_repro():
    """Minimal unmodified #181 worked-example values, without auth/cache/media."""
    return {
        "concept_registry": {"concepts": [{
            "concept_id": "c_workedexam_e8f1933850",
            "label": "Worked example: In [2, 5, 8, 12, 16, 23, 38], search for 16. Check middle value 12; 16 is larger, so keep [16, 23, 38]. Check middle value 23; 16 is smaller, so keep [16]. The target is found.",
        }]},
        "lesson_script": {"segments": [{
            "segment_id": "segment-2",
            "subtitle_text": "Search for 24 in [3, 7, 12, 18, 24, 31, 40]. Check 18, then keep [24, 31, 40]. Check 31, then keep [24]. Check 24: found.",
        }]},
        "storyboard": {"scenes": [{
            "scene_id": "scene-worked-trace",
            "concept_refs": ["c_workedexam_e8f1933850"],
            "script_segment_ids": ["segment-2"],
            "visual_intent": "Trace the search for 24 through the sorted list [3, 7, 12, 18, 24, 31, 40], successively retaining [24, 31, 40].",
        }]},
        "scenegraphs": [{"scene_id": "scene-worked-trace", "nodes": [
            {"id": "target", "semantic_role": "search_target", "content": "24"},
            {"id": "initial-candidates", "semantic_role": "search_interval", "content": "[3, 7, 12, 18, 24, 31, 40]"},
            {"id": "found", "semantic_role": "search_result", "concept_ref": "c_workedexam_e8f1933850", "content": "24"},
        ]}],
    }


def test_action181_historical_mismatch_reproduces_offline():
    with pytest.raises(SemanticConsistencyError, match="SEMANTIC_WORKED_EXAMPLE_MISMATCH"):
        assert_semantic_consistency(action181_repro())


def test_aligned_worked_example_passes():
    data = action181_repro()
    data["concept_registry"]["concepts"][0]["label"] = (
        "Worked example: In [3, 7, 12, 18, 24, 31, 40], search for 24. Check middle 18 then 31, find 24."
    )
    assert_semantic_consistency(data)


def test_correct_script_but_wrong_visual_target_fails():
    data = action181_repro()
    data["concept_registry"]["concepts"][0]["label"] = "Worked example: In [3, 7, 12, 18, 24, 31, 40], search for 24."
    data["scenegraphs"][0]["nodes"][2]["content"] = "16"
    with pytest.raises(SemanticConsistencyError, match="SEMANTIC_REFERENCED_RESULT_MISMATCH"):
        assert_semantic_consistency(data)


def test_unrelated_concept_does_not_trigger_numeric_matching():
    data = action181_repro()
    data["concept_registry"]["concepts"][0]["label"] = "Binary search halves the sorted interval."
    assert_semantic_consistency(data)


def test_evidence_export_allowlist_rejects_auth_and_runtime_cache(tmp_path):
    root = tmp_path / "input"
    root.mkdir()
    (root / "pilot_report.json").write_text('{"success":true}')
    auth = root / "hermes-home"
    auth.mkdir()
    (auth / "auth.json").write_text('{"api_key":"fake-secret"}')
    governance = root / "governance"
    governance.mkdir()
    (governance / "events.jsonl").write_text('"Bearer fake-secret"')
    run = root / "lesson-runs" / "079bc93cbe4b74cb"
    run.mkdir(parents=True)
    (run / "script.json").write_text('{"segments":[]}')
    output = tmp_path / "exported"
    report = export_evidence(root, output)
    assert report["file_count"] == 2
    assert (output / "lesson-runs" / "079bc93cbe4b74cb" / "script.json").is_file()
    assert not (output / "hermes-home").exists()
    assert not (output / "governance").exists()
    assert "auth.json" not in "\n".join(x["path"] for x in report["files"])


def test_evidence_export_fails_closed_on_credential_in_allowlisted_file(tmp_path):
    root = tmp_path / "input"
    root.mkdir()
    (root / "pilot_report.json").write_text('{"api_key":"fake-secret"}')
    with pytest.raises(ValueError, match="sensitive credential"):
        export_evidence(root, tmp_path / "out")

def test_stale_registry_key_is_rejected_even_when_label_is_repaired():
    data = action181_repro()
    data["concept_registry"]["concepts"][0]["label"] = (
        "Worked example: In [3, 7, 12, 18, 24, 31, 40], search for 24."
    )
    data["concept_registry"]["concepts"][0]["canonical_key"] = (
        "concept:worked_example_in_2_5_8_12_16_23_38_search_for_16"
    )
    with pytest.raises(SemanticConsistencyError, match="SEMANTIC_REGISTRY_KEY_LABEL_MISMATCH"):
        assert_semantic_consistency(data)


def test_stale_scenegraph_semantic_key_is_rejected():
    from learnflow_v2.concepts.normalize import normalize_canonical_key, deterministic_concept_id
    data = action181_repro()
    label = "Worked example: In [3, 7, 12, 18, 24, 31, 40], search for 24."
    key = normalize_canonical_key(label)
    cid = deterministic_concept_id(key)
    entry = data["concept_registry"]["concepts"][0]
    previous_id = entry["concept_id"]
    entry.update({"label": label, "concept_id": cid, "canonical_key": key})
    data["storyboard"]["scenes"][0]["concept_refs"] = [cid]
    for node in data["scenegraphs"][0]["nodes"]:
        if node.get("concept_ref") == previous_id:
            node["concept_ref"] = cid
            node["semantic_key"] = "concept:worked_example_in_2_5_8_12_16_23_38_search_for_16"
    with pytest.raises(SemanticConsistencyError, match="SEMANTIC_NODE_CONCEPT_KEY_MISMATCH"):
        assert_semantic_consistency(data)


def _basic_export_source(tmp_path):
    source = tmp_path / "input"
    source.mkdir()
    (source / "pilot_report.json").write_text('{"success":true}')
    return source


def test_export_rejects_self_ancestors_descendants_and_root_without_deletion(tmp_path):
    source = _basic_export_source(tmp_path)
    keep = source / "pilot_report.json"
    for destination in (
        source,
        tmp_path,
        tmp_path.parent,
        tmp_path / "input" / "nested",
        Path(source.anchor),
    ):
        with pytest.raises(ValueError, match="unsafe"):
            export_evidence(source, destination)
        assert keep.read_text() == '{"success":true}'
        assert tmp_path.is_dir()


def test_export_does_not_overwrite_caller_owned_output(tmp_path):
    source = _basic_export_source(tmp_path)
    dest = tmp_path / "published"
    dest.mkdir()
    marker = dest / "must-survive.txt"
    marker.write_text("keep")
    with pytest.raises(ValueError, match="already exists"):
        export_evidence(source, dest)
    assert marker.read_text() == "keep"
    assert (source / "pilot_report.json").is_file()


def test_export_rejects_existing_and_dangling_output_symlinks(tmp_path):
    source = _basic_export_source(tmp_path)
    external = tmp_path / "external"
    external.mkdir()
    marker = external / "marker"
    marker.write_text("unchanged")
    for target in (external, tmp_path / "nonexistent"):
        link = tmp_path / "published"
        link.symlink_to(target, target_is_directory=True)
        try:
            with pytest.raises(ValueError, match="symlinked"):
                export_evidence(source, link)
            assert marker.read_text() == "unchanged"
            assert (source / "pilot_report.json").is_file()
        finally:
            link.unlink()


def test_export_rejects_symlinked_lesson_runs_escape(tmp_path):
    source = _basic_export_source(tmp_path)
    external = tmp_path / "external"
    run = external / "079bc93cbe4b74cb"
    run.mkdir(parents=True)
    marker = run / "script.json"
    marker.write_text('{"sensitive_external":"do-not-export"}')
    (source / "lesson-runs").symlink_to(external, target_is_directory=True)
    dest = tmp_path / "published"
    with pytest.raises(ValueError, match="symlinked lesson-runs"):
        export_evidence(source, dest)
    assert marker.is_file()
    assert not dest.exists()
    assert not list(tmp_path.glob(".published.staging-*"))


def test_export_rejects_symlinked_run_and_subdirectory(tmp_path):
    source = _basic_export_source(tmp_path)
    external = tmp_path / "external"
    external.mkdir()
    run_root = source / "lesson-runs"
    run_root.mkdir()
    linked_run = run_root / "079bc93cbe4b74cb"
    linked_run.symlink_to(external, target_is_directory=True)
    dest = tmp_path / "published"
    with pytest.raises(ValueError, match="unrecognized lesson run"):
        export_evidence(source, dest)
    linked_run.unlink()
    linked_run.mkdir()
    subdir = linked_run / "scenegraphs"
    subdir.symlink_to(external, target_is_directory=True)
    with pytest.raises(ValueError, match="symlinked evidence folder"):
        export_evidence(source, dest)
    assert not dest.exists()
    assert not list(tmp_path.glob(".published.staging-*"))


def test_export_rejects_allowlisted_leaf_symlink_and_preserves_external(tmp_path):
    source = _basic_export_source(tmp_path)
    external = tmp_path / "external.json"
    external.write_text('{"external":"private"}')
    (source / "model_probe.json").symlink_to(external)
    dest = tmp_path / "published"
    with pytest.raises(ValueError, match="symlinked evidence path"):
        export_evidence(source, dest)
    assert external.read_text() == '{"external":"private"}'
    assert not dest.exists()


def test_export_rejects_credential_without_partial_publication(tmp_path):
    source = _basic_export_source(tmp_path)
    run = source / "lesson-runs" / "079bc93cbe4b74cb"
    run.mkdir(parents=True)
    (run / "script.json").write_text('{"api_key":"fake-secret"}')
    dest = tmp_path / "published"
    with pytest.raises(ValueError, match="sensitive credential"):
        export_evidence(source, dest)
    assert not dest.exists()
    assert not list(tmp_path.glob(".published.staging-*"))
    assert (source / "pilot_report.json").is_file()


def test_export_valid_empty_source_and_allowlist_atomic_publication(tmp_path):
    source = tmp_path / "empty"
    source.mkdir()
    dest = tmp_path / "empty-export"
    report = export_evidence(source, dest)
    assert report["file_count"] == 0
    assert (dest / "export_manifest.json").is_file()
    assert not list(tmp_path.glob(".empty-export.staging-*"))
    # Valid nonempty export retains allowlisted evidence and excludes auth.
    full = _basic_export_source(tmp_path)
    (full / "hermes-home").mkdir()
    (full / "hermes-home" / "auth.json").write_text('{"api_key":"fake"}')
    (full / "governance").mkdir()
    (full / "governance" / "debug.log").write_text("private")
    published = tmp_path / "published"
    report = export_evidence(full, published)
    assert report["file_count"] == 1
    assert (published / "pilot_report.json").read_text() == '{"success":true}'
    assert not (published / "hermes-home").exists()
    assert not (published / "governance").exists()
    assert not list(tmp_path.glob(".published.staging-*"))
