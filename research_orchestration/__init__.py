"""LearnFlow research orchestration built on Hermes native delegation."""

from .assembly import assemble_specialist_delegation_results, validate_specialist_summary
from .merge import merge_specialist_findings
from .models import (
    ConceptResearchFindings,
    EvidenceResearchFindings,
    MAX_DELEGATION_DEPTH,
    MAX_SPECIALIST_RESEARCHERS,
    MisconceptionResearchFindings,
    ResearchOrchestrationPlan,
    ResearchOrchestrationResult,
    ResearchRole,
    SpecialistTask,
)
from .planner import (
    build_director_delegate_task,
    build_research_orchestration_plan,
    expected_hermes_limits,
)

__all__ = [
    "MAX_DELEGATION_DEPTH",
    "MAX_SPECIALIST_RESEARCHERS",
    "ResearchRole",
    "ConceptResearchFindings",
    "EvidenceResearchFindings",
    "MisconceptionResearchFindings",
    "SpecialistTask",
    "ResearchOrchestrationPlan",
    "ResearchOrchestrationResult",
    "build_research_orchestration_plan",
    "build_director_delegate_task",
    "expected_hermes_limits",
    "merge_specialist_findings",
    "assemble_specialist_delegation_results",
    "validate_specialist_summary",
]
