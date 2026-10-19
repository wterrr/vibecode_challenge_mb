"""V3-10 actual decoded H264 beat-to-visual grounding and timing mutations."""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v3.beat_grounding import (
    BeatGroundingEvidence,BeatGroundingManifest,BoundBeat,
    compile_binary_beat_manifest,verify_binary_beat_video,
)
from learnflow_v3.models import SemanticContractError
from learnflow_v3.sequence_renderer import SequenceRenderProfile
from scripts.verify_v3_beat_grounding import generate_verified_case


@pytest.fixture(scope="module")
def golden(tmp_path_factory):
    dest=tmp_path_factory.mktemp("v3_10_beat_pixels")
    profile=SequenceRenderProfile(width=640,height=360,fps=12,seconds_per_step=.75)
    b,t,m,r,e,v=generate_verified_case(directory=dest,case="duplicate",profile=profile)
    params={k:x for k,x in b.items() if k!="verified_trace_refs"}
    return dict(params=params,trace=t,manifest=m,renderer=r,evidence=e,
                video=v,profile=profile,directory=dest)


def _validate(golden,**overrides):
    args=dict(trace=golden["trace"],**golden["params"],
              manifest=golden["manifest"],video_evidence=golden["renderer"],
              video_path=golden["video"],profile=golden["profile"])
    args.update(overrides)
    return verify_binary_beat_video(**args)


def test_real_mp4_pixel_grounding_all_essential_beats(golden):
    e=golden["evidence"]
    assert e.status=="RENDERED_SYNTHETIC_BEAT_GROUNDING_PASS"
    assert e.dynamic_beat_count==e.dynamic_beat_pass_count>0
    assert e.observable_coverage==1
    assert e.beat_count==len(golden["trace"].steps)
    assert all(max(b.frame_anchor_mae)<8 for b in e.per_beat)
    assert all(b.semantic_roi_early_late_delta>=.08
               for b in e.per_beat if b.result=="DYNAMIC_OBSERVED")
    assert all(b.target_object_ids==tuple(x.object_id for x in
               golden["params"]["pattern"].semantic_objects) for b in e.per_beat)
    assert e.audio_sync_verified is False
    assert e.independent_semantic_cv_verified is False
    assert e.human_learning_outcome=="UNMEASURED"


def test_derived_boundaries_are_contiguous_and_exact(golden):
    m=golden["manifest"]
    n=golden["profile"].frames_per_step()
    assert m.frame_count==len(m.beats)*n
    for i,b in enumerate(m.beats):
        assert (b.frame_start,b.frame_end_exclusive)==(i*n,(i+1)*n)
        assert all(i*n<=f<(i+1)*n for f in b.sample_frame_indices)
        assert b.state_ledger_step_id==golden["params"]["ledger"].steps[i].step_id
        assert b.time_anchor_source=="RENDERER_SYNTHETIC_BEAT"


def test_manifest_is_repeatably_rebuilt_from_oracle_not_declared_state(golden):
    actual=compile_binary_beat_manifest(
        trace=golden["trace"],**golden["params"],profile=golden["profile"])
    assert actual.model_dump(mode="json")==golden["manifest"].model_dump(mode="json")
    assert _validate(golden).manifest_sha256==actual.manifest_sha256


@pytest.mark.parametrize("mutation",["shift_forward","shift_backward","wrong_beat","wrong_claim",
                                       "wrong_object","wrong_trace_step","wrong_manifest_sha"])
def test_forged_binding_timing_or_semantics_never_accepted(golden,mutation):
    data=golden["manifest"].model_dump(mode="json")
    first=data["beats"][0]
    if mutation=="shift_forward":
        first["sample_frame_indices"]=[x+1 for x in first["sample_frame_indices"]]
    elif mutation=="shift_backward":
        first["sample_frame_indices"]=[x-1 for x in first["sample_frame_indices"]]
    elif mutation=="wrong_beat":
        first["beat_id"]="beat-from-other-scene"
    elif mutation=="wrong_claim":
        first["claim_refs"]=["unverified-claim"]
    elif mutation=="wrong_object":
        first["target_object_ids"]=["fake-title-object"]
    elif mutation=="wrong_trace_step":
        first["trace_step_sha256"]="0"*64
    elif mutation=="wrong_manifest_sha":
        data["manifest_sha256"]="a"*64
    with pytest.raises((SemanticContractError,ValueError),match="V3_10_"):
        tampered=BeatGroundingManifest.model_validate(data)
        _validate(golden,manifest=tampered)


def test_stale_trace_or_source_provenance_is_rejected_even_if_manifest_rehashed(golden):
    params=dict(golden["params"])
    s=params["script"].model_dump(mode="json")
    s["segments"][0]["spoken_text"]="Binary search for 100 in [1, 3, 5]."
    params["script"]=type(params["script"]).model_validate(s)
    with pytest.raises(SemanticContractError):
        verify_binary_beat_video(
            trace=golden["trace"],**params,manifest=golden["manifest"],
            video_evidence=golden["renderer"],video_path=golden["video"],
            profile=golden["profile"])


def test_render_artifact_sha_and_forged_evidence_blocked(golden,tmp_path):
    ev=golden["renderer"].model_copy(update={"video_sha256":"0"*64})
    with pytest.raises(SemanticContractError,match="UNTRUSTED_OR_STALE_RENDER_EVIDENCE"):
        _validate(golden,video_evidence=ev)
    forged=golden["renderer"].model_copy(update={"source_manifest_hash":"0"*64})
    with pytest.raises(SemanticContractError,match="RENDER_SOURCE_MANIFEST_MISMATCH"):
        _validate(golden,video_evidence=forged)
    video=tmp_path/"tampered.mp4"
    original=golden["video"].read_bytes()
    video.write_bytes(original[:-100]+bytes((x^0xFF for x in original[-100:])))
    ev=golden["renderer"].model_copy(update={
        "video_sha256":hashlib.sha256(video.read_bytes()).hexdigest(),
        "video_bytes":video.stat().st_size,
    })
    with pytest.raises(SemanticContractError):
        _validate(golden,video_path=video,video_evidence=ev)


def test_shifted_video_with_plausible_codec_and_recomputed_sha_rejected(golden,tmp_path):
    """Frame-shift is the dangerous case: all timings are in range, pixels wrong."""
    video=tmp_path/"delayed.mp4"
    count=golden["manifest"].frame_count
    proc=subprocess.run([
        "ffmpeg","-hide_banner","-nostdin","-v","error","-i",str(golden["video"]),
        "-vf","tpad=start_mode=clone:start_duration=0.5",
        "-frames:v",str(count),"-an","-c:v","libx264",
        "-pix_fmt","yuv420p",str(video),
    ],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
    assert proc.returncode==0,proc.stderr.decode(errors="replace")
    assert video.stat().st_size>1000
    ev=golden["renderer"].model_copy(update={
        "video_sha256":hashlib.sha256(video.read_bytes()).hexdigest(),
        "video_bytes":video.stat().st_size,
    })
    with pytest.raises(SemanticContractError,match="SEMANTIC_FRAME_MISMATCH|ESSENTIAL_BEAT_NOT_VISUALLY_OBSERVED"):
        _validate(golden,video_evidence=ev,video_path=video)


def test_frozen_video_with_forged_matching_sha_is_not_visual_evidence(golden,tmp_path):
    video=tmp_path/"frozen.mp4"
    proc=subprocess.run([
        "ffmpeg","-hide_banner","-nostdin","-v","error",
        "-f","lavfi","-i","color=c=black:s=640x360:r=12",
        "-frames:v",str(golden["manifest"].frame_count),"-an",
        "-c:v","libx264","-pix_fmt","yuv420p",str(video),
    ],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
    assert proc.returncode==0,proc.stderr.decode(errors="replace")
    ev=golden["renderer"].model_copy(update={
        "video_sha256":hashlib.sha256(video.read_bytes()).hexdigest(),
        "video_bytes":video.stat().st_size,
    })
    with pytest.raises(SemanticContractError,match="SEMANTIC_FRAME_MISMATCH"):
        _validate(golden,video_evidence=ev,video_path=video)


def test_wrong_actual_source_video_with_valid_format_and_forged_metadata_is_rejected(golden,tmp_path):
    profile=golden["profile"]
    _,_,_,_,_,other=generate_verified_case(directory=tmp_path,case="missing",profile=profile)
    # Different content can have same 960x540/12fps and may even same frame count.
    ev=golden["renderer"].model_copy(update={
        "video_sha256":hashlib.sha256(other.read_bytes()).hexdigest(),
        "video_bytes":other.stat().st_size,
    })
    with pytest.raises(SemanticContractError,match="FRAME_COUNT_MISMATCH|SEMANTIC_FRAME_MISMATCH"):
        _validate(golden,video_evidence=ev,video_path=other)


def test_terminal_static_exception_must_be_true_trace_terminal(tmp_path):
    profile=SequenceRenderProfile(width=640,height=360,fps=12,seconds_per_step=.75)
    b,t,m,r,e,v=generate_verified_case(directory=tmp_path,case="empty",profile=profile)
    assert e.dynamic_beat_count==0
    assert e.beat_count==1
    assert e.per_beat[0].result=="STATIC_EXCEPTION_SOURCE_VERIFIED"
    assert e.audio_sync_verified is False
    data=m.model_dump(mode="json")
    data["beats"][0]["expected_visible_change"]="Invented animation"
    data["beats"][0]["static_exception"]=None
    with pytest.raises(SemanticContractError,match="TAMPERED_TIMING_OR_SOURCE_MANIFEST"):
        verify_binary_beat_video(trace=t,
            **{k:x for k,x in b.items() if k!="verified_trace_refs"},
            manifest=BeatGroundingManifest.model_validate(data),
            video_evidence=r,video_path=v,profile=profile)


def test_claims_cannot_upgrade_to_real_narration_or_human_learning(golden):
    raw=golden["evidence"].model_dump(mode="json")
    raw["audio_sync_verified"]=True
    with pytest.raises(ValueError):
        BeatGroundingEvidence.model_validate(raw)
    raw=golden["evidence"].model_dump(mode="json")
    raw["independent_semantic_cv_verified"]=True
    with pytest.raises(ValueError):
        BeatGroundingEvidence.model_validate(raw)
