"""Deterministic QA contracts and analyzer for LearnFlow V2 CP2.11."""

from learnflow_v2.qa.analyzer import analyze_deterministic_qa
from learnflow_v2.qa.errors import DeterministicQAError, QAInvalidInputError
from learnflow_v2.qa.evaluation import evaluate_fixture_results
from learnflow_v2.qa.schema import (
    AssetProbe,
    AudioProbe,
    DeterministicQAConfig,
    DeterministicQAReport,
    FrameProbe,
    QAFixtureEvaluation,
    QAFixtureResult,
    QAIssue,
    QAIssueCode,
    QAIssueSeverity,
    RenderedSceneProbe,
    SubtitleCueProbe,
    TextElementProbe,
    V2_QA_SCHEMA_VERSION,
    VisualElementProbe,
)

__all__ = [
    "AssetProbe",
    "AudioProbe",
    "DeterministicQAConfig",
    "DeterministicQAError",
    "DeterministicQAReport",
    "FrameProbe",
    "QAFixtureEvaluation",
    "QAInvalidInputError",
    "QAFixtureResult",
    "QAIssue",
    "QAIssueCode",
    "QAIssueSeverity",
    "RenderedSceneProbe",
    "SubtitleCueProbe",
    "TextElementProbe",
    "V2_QA_SCHEMA_VERSION",
    "VisualElementProbe",
    "analyze_deterministic_qa",
    "evaluate_fixture_results",
]
