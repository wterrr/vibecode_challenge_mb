"""V3-44 reusable semantic event compiler and genuine-source negative gates.

No OpenRouter key, POST, model inference or synthetic reattribution. CI MUST
read the immutable V3-42 genuine MP4 and replay original four narrations.
"""
from __future__ import annotations
from copy import deepcopy
import json
import os
import wave
from hashlib import sha256
from pathlib import Path
import shutil

import pytest
from pydantic import ValidationError

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.semantic_visual_events import (
    HOST_ORIGIN, SemanticLesson, compile_manim,
    create_counterfactual_from_real_scene, compiled_event_windows,
    verify_source_artifact)
from scripts.run_v3_44_semantic_counterfactual import REGISTRATION, deterministic_mux, _track_probe

ROOT=Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def genuine():
    root=Path(os.environ["V344_SOURCE_DIR"]).resolve()
    return verify_source_artifact(root)


@pytest.fixture(scope="module")
def counterfactual(genuine):
    p=create_counterfactual_from_real_scene(genuine)
    return p


def test_independent_preregister_has_no_new_paid_trial():
    p=json.loads((ROOT/REGISTRATION).read_text())
    assert p["checkpoint"]=="V3-44" and p["preregistered_before_implementation"]
    assert p["parent_pr"]==77
    assert p["parent_sha"]=="cf6a813842e1d5928a7cefb6efe34ce190155252"
    assert p["measured_gates"]["model_http_posts"]==0
    assert p["measured_gates"]["complete_partition_reveal_delay_seconds_max"]==3
    assert p["measured_gates"]["explicit_arithmetic_step_required"] is True


def test_genuine_original_plan_and_media_are_byte_verified(genuine,counterfactual):
    assert genuine.model_author=="openai/gpt-6-luna"
    assert counterfactual.provenance==HOST_ORIGIN
    assert [b.narration for b in counterfactual.beats]==[b.narration for b in genuine.beats]
    assert [b.claim_ids for b in counterfactual.beats]==[b.claim_ids for b in genuine.beats]


def test_typed_events_are_generic_and_actual_visual_proof(counterfactual):
    assert len(counterfactual.partitions)==2
    assert any(e.kind=="morph_partition" for b in counterfactual.beats for e in b.events)
    assert any(e.kind=="show_label" and e.target=="proof" for b in counterfactual.beats for e in b.events)
    r=counterfactual.relations[0]
    assert r.source=="halves" and r.target=="quarters"
    assert r.multiply_by==2
    labels={l.id:l for l in counterfactual.labels}
    assert labels[r.proof_label_id].text=="(1×2)/(2×2) = 2/4"
    t={o.id:o for o in counterfactual.tiles}
    a=lambda p:sum(t[k].width*t[k].height for k in p.part_ids)
    assert abs(a(counterfactual.partitions[0])-a(counterfactual.partitions[1]))<1e-8


def test_beat_audio_anchor_and_early_complete_reveals(counterfactual):
    # This test checks deterministic scheduled completion, not actual word-level ASR.
    duration=[9.2,9.933,10.4,9.8]
    events=compiled_event_windows(counterfactual,duration)
    assert len(events)>=13
    complete={x["target"]:x for x in events
              if x["kind"] in ("reveal_partition","morph_partition")}
    assert complete["halves"]["end_seconds"]<=3
    assert complete["quarters"]["end_seconds"]-9.2<=3
    proof=next(x for x in events if x["kind"]=="show_label" and x["target"]=="proof")
    assert proof["beat"]==3
    assert 19.133<=proof["start_seconds"]<22


def test_host_only_compiler_has_no_eval_and_no_serial_four_piece_reveal(counterfactual):
    code=compile_manim(counterfactual,[9.2,9.933,10.4,9.8])
    assert "TransformFromCopy(" in code
    assert "LaggedStart(" in code
    assert "AnimationGroup(" in code
    assert "(1×2)/(2×2) = 2/4" in code
    assert "HOST-CURATED" in code
    assert "VIDEO-ONLY SAFETY TAIL" in code
    assert "self.wait(0.80000)" in code
    assert "from manim import *" in code
    assert "from openai" not in code
    assert "__import__" not in code
    assert "subprocess" not in code
    assert "import os" not in code
    compile(code,"<host-compiled v3-44>","exec")


@pytest.mark.parametrize("kind",[
    "unequal_whole","wrong_multiplier","falsified_proof_label","overlapping_tiles",
    "removed_target","repeated_id","early_emphasis","missing_morph",
    "fraction_count_drift","event_overlap","ref_out_of_bounds",
    "unsupported_numeric_visible_text","proof_wrong_claim_beat",
])
def test_host_contract_rejects_mutated_storyboard(counterfactual,kind):
    d=counterfactual.model_dump(mode="json")
    if kind=="unequal_whole":
        d["tiles"][2]["height"]=1.5
        d["tiles"][3]["height"]=1.5
        d["tiles"][4]["height"]=1.5
        d["tiles"][5]["height"]=1.5
    elif kind=="wrong_multiplier":
        d["relations"][0]["multiply_by"]=3
    elif kind=="falsified_proof_label":
        next(x for x in d["labels"] if x["id"]=="proof")["text"]="(1×3)/(2×3) = 2/4"
    elif kind=="overlapping_tiles":
        d["tiles"][1]["x"]=d["tiles"][0]["x"]
    elif kind=="removed_target":
        d["partitions"][1]["part_ids"][0]="does_not_exist"
    elif kind=="repeated_id":
        d["labels"][1]["id"]=d["tiles"][0]["id"]
    elif kind=="early_emphasis":
        d["beats"][0]["events"][0]={"kind":"emphasize","target":"quarters","at":0,"span":.12,"source":""}
    elif kind=="missing_morph":
        d["beats"][1]["events"][0]={"kind":"reveal_partition","target":"quarters","at":0,"span":.20,"source":""}
    elif kind=="fraction_count_drift":
        d["partitions"][1]["numerator"]=3
    elif kind=="event_overlap":
        d["beats"][0]["events"][1]["at"]=.1
    elif kind=="ref_out_of_bounds":
        d["tiles"][0]["x"]=100.
    elif kind=="unsupported_numeric_visible_text":
        d["labels"][1]["text"]="1/3"
    elif kind=="proof_wrong_claim_beat":
        d["beats"][2]["claim_ids"]=["F1"]
    with pytest.raises(ValidationError):
        SemanticLesson.model_validate(d)


def test_broken_real_video_sha_prevents_evidence_bridge(tmp_path,genuine):
    source=Path(os.environ["V344_SOURCE_DIR"]).resolve()
    src=tmp_path/"modified"
    src.mkdir()
    shutil.copy2(source/"scene_plan.json",src/"scene_plan.json")
    (src/"creative_manim_with_audio.mp4").write_bytes(b"not genuine")
    with pytest.raises(Blocked,match="V344_SOURCE_MODEL_ARTIFACT_TAMPERED"):
        verify_source_artifact(src)


def test_event_budget_invalid_rejected(counterfactual):
    with pytest.raises(Blocked,match="V344_MEASURED_BEAT_DURATION_INVALID"):
        compile_manim(counterfactual,[9.2,9.3,100.,9.8])


def test_workflow_has_source_locked_and_zero_paid_key():
    code=(ROOT/".github/workflows/v3-44-semantic-visual-narration.yml").read_text()
    assert "38189257163" in code
    assert "v3-42-genuine-model-video-or-failclosed-receipt" in code
    assert "actions/download-artifact@v4" in code
    assert "V344_SOURCE_DIR" in code
    assert "OPENROUTER_API_KEY" not in code and "secrets.OPENROUTER" not in code
    assert "v3_44_host_counterfactual_with_audio.mp4" in code


def test_host_final_label_is_in_open_whole_gap(counterfactual):
    t={x.id:x for x in counterfactual.tiles}
    label=next(x for x in counterfactual.labels if x.id=="equivalent")
    left_right=max(t[n].x+t[n].width/2 for n in ("hshade","hplain"))
    right_left=min(t[n].x-t[n].width/2 for n in
                   ("qshade1","qshade2","qplain1","qplain2"))
    estimated_label_half_width=min(8.,max(.5,len(label.text)*.23))/2
    assert label.x-estimated_label_half_width > left_right
    assert label.x+estimated_label_half_width < right_left
    assert label.text=="Same whole"



@pytest.fixture(scope="module")
def failing_mux_artifact():
    """Frozen V3-44 failed *host* render; never counted as a real model response."""
    root=Path(os.environ["V344_FAILING_MUX_DIR"]).resolve()
    raw=root/"manim_output/videos/v3_44_host_compiled_manim/720p15/GeneratedLesson.mp4"
    wav=root/"narration.wav"
    broken=root/"v3_44_host_counterfactual_with_audio.mp4"
    expected={
        raw:"3ca3559f4204015828302783d54a0f5e34c0632d628358328cc55467ac591fe9",
        wav:"da180c5874c30fb98f8b0ca66c2987ad81decb28ad37f5d2d47d84f6b416bd7f",
        broken:"2017c385c666c07fb13dfca463d60ca812e7c28f558d304d7a3c619f2bccc9e4",
    }
    assert all(path.is_file() and sha256(path.read_bytes()).hexdigest()==digest
               for path,digest in expected.items()), "V344_FROZEN_FAILING_ARTIFACT_DRIFT"
    return raw,wav,broken


def test_historical_shortest_failure_is_reproduced_from_actual_failed_mp4(failing_mux_artifact):
    raw,wav,broken=failing_mux_artifact
    raw_probe=_track_probe(raw)
    bad_probe=_track_probe(broken)
    v=lambda info:next(s for s in info["streams"] if s["codec_type"]=="video")
    assert int(v(raw_probe)["nb_frames"])==595
    assert int(v(bad_probe)["nb_frames"])==588
    with wave.open(str(wav),"rb") as a:
        assert abs(a.getnframes()/a.getframerate()-590/15)<1e-6


def test_fixed_mux_preserves_exact_video_frames_and_full_aac(failing_mux_artifact,tmp_path):
    raw,wav,broken=failing_mux_artifact
    output=tmp_path/"repaired_native.mp4"
    receipt=deterministic_mux(raw,wav,output,[{"frames":590}])
    assert receipt["raw_manim_frames"]==595
    assert receipt["required_audio_derived_video_frames"]==590
    assert receipt["output_h264_frames"]==590
    assert receipt["mux_strategy"]=="EXACT_AUDIO_FRAME_BUDGET_WITHOUT_SHORTEST"
    assert receipt["video_sha256"]==sha256(output.read_bytes()).hexdigest()
    assert abs(receipt["output_aac_seconds"]-receipt["input_wav_seconds"])<1/15
    assert abs(receipt["output_h264_seconds"]-590/15)<1e-5
    probed=_track_probe(output)
    assert {s["codec_name"] for s in probed["streams"]}=={"h264","aac"}
    # A source at 595 frames MUST never permit muxing to stop at 588 like -shortest.
    assert receipt["output_h264_frames"]>588


def test_mismatched_source_frame_budget_fails_closed(failing_mux_artifact,tmp_path):
    _,wav,broken=failing_mux_artifact
    # 588-frame H.264 stream, but original narration needs 590 frames.
    with pytest.raises(Blocked,match="V344_MANIM_VIDEO_TOO_SHORT_FOR_NARRATION"):
        deterministic_mux(broken,wav,tmp_path/"not_created.mp4",[{"frames":590}])
    assert not (tmp_path/"not_created.mp4").exists()


def test_shortened_input_wav_fails_closed_before_ffmpeg(failing_mux_artifact,tmp_path):
    raw,wav,_=failing_mux_artifact
    short=tmp_path/"shortened.wav"
    with wave.open(str(wav),"rb") as source:
        params=source.getparams()
        pcm=source.readframes(source.getnframes())
    with wave.open(str(short),"wb") as dest:
        dest.setparams(params)
        dest.writeframes(pcm[:int(params.framerate*37.0)*params.sampwidth])
    with pytest.raises(Blocked,match="V344_AUDIO_BUDGET_MISMATCH"):
        deterministic_mux(raw,short,tmp_path/"not_created.mp4",[{"frames":590}])
    assert not (tmp_path/"not_created.mp4").exists()


def test_frozen_mux_source_and_ci_do_not_use_shortest_or_model_secrets():
    source=(ROOT/"scripts/run_v3_44_semantic_counterfactual.py").read_text()
    workflow=(ROOT/".github/workflows/v3-44-semantic-visual-narration.yml").read_text()
    assert '"-frames:v",str(expected)' in source
    assert '"-shortest" in cmd' in source  # explicit fail-closed guard only
    assert '         "-shortest",' not in source
    assert "38192773382" in workflow
    assert "V344_FAILING_MUX_DIR" in workflow
    assert "OPENROUTER_API_KEY" not in workflow
