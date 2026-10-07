"""Repository-layer exceptions shared across storage backends."""


class DuplicateJobError(Exception):
    """Raised when attempting to persist a job with an existing ID."""
