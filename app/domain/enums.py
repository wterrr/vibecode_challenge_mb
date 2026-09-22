"""Domain enums for LearnFlow AI."""

from enum import Enum


class JobStatus(str, Enum):
    """Job status lifecycle states."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobStage(str, Enum):
    """Execution stages during video generation."""

    PLANNING = "planning"
    VALIDATING_PLAN = "validating_plan"
    AUDIO = "audio"
    RENDERING = "rendering"
    ASSEMBLING = "assembling"
    VALIDATING_OUTPUT = "validating_output"


RUNNING_STAGE_ORDER: list[JobStage] = [
    JobStage.PLANNING,
    JobStage.VALIDATING_PLAN,
    JobStage.AUDIO,
    JobStage.RENDERING,
    JobStage.ASSEMBLING,
    JobStage.VALIDATING_OUTPUT,
]


class VisualIntent(str, Enum):
    """Supported visual intents for scenes (MVP)."""

    CONCEPT_CARD = "concept_card"
    PROCESS_DIAGRAM = "process_diagram"
    COMPARISON = "comparison"
    ILLUSTRATION = "illustration"
