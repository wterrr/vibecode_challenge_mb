#!/usr/bin/env python3
"""V3-22: generate actual 360p baseline and native 720p 24fps retrofit offline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from scripts.verify_v3_event_alignment import produce as render_original
from learnflow_v3.native_hd_lesson import render_hd, verify_hd
from learnflow_v3.lesson_quality import _frames


def produce(out:Path, *, source_dir:Path|None=None)->dict:
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    original=(Path(source_dir) if source_dir is not None else out/"source_v3_20")
    if source_dir is None:
        render_original(original)
    target=out/"native_hd"
    target.mkdir(parents=True,exist_ok=True)
    receipt=render_hd(source_folder=original,output_dir=target)
    video=target/"v3_22_binary_search_native_720p.mp4"
    result=verify_hd(source_folder=original,output=video,receipt=receipt)
    assert receipt["frames"]==1082
    assert receipt["width"]==1280 and receipt["height"]==720 and receipt["fps"]==24
    assert len(result["pointer_continuity"])==3
    assert receipt["publication"]=="BLOCKED"
    assert receipt["human_legibility"]=="UNMEASURED"
    assert receipt["human_learning"]=="UNMEASURED"
    # Native 720p stills from the actual compressed output, not PIL originals.
    frame_ids=[0,344,416,480,540,641,804,875,1081]
    samples=_frames(video,1280,720,frame_ids)
    from PIL import Image,ImageDraw
    sheet=Image.new("RGB",(2560,5*(720+28)),(18,18,18))
    d=ImageDraw.Draw(sheet)
    for i,(idx,image) in enumerate(zip(frame_ids,samples,strict=True)):
        x=(i%2)*1280
        y=(i//2)*748
        sheet.paste(image,(x,y))
        d.text((x+10,y+723),f"Decoded native H264 frame {idx}, t={idx/24:.3f}s",
               fill=(225,225,225))
    sheet.save(out/"v3_22_actual_native_frame_contact_sheet.jpg",quality=88)
    qa={
        "checkpoint":"V3-22","status":"NATIVE_HD_TECHNICAL_CANDIDATE",
        "source_360p_sha256":receipt["source_video_sha256"],
        "actual_720p_sha256":receipt["video_sha256"],
        "audio_adts_sha256_unchanged":receipt["audio_adts_sha256"],
        "resolution":[1280,720],"fps":24,"frames":1082,
        "semantic_utterance_count":10,
        "observed_pointer_continuity":result["pointer_continuity"],
        "max_decoded_expected_rgb_mae":result["max_decoded_expected_mae"],
        "visual_typography":"native CMU at >=32px overlay/captions",
        "word_phoneme_alignment":"UNMEASURED",
        "independent_viewer_readability":"UNMEASURED",
        "human_learning_quality":"UNMEASURED",
        "eSpeak_voice_commercial_rights":"UNVERIFIED",
        "release":"BLOCKED","provider_calls":0
    }
    (out/"v3_22_native_hd_quality_evidence.json").write_text(
        json.dumps(qa,indent=2)+"\n",encoding="utf-8")
    print("V3_22_HD_PIXELS=PASS native=1280x720 fps=24 frames=1082")
    print("V3_22_AUDIO=PASS copied_original_aac_packets=True")
    print("V3_22_EVENT_PACING=PASS apply_only_delayed_tween_and_source_continuity=True")
    print("V3_22_HUMAN_READABILITY=UNMEASURED publication=BLOCKED")
    return qa


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",required=True,type=Path)
    parser.add_argument("--source-dir",type=Path)
    arguments=parser.parse_args()
    produce(arguments.output_dir,source_dir=arguments.source_dir)
