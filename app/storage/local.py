"""Local filesystem implementation of ArtifactStore with path traversal defenses."""

import os
import re
import shutil
from pathlib import Path
from app.storage.base import ArtifactStore

JOB_ID_REGEX = re.compile(r"^[A-Za-z0-9_-]+$")
SEGMENT_REGEX = re.compile(r"^[A-Za-z0-9_.-]+$")


class ArtifactPathSecurityError(ValueError):
    """Raised when an illegal or escaping path segment is provided."""


class LocalArtifactStore(ArtifactStore):
    """Filesystem-backed artifact store scoped to a root directory."""

    def __init__(self, root_dir: str | Path):
        self.root = Path(root_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _validate_job_id(self, job_id: str) -> str:
        if not job_id or not JOB_ID_REGEX.match(job_id):
            raise ArtifactPathSecurityError(
                f"Invalid job ID '{job_id}': must match ^[A-Za-z0-9_-]+$"
            )
        return job_id

    def _validate_segment(self, segment: str) -> str:
        if not segment or segment in (".", "..") or not SEGMENT_REGEX.match(segment):
            raise ArtifactPathSecurityError(
                f"Invalid path segment '{segment}': traversal characters and slashes are forbidden"
            )
        if "/" in segment or "\\" in segment:
            raise ArtifactPathSecurityError(
                f"Path segment '{segment}' contains illegal path separators"
            )
        return segment

    def get_job_dir(
        self,
        job_id: str,
        create: bool = False,
    ) -> Path:
        valid_id = self._validate_job_id(job_id)
        job_dir = (self.root / valid_id).resolve()

        if not job_dir.is_relative_to(self.root) or job_dir == self.root:
            raise ArtifactPathSecurityError(f"Job path escapes artifact root: {job_id}")

        if create:
            job_dir.mkdir(parents=True, exist_ok=True)

        return job_dir

    def get_path(
        self,
        job_id: str,
        *parts: str,
    ) -> Path:
        job_dir = self.get_job_dir(job_id, create=False)
        if not parts:
            return job_dir

        for part in parts:
            self._validate_segment(part)

        target = (job_dir.joinpath(*parts)).resolve()
        if not target.is_relative_to(job_dir):
            raise ArtifactPathSecurityError(
                f"Target path escapes job directory: {parts}"
            )

        return target

    def get_pending_final_path(
        self,
        job_id: str,
    ) -> Path:
        job_dir = self.get_job_dir(job_id, create=True)
        return job_dir / "final.pending.mp4"

    def get_final_path(
        self,
        job_id: str,
    ) -> Path | None:
        job_dir = self.get_job_dir(job_id, create=False)
        final_path = job_dir / "final.mp4"
        if final_path.exists() and final_path.is_file() and final_path.stat().st_size > 0:
            return final_path
        return None

    def publish_final(
        self,
        job_id: str,
    ) -> Path:
        job_dir = self.get_job_dir(job_id, create=True)
        pending = job_dir / "final.pending.mp4"
        final = job_dir / "final.mp4"

        if not pending.exists():
            raise FileNotFoundError(
                f"Cannot publish final video: pending artifact '{pending}' not found"
            )
        if not pending.is_file():
            raise ValueError(
                f"Pending artifact '{pending}' is not a regular file"
            )
        if pending.stat().st_size <= 0:
            raise ValueError(
                f"Pending artifact '{pending}' is empty (0 bytes)"
            )

        # Atomic replacement
        os.replace(pending, final)

        if not final.exists() or not final.is_file() or final.stat().st_size <= 0:
            raise RuntimeError(
                f"Publication failed: final artifact '{final}' was not created properly"
            )

        return final

    def delete_job_artifacts(
        self,
        job_id: str,
    ) -> None:
        job_dir = self.get_job_dir(job_id, create=False)
        if not job_dir.is_relative_to(self.root) or job_dir == self.root:
            raise ArtifactPathSecurityError(
                f"Refusing to delete unsafe path: {job_dir}"
            )

        if job_dir.exists() and job_dir.is_dir():
            shutil.rmtree(job_dir)
