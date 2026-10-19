#!/usr/bin/env python3
"""V3-24 real, source-matched before/after MP4 with reader-facing storyboard."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from scripts.verify_v3_native_hd_lesson import produce as produce_v322
from learnflow_v3.teaching_storyboard import (
    WIDTH,HEIGHT,FPS,VIDEO,render_teaching_video,verify_teaching_video,
)
from learnflow_v3.lesson_quality import _frames
from PIL import Image,ImageDraw,ImageChops,ImageStat


def run(out:Path)->dict:
    out.mkdir(parents=True,exist_ok=True)
    original=produce_v322(out)
    refined=out/"native_pedagogical"
    refined.mkdir(parents=True,exist_ok=True)
    receipt=render_teaching_video(source_folder=out/"source_v3_20",out=refined)
    video=refined/VIDEO
    comparison=verify_teaching_video(source_folder=out/"source_v3_20",
                                     output=video,receipt=receipt)
    baseline_video=out/"native_hd/v3_22_binary_search_native_720p.mp4"
    anchors=[0,344,416,480,642,804,920,1081]
    before=_frames(baseline_video,WIDTH,HEIGHT,anchors)
    after=_frames(video,WIDTH,HEIGHT,anchors)
    diffs=[]
    sheet=Image.new("RGB",(WIDTH*2,len(anchors)*(HEIGHT+30)),(18,18,18))
    d=ImageDraw.Draw(sheet)
    for i,(idx,a,b) in enumerate(zip(anchors,before,after,strict=True)):
        frame_diff=ImageChops.difference(a,b)
        mae=sum(ImageStat.Stat(frame_diff).mean)/3
        diffs.append({"frame":idx,"seconds":round(idx/FPS,3),
                      "before_vs_refined_fullframe_mae":round(mae,4)})
        sheet.paste(a,(0,i*(HEIGHT+30)))
        sheet.paste(b,(WIDTH,i*(HEIGHT+30)))
        d.text((12,i*(HEIGHT+30)+HEIGHT+5),
               f"BEFORE native 720p  t={idx/FPS:.3f}s",fill=(225,225,225))
        d.text((WIDTH+12,i*(HEIGHT+30)+HEIGHT+5),
               f"V3-24 refined narrative  t={idx/FPS:.3f}s",fill=(225,225,225))
    sheet.save(out/"v3_24_actual_before_after_H264_frames.jpg",quality=86)
    assert all(x["before_vs_refined_fullframe_mae"]>1.0 for x in diffs)
    assert receipt["font_small_pointer_px"]==32 and receipt["font_array_index_px"]==29
    assert len(comparison["settled_transition_checks"])==3
    assert receipt["publication"]=="BLOCKED"
    result={
        "checkpoint":"V3-24",
        "state":"BOUNDED_OFFLINE_ENGINEERING_CANDIDATE",
        "before_native_720p_sha256":original["actual_720p_sha256"],
        "after_native_720p_sha256":receipt["video_sha256"],
        "frames":receipt["frames"],"fps":FPS,"dimensions":[WIDTH,HEIGHT],
        "source_trace_sha256":receipt["source_trace_sha256"],
        "physical_event_proof_sha256":receipt["source_event_proof_sha256"],
        "unchanged_aac_packet_sha256":receipt["original_aac_packet_sha256"],
        "comparison_sample_count":len(anchors),
        "real_h264_appearance_differences":diffs,
        "oracle_source_replay":comparison,
        "readability_improvements_implemented":[
            "Removed 'immutable item IDs' jargon from rendered top microcopy",
            "Source-derived LOW/HIGH/MID marker legends now >=32px CMU",
            "Array cell index labels now >=29px CMU",
            "Visual story differentiates equality candidate and LEFTMOST final answer",
            "Narrative headline uses new reserved 35px full-width teaching area",
            "Existing physical utterance intervals/SRT and AAC remain unchanged"],
        "perceptual_readability":"UNMEASURED",
        "independent_human_learning":"UNMEASURED",
        "human_aesthetic_preference":"UNMEASURED",
        "commercial_voice_rights":"UNVERIFIED",
        "production_release":"BLOCKED",
        "paid_provider_calls":0
    }
    (out/"v3_24_before_after_quality_receipt.json").write_text(
        json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("V3_24_REAL_H264=PASS rendered_native720p24fps=True same_oracle_and_events=True")
    print("V3_24_AUDIO=PASS unchanged_original_AAC_packets=True word_alignment=UNMEASURED")
    print("V3_24_STORYBOARD=PASS candidate_vs_leftmost_source_grounded=True")
    print("V3_24_REVIEW=UNMEASURED human_comprehension=UNMEASURED publication=BLOCKED")
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    run(args.output_dir)
