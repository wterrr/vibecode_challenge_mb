"""Abstract base class for artifact storage."""

from abc import ABC, abstractmethod
from pathlib import Path


class ArtifactStore(ABC):
    """Abstract interface for storing and retrieving pipeline artifacts."""

    @abstractmethod
    def get_job_dir(
        self,
        job_id: str,
        create: bool = False,
    ) -> Path:
        """Return the directory dedicated to a job."""
        ...

    @abstractmethod
    def get_path(
        self,
        job_id: str,
        *parts: str,
    ) -> Path:
        """Return an internal path safely scoped within the job directory."""
        ...

    @abstractmethod
    def get_pending_final_path(
        self,
        job_id: str,
    ) -> Path:
        """Return path to final.pending.mp4 for assembly stage."""
        ...

    @abstractmethod
    def get_final_path(
        self,
        job_id: str,
    ) -> Path | None:
        """Return path to published final.mp4 if it exists as a non-empty regular file, else None."""
        ...

    @abstractmethod
    def publish_final(
        self,
        job_id: str,
    ) -> Path:
        """Atomically promote final.pending.mp4 to final.mp4 using os.replace."""
        ...

    @abstractmethod
    def delete_job_artifacts(
        self,
        job_id: str,
    ) -> None:
        """Safely delete the job artifact directory if it exists."""
        ...
