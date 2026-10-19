"""V3-12 fail-closed QA policy for re-verified V3-10/11 offline evidence.

This is a review-only boundary. It does not implement publication, an actor
authorization mechanism or a V3-13 artifact critic. Even a valid local video
is NOT a complete narrated lesson, and cannot be silently promoted to release.
"""
from __future__ import annotations

import hashlib
from enum import Enum
from pathlib import Path
from typing import Callable, Literal

from pydantic import Field, model_validator

from learnflow_v2.repair import compute_content_hash
from .models import SemanticContractError, V3Model
from .beat_grounding import BeatGroundingManifest, verify_binary_beat_video
from .temporal_geometry import TemporalLayoutPlan, TemporalGeometryCertificate
from .temporal_demo_renderer import TemporalRenderEvidence, verify_temporal_render

VERSION = "v3-12-fail-closed-publication-v1"
REQUIRED = (
    "CERTIFIED_SOURCE", "RENDERED_PIXELS", "BEAT_VISUAL_ALIGNMENT",
    "LESSON_WIDE_TEMPORAL_GEOMETRY", "COMPLETE_SCENES",
    "FACT_AND_CONCEPT_AGREEMENT", "SUBTITLE_AND_AUDIO_SYNC",
    "VERIFIED_ARTIFACT_CRITIC", "VERIFIED_PUBLISH_AUTHORITY",
)


class DeterministicStatus(str, Enum):
    DETERMINISTIC_PASS = "DETERMINISTIC_PASS"
    DETERMINISTIC_FAIL = "DETERMINISTIC_FAIL"
    QA_ERROR = "QA_ERROR"


class CriticStatus(str, Enum):
    CRITIC_PASS = "CRITIC_PASS"  # reserved: no V3-13 verifier currently available
    CRITIC_FAIL = "CRITIC_FAIL"
    CRITIC_UNAVAILABLE = "CRITIC_UNAVAILABLE"
    QA_ERROR = "QA_ERROR"


class GateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNVERIFIED = "UNVERIFIED"
    ERROR = "ERROR"


class CriticObservation(V3Model):
    outcome: Literal["NOT_RUN", "UNAVAILABLE", "FAIL", "PASS_UNVERIFIED", "ERROR"] = "NOT_RUN"
    diagnostic_code: str = Field(default="NO_TRUSTED_V3_13_CRITIC", min_length=1, max_length=100)
    retry_count: Literal[0] = 0


class PublicationPolicy(V3Model):
    version: Literal["v3-12-fail-closed-publication-v1"] = VERSION
    require_verified_critic: Literal[True] = True
    dry_run_only: Literal[True] = True
    enable_publication: Literal[False] = False
    allow_unverified_deterministic_only: Literal[False] = False
    retry_llm: Literal[False] = False


class Requirement(V3Model):
    key: Literal[
        "CERTIFIED_SOURCE", "RENDERED_PIXELS", "BEAT_VISUAL_ALIGNMENT",
        "LESSON_WIDE_TEMPORAL_GEOMETRY", "COMPLETE_SCENES",
        "FACT_AND_CONCEPT_AGREEMENT", "SUBTITLE_AND_AUDIO_SYNC",
        "VERIFIED_ARTIFACT_CRITIC", "VERIFIED_PUBLISH_AUTHORITY",
    ]
    status: GateStatus
    proof_hash: str | None = None
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def _proof(self):
        if self.status == GateStatus.PASS:
            if self.proof_hash is None or len(self.proof_hash) != 64:
                raise ValueError("V3_12_PASS_MISSING_BOUND_PROOF")
        elif self.proof_hash is not None:
            raise ValueError("V3_12_NONPASS_CANNOT_DECLARE_PROOF")
        return self


class LifecycleEvent(V3Model):
    index: int = Field(strict=True, ge=0)
    stage: Literal[
        "INPUT_RECEIVED", "SCHEMA_VALID", "SEMANTIC_VALID", "FEASIBLE",
        "COMPILED", "RENDERED", "DETERMINISTIC_QA_PASS",
        "DETERMINISTIC_FAIL", "QA_ERROR", "CRITIC_STATUS", "PUBLISH_BLOCKED",
    ]
    result: Literal["PASS", "FAIL", "UNVERIFIED", "ERROR", "BLOCKED"]
    reason: str = Field(min_length=1)
    previous_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class PublicationReview(V3Model):
    version: Literal["v3-12-fail-closed-publication-v1"] = VERSION
    subject: Literal["BINARY_SEARCH_SAMPLE", "TEMPORAL_GEOMETRY_DEMO"]
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    video_sha256: str | None
    policy: PublicationPolicy
    deterministic_status: DeterministicStatus
    critic_status: CriticStatus
    publication_status: Literal["PUBLISH_BLOCKED"] = "PUBLISH_BLOCKED"
    requirements: tuple[Requirement, ...] = Field(min_length=9, max_length=9)
    lifecycle: tuple[LifecycleEvent, ...] = Field(min_length=3)
    blocked_reasons: tuple[str, ...] = Field(min_length=1)
    release_quality_tier: Literal["NO_RELEASE_GRADE"] = "NO_RELEASE_GRADE"
    real_audio_alignment: Literal["UNMEASURED"] = "UNMEASURED"
    human_learning: Literal["UNMEASURED"] = "UNMEASURED"
    production_release_executed: Literal[False] = False
    review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _complete(self):
        if tuple(x.key for x in self.requirements) != REQUIRED:
            raise ValueError("V3_12_REQUIRED_GATES_INCOMPLETE")
        absent = tuple(x.key for x in self.requirements if x.status != GateStatus.PASS)
        if not absent or absent != self.blocked_reasons:
            raise ValueError("V3_12_BLOCK_REASON_MISMATCH")
        if self.critic_status == CriticStatus.CRITIC_PASS:
            raise ValueError("V3_12_UNVERIFIED_CRITIC_CANNOT_PASS")
        if self.lifecycle[-1].stage != "PUBLISH_BLOCKED":
            raise ValueError("V3_12_MISSING_TERMINAL_BLOCK")
        previous = "0" * 64
        for i, event in enumerate(self.lifecycle):
            raw = event.model_dump(mode="json")
            claimed = raw.pop("event_hash")
            if event.index != i or event.previous_hash != previous or compute_content_hash(raw) != claimed:
                raise ValueError("V3_12_AUDIT_CHAIN_TAMPERED")
            previous = claimed
        payload = self.model_dump(mode="json", exclude={"review_sha256"})
        if compute_content_hash(payload) != self.review_sha256:
            raise ValueError("V3_12_REVIEW_CHECKSUM_MISMATCH")
        return self


def _events(rows):
    result = []
    previous = "0" * 64
    for i, (stage, state, reason) in enumerate(rows):
        item = {"index": i, "stage": stage, "result": state,
                "reason": reason, "previous_hash": previous}
        item["event_hash"] = compute_content_hash(item)
        result.append(item)
        previous = item["event_hash"]
    return result


def _file_hash(path: Path) -> str | None:
    if not path.is_file() or path.is_symlink():
        return None
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1048576), b""):
            sha.update(part)
    return sha.hexdigest()


def _critic_state(observation: CriticObservation) -> CriticStatus:
    if observation.outcome == "FAIL":
        return CriticStatus.CRITIC_FAIL
    if observation.outcome == "ERROR":
        return CriticStatus.QA_ERROR
    # PASS_UNVERIFIED must never masquerade as a verified V3-13 critic result.
    return CriticStatus.CRITIC_UNAVAILABLE


def _review(*, subject: str, source: str, video_path: str | Path,
            critic: CriticObservation, policy: PublicationPolicy,
            verifier: Callable[[], object]) -> PublicationReview:
    statuses = {name: GateStatus.UNVERIFIED for name in REQUIRED}
    reasons = {name: "NO_COMPLETE_LESSON_ATTESTATION" for name in REQUIRED}
    timeline = [
        ("INPUT_RECEIVED", "PASS", "Typed review inputs received"),
        ("SCHEMA_VALID", "PASS", "Frozen Pydantic boundary contracts"),
    ]
    digest = None
    deterministic = DeterministicStatus.QA_ERROR
    proof_hash = None
    try:
        # Call the real independently source-replayed V3-10 or V3-11 verifier.
        verified = verifier()
        digest = _file_hash(Path(video_path))
        if digest is None:
            raise SemanticContractError("V3_12_REAL_FILE_DISAPPEARED")
        proof_dict = (verified.model_dump(mode="json") if hasattr(verified, "model_dump")
                      else {"void_verified_by_existing_source_replay": source})
        proof_hash = compute_content_hash({
            "proof": proof_dict, "source": source, "real_video": digest, "subject": subject,
        })
        statuses["CERTIFIED_SOURCE"] = GateStatus.PASS
        statuses["RENDERED_PIXELS"] = GateStatus.PASS
        reasons["CERTIFIED_SOURCE"] = "REPLAYED_SOURCE_PROVENANCE"
        reasons["RENDERED_PIXELS"] = "REDECODED_REAL_MP4"
        if subject == "BINARY_SEARCH_SAMPLE":
            statuses["BEAT_VISUAL_ALIGNMENT"] = GateStatus.PASS
            reasons["BEAT_VISUAL_ALIGNMENT"] = "RENDERER_SYNTHETIC_BEAT_ONLY"
        # A V3-11 geometry demo is not a full lesson. A V3-10 sequence
        # video has no V3-11 geometry integration. Never mix these proofs.
        deterministic = DeterministicStatus.DETERMINISTIC_PASS
        timeline.extend([
            ("SEMANTIC_VALID", "PASS", "Specialized source replay succeeded"),
            ("FEASIBLE", "UNVERIFIED", "Full-lesson geometry unsupported"),
            ("COMPILED", "PASS", "Specialized renderer contract accepted"),
            ("RENDERED", "PASS", "Actual pixels and source digest checked"),
            ("DETERMINISTIC_QA_PASS", "PASS", "Bounded component only"),
        ])
    except (SemanticContractError, ValueError, OSError):
        deterministic = DeterministicStatus.DETERMINISTIC_FAIL
        for key in ("CERTIFIED_SOURCE", "RENDERED_PIXELS"):
            statuses[key] = GateStatus.FAIL
            reasons[key] = "VERIFICATION_REJECTED"
        timeline.append(("DETERMINISTIC_FAIL", "FAIL", "Original source/render failed replay"))
    except Exception:
        deterministic = DeterministicStatus.QA_ERROR
        for key in ("CERTIFIED_SOURCE", "RENDERED_PIXELS"):
            statuses[key] = GateStatus.ERROR
            reasons[key] = "VERIFIER_EXECUTION_ERROR"
        timeline.append(("QA_ERROR", "ERROR", "Unexpected deterministic QA exception"))

    cs = _critic_state(critic)
    if cs == CriticStatus.CRITIC_FAIL:
        statuses["VERIFIED_ARTIFACT_CRITIC"] = GateStatus.FAIL
        reasons["VERIFIED_ARTIFACT_CRITIC"] = "NEGATIVE_CRITIC_RESULT"
    elif cs == CriticStatus.QA_ERROR:
        statuses["VERIFIED_ARTIFACT_CRITIC"] = GateStatus.ERROR
        reasons["VERIFIED_ARTIFACT_CRITIC"] = "CRITIC_RUNTIME_ERROR"
    else:
        reasons["VERIFIED_ARTIFACT_CRITIC"] = "V3_13_NOT_IMPLEMENTED_OR_PROOF_UNVERIFIED"
    reasons["VERIFIED_PUBLISH_AUTHORITY"] = "NO_AUTHORIZATION_OR_PRODUCTION_WRITER"
    timeline.extend([
        ("CRITIC_STATUS", "UNVERIFIED" if cs == CriticStatus.CRITIC_UNAVAILABLE
         else "FAIL" if cs == CriticStatus.CRITIC_FAIL else "ERROR", cs.value),
        ("PUBLISH_BLOCKED", "BLOCKED", "REQUIRED_GATES_NOT_VERIFIED"),
    ])
    digest = digest or _file_hash(Path(video_path))
    requirements = [
        {"key": key, "status": statuses[key].value,
         "proof_hash": proof_hash if statuses[key] == GateStatus.PASS else None,
         "reason": reasons[key]}
        for key in REQUIRED
    ]
    values = {
        "version": VERSION, "subject": subject, "source_sha256": source,
        "video_sha256": digest, "policy": policy.model_dump(mode="json"),
        "deterministic_status": deterministic.value, "critic_status": cs.value,
        "publication_status": "PUBLISH_BLOCKED",
        "requirements": requirements, "lifecycle": _events(timeline),
        "blocked_reasons": [x["key"] for x in requirements if x["status"] != "PASS"],
        "release_quality_tier": "NO_RELEASE_GRADE",
        "real_audio_alignment": "UNMEASURED", "human_learning": "UNMEASURED",
        "production_release_executed": False,
    }
    values["review_sha256"] = compute_content_hash(values)
    return PublicationReview.model_validate(values)


def review_binary_publication(*, trace, plan, pattern, ledger, registry, script,
                              storyboard, scenegraph, manifest: BeatGroundingManifest,
                              video_evidence, video_path: str | Path, profile,
                              critic: CriticObservation = CriticObservation(),
                              policy: PublicationPolicy = PublicationPolicy()) -> PublicationReview:
    return _review(
        subject="BINARY_SEARCH_SAMPLE", source=manifest.manifest_sha256,
        video_path=video_path, critic=critic, policy=policy,
        verifier=lambda: verify_binary_beat_video(
            trace=trace, plan=plan, pattern=pattern, ledger=ledger,
            registry=registry, script=script, storyboard=storyboard,
            scenegraph=scenegraph, manifest=manifest,
            video_evidence=video_evidence, video_path=video_path, profile=profile,
        ),
    )


def review_geometry_publication(*, plan: TemporalLayoutPlan,
                                certificate: TemporalGeometryCertificate,
                                evidence: TemporalRenderEvidence, video_path: str | Path,
                                critic: CriticObservation = CriticObservation(),
                                policy: PublicationPolicy = PublicationPolicy()) -> PublicationReview:
    def verify():
        verify_temporal_render(plan=plan, certificate=certificate,
                               evidence=evidence, video_path=video_path)
        return certificate
    return _review(
        subject="TEMPORAL_GEOMETRY_DEMO", source=certificate.source_hash,
        video_path=video_path, critic=critic, policy=policy, verifier=verify,
    )


def verify_publication_review(*, candidate: PublicationReview,
                              replay: Callable[[], PublicationReview]) -> None:
    if candidate.model_dump(mode="json") != replay().model_dump(mode="json"):
        raise SemanticContractError("V3_12_STALE_OR_REHASHED_REVIEW")


def publish(*_args, **_kwargs):
    raise SemanticContractError("V3_12_PUBLICATION_DISABLED_NO_VERIFIED_AUTHORITY")
