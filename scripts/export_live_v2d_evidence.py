"""Publish only non-credential V2D evidence. Never upload Hermes runtime home."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

TOP_FILES = frozenset({"pilot_report.json", "model_probe.json"})
LESSON_FILES = frozenset({
    "learning_brief.json", "research_pack.json", "evidence_graph.json",
    "fact_verification.json", "pedagogy_plan.json", "script.json",
    "storyboard.json", "concept_registry.json", "artifact_manifest.json",
    "render_manifest.json", "core_preview.mp4", "final.mp4",
    "final.video.mp4", "final.av.mp4",
})
SUBDIR_PATTERNS = {
    "scenegraphs": re.compile(r"\d{3}\.json"),
    "layouts": re.compile(r"\d{3}\.json"),
    "scenes": re.compile(r"\d{3}\.mp4"),
    "motion": re.compile(r"\d{3}\.(?:beats|compiled|plan|resolved|schedule)\.json"),
    "transitions": re.compile(r"\d{3}\.(?:json|mp4)"),
    "audio": re.compile(r"(?:\d{3}\.mp3|\d{3}\.provider_cues\.json|lesson\.m4a)"),
    "verification": re.compile(r"[a-z][a-z0-9_]*\.json"),
}
SENSITIVE = re.compile(
    rb"(?i)(?:sk-or-v1-|sk-ant-|github_pat_|ghp_[A-Za-z0-9]{12}|"
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    rb'"(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|credential_pool)"\s*:|'
    rb"OPENROUTER_API_KEY\s*[=:]\s*[^\s\"']+)"
)
RUN_NAME = re.compile(r"[0-9a-f]{16,64}")


def _checked_path(path: Path) -> Path:
    """Resolve a caller path without silently traversing an existing symlink.

    Check every existing path component, including the leaf (dangling symlinks
    are rejected). Avoid Path.resolve() *before* checking, since resolve() hides
    the very symlink we must detect.
    """
    path = Path(os.path.abspath(os.fspath(path)))
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError(f"symlinked evidence path: {path}")
    return path


def _safe_file(path: Path, source: Path) -> None:
    _checked_path(path)
    if not path.is_relative_to(source) or not path.is_file():
        raise ValueError(f"non-regular or out-of-root evidence file: {path}")
    if path.suffix == ".json" and SENSITIVE.search(path.read_bytes()):
        raise ValueError(f"sensitive credential material in evidence file: {path}")


def export_evidence(source: Path, destination: Path) -> dict:
    # Refuse ancestor/descendant relationships in BOTH directions. In
    # particular, never remove a parent directory containing the input.
    source = _checked_path(source)
    destination = _checked_path(destination)
    if (
        not source.is_dir()
        or source == destination
        or source in destination.parents
        or destination in source.parents
        or destination == Path(destination.anchor)
        or destination == Path(source.anchor)
    ):
        raise ValueError("unsafe or missing evidence source/destination")
    # Existing output is always caller-owned; never delete or overwrite it.
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"evidence output already exists: {destination}")
    if not destination.parent.is_dir():
        raise ValueError(f"evidence output parent does not exist: {destination.parent}")

    # Build privately, publish with a single same-filesystem rename, and
    # clean up ONLY our freshly generated staging dir after a failure.
    staging = Path(tempfile.mkdtemp(
        prefix=f".{destination.name}.staging-",
        dir=destination.parent,
    ))
    exported = []
    try:
        def copy(src: Path, relative: Path) -> None:
            _safe_file(src, source)
            dest = staging / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            # Defense in depth: validate the staged copy too, including a
            # source-changed-during-copy scenario.
            _safe_file(dest, staging)
            exported.append({
                "path": relative.as_posix(),
                "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
            })

        for name in sorted(TOP_FILES):
            path = source / name
            if path.exists() or path.is_symlink():
                copy(path, Path(name))
        run_root = source / "lesson-runs"
        if run_root.is_symlink():
            raise ValueError(f"symlinked lesson-runs directory: {run_root}")
        if run_root.exists():
            if not run_root.is_dir():
                raise ValueError(f"non-directory lesson-runs: {run_root}")
            for run in sorted(run_root.iterdir()):
                if run.is_symlink() or not run.is_dir() or not RUN_NAME.fullmatch(run.name):
                    raise ValueError(f"unrecognized lesson run directory: {run}")
                relative = Path("lesson-runs") / run.name
                for name in sorted(LESSON_FILES):
                    path = run / name
                    if path.exists() or path.is_symlink():
                        copy(path, relative / name)
                for subdir, pattern in SUBDIR_PATTERNS.items():
                    folder = run / subdir
                    if folder.is_symlink():
                        raise ValueError(f"symlinked evidence folder: {folder}")
                    if not folder.exists():
                        continue
                    if not folder.is_dir():
                        raise ValueError(f"unsafe evidence folder: {folder}")
                    for path in sorted(folder.iterdir()):
                        if pattern.fullmatch(path.name):
                            copy(path, relative / subdir / path.name)
        manifest = {
            "schema_version": "governed-redacted-evidence-v1",
            "file_count": len(exported),
            "files": exported,
            "excludes": [
                "hermes-home/", "governance/", "logs/", "caches/",
                "state.db", "auth.json",
            ],
        }
        (staging / "export_manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        # A non-cooperating concurrent writer is outside the isolated CI
        # threat model; reject any output that appeared during the build.
        if destination.exists() or destination.is_symlink():
            raise ValueError(f"evidence output appeared during export: {destination}")
        os.rename(staging, destination)
        return manifest
    finally:
        # Never rmtree(destination). Only clean our private temp tree if it
        # still exists (after successful rename the staging name is gone).
        if staging.exists():
            shutil.rmtree(staging)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path(".hermes_runtime/live-v2d-evaluation"))
    parser.add_argument("--output", type=Path, default=Path(".hermes_runtime/approved-live-v2d-evidence"))
    opts = parser.parse_args()
    report = export_evidence(opts.source, opts.output)
    print(f"REDACTED_EVIDENCE_EXPORT=PASS files={report['file_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
