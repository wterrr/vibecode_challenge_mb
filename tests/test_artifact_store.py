"""Unit tests for LocalArtifactStore security, semantics, and atomicity."""

import pytest
from pathlib import Path
from app.storage.local import ArtifactPathSecurityError, LocalArtifactStore


def test_safe_paths_creation(tmp_path):
    store = LocalArtifactStore(tmp_path)
    job_dir = store.get_job_dir("job_123", create=True)
    assert job_dir.exists()
    assert job_dir.is_dir()
    assert job_dir.name == "job_123"

    # Nested safe path
    subfile = store.get_path("job_123", "frames", "f01.png")
    assert subfile.name == "f01.png"
    assert subfile.parent.name == "frames"


def test_traversal_rejection_in_job_id(tmp_path):
    store = LocalArtifactStore(tmp_path)

    bad_job_ids = [
        "../bad",
        "job/slash",
        "job\\backslash",
        "/etc/passwd",
        "..",
        ".",
        "job$dollar",
        "job space",
    ]
    for bad_id in bad_job_ids:
        with pytest.raises(ArtifactPathSecurityError):
            store.get_job_dir(bad_id)


def test_traversal_rejection_in_segments(tmp_path):
    store = LocalArtifactStore(tmp_path)

    bad_segments = [
        "..",
        ".",
        "sub/dir",
        "sub\\dir",
        "../escaped",
        "/absolute",
        "file with spaces.txt",
    ]
    for bad_seg in bad_segments:
        with pytest.raises(ArtifactPathSecurityError):
            store.get_path("valid_job", bad_seg)


def test_missing_final_returns_none(tmp_path):
    store = LocalArtifactStore(tmp_path)
    assert store.get_final_path("job_none") is None


def test_empty_final_returns_none(tmp_path):
    store = LocalArtifactStore(tmp_path)
    job_dir = store.get_job_dir("job_empty_final", create=True)
    final_file = job_dir / "final.mp4"
    final_file.write_bytes(b"")  # 0 bytes, empty file

    assert final_file.exists()
    assert store.get_final_path("job_empty_final") is None


def test_non_empty_final_returns_path(tmp_path):
    store = LocalArtifactStore(tmp_path)
    job_dir = store.get_job_dir("job_valid_final", create=True)
    final_file = job_dir / "final.mp4"
    final_file.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"A" * 50)

    result = store.get_final_path("job_valid_final")
    assert result is not None
    assert result == final_file
    assert result.stat().st_size > 0


def test_pending_is_not_final(tmp_path):
    store = LocalArtifactStore(tmp_path)
    pending_path = store.get_pending_final_path("job_pending")
    pending_path.write_bytes(b"sample video bytes")

    assert pending_path.exists()
    assert store.get_final_path("job_pending") is None


def test_publish_missing_raises_error(tmp_path):
    store = LocalArtifactStore(tmp_path)
    with pytest.raises(FileNotFoundError, match="not found"):
        store.publish_final("job_no_pending")


def test_publish_empty_raises_error(tmp_path):
    store = LocalArtifactStore(tmp_path)
    pending = store.get_pending_final_path("job_empty")
    pending.write_bytes(b"")  # 0 bytes

    with pytest.raises(ValueError, match="empty"):
        store.publish_final("job_empty")


def test_publish_valid_atomic_promotion(tmp_path):
    store = LocalArtifactStore(tmp_path)
    pending = store.get_pending_final_path("job_valid")
    data = b"\x00\x00\x00\x18ftypmp42" + b"A" * 100
    pending.write_bytes(data)

    final = store.publish_final("job_valid")
    assert final.exists()
    assert final.is_file()
    assert final.read_bytes() == data

    # Pending must no longer exist (promoted via os.replace)
    assert not pending.exists()
    assert store.get_final_path("job_valid") == final


def test_publish_replaces_existing_final(tmp_path):
    store = LocalArtifactStore(tmp_path)
    job_dir = store.get_job_dir("job_replace", create=True)

    old_final = job_dir / "final.mp4"
    old_final.write_bytes(b"OLD_FINAL_DATA")

    pending = store.get_pending_final_path("job_replace")
    new_data = b"NEW_FINAL_DATA"
    pending.write_bytes(new_data)

    final = store.publish_final("job_replace")
    assert final.read_bytes() == new_data
    assert not pending.exists()


def test_delete_job_artifacts(tmp_path):
    store = LocalArtifactStore(tmp_path)
    job_dir = store.get_job_dir("job_to_delete", create=True)
    nested = job_dir / "audio"
    nested.mkdir(parents=True)
    (nested / "s01.wav").write_bytes(b"wavdata")

    assert job_dir.exists()

    store.delete_job_artifacts("job_to_delete")

    assert not job_dir.exists()
    # Root directory must still exist and be intact
    assert tmp_path.exists()

    # Deleting nonexistent job is a safe no-op
    store.delete_job_artifacts("job_to_delete")
