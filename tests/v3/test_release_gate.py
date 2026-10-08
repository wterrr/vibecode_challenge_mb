"""V3-17 fail-closed RC readiness, real independent H264 and local V2 rollback."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v2.repair import compute_content_hash
from learnflow_v3.models import SemanticContractError
from learnflow_v3.release_gate import (
    GATES,UNMET,PROVEN_GATES,
    ReleaseAudit,ReplayProof,ReleaseGateRow,LocalRollbackProof,
    rehearse_local_v2_route,verify_independent_pixel_replay,
    audit_release_candidate,verify_release_audit,publish,
)
from scripts.verify_v3_release_gate import produce,_pair
from scripts.verify_v3_benchmark_protocol import PROTOCOL_PATH
from scripts.verify_v2_core_freeze import git_blob_sha


@pytest.fixture(scope="module")
def golden(tmp_path_factory):
    path=tmp_path_factory.mktemp("v3_17_real_4_mp4")
    result=produce(path)
    return path,result


@pytest.fixture(scope="module")
def replay_inputs(golden):
    folder,result=golden
    binary,geom=_source_only_for_replay(folder,result)
    return binary,geom


def _source_only_for_replay(folder,result):
    # Source object construction strictly mirrors V3-17, but must not overwrite
    # the original four MP4s. This is not required for trivial schema tests.
    duplicate=folder/"review_src"
    duplicate.mkdir(exist_ok=True)
    return _pair(duplicate)


def _read_audit(result):
    return ReleaseAudit.model_validate(result["release_audit"])


def _paths(folder):
    return (folder/"independent/grounded_duplicate.mp4",
            folder/"independent/release_geometry.mp4")


def _proofs(result):
    return tuple(ReplayProof.model_validate(x)
                 for x in result["release_audit"]["normalized_sample_replay"])


def _protocol():
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def test_real_source_bound_v3_17_rehearsal_4_h264(golden):
    path,result=golden
    audit=_read_audit(result)
    assert audit.stage=="BLOCKED_NO_RELEASE"
    assert audit.candidate_kind=="RC_READINESS_AUDIT_NOT_RELEASE_CANDIDATE"
    assert audit.v3_released is False and audit.release_authorized is False
    assert audit.observed_human_participants==0
    assert audit.evaluated_real_topic_pairs==0
    assert audit.external_provider_calls==audit.attempted_production_deploys==0
    assert audit.manifest_tier=="REHEARSAL_ONLY_NOT_PRODUCTION"
    assert audit.full_artifact_provenance=="UNMEASURED"
    assert result["reproducible_full_application_build"]=="NOT_ESTABLISHED"
    assert len(audit.source_samples)==2
    assert len(audit.normalized_sample_replay)==2
    assert len(audit.gates)==12
    assert tuple(x.name for x in audit.gates)==GATES
    assert audit.blocked_reasons==tuple(UNMET)
    assert all(x.state=="PASS_COMPONENT_ONLY" for x in audit.gates[:5])
    assert all(x.state=="BLOCKED_UNMEASURED" for x in audit.gates[5:])
    for video in ("primary/grounded_duplicate.mp4","primary/release_geometry.mp4",
                  "independent/grounded_duplicate.mp4","independent/release_geometry.mp4"):
        p=path/video
        assert p.is_file() and p.stat().st_size>1000
    assert result["actual_release"]=="BLOCKED"
    assert result["rollback_restored_a_running_service"] is False


def test_exact_frozen_v2_baseline_blob_local_simulated_rollback(golden):
    _,result=golden
    rollback=LocalRollbackProof.model_validate(
        result["release_audit"]["local_rollback"])
    protected=ROOT/"benchmarks/baselines/v1/baseline.json"
    assert git_blob_sha(protected)==rollback.v1_baseline_blob_sha
    assert hashlib.sha256(protected.read_bytes()).hexdigest()==rollback.unchanged_v1_baseline_sha256
    assert rollback.historical_main_ref=="a06e0b0b5f35e9147b4081da7ed7f7934affe0c6"
    assert rollback.route_before=="v3_staging" and rollback.route_after=="v2_frozen"
    assert rollback.production_route_changed is False
    assert rollback.git_ref_changed is False
    assert rollback.deployed_services_touched is False


def test_local_rollback_corrupt_baseline_fails_without_touching_repository(tmp_path):
    case_root=tmp_path/"local_checkout"
    baseline=case_root/"benchmarks/baselines/v1/baseline.json"
    core=case_root/"benchmarks/core_freeze/manifest.json"
    baseline.parent.mkdir(parents=True);core.parent.mkdir(parents=True)
    baseline.write_bytes((ROOT/"benchmarks/baselines/v1/baseline.json").read_bytes()+b"corrupt")
    core.write_bytes((ROOT/"benchmarks/core_freeze/manifest.json").read_bytes())
    with pytest.raises(SemanticContractError,match="V1_ROLLBACK_BLOB_CHANGED"):
        rehearse_local_v2_route(root=case_root)
    assert baseline.read_bytes().endswith(b"corrupt")
    assert git_blob_sha(ROOT/"benchmarks/baselines/v1/baseline.json")!="0"*40


def test_local_rollback_protects_against_symlink_and_foreign_paths(tmp_path):
    case_root=tmp_path/"local_checkout"
    baseline=case_root/"benchmarks/baselines/v1/baseline.json"
    core=case_root/"benchmarks/core_freeze/manifest.json"
    baseline.parent.mkdir(parents=True);core.parent.mkdir(parents=True)
    core.write_bytes((ROOT/"benchmarks/core_freeze/manifest.json").read_bytes())
    baseline.symlink_to(ROOT/"benchmarks/baselines/v1/baseline.json")
    with pytest.raises(SemanticContractError,match="ROLLBACK_INPUT_OUTSIDE_REPO"):
        rehearse_local_v2_route(root=case_root)
    with pytest.raises(SemanticContractError,match="ROLLBACK_INPUT_OUTSIDE_REPO"):
        rehearse_local_v2_route(root=ROOT,baseline_path=tmp_path/"missing.json")


def test_copy_of_valid_rollback_source_yields_same_route_digest(tmp_path,golden):
    case_root=tmp_path/"safe_checkout"
    baseline=case_root/"benchmarks/baselines/v1/baseline.json"
    core=case_root/"benchmarks/core_freeze/manifest.json"
    baseline.parent.mkdir(parents=True);core.parent.mkdir(parents=True)
    baseline.write_bytes((ROOT/"benchmarks/baselines/v1/baseline.json").read_bytes())
    core.write_bytes((ROOT/"benchmarks/core_freeze/manifest.json").read_bytes())
    expected=golden[1]["release_audit"]["local_rollback"]
    proof=rehearse_local_v2_route(root=case_root)
    assert proof.model_dump(mode="json")==expected
    assert not list(tmp_path.glob("active_route*.json"))


def test_forged_permission_and_stale_rehashed_audit_blocked(golden):
    _,result=golden
    data=result["release_audit"]
    for key,value in (("v3_released",True),("release_authorized",True),
                      ("authenticated_release_approval",True),
                      ("observed_human_participants",12),("stage","RELEASED")):
        copy=json.loads(json.dumps(data))
        copy[key]=value
        copy["report_sha256"]=compute_content_hash({k:v for k,v in copy.items()
                                                    if k!="report_sha256"})
        with pytest.raises(ValidationError):
            ReleaseAudit.model_validate(copy)


def test_gate_cannot_be_promoted_to_pass_by_rehashing(golden):
    _,result=golden
    data=json.loads(json.dumps(result["release_audit"]))
    data["gates"][6]["state"]="PASS_COMPONENT_ONLY"
    data["gates"][6]["evidence_sha256"]="f"*64
    data["blocked_reasons"].remove("BLINDED_INDEPENDENT_HUMAN_QUALITY")
    data["report_sha256"]=compute_content_hash({k:v for k,v in data.items()
                                                if k!="report_sha256"})
    with pytest.raises(ValidationError):
        ReleaseAudit.model_validate(data)


def test_gate_missing_or_reordered_cannot_be_repackaged(golden):
    _,result=golden
    d=json.loads(json.dumps(result["release_audit"]))
    d["gates"]=d["gates"][:-1]
    d["report_sha256"]=compute_content_hash({k:v for k,v in d.items()
                                             if k!="report_sha256"})
    with pytest.raises(ValidationError):
        ReleaseAudit.model_validate(d)
    d=json.loads(json.dumps(result["release_audit"]))
    d["gates"][0],d["gates"][1]=d["gates"][1],d["gates"][0]
    d["report_sha256"]=compute_content_hash({k:v for k,v in d.items()
                                             if k!="report_sha256"})
    with pytest.raises(ValidationError,match="GATE_ORDER"):
        ReleaseAudit.model_validate(d)


def test_historical_source_refs_and_review_are_not_release_authority(golden):
    _,result=golden
    audit=_read_audit(result)
    assert all(s.release_status=="PUBLISH_BLOCKED" for s in audit.source_samples)
    assert all(s.deterministic=="DETERMINISTIC_PASS" for s in audit.source_samples)
    assert all(s.artifact_kind=="BOUNDED_COMPONENT_MP4" for s in audit.source_samples)
    for gate in audit.gates[5:]:
        assert gate.reason==UNMET[gate.name]
    with pytest.raises(SemanticContractError,match="DISALLOWED_NO_AUTHORIZATION"):
        publish(artifact_path="/tmp/example.mp4")


def test_independent_full_decoded_rgb_replay_rejects_fake_hashes(golden,replay_inputs):
    path,result=golden
    binary,geom=replay_inputs
    evidence=list(_proofs(result))
    spoof=evidence[0].model_copy(update={
        "primary_sha256":"0"*64,
        "independent_sha256":"0"*64,
    })
    with pytest.raises(SemanticContractError,match="PIXEL_REPLAY_MISMATCH"):
        verify_independent_pixel_replay(
            binary_args=binary,geometry_args=geom,
            independent_video_paths=_paths(path),
            pixel_replays=(spoof,evidence[1]))


def test_independent_replay_does_not_accept_same_file_twice(golden,replay_inputs):
    path,result=golden
    binary,geom=replay_inputs
    with pytest.raises(SemanticContractError,match="IDENTICAL_REPLAY_FILE"):
        verify_independent_pixel_replay(
            binary_args=binary,geometry_args=geom,
            independent_video_paths=(
                Path(binary["video_path"]),Path(geom["video_path"])),
            pixel_replays=_proofs(result))


def test_swapped_temporal_and_algorithm_video_rejected(golden,replay_inputs):
    path,result=golden
    binary,geom=replay_inputs
    wrong=tuple(reversed(_paths(path)))
    with pytest.raises(SemanticContractError):
        verify_independent_pixel_replay(
            binary_args=binary,geometry_args=geom,
            independent_video_paths=wrong,
            pixel_replays=_proofs(result))


def test_audit_source_replay_rejects_stale_mp4_proof(golden,replay_inputs,tmp_path):
    path,result=golden
    binary,geom=replay_inputs
    wrong=tmp_path/"modified.mp4"
    wrong.write_bytes(Path(binary["video_path"]).read_bytes()+b"altered-container")
    args={**binary,"video_path":wrong}
    with pytest.raises(SemanticContractError,match="DEMO_COMPONENT_NOT_CERTIFIED"):
        audit_release_candidate(
            root=ROOT,protocol=_protocol(),binary_args=args,geometry_args=geom,
            pixel_replays=_proofs(result),independent_video_paths=_paths(path))


def test_cannot_claim_reproducible_full_application_build(golden):
    audit=_read_audit(golden[1])
    assert audit.full_artifact_provenance=="UNMEASURED"
    assert audit.actual_end_to_end_reliability=="UNMEASURED"
    assert audit.human_efficacy=="UNMEASURED"
    assert audit.v3_released is False
    bad=audit.model_dump(mode="json")
    bad["full_artifact_provenance"]="PASS"
    with pytest.raises(ValidationError):
        ReleaseAudit.model_validate(bad)
