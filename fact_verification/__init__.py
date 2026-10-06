"""Fact verification and factual-narration gating."""

from .hermes import build_fact_verifier_task
from .models import (
    ClaimVerification,
    FactVerificationReport,
    SemanticClaimReview,
    SemanticFactReview,
    SemanticVerdict,
    VerificationIssue,
)
from .verifier import require_narration_claims, verify_facts

__all__ = [
    "VerificationIssue",
    "SemanticVerdict",
    "SemanticClaimReview",
    "SemanticFactReview",
    "ClaimVerification",
    "FactVerificationReport",
    "build_fact_verifier_task",
    "verify_facts",
    "require_narration_claims",
]
