from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_contracts import (
    AgentContractError,
    EvidenceEdge,
    EvidenceGraph,
    EvidenceNodeKind,
    EvidenceRelation,
    ResearchClaim,
    ResearchPack,
    SourceRecord,
)
from fact_verification import (
    SemanticClaimReview,
    SemanticFactReview,
    SemanticVerdict,
    VerificationIssue,
    build_fact_verifier_task,
    require_narration_claims,
    verify_facts,
)


def _pack_and_graph(edges):
    s1 = SourceRecord(
        source_id="S1",
        title="Source 1",
        locator="https://example.test/1",
    )
    s2 = SourceRecord(
        source_id="S2",
        title="Source 2",
        locator="https://example.test/2",
    )
    pack = ResearchPack(
        pack_id="research.demo",
        topic="demo",
        sources=(s1, s2),
        claims=(
            ResearchClaim(
                claim_id="C1",
                statement="Claim one.",
                source_ids=("S1",),
                confidence=0.9,
            ),
            ResearchClaim(
                claim_id="C2",
                statement="Claim two.",
                source_ids=("S1", "S2"),
                confidence=0.8,
            ),
        ),
    )
    graph = EvidenceGraph(
        graph_id="evidence.demo",
        research_pack_id=pack.pack_id,
        source_ids=("S1", "S2"),
        claim_ids=("C1", "C2"),
        edges=tuple(edges),
    )
    return pack, graph


def _support(edge_id, source_id, claim_id):
    return EvidenceEdge(
        edge_id=edge_id,
        from_kind=EvidenceNodeKind.SOURCE,
        from_id=source_id,
        to_claim_id=claim_id,
        relation=EvidenceRelation.SUPPORTS,
    )


def test_acceptance_verifier_passes():
    proc = subprocess.run(
        [sys.executable, "scripts/verify_fact_verification.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "FACT_VERIFICATION=PASS" in proc.stdout
    assert "claim_only_cycle_blocked=PASS" in proc.stdout
    assert "contradiction_flagged=PASS" in proc.stdout


def test_direct_source_support_is_approved_for_narration():
    pack, graph = _pack_and_graph(
        (
            _support("E1", "S1", "C1"),
            _support("E2", "S2", "C2"),
        )
    )
    report = verify_facts(pack, graph)
    assert report.approved_claim_ids == ("C1", "C2")
    assert report.blocked_claim_ids == ()
    require_narration_claims(report, ("C1", "C2"))


def test_claim_derived_from_grounded_claim_is_grounded():
    pack, graph = _pack_and_graph(
        (
            _support("E1", "S1", "C1"),
            EvidenceEdge(
                edge_id="E2",
                from_kind=EvidenceNodeKind.CLAIM,
                from_id="C1",
                to_claim_id="C2",
                relation=EvidenceRelation.DERIVES,
            ),
        )
    )
    report = verify_facts(pack, graph)
    c2 = next(item for item in report.claims if item.claim_id == "C2")
    assert c2.eligible_for_narration
    assert c2.grounded_source_ids == ("S1",)
    assert set(c2.support_edge_ids) == {"E1", "E2"}


def test_declared_source_without_evidence_edge_is_blocked():
    pack, graph = _pack_and_graph((_support("E1", "S1", "C1"),))
    report = verify_facts(pack, graph)
    c2 = next(item for item in report.claims if item.claim_id == "C2")
    assert VerificationIssue.UNSUPPORTED in c2.issues
    assert not c2.eligible_for_narration
    with pytest.raises(AgentContractError, match="blocked claim_ids"):
        require_narration_claims(report, ("C2",))


def test_claim_only_derivation_cycle_does_not_count_as_provenance():
    pack, graph = _pack_and_graph(
        (
            EvidenceEdge(
                edge_id="E1",
                from_kind=EvidenceNodeKind.CLAIM,
                from_id="C2",
                to_claim_id="C1",
                relation=EvidenceRelation.DERIVES,
            ),
            EvidenceEdge(
                edge_id="E2",
                from_kind=EvidenceNodeKind.CLAIM,
                from_id="C1",
                to_claim_id="C2",
                relation=EvidenceRelation.DERIVES,
            ),
        )
    )
    report = verify_facts(pack, graph)
    assert report.approved_claim_ids == ()
    assert set(report.blocked_claim_ids) == {"C1", "C2"}
    assert all(
        VerificationIssue.UNSUPPORTED in item.issues
        for item in report.claims
    )


def test_supported_but_contradicted_claim_is_flagged_and_blocked():
    pack, graph = _pack_and_graph(
        (
            _support("E1", "S1", "C1"),
            _support("E2", "S1", "C2"),
            EvidenceEdge(
                edge_id="E3",
                from_kind=EvidenceNodeKind.SOURCE,
                from_id="S2",
                to_claim_id="C2",
                relation=EvidenceRelation.CONTRADICTS,
            ),
        )
    )
    report = verify_facts(pack, graph)
    c2 = next(item for item in report.claims if item.claim_id == "C2")
    assert VerificationIssue.CONTRADICTION in c2.issues
    assert c2.contradiction_edge_ids == ("E3",)
    assert not c2.eligible_for_narration
    assert report.contradiction_claim_ids == ("C2",)


def _semantic_review(verdict_c1, verdict_c2, sources_c1=("S1",), sources_c2=("S2",)):
    return SemanticFactReview(
        review_id="semantic.demo",
        research_pack_id="research.demo",
        evidence_graph_id="evidence.demo",
        claims=(
            SemanticClaimReview(
                claim_id="C1",
                verdict=verdict_c1,
                rationale="Review C1.",
                cited_source_ids=sources_c1,
            ),
            SemanticClaimReview(
                claim_id="C2",
                verdict=verdict_c2,
                rationale="Review C2.",
                cited_source_ids=sources_c2,
            ),
        ),
    )


def test_hermes_supported_verdict_cannot_override_unsupported_graph():
    pack, graph = _pack_and_graph((_support("E1", "S1", "C1"),))
    semantic = _semantic_review(SemanticVerdict.SUPPORTED, SemanticVerdict.SUPPORTED)
    report = verify_facts(pack, graph, semantic)
    c2 = next(item for item in report.claims if item.claim_id == "C2")
    assert c2.semantic_verdict == SemanticVerdict.SUPPORTED
    assert VerificationIssue.UNSUPPORTED in c2.issues
    assert not c2.eligible_for_narration


def test_hermes_contradiction_or_uncertainty_blocks_even_when_graph_supports():
    pack, graph = _pack_and_graph(
        (
            _support("E1", "S1", "C1"),
            _support("E2", "S2", "C2"),
        )
    )
    semantic = _semantic_review(
        SemanticVerdict.CONTRADICTED,
        SemanticVerdict.UNCERTAIN,
    )
    report = verify_facts(pack, graph, semantic)
    c1, c2 = report.claims
    assert VerificationIssue.CONTRADICTION in c1.issues
    assert VerificationIssue.SEMANTIC_UNCERTAINTY in c2.issues
    assert report.approved_claim_ids == ()


def test_semantic_review_must_cover_exact_claim_set_and_known_sources():
    pack, graph = _pack_and_graph(
        (
            _support("E1", "S1", "C1"),
            _support("E2", "S2", "C2"),
        )
    )
    partial = SemanticFactReview(
        review_id="semantic.partial",
        research_pack_id=pack.pack_id,
        evidence_graph_id=graph.graph_id,
        claims=(
            SemanticClaimReview(
                claim_id="C1",
                verdict=SemanticVerdict.SUPPORTED,
                rationale="Only C1.",
                cited_source_ids=("S1",),
            ),
        ),
    )
    with pytest.raises(AgentContractError, match="cover every"):
        verify_facts(pack, graph, partial)

    unknown_source = _semantic_review(
        SemanticVerdict.SUPPORTED,
        SemanticVerdict.SUPPORTED,
        sources_c1=("S404",),
    )
    with pytest.raises(AgentContractError, match="unknown sources"):
        verify_facts(pack, graph, unknown_source)


def test_every_factual_narration_requires_known_approved_claim_id():
    pack, graph = _pack_and_graph(
        (
            _support("E1", "S1", "C1"),
            _support("E2", "S2", "C2"),
        )
    )
    report = verify_facts(pack, graph)

    with pytest.raises(AgentContractError, match="at least one claim_id"):
        require_narration_claims(report, ())
    with pytest.raises(AgentContractError, match="unknown claim_ids"):
        require_narration_claims(report, ("C404",))
    with pytest.raises(AgentContractError, match="must be unique"):
        require_narration_claims(report, ("C1", "C1"))


def test_hermes_task_contains_full_evidence_and_structured_review_schema():
    pack, graph = _pack_and_graph(
        (
            _support("E1", "S1", "C1"),
            _support("E2", "S2", "C2"),
        )
    )
    task = build_fact_verifier_task(pack, graph)
    assert set(task) == {"goal", "context", "output_schema"}
    assert "claims" in task["output_schema"]["properties"]
    context = json.loads(task["context"])
    assert context["research_pack"]["pack_id"] == pack.pack_id
    assert context["evidence_graph"]["graph_id"] == graph.graph_id
    assert any(
        "deterministic verification has final authority" in item
        for item in context["instructions"]
    )


def test_fact_verification_surface_has_no_renderer_or_pedagogy_controls():
    paths = [
        ROOT / "fact_verification" / "models.py",
        ROOT / "fact_verification" / "verifier.py",
        ROOT / "fact_verification" / "hermes.py",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()
    for forbidden in (
        "render_scene_video",
        "deterministicpillowrenderer",
        "ffmpeg",
        "storyboard",
        "pedagogyplan",
        "scriptsegment",
    ):
        assert forbidden not in text
