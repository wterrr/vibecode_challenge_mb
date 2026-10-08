"""V3-17 release-candidate audit and local-only frozen-V2 rollback rehearsal.

Security boundary: this is a read-only candidate audit, not a deployment system.
A v3.0 *component* MP4 and synthetic human scores cannot authorize release.
The real V3-01 experiment is UNEXECUTED; we always fail closed.

Reuse: V3-12 source-replayed PublicationReview, V3-16 human manifest,
V3-01 locked corpus/protocol, frozen V2 Core manifest/blobs, V2 content hashes.
No provider calls or production filesystem mutations are permitted.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Literal

from pydantic import Field, model_validator

from learnflow_v2.repair import compute_content_hash
from .models import V3Model, SemanticContractError
from .publication_gate import (
    PublicationReview, review_binary_publication, review_geometry_publication,
    DeterministicStatus,
)
from .evaluation_pilot import PilotManifest, build_manifest

VERSION="v3-17-release-rollback-audit-v1"
V2_FROZEN_MAIN="a06e0b0b5f35e9147b4081da7ed7f7934affe0c6"
V1_FREEZE_COMMIT="f6dae0e8510a6db8fc49a761eddc2a055ffaefda"
GATES=(
    "FROZEN_V2_CORE",
    "FROZEN_TOPIC_PREREG",
    "COMPONENT_H264_SOURCE_QA",
    "REPRODUCIBLE_SAMPLE_PIXELS",
    "LOCAL_V2_ROLLBACK_REHEARSAL",
    "COMPLETE_TWELVE_TOPIC_PAIRED_VIDEOS",
    "BLINDED_INDEPENDENT_HUMAN_QUALITY",
    "REAL_C6_CRITIC_RECALL",
    "REAL_C7_REPAIR_EFFICACY",
    "FULL_LESSON_FACT_AUDIO_AND_SUBTITLE_QA",
    "REAL_COST_AND_RELIABILITY",
    "AUTHENTICATED_PUBLISH_PERMISSION",
)
UNMET={
    "COMPLETE_TWELVE_TOPIC_PAIRED_VIDEOS":"UNEXECUTED_FROZEN_12_TOPIC_PILOT",
    "BLINDED_INDEPENDENT_HUMAN_QUALITY":"NO_INDEPENDENT_HUMAN_RATINGS",
    "REAL_C6_CRITIC_RECALL":"AUTHOR_SEEDED_CRITIC_ONLY_REAL_RECALL_NOT_ESTABLISHED",
    "REAL_C7_REPAIR_EFFICACY":"FULL_CLIP_REENCODED_REAL_RECOVERY_NOT_ESTABLISHED",
    "FULL_LESSON_FACT_AUDIO_AND_SUBTITLE_QA":"COMPONENT_DEMOS_NOT_NARRATED_LESSONS",
    "REAL_COST_AND_RELIABILITY":"NO_12_TOPIC_LIVE_BUDGET_AND_FAILURE_MEASUREMENT",
    "AUTHENTICATED_PUBLISH_PERMISSION":"FROZEN_PREREG_PUBLISH_AUTHORIZATION_FALSE",
}
PROVEN_GATES=GATES[:5]


def _deny(reason):
    raise SemanticContractError("V3_17_"+reason)


def _sha(path:Path)->str:
    if not path.is_file() or path.is_symlink():
        _deny("UNSAFE_OR_MISSING_FILE")
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()


class SampleProvenance(V3Model):
    subject:Literal["BINARY_SEARCH_SAMPLE","TEMPORAL_GEOMETRY_DEMO"]
    video_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    source_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    publication_review_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    deterministic:Literal["DETERMINISTIC_PASS"]="DETERMINISTIC_PASS"
    release_status:Literal["PUBLISH_BLOCKED"]="PUBLISH_BLOCKED"
    artifact_kind:Literal["BOUNDED_COMPONENT_MP4"]="BOUNDED_COMPONENT_MP4"


class ReplayProof(V3Model):
    subject:Literal["BINARY_SEARCH_SAMPLE","TEMPORAL_GEOMETRY_DEMO"]
    primary_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    independent_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    decoded_frame_bytes_identical:Literal[True]=True
    provenance:Literal["AUTHOR_CURATED_DETERMINISTIC_REPLAY"]="AUTHOR_CURATED_DETERMINISTIC_REPLAY"

    @model_validator(mode="after")
    def _matches(self):
        if self.primary_sha256!=self.independent_sha256:
            raise ValueError("V3_17_INDEPENDENT_SAMPLE_PIXEL_DRIFT")
        return self


class LocalRollbackProof(V3Model):
    state:Literal["LOCAL_EPHEMERAL_V2_RESTORE_PASS"]="LOCAL_EPHEMERAL_V2_RESTORE_PASS"
    route_before:Literal["v3_staging"]="v3_staging"
    route_after:Literal["v2_frozen"]="v2_frozen"
    historical_main_ref:Literal["a06e0b0b5f35e9147b4081da7ed7f7934affe0c6"]=V2_FROZEN_MAIN
    frozen_v1_commit:Literal["f6dae0e8510a6db8fc49a761eddc2a055ffaefda"]=V1_FREEZE_COMMIT
    v1_baseline_blob_sha:str=Field(pattern=r"^[0-9a-f]{40}$")
    core_manifest_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    unchanged_v1_baseline_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    route_state_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    production_route_changed:Literal[False]=False
    git_ref_changed:Literal[False]=False
    deployed_services_touched:Literal[False]=False


class ReleaseGateRow(V3Model):
    name:Literal[
        "FROZEN_V2_CORE","FROZEN_TOPIC_PREREG","COMPONENT_H264_SOURCE_QA",
        "REPRODUCIBLE_SAMPLE_PIXELS","LOCAL_V2_ROLLBACK_REHEARSAL",
        "COMPLETE_TWELVE_TOPIC_PAIRED_VIDEOS","BLINDED_INDEPENDENT_HUMAN_QUALITY",
        "REAL_C6_CRITIC_RECALL","REAL_C7_REPAIR_EFFICACY",
        "FULL_LESSON_FACT_AUDIO_AND_SUBTITLE_QA","REAL_COST_AND_RELIABILITY",
        "AUTHENTICATED_PUBLISH_PERMISSION",
    ]
    state:Literal["PASS_COMPONENT_ONLY","BLOCKED_UNMEASURED"]
    evidence_sha256:str|None=None
    reason:str=Field(min_length=8,max_length=120)

    @model_validator(mode="after")
    def _consistent(self):
        if self.name in PROVEN_GATES:
            if self.state!="PASS_COMPONENT_ONLY" or self.evidence_sha256 is None:
                raise ValueError("V3_17_COMPONENT_PROOF_ABSENT")
        elif (self.state!="BLOCKED_UNMEASURED" or self.evidence_sha256 is not None
              or self.reason!=UNMET[self.name]):
            raise ValueError("V3_17_UNMEASURED_CANNOT_PASS")
        return self


class ReleaseAudit(V3Model):
    version:Literal["v3-17-release-rollback-audit-v1"]=VERSION
    candidate_kind:Literal["RC_READINESS_AUDIT_NOT_RELEASE_CANDIDATE"]="RC_READINESS_AUDIT_NOT_RELEASE_CANDIDATE"
    frozen_v2_main_sha:Literal["a06e0b0b5f35e9147b4081da7ed7f7934affe0c6"]=V2_FROZEN_MAIN
    pinned_v3_integration_ref:Literal["0479d6a4c7c99b447d6bcf03b9f938042623e380"]="0479d6a4c7c99b447d6bcf03b9f938042623e380"
    frozen_pilot_protocol_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    evaluated_real_topic_pairs:Literal[0]=0
    observed_human_participants:Literal[0]=0
    authenticated_release_approval:Literal[False]=False
    external_provider_calls:Literal[0]=0
    attempted_production_deploys:Literal[0]=0
    stage:Literal["BLOCKED_NO_RELEASE"]="BLOCKED_NO_RELEASE"
    manifest_tier:Literal["REHEARSAL_ONLY_NOT_PRODUCTION"]="REHEARSAL_ONLY_NOT_PRODUCTION"
    normalized_sample_replay:tuple[ReplayProof,...]=Field(min_length=2,max_length=2)
    source_samples:tuple[SampleProvenance,...]=Field(min_length=2,max_length=2)
    local_rollback:LocalRollbackProof
    gates:tuple[ReleaseGateRow,...]=Field(min_length=len(GATES),max_length=len(GATES))
    blocked_reasons:tuple[str,...]=Field(min_length=1)
    full_artifact_provenance:Literal["UNMEASURED"]="UNMEASURED"
    actual_end_to_end_reliability:Literal["UNMEASURED"]="UNMEASURED"
    human_efficacy:Literal["UNMEASURED"]="UNMEASURED"
    v3_released:Literal[False]=False
    release_authorized:Literal[False]=False
    report_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self):
        if tuple(g.name for g in self.gates)!=GATES:
            raise ValueError("V3_17_GATE_ORDER_OR_ID_TAMPERED")
        expected=tuple(g.name for g in self.gates if g.state=="BLOCKED_UNMEASURED")
        if expected!=self.blocked_reasons or expected!=tuple(UNMET):
            raise ValueError("V3_17_BLOCKERS_REMOVED")
        if tuple(s.subject for s in self.source_samples)!=(
            "BINARY_SEARCH_SAMPLE","TEMPORAL_GEOMETRY_DEMO"):
            raise ValueError("V3_17_SOURCE_SUBJECTS_CHANGED")
        if tuple(s.subject for s in self.normalized_sample_replay)!=(
            "BINARY_SEARCH_SAMPLE","TEMPORAL_GEOMETRY_DEMO"):
            raise ValueError("V3_17_REPLAY_SUBJECTS_CHANGED")
        if self.report_sha256!=compute_content_hash(
            self.model_dump(mode="json",exclude={"report_sha256"})
        ):
            raise ValueError("V3_17_REPORT_HASH_TAMPERED")
        return self


def rehearse_local_v2_route(*,root:Path,baseline_path:Path|None=None,
                            core_manifest_path:Path|None=None)->LocalRollbackProof:
    """Atomic, ephemeral *local config-pointer* rollback only.

    Fails before any write on changed protected blobs. This does not deploy V2
    or reset a GitHub ref, hence it is a limited rollback readiness drill.
    """
    from scripts.verify_v2_core_freeze import (
        MANIFEST_PATH,EXPECTED_EVIDENCE_COMMIT,git_blob_sha,verify,
    )
    if verify():
        _deny("V2_FROZEN_CORE_VERIFY_FAILED")
    baseline=root/"benchmarks/baselines/v1/baseline.json" if baseline_path is None else baseline_path
    core=MANIFEST_PATH if core_manifest_path is None else core_manifest_path
    if not baseline.resolve().is_relative_to(root.resolve()) or not core.resolve().is_relative_to(root.resolve()):
        _deny("ROLLBACK_INPUT_OUTSIDE_REPO")
    baseline_sha=_sha(baseline);core_sha=_sha(core)
    frozen=json.loads(core.read_text(encoding="utf-8"))
    if frozen["evidence_freeze_commit"]!=EXPECTED_EVIDENCE_COMMIT:
        _deny("V2_FROZEN_CORE_COMMIT_DRIFT")
    expected_blob=frozen["rollback"]["baseline_git_blob_sha"]
    if git_blob_sha(baseline)!=expected_blob:
        _deny("V1_ROLLBACK_BLOB_CHANGED")
    if frozen["rollback"]["v1_freeze_commit"]!=V1_FREEZE_COMMIT:
        _deny("V1_ROLLBACK_REF_CHANGED")
    if (frozen["rollback"]["baseline_path"]!="benchmarks/baselines/v1/baseline.json"
        or frozen["accepted_engine_commit"]!="fdad3db1340d8b28175ab5382d800ff79df9a8a0"):
        _deny("V2_FROZEN_LINEAGE_CHANGED")
    route_record={"route":"v3_staging","v2_fallback_commit":V2_FROZEN_MAIN,
                  "v1_blob":expected_blob}
    with tempfile.TemporaryDirectory(prefix="v3_17_local_rollback_") as tmpdir:
        folder=Path(tmpdir)
        route=folder/"active_route.json"
        route.write_text(json.dumps(route_record,sort_keys=True),encoding="utf-8")
        observed=json.loads(route.read_text(encoding="utf-8"))
        if observed!=route_record:_deny("STAGING_ROUTE_MUTATED")
        observed["route"]="v2_frozen"
        staging=folder/"active_route.next"
        staging.write_text(json.dumps(observed,sort_keys=True),encoding="utf-8")
        os.replace(staging,route)
        actual=json.loads(route.read_text(encoding="utf-8"))
        if (actual["route"]!="v2_frozen" or
            actual["v2_fallback_commit"]!=V2_FROZEN_MAIN or
            actual["v1_blob"]!=expected_blob):
            _deny("LOCAL_RESTORE_INVALID")
        route_sha=_sha(route)
    if _sha(baseline)!=baseline_sha or _sha(core)!=core_sha:
        _deny("FROZEN_SOURCE_CHANGED_DURING_REHEARSAL")
    return LocalRollbackProof(
        v1_baseline_blob_sha=expected_blob,
        core_manifest_sha256=core_sha,
        unchanged_v1_baseline_sha256=baseline_sha,
        route_state_sha256=route_sha,
    )


def _proof_sha(value)->str:
    return compute_content_hash(value.model_dump(mode="json"))


def _source_samples(*,binary_args:dict,geometry_args:dict):
    output=[]
    for subject,func,args in (
        ("BINARY_SEARCH_SAMPLE",review_binary_publication,binary_args),
        ("TEMPORAL_GEOMETRY_DEMO",review_geometry_publication,geometry_args),
    ):
        review=func(**args)
        if (review.subject!=subject or
            review.deterministic_status!=DeterministicStatus.DETERMINISTIC_PASS or
            review.publication_status!="PUBLISH_BLOCKED" or review.production_release_executed or
            not review.video_sha256):
            _deny("DEMO_COMPONENT_NOT_CERTIFIED")
        video=Path(args["video_path"])
        if _sha(video)!=review.video_sha256:
            _deny("DEMO_VIDEO_MUTATED")
        output.append(SampleProvenance(
            subject=subject,video_sha256=review.video_sha256,
            source_sha256=review.source_sha256,
            publication_review_sha256=review.review_sha256,
        ))
    return tuple(output)


def audit_release_candidate(*,root:Path,protocol:dict,
                            binary_args:dict,geometry_args:dict,
                            pixel_replays:tuple[ReplayProof,...],
                            baseline_path:Path|None=None)->ReleaseAudit:
    """Recompute all bounded PASS rows from real inputs, NEVER from a claimant."""
    from scripts.verify_v3_benchmark_protocol import validate,PROTOCOL_PATH
    from scripts.verify_v2_core_freeze import verify as verify_v2
    validate(protocol)
    if compute_content_hash(protocol)!=compute_content_hash(
        json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    ):_deny("PREREG_PAYLOAD_NOT_ON_DISK")
    if verify_v2():_deny("FROZEN_CORE_NOT_VERIFIED")
    pilot=build_manifest(protocol)
    if (pilot.status!="DESIGN_READY_UNEXECUTED" or
        pilot.evaluated_pair_count!=0 or pilot.human_scores_state!="UNMEASURED" or
        pilot.study_permissions!="NOT_AUTHORIZED"):
        _deny("FABRICATED_PILOT_OUTCOMES")
    source_samples=_source_samples(binary_args=binary_args,geometry_args=geometry_args)
    if tuple(p.subject for p in pixel_replays)!=tuple(x.subject for x in source_samples):
        _deny("SAMPLE_REPLAY_SUBJECT_MISMATCH")
    # Replay proofs must be derived from actual independently decoded videos,
    # caller is explicitly responsible for constructing their equality proof.
    for observed,record in zip(source_samples,pixel_replays,strict=True):
        if observed.subject!=record.subject:
            _deny("REPLAY_PROOF_NOT_BOUND_TO_SAMPLE")
    rollback=rehearse_local_v2_route(root=root,baseline_path=baseline_path)
    rows=[]
    passed={
        "FROZEN_V2_CORE":_proof_sha(rollback),
        "FROZEN_TOPIC_PREREG":pilot.manifest_sha256,
        "COMPONENT_H264_SOURCE_QA":compute_content_hash(
            [x.model_dump(mode="json") for x in source_samples]
        ),
        "REPRODUCIBLE_SAMPLE_PIXELS":compute_content_hash(
            [x.model_dump(mode="json") for x in pixel_replays]
        ),
        "LOCAL_V2_ROLLBACK_REHEARSAL":_proof_sha(rollback),
    }
    for name in GATES:
        if name in passed:
            rows.append(ReleaseGateRow(
                name=name,state="PASS_COMPONENT_ONLY",
                evidence_sha256=passed[name],
                reason="BOUNDED_OFFLINE_EVIDENCE_NOT_PRODUCTION_AUTHORIZATION"))
        else:
            rows.append(ReleaseGateRow(
                name=name,state="BLOCKED_UNMEASURED",reason=UNMET[name]))
    obj=dict(
        frozen_pilot_protocol_sha256=compute_content_hash(protocol),
        normalized_sample_replay=[x.model_dump(mode="json") for x in pixel_replays],
        source_samples=[x.model_dump(mode="json") for x in source_samples],
        local_rollback=rollback.model_dump(mode="json"),
        gates=[x.model_dump(mode="json") for x in rows],
        blocked_reasons=list(UNMET),
    )
    preliminary=ReleaseAudit.model_construct(**obj)
    payload=preliminary.model_dump(mode="json",exclude={"report_sha256"})
    return ReleaseAudit.model_validate(payload|{"report_sha256":compute_content_hash(payload)})


def verify_release_audit(*,candidate:ReleaseAudit,root:Path,protocol:dict,
                         binary_args:dict,geometry_args:dict,
                         pixel_replays:tuple[ReplayProof,...])->None:
    replay=audit_release_candidate(root=root,protocol=protocol,binary_args=binary_args,
                                    geometry_args=geometry_args,pixel_replays=pixel_replays)
    if candidate!=replay:
        _deny("STALE_OR_REHASHED_RELEASE_AUDIT")


def publish(*_args,**_kwargs):
    _deny("REAL_DEPLOYMENT_DISALLOWED_NO_AUTHORIZATION")
