"""V3-06 real MP4, decoded semantic frames, oracle and geometry regressions."""
from __future__ import annotations

from pathlib import Path
import sys
import pytest
from pydantic import ValidationError
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v2.repair import compute_content_hash
from learnflow_v3 import SemanticContractError
from learnflow_v3.binary_search_trace import BinarySearchTrace
from learnflow_v3.sequence_renderer import (
    SequenceRenderProfile,draw_binary_search_frame,
    render_certified_binary_search_video,_layout,_ffmpeg_anchor,_mean_absolute_error,
)
from scripts.verify_v3_binary_search_render import create_certified_demo_bundle


@pytest.fixture
def profile():
    return SequenceRenderProfile(width=640,height=360,fps=12,seconds_per_step=0.75)


def render_case(tmp_path,values,target,profile):
    bundle,trace=create_certified_demo_bundle(values=values,target=target)
    out=tmp_path/"certified.mp4"
    evidence=render_certified_binary_search_video(
        trace=trace,**{k:v for k,v in bundle.items() if k!="verified_trace_refs"},
        output_path=out,profile=profile,
    )
    return bundle,trace,evidence,out


def test_real_mp4_decoded_steps_move_and_array_identity_remains(profile,tmp_path):
    bundle,trace,evidence,out=render_case(tmp_path,(1,3,5,7,9,12,12,14,18),12,profile)
    assert out.read_bytes()[4:8]==b"ftyp"
    assert evidence.video_bytes>2000
    assert evidence.frame_count==len(trace.steps)*profile.frames_per_step()
    assert evidence.duration_seconds==evidence.frame_count/profile.fps
    assert evidence.status=="RENDERED_VERIFIED_OFFLINE_NO_NARRATION_AUDIO"
    assert evidence.temporal_geometry_pass and evidence.decoded_semantic_frames_pass
    assert all(x<8 for x in evidence.decoded_anchor_mae)
    assert all(x>=1.25 for x in evidence.decoded_step_deltas)
    assert evidence.identity_centers==_layout(profile,len(trace.query.values))
    for a,b in zip(evidence.identity_centers,evidence.identity_centers[1:]):
        assert b-a>=30
    assert evidence.source_trace_sha256==trace.trace_sha256


def test_actual_mp4_frames_match_independently_drawn_step_anchors(profile,tmp_path):
    bundle,trace,evidence,out=render_case(tmp_path,(1,3,5,7,9,12,12,14,18),12,profile)
    for i,idx in enumerate(evidence.step_frame_indices):
        decoded=_ffmpeg_anchor(out,at=(idx+0.4)/profile.fps,profile=profile)
        ideal=draw_binary_search_frame(
            trace=trace,step_index=i,progress=0.75,
            subtitle=bundle["script"].segments[i].spoken_text,profile=profile,
        )
        roi=(35,94,605,249)
        assert _mean_absolute_error(decoded,ideal,rect=roi)<8


@pytest.mark.parametrize("values,target,expected",[
    ((),5,None),((12,),12,0),((12,),11,None),
    ((1,2,2,2,5),2,1),((1,3,5,7,9),4,None),
    ((-9,-4,0,2,2,10),-9,0),
])
def test_edge_case_mp4_oracle_and_terminal_frame(profile,tmp_path,values,target,expected):
    bundle,trace,evidence,out=render_case(tmp_path,values,target,profile)
    assert trace.result_index==expected
    assert out.stat().st_size>1000
    assert len(evidence.step_frame_indices)==len(trace.steps)
    if not values:
        assert len(trace.steps)==1 and evidence.identity_centers==()
        assert evidence.decoded_step_deltas==()
    else:
        assert all(x>=1.25 for x in evidence.decoded_step_deltas)


def test_static_values_fixed_positions_over_all_animation_frames(profile):
    _,trace=create_certified_demo_bundle(values=(1,3,3,7,9),target=3)
    frames=[
        draw_binary_search_frame(trace=trace,step_index=i,progress=p,
            subtitle="Binary search for 3 in [1, 3, 3, 7, 9]",profile=profile)
        for i in range(len(trace.steps)) for p in (0.0,0.25,0.75,1.0)
    ]
    assert len(set(f.size for f in frames))==1
    assert len(set(f.tobytes() for f in frames))>=len(trace.steps)


def test_oversized_array_fails_instead_of_tiny_cards(profile,tmp_path):
    b,trace=create_certified_demo_bundle(values=tuple(range(17)),target=8)
    with pytest.raises(SemanticContractError,match="VISIBLE_ARRAY_CAP_EXCEEDED"):
        render_certified_binary_search_video(
            trace=trace,**{k:v for k,v in b.items() if k!="verified_trace_refs"},
            output_path=tmp_path/"bad.mp4",profile=profile,
        )


def test_rehashed_forged_algorithm_step_cannot_render(profile,tmp_path):
    b,trace=create_certified_demo_bundle(values=(1,3,5),target=3)
    d=trace.model_dump(mode="json")
    d["steps"][0]["mid"]=0
    d["trace_sha256"]=compute_content_hash({k:v for k,v in d.items() if k!="trace_sha256"})
    forged=BinarySearchTrace.model_validate(d)
    with pytest.raises(SemanticContractError,match="STEP_MISMATCH"):
        render_certified_binary_search_video(
            trace=forged,**{k:v for k,v in b.items() if k!="verified_trace_refs"},
            output_path=tmp_path/"forged.mp4",profile=profile,
        )
    assert not (tmp_path/"forged.mp4").exists()


def test_changed_ledger_or_teaching_target_cannot_render(profile,tmp_path):
    b,trace=create_certified_demo_bundle(values=(1,3,5),target=3)
    raw=b["ledger"].model_dump(mode="json")
    raw["steps"][0]["object_states"][0]["properties"]["high"]=999
    bad=type(b["ledger"]).model_validate(raw)
    with pytest.raises(SemanticContractError,match="STATE_LEDGER_MISMATCH"):
        render_certified_binary_search_video(
            trace=trace,**{k:(bad if k=="ledger" else v) for k,v in b.items() if k!="verified_trace_refs"},
            output_path=tmp_path/"invalid-ledger.mp4",profile=profile,
        )
    sb=b["storyboard"].model_dump(mode="json")
    sb["scenes"][0]["visual_intent"]="Binary search for 4 in [1, 3, 5]"
    bad_story=type(b["storyboard"]).model_validate(sb)
    with pytest.raises(SemanticContractError,match="SEMANTIC_INPUT_MISMATCH"):
        render_certified_binary_search_video(
            trace=trace,**{k:(bad_story if k=="storyboard" else v) for k,v in b.items() if k!="verified_trace_refs"},
            output_path=tmp_path/"invalid-lesson.mp4",profile=profile,
        )


def test_existing_output_or_symlink_never_erased(profile,tmp_path):
    b,trace=create_certified_demo_bundle(values=(12,),target=12)
    args={k:v for k,v in b.items() if k!="verified_trace_refs"}
    occupied=tmp_path/"data.mp4"
    occupied.write_bytes(b"PROTECTED")
    with pytest.raises(SemanticContractError,match="UNSAFE_OUTPUT_PATH"):
        render_certified_binary_search_video(trace=trace,**args,output_path=occupied,profile=profile)
    link=tmp_path/"linked.mp4"
    link.symlink_to(occupied)
    with pytest.raises(SemanticContractError,match="UNSAFE_OUTPUT_PATH"):
        render_certified_binary_search_video(trace=trace,**args,output_path=link,profile=profile)
    assert occupied.read_bytes()==b"PROTECTED"


def test_unchecked_pixel_mode_rejected_and_invalid_profile_fails(profile,tmp_path):
    with pytest.raises(ValidationError):
        SequenceRenderProfile(width=641,height=360)
    b,trace=create_certified_demo_bundle(values=(1,2,3),target=2)
    with pytest.raises(SemanticContractError,match="PIXEL_VERIFICATION_REQUIRED"):
        render_certified_binary_search_video(
            trace=trace,**{k:v for k,v in b.items() if k!="verified_trace_refs"},
            output_path=tmp_path/"unchecked.mp4",profile=profile,verify_decoded=False,
        )


def test_numeric_label_overflow_and_wrong_aspect_fail_before_encoding(profile,tmp_path):
    with pytest.raises(ValidationError, match="16_9_ASPECT_RATIO_REQUIRED"):
        SequenceRenderProfile(width=640,height=400)
    b,trace=create_certified_demo_bundle(values=(10**22,),target=10**22)
    with pytest.raises(SemanticContractError,match="NUMERIC_LABEL_OVERLAP|TARGET_LABEL_OVERLAP"):
        render_certified_binary_search_video(
            trace=trace,**{k:v for k,v in b.items() if k!="verified_trace_refs"},
            output_path=tmp_path/"overflow.mp4",profile=profile,
        )
    assert not (tmp_path/"overflow.mp4").exists()
