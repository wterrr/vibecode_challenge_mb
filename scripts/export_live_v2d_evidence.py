"""Publish only non-credential V2D evidence. Never upload Hermes runtime home."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

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


def _safe_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"non-regular evidence file: {path}")
    if path.suffix == ".json" and SENSITIVE.search(path.read_bytes()):
        raise ValueError(f"sensitive credential material in evidence file: {path}")


def export_evidence(source: Path, destination: Path) -> dict:
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if not source.is_dir() or source == destination or source in destination.parents:
        raise ValueError("unsafe or missing evidence source/destination")
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    exported = []

    def copy(src: Path, relative: Path) -> None:
        _safe_file(src)
        dest = destination / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        exported.append({"path": relative.as_posix(), "sha256": hashlib.sha256(src.read_bytes()).hexdigest()})

    for name in sorted(TOP_FILES):
        p = source / name
        if p.exists():
            copy(p, Path(name))
    run_root = source / "lesson-runs"
    if run_root.is_dir():
        for run in sorted(run_root.iterdir()):
            if not run.is_dir() or run.is_symlink() or not RUN_NAME.fullmatch(run.name):
                raise ValueError("unrecognized lesson run directory")
            relative = Path("lesson-runs") / run.name
            for name in sorted(LESSON_FILES):
                p = run / name
                if p.exists():
                    copy(p, relative / name)
            for subdir, pattern in SUBDIR_PATTERNS.items():
                folder = run / subdir
                if not folder.exists():
                    continue
                if not folder.is_dir() or folder.is_symlink():
                    raise ValueError("unsafe evidence folder")
                for p in sorted(folder.iterdir()):
                    if pattern.fullmatch(p.name):
                        copy(p, relative / subdir / p.name)
    manifest = {
        "schema_version": "governed-redacted-evidence-v1",
        "file_count": len(exported),
        "files": exported,
        "excludes": ["hermes-home/", "governance/", "logs/", "caches/", "state.db", "auth.json"],
    }
    (destination / "export_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


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
