#!/usr/bin/env python3
"""Fail-closed native smoke on TWO HOST TEST ONLY proposals before any paid POST."""
import argparse,copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.v364_heldout_storyboard import host_test_baseline,accept
from learnflow_v3.v364_native_array_compiler import build_comparison

def run(out):
    a=host_test_baseline()
    b=copy.deepcopy(a)
    b["narrative_designer"]["opening"]="notice_paradox"
    b["visual_thinker"]["focus"]="track_corner"
    b["visual_thinker"]["composition"]="side_by_side"
    b["motion_director"]["method"]="staggered_morph"
    b["beats"][2]["visual_focus"]="track_corner"
    accept(a);accept(b)
    r=build_comparison(a,b,out)
    assert len(r["native_mp4s"])==2
    assert r["matched_video_frame_counts"] is True
    assert r["early_to_witness_MAD"]>.25
    print("V364_NATIVE_HOST_TEST_PREFLIGHT_PASS_NO_PROVIDER_REQUESTS",
          r["native_mp4s"][0]["native_frames"],flush=True)
    return r
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    run(p.parse_args().output)
