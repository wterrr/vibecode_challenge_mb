"""V3-86 negative and metamorphic source-to-voiced-visual alignment tests."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.v382_query_evidence_bridge import compile_question,registered
from learnflow_v3.v385_affine_visual_semantics import role_contract,finite_manim_source
from learnflow_v3.v386_pedagogical_speech_contract import PHASES,semantic_phases,align_real_wav
from learnflow_v3.v386_phased_affine_manim import finite_source
from learnflow_v3.v386_native_speech_visual_gate import RESULT_ROI

ROOT=Path(__file__).resolve().parents[2]


def rows():
    return registered(ROOT)["cases"]


def case(i=1):
    row=rows()[i]
    bundle=compile_question(row,ROOT)
    role=role_contract(row,bundle)
    return row,bundle,role,semantic_phases(row,bundle,role)


def test_preregistered_before_any_code_changes():
    d=json.loads((ROOT/"benchmarks/learnflowbench/v3/v3_86_speech_visual_preregister.json").read_text())
    assert d["checkpoint"]=="V3-86"
    assert d["status"]=="FIRST_CHILD_PREREGISTRATION_BEFORE_IMPLEMENTATION"
    assert d["parent"]=={"draft_pr":122,"sha":"4bc942e489576a0f8f76db118a0be493a5d19a32"}
    assert d["fixed_case_ids"]==[r["id"] for r in rows()]
    assert (d["positive"],d["negative_abstain"],d["heldout_parameters"])==(3,2,1)
    assert d["frozen_semantics"]["phase_types"]==list(PHASES)
    assert d["frozen_semantics"]["true_word_alignment"]=="NOT_DONE"


@pytest.mark.parametrize("i",(0,1,2))
def test_six_real_source_bound_semantic_utterances(i):
    row,bundle,role,phases=case(i)
    assert len(phases)==6
    assert [p["phase_kind"] for p in phases]==list(PHASES)*2
    assert [p["semantic_beat_index"] for p in phases]==[0]*3+[1]*3
    assert [p["claim_id"] for p in phases]==["C1"]*3+["C2"]*3
    assert all(p["source_sha256"]==role["source_sha256"] for p in phases)
    assert all(p["word_timestamps"]=="NOT_AVAILABLE_NOT_FABRICATED" for p in phases)
    assert all(p["origin"]=="DETERMINISTIC_HOST_FROM_VERIFIED_FACTS_NOT_MODEL" for p in phases)
    assert len(set(p["narration_sha256"] for p in phases))==6
    assert all(hashlib.sha256(p["narration"].encode()).hexdigest()==p["narration_sha256"]
               for p in phases)
    assert bundle["contracts"]["pedagogy_gate"]=="V3_09_VALIDATED"
    assert bundle["contracts"]["visual_director_gate"]=="CORE_READY"


@pytest.mark.parametrize("i",(0,1,2))
def test_each_real_utterance_owns_a_typed_visual_decision(i):
    row,bundle,role,phases=case(i)
    src=finite_source(bundle["trace"],[9.0]*6,role,phases)
    compile(src,"<trusted-v386>",'exec')
    assert src.count("V386_GROUNDED_AUDIO_PHASE_")==6
    assert src.count("run_time=26/15")==2
    assert src.count("self.wait(2/15)")==1
    assert "MoveAlongPath" in src and "DashedLine" in src
    assert "V386_GROUNDED_AUDIO_PHASE_0_TRANSFORM" in src
    assert "V386_GROUNDED_AUDIO_PHASE_1_INTERPRET" in src
    original=finite_manim_source(bundle["trace"],[12.0,12.0],role)
    assert "V386_GROUNDED_AUDIO_PHASE_" not in original


def test_physics_speech_distinguishes_slope_and_displacement():
    for i in (1,2):
        row,b,role,phases=case(i)
        speech=" ".join(x["narration"] for x in phases).lower()
        assert "acceleration" in speech and "velocity" in speech
        assert "distance traveled" in speech
        assert "not the object's physical path" in speech
        assert role["actual_object_motion"]=="NONE_GRAPH_POINT_ONLY"
    math=" ".join(x["narration"] for x in case(0)[-1]).lower()
    assert "acceleration" not in math and "input" in math


def test_unseen_physics_parameters_change_voiced_numbers():
    a=[x["narration"] for x in case(1)[-1]]
    b=[x["narration"] for x in case(2)[-1]]
    assert a!=b
    assert "final velocity is 11" in a[4]
    assert "final velocity is 17" in b[4]


@pytest.mark.parametrize("i",(3,4))
def test_unsupported_knowledge_question_still_abstains(i):
    r=compile_question(rows()[i],ROOT)
    assert r["status"]=="ABSTAIN" and r["video"] is None


def test_mutated_source_arithmetic_blocks_speech():
    row,b,role,p=case()
    b["trace"]["events"][0]["actual"]["n"]+=1
    with pytest.raises(Blocked):
        semantic_phases(row,b,role)


def test_swapped_role_blocks_speech():
    row,b,role,p=case()
    role["role"]="input_output_line"
    with pytest.raises(Blocked):
        semantic_phases(row,b,role)


def test_cross_claim_audio_cannot_be_rendered():
    row,b,role,p=case()
    fake=deepcopy(p)
    fake[1]["claim_id"]="C2"
    with pytest.raises(Blocked,match="V385_V386_CROSS_CLAIM_AUDIO_IN_VISUAL_PHASE"):
        finite_source(b["trace"],[9.0]*6,role,fake)


@pytest.mark.parametrize("count",(0,5,7))
def test_missing_or_extra_utterances_refuse_native_source(count):
    row,b,role,p=case()
    with pytest.raises(Blocked,match="V385_V386_SIX_PHASE_TIMELINE_REQUIRED"):
        finite_source(b["trace"],[9.0]*count,role,p)


def test_wav_segments_are_contiguous_and_not_word_timestamps():
    row,b,role,p=case()
    fake=[{"index":i,"claim_ids":[x["claim_id"]],
           "narration":x["narration"],"frame_start":i*120,
           "frames":120,"wav_samples":120000,"wav_rate":16000}
          for i,x in enumerate(p)]
    rec=align_real_wav(p,fake)
    assert len(rec)==6 and rec[-1]["frame_end_exclusive"]==720
    assert all(x["word_level_alignment"]=="NOT_MEASURED" for x in rec)
    fake[3]["frame_start"]+=1
    with pytest.raises(Blocked,match="V385_V386_VOICE_SEGMENT_CLAIM_OR_TIMELINE_DRIFT"):
        align_real_wav(p,fake)


def test_short_voice_window_blocked():
    row,b,role,p=case()
    with pytest.raises(Blocked,match="V385_V386_INSUFFICIENT_VOICED_SEMANTIC_PHASE_FRAMES"):
        finite_source(b["trace"],[2.0]*6,role,p)


def test_no_topic_specific_renderer_or_bypassed_av_validation():
    src="\n".join((ROOT/x).read_text() for x in (
        "learnflow_v3/v386_phased_affine_manim.py",
        "learnflow_v3/v386_pedagogical_speech_contract.py"))
    for forbidden in ("if case_id ==","if topic ==","linear_output_new",
                      "accelerating_new","counterfactual_physics_heldout"):
        assert forbidden not in src
    runner=(ROOT/"scripts/run_v3_86_pcm_grounded_pedagogy.py").read_text()
    for token in ("_audio","_codec_and_pixel_gates","deterministic_mux",
                  "verify_native_phases","_docker_manim","full_native_decode"):
        assert token in runner
    assert RESULT_ROI==(200,558,1080,695)
