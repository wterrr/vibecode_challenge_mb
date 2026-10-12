#!/usr/bin/env python3
"""V3-46 reproducible two-family real-pixel baseline/updated quality benchmark.

Only local synthetic data; no external model; human rubric intentionally UNRATED.
Uses the V3-45 fully certified native renderer and exact-frame physical audio
mux. Comparisons keep the same model-facing JSON, narration and beat clock.
All output remains host-curated: never claim AI-authored or education PASS.
"""
from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import wave

import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.semantic_scene_offline_fixtures import fixture_cases
from learnflow_v3.semantic_scene_wire import decode_model_facing_scene
from learnflow_v3.visual_quality_system import style_receipt,safe_rectangles
from scripts.run_v3_45_semantic_offline import run as render_two_families

REGISTRATION="benchmarks/learnflowbench/v3/v3_46_visual_quality_preregister.json"
ORIGINAL_RUN=38198567269
FAMILIES={"v345-synthetic-fractions":"fraction_equivalence",
          "v345-synthetic-process":"ordered_process"}
RATINGS=("composition","typography","semantic_clarity","motion_pacing",
         "perceptual_polish","narration_coherence")


def _sha(path):
    return sha256(path.read_bytes()).hexdigest()


def _probe(path):
    r=subprocess.run(["ffprobe","-v","error","-show_streams","-of","json",str(path)],
                     capture_output=True,text=True,timeout=30)
    if r.returncode:
        raise Blocked("V346_NATIVE_PROBE_FAILURE")
    return json.loads(r.stdout)["streams"]


def _samples(root):
    # The V3-44 physical sampler inserts +3 frames of WAV padding per beat.
    beats=[]
    for i in range(4):
        wav=root/f"beat_{i}.wav"
        if not wav.is_file():raise Blocked("V346_MISSING_PHYSICAL_BEAT")
        with wave.open(str(wav),"rb") as w:
            import math
            beats.append(math.ceil(w.getnframes()/w.getframerate()*15)+3)
    starts=[0,beats[0],sum(beats[:2]),sum(beats[:3])]
    indices=[start+round(frames*ratio) for start,frames in zip(starts,beats)
             for ratio in (.15,.50,.82)]
    return beats,indices


def _frames(path,indices):
    # Decode independently authenticated H264 pixels, preserve indices, and
    # never substitute source Manim object metadata for rendered evidence.
    if not path.is_file():raise Blocked("V346_MISSING_VIDEO")
    predicate="+".join(f"eq(n\\,{i})" for i in indices)
    p=subprocess.run(["ffmpeg","-nostdin","-hide_banner","-v","error",
                      "-i",str(path),"-vf",
                      f"select={predicate},scale=320:180",
                      "-vsync","0","-f","rawvideo","-pix_fmt","rgb24","-"],
                     capture_output=True,timeout=120)
    n=320*180*3
    if p.returncode or len(p.stdout)!=n*len(indices):
        raise Blocked("V346_MISSING_DECODED_BENCHMARK_FRAME")
    return np.frombuffer(p.stdout,dtype=np.uint8).reshape(len(indices),180,320,3)


def _descriptors(frames):
    light=np.max(frames,axis=3)>70
    occupancy=np.mean(light,axis=(1,2))
    activity=np.mean(np.abs(np.diff(frames.astype(np.int16),axis=0)),axis=(1,2,3))
    # Bright foreground must never be cropped by a 2% frame perimeter.
    band=np.zeros((180,320),dtype=bool)
    band[:5,:]=True;band[-5:,:]=True;band[:,:6]=True;band[:,-6:]=True
    bright_borders=np.sum(light & band[None,:,:],axis=(1,2))
    return {"sample_count":int(len(frames)),
            "foreground_occupancy_mean":round(float(np.mean(occupancy)),5),
            "foreground_occupancy_min":round(float(np.min(occupancy)),5),
            "frame_sample_mean_absolute_delta":round(float(np.mean(activity)),4),
            "low_change_sample_fraction":round(float(np.mean(activity<1.5)),4),
            "bright_boundary_pixel_max":int(np.max(bright_borders)),
            "sample_index_note":"three beat-relative frames per narrated beat; sparse sample cannot establish continuous motion quality"}


def _sheet(old,new,indices,destination,family):
    pad=12;cellw=640;cellh=205
    sheet=Image.new("RGB",(4*cellw,3*cellh),(245,245,246))
    drawer=ImageDraw.Draw(sheet)
    for i,(o,n,idx) in enumerate(zip(old,new,indices)):
        x=i%4*cellw
        y=i//4*cellh
        sheet.paste(Image.fromarray(o),(x+2,y+18))
        sheet.paste(Image.fromarray(n),(x+322,y+18))
        drawer.text((x+5,y+1),f"{family}: beat {i//3+1}, sample {i%3+1} / frame {idx}",
                    fill=(15,20,27))
        drawer.text((x+4,y+183),"BEFORE / V3-45",fill=(28,50,70))
        drawer.text((x+324,y+183),"AFTER / V3-46",fill=(28,50,70))
    sheet.save(destination,quality=91)
    return _sha(destination)


def _rubric(out):
    rubric=out/"v3_46_BLIND_HUMAN_REVIEW_UNRATED.csv"
    with rubric.open("w",newline="",encoding="utf-8") as fp:
        writer=csv.writer(fp)
        writer.writerow(("fixture","dimension","baseline_score_1to5","v346_score_1to5",
                         "blind_reviewer_id","frame_timestamp_evidence","review_notes",
                         "review_status"))
        for fixture in FAMILIES:
            for dimension in RATINGS:
                writer.writerow((fixture,dimension,"","","","","","AWAITING_INDEPENDENT_HUMAN"))
    return rubric


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--baseline-dir",required=True,type=Path)
    parser.add_argument("--output-dir",required=True,type=Path)
    args=parser.parse_args()
    registration=json.loads((ROOT/REGISTRATION).read_text())
    if (registration.get("checkpoint")!="V3-46" or
        not registration.get("registered_before_implementation") or
        registration.get("model_http_calls")!=0 or
        registration.get("parent_sha")!="646a82c021b17400aafa1dfd30a0a157c930ec10"):
        raise Blocked("V346_PREREGISTRATION_DRIFT")
    if args.output_dir.exists():
        raise Blocked("V346_OUTPUT_MUST_NOT_ALREADY_EXIST")
    args.output_dir.mkdir(parents=True)
    try:
        render_two_families(ROOT,args.output_dir,visual_quality=True)
        facts=fixture_cases()
        items=[]
        for fixture,family in FAMILIES.items():
            old=args.baseline_dir/fixture/"offline_host_semantic_with_audio.mp4"
            oldreceipt=args.baseline_dir/fixture/"offline_case_receipt.json"
            newdir=args.output_dir/fixture
            new=newdir/"offline_host_semantic_with_audio.mp4"
            newreceipt=json.loads((newdir/"offline_case_receipt.json").read_text())
            if not oldreceipt.is_file() or not old.is_file():
                raise Blocked("V346_IMMUTABLE_BASELINE_MISSING")
            previous=json.loads(oldreceipt.read_text())
            if (_sha(old)!=previous["output_video_sha256"] or
                _sha(new)!=newreceipt["output_video_sha256"] or
                previous["input_wire_sha256"]!=newreceipt["input_wire_sha256"] or
                previous["origin"]!="SYNTHETIC_OFFLINE_JSON_MODEL_FACING_NOT_LIVE_MODEL"):
                raise Blocked("V346_SOURCE_OR_VIDEO_PROVENANCE_DRIFT")
            if fixture=="v345-synthetic-fractions" and _sha(old)!=registration["source_sha256"]["fraction"]:
                raise Blocked("V346_FROZEN_FRACTION_BASELINE_SHA_DRIFT")
            oldstreams,newstreams=_probe(old),_probe(new)
            for streams in (oldstreams,newstreams):
                v=next(x for x in streams if x["codec_type"]=="video")
                a=next(x for x in streams if x["codec_type"]=="audio")
                if (v.get("codec_name")!="h264" or a.get("codec_name")!="aac" or
                    v.get("r_frame_rate")!="15/1" or
                    (v.get("width"),v.get("height"))!=(1280,720)):
                    raise Blocked("V346_NATIVE_STREAM_CONTRACT_DRIFT")
            beats,indices=_samples(newdir)
            if len(indices)!=12:raise Blocked("V346_MISSING_MATCHED_FRAME_SCHEDULE")
            for streams in (oldstreams,newstreams):
                video=next(x for x in streams if x["codec_type"]=="video")
                if int(video["nb_frames"])!=sum(beats):
                    raise Blocked("V346_NARRATION_FRAME_BUDGET_DRIFT")
            scene=decode_model_facing_scene(facts[fixture])
            geometry=safe_rectangles(family,scene.graphics)
            oldframes,newframes=_frames(old,indices),_frames(new,indices)
            olddesc,newdesc=_descriptors(oldframes),_descriptors(newframes)
            if newdesc["bright_boundary_pixel_max"]>10:
                raise Blocked("V346_VISIBLE_CONTENT_CLIPPED_AT_FRAME_EDGE")
            if newdesc["foreground_occupancy_min"]<.001:
                raise Blocked("V346_UNEXPECTED_NEAR_BLANK_FRAME")
            if newdesc["frame_sample_mean_absolute_delta"]<1:
                raise Blocked("V346_STATIC_MOVIE_OR_EMPTY_EVENT_COVERAGE")
            pairfile=args.output_dir/(fixture+"_before_after_12_timelines.jpg")
            contactsha=_sheet(oldframes,newframes,indices,pairfile,family)
            items.append({
              "fixture":fixture,"family":family,
              "old_mp4_sha256":_sha(old),"new_mp4_sha256":_sha(new),
              "physical_beat_frames":beats,"sampled_frame_indices":indices,
              "input_wire_sha256":previous["input_wire_sha256"],
              "source_narration_unmodified":True,
              "host_scene_graph_safe_area":geometry,
              "baseline_measured":olddesc,"updated_measured":newdesc,
              "side_by_side_contact":pairfile.name,
              "contact_sha256":contactsha,
              "native_media_technical_status":"PASS",
              "human_visual_quality_status":"AWAITING_INDEPENDENT_HUMAN_REVIEW",
              "claim_about_video_being_better":"NOT_ESTABLISHED_BY_PIXEL_METRICS"
            })
        rubric=_rubric(args.output_dir)
        output={"checkpoint":"V3-46",
                "status":"NATIVE_VISUAL_LAYOUT_GATES_PASS_HUMAN_VISUAL_QUALITY_UNRATED",
                "source_run":ORIGINAL_RUN,
                "same_audio_beats_and_model_facing_wire":True,
                "rubric_file":rubric.name,
                "rubric_scores":None,
                "visual_style":style_receipt(),
                "comparisons":items,
                "model_requests":0,"production":"BLOCKED",
                "model_authorship":"SYNTHETIC_HOST_TEST_ONLY",
                "educational_quality":"NOT_CERTIFIED",
                "generalization":"ONLY_TWO_BOUNDED_FAMILIES",
                "no_human_reviews_fabricated":True}
        (args.output_dir/"v3_46_visual_quality_receipt.json").write_text(
          json.dumps(output,indent=2)+"\n")
        print("V3_46=NATIVE_LAYOUT_QA_PASS_HUMAN_VISUAL_QUALITY_PENDING",flush=True)
    except Exception:
        (args.output_dir/"v3_46_BLOCKED_NOT_CERTIFIED.txt").write_text(
            "V3-46 blocked; no successful visual quality certification\n")
        raise

if __name__=="__main__":
    main()
