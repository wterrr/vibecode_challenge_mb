"""Hermes-facing semantic fact-review task specification."""

from __future__ import annotations

import json

from agent_contracts import EvidenceGraph, ResearchPack

from .models import SemanticFactReview


def build_fact_verifier_task(pack: ResearchPack, graph: EvidenceGraph) -> dict:
    """Build a structured Hermes task; deterministic gating remains outside the model."""

    payload = {
        "research_pack": json.loads(pack.to_canonical_json()),
        "evidence_graph": json.loads(graph.to_canonical_json()),
        "instructions": [
            "Review every claim exactly once.",
            "Judge only whether supplied evidence supports, contradicts, or leaves the claim uncertain.",
            "Do not invent sources, claim IDs, or evidence.",
            "cited_source_ids must come from the supplied ResearchPack.",
            "Return CONTRADICTED when evidence materially conflicts with the claim.",
            "Return UNCERTAIN when support is insufficient or ambiguous.",
            "A SUPPORTED verdict is advisory only; LearnFlow deterministic verification has final authority.",
        ],
    }

    return {
        "goal": (
            "Act as LearnFlow Fact Verifier. Semantically review each research claim against "
            "the supplied evidence and return a structured review."
        ),
        "context": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        "output_schema": SemanticFactReview.model_json_schema(),
    }
