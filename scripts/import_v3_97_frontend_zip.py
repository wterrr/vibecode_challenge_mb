#!/usr/bin/env python3
"""Import the verified user-supplied FE archive, preserving its media, into this checkout.

This is a local import, not a substitute for committing the actual frontend. The
backend remains OFF by default until both build assets and a dev-only flag exist.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
from pathlib import Path, PurePosixPath
import shutil
import stat
import zipfile

EXPECTED_ARCHIVE_SHA256 = "66a11a7348811337b236c33fe37497fa6a28b0a30ae588c86e8e445cff1b4aa7"
REQUIRED = {
    "package.json", "vite.config.js", "index.html",
    "src/App.jsx", "src/styles.css", "src/api/learnflow.js",
    "src/components/PromptComposer.jsx", "src/components/LessonLibrary.jsx",
    "public/media/learnflow-opening-v2-no-loop.mp4",
    "public/media/learnflow-product-film.mp4",
    "public/mascots/learner.png", "public/mascots/insight.png",
    "public/mascots/creator.png", "public/mascots/research.png",
}
PREFIX = "learnflow-landing/"


def import_archive(archive: Path, target: Path) -> None:
    if not archive.is_file() or archive.is_symlink():
        raise ValueError("Expected regular FE ZIP")
    if sha256(archive.read_bytes()).hexdigest() != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("FE archive SHA mismatch; refusing unknown source")
    if target.exists():
        raise ValueError("Destination exists; will not overwrite FE or media")
    with zipfile.ZipFile(archive) as zf:
        files = {}
        total = 0
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if not name.startswith(PREFIX):
                raise ValueError("FE archive path outside approved root")
            relative = name[len(PREFIX):]
            path = PurePosixPath(relative)
            if not relative or path.is_absolute() or any(part in ("..", ".") for part in path.parts):
                raise ValueError("Unsafe ZIP entry")
            if stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK:
                raise ValueError("Symlinks forbidden")
            if relative in files:
                raise ValueError("Duplicate ZIP entry")
            total += info.file_size
            if info.file_size > 8_000_000 or total > 15_000_000:
                raise ValueError("ZIP decompression budget exceeded")
            files[relative] = info
        if not REQUIRED.issubset(files):
            raise ValueError("FE missing required source or original visual assets")
        target.mkdir(parents=True)
        try:
            for relative, info in files.items():
                output = target.joinpath(*PurePosixPath(relative).parts)
                output.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as source, output.open("wb") as dest:
                    shutil.copyfileobj(source, dest)
        except Exception:
            shutil.rmtree(target)
            raise
    print("Imported verified FE archive into", target)
    print("Next: npm install && npm run build (inside imported FE directory)")


def install_dist(source: Path, static_dir: Path) -> None:
    dist = source / "dist"
    if not (dist / "index.html").is_file() or not (dist / "assets").is_dir():
        raise ValueError("Missing built Vite assets: run npm run build first")
    if (static_dir / "landing").exists():
        raise ValueError("Landing bundle already exists; no destructive overwrite")
    if (static_dir / "landing").is_symlink():
        raise ValueError("Unsafe landing symlink")
    shutil.copytree(dist, static_dir / "landing", symlinks=False)
    print("Installed verified React build at", static_dir / "landing")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--zip", dest="archive", type=Path)
    p.add_argument("--source", type=Path, default=Path("frontend/learnflow-landing"))
    p.add_argument("--install-dist", action="store_true")
    p.add_argument("--static", type=Path, default=Path("app/static"))
    args = p.parse_args()
    if args.archive:
        import_archive(args.archive, args.source)
    if args.install_dist:
        install_dist(args.source, args.static)
    if not args.archive and not args.install_dist:
        p.error("Supply --zip or --install-dist")
