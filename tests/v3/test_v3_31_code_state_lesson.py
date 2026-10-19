"""V3-31: original paid-model artifact, source audit and typed video-state checks."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json
import pytest
from learnflow_v3.cs_code_state_lesson import (
    ORIGINAL_MODEL_RESEARCH, ORIGINAL_MODEL_SCRIPT,
    load_pinned_receipt, consistency_audit, inspect_fixed_code,
    certified_integer_replay, build_certified_bundle, draw_code_state_frame,
)
from learnflow_v3.paid_cs_lesson import Blocked
from learnflow_v3.sequence_renderer import SequenceRenderProfile, _mean_absolute_error

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=ROOT/"reports"/"v3_31_v330_real_receipt_subset.json"
def actual_receipt():
    return load_pinned_receipt(EVIDENCE)

def test_original_research_has_three_example_conflicts():
    record=actual_receipt()
    audit=consistency_audit(record)
    assert audit["status"]=="CONFLICT" and audit["count"]==3
    assert set(i["claim_id"] for i in audit["issues"])=={"C_DEFINE","C_BIND","C_RETURN"}
    assert record["research_claims"][0]["explanation"]==ORIGINAL_MODEL_RESEARCH[0]
    assert record["script_segments"][0]["spoken_text"]==ORIGINAL_MODEL_SCRIPT[0]

def test_unrepaired_conflict_blocks_and_host_repair_is_disclosed():
    record=actual_receipt()
    with pytest.raises(Blocked,match="UNREPAIRED"):
        build_certified_bundle(ROOT,record,repair=False)
    b=build_certified_bundle(ROOT,record,repair=True)
    assert len(b["_v331_edits"])==3
    assert all(x["author"]=="HOST_ADAPTIVE_EDIT_NOT_GPT6_LUNA" for x in b["_v331_edits"])
    assert [s.spoken_text for s in b["script"].segments]==list(ORIGINAL_MODEL_SCRIPT)
    assert b["_v331_trace"][-1]["calculation"]=="3 + 2 = 5"

@pytest.mark.parametrize("mutated",[
    "def add_two(n):\n    return n*2\n\nanswer = add_two(3)",
    "def add_two(n):\n    return n+2\n\nanswer = add_two(4)",
    "def add_two(n):\n    return n-2\n\nanswer = add_two(3)",
    "def add_two(n):\n    return n+2\n\nanswer = add_two(__import__('os').system('id'))",
    "@evil\ndef add_two(n):\n    return n+2\n\nanswer = add_two(3)",
    "def add_two(n):\n    return n+2\n\nanswer = add_two(3)\nprint(answer)",
])
def test_illegal_function_ast_rejected_without_execution(mutated):
    with pytest.raises(Blocked,match="CODE_AST_NOT_CERTIFIED"):
        inspect_fixed_code(mutated)

def test_reuse_v3_07_typed_numeric_verifier():
    cert=certified_integer_replay()
    assert len(cert["numeric_code_walkthrough_sha256"])==64

def test_original_source_and_script_tampering_fail_closed(tmp_path):
    record=actual_receipt()
    for target in ("source","research","script"):
        r=deepcopy(record)
        if target=="source":r["source_certificate"]["sha256_html"]="0"*64
        elif target=="research":r["research_claims"][1]["explanation"]="Forged explanation"
        else:r["script_segments"][3]["spoken_text"]="Return eight"
        file=tmp_path/(target+".json")
        file.write_text(json.dumps(r))
        with pytest.raises(Blocked):
            load_pinned_receipt(file)

def test_all_visual_states_are_distinct_and_blackboard():
    bundle=build_certified_bundle(ROOT,actual_receipt(),repair=True)
    profile=SequenceRenderProfile(width=1280,height=720,fps=18,seconds_per_step=1.0)
    frames=[draw_code_state_frame(bundle,i,.6,profile,bundle["script"].segments[i].spoken_text) for i in range(4)]
    assert all(f.getpixel((0,0))==(0,0,0) for f in frames)
    roi=(770,218,1196,495)
    deltas=[_mean_absolute_error(a.crop(roi),b.crop(roi)) for a,b in zip(frames,frames[1:])]
    assert len(deltas)==3 and all(d>.8 for d in deltas)
