"""Research-only native compiler demonstrating observable five-role decision impact.

Uses frozen V3-62 host truth, renders only approved objects/claims, copies source
AAC bitwise. Two host TEST_ONLY candidates do not constitute model creativity.
"""
from __future__ import annotations
import io
import json
import math
import subprocess
from pathlib import Path
from hashlib import sha256
from PIL import Image,ImageDraw,ImageChops,ImageStat
from learnflow_v3.creative_pedagogical_native import (
    W,H,FPS,render_frame,scene_objects,media_probe,aac_sha,sha,decode_all,frame,
    tx,AMBER,MINT,WHITE,INK
)
from learnflow_v3.creative_pedagogical_director import CASES
from learnflow_v3.five_role_creative_admission import admit

def require(ok,code):
    if not ok:raise ValueError("V363_"+code)

def bounded_progress(decision,progress):
    require(type(progress) in (float,int) and math.isfinite(progress) and
            0<=progress<=1,"INVALID_PROGRESS")
    delay=.08 if decision["precondition_hold"]=="short" else .28
    p=max(0.,min(1.,(progress-delay)/(1-delay)))
    if decision["transformation_profile"]=="stepwise":
        return min(1.,math.floor(p*4+1e-9)/4)
    return p

def render_decision_frame(decision,act:int,progress:float):
    story=decision["story"]
    assert act in range(5)
    transformed=bounded_progress(decision,progress) if act==2 else progress
    img=render_frame(story,act,transformed)
    draw=ImageDraw.Draw(img)
    if act!=2: return img
    state=scene_objects(story,act,transformed)
    if decision["focus_mode"]=="invariant":
        message={
            CASES[0]:"INVARIANT   /   Eight outcomes remain eight",
            CASES[1]:"INVARIANT   /   Constant speed: three metres each second",
            CASES[2]:"INVARIANT   /   Four H and two O remain present"
        }[story.case_id]
        draw.rounded_rectangle((81,201,1110,253),radius=14,
                               outline=AMBER,width=3)
        tx(draw,(100,214),message,25,AMBER)
    else:
        # A deliberate moving spotlight follows only a host-certified object.
        if story.case_id==CASES[0]:
            a=state["eight_objects"]
            # Probe a remaining outcome with stable index and frozen identity.
            n=min(7,3+int(5*transformed))
            x=173+n*118+43;y=352
            require(a[n]["id"]==f"outcome_{n}","IDENTITY_DRIFT")
        elif story.case_id==CASES[1]:
            require(state["marker_id"]=="moving_marker","IDENTITY_DRIFT")
            x=175+930*state["marker_m"]/12;y=412
        else:
            atoms={a["id"]:a for a in state["atoms"]}
            require(set(atoms)=={"H0","H1","H2","H3","O0","O1"},"ATOM_DRIFT")
            x=atoms["O0"]["x"];y=atoms["O0"]["y"]
        x=round(x);y=round(y)
        draw.ellipse((x-57,y-57,x+57,y+57),outline=AMBER,width=6)
    return img

def encode_frames(decision,counts,out):
    ff=["ffmpeg","-nostdin","-y","-hide_banner","-loglevel","error",
        "-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),
        "-i","-","-an","-c:v","libx264","-preset","ultrafast","-crf","27",
        "-pix_fmt","yuv420p",str(out)]
    proc=subprocess.Popen(ff,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for i,n in enumerate(counts):
            for j in range(n):
                p=min(1.,j/max(1,int(n*.70)))
                proc.stdin.write(render_decision_frame(decision,i,p).tobytes())
        proc.stdin.close();proc.stdin=None
        err=proc.stderr.read().decode(errors="replace")
        result=proc.wait(timeout=240)
        require(result==0,"FRAME_ENCODER_FAILED_"+err[-170:])
    except BaseException:
        proc.kill();proc.wait()
        raise

def mean_diff(a,b):
    return sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3

def native_compare(source_dir:Path,out:Path,raw_candidates:tuple[bytes,bytes]):
    require(not out.exists(),"OUTPUT_ALREADY_EXISTS")
    parsed=[admit(raw) for raw in raw_candidates]
    require(parsed[0][0].case_id==parsed[1][0].case_id,"DIFFERENT_CASES")
    case=parsed[0][0].case_id
    source=source_dir/case/"causal_timeline.mp4"
    receipt_path=source_dir/case/"receipt.json"
    require(source.is_file() and receipt_path.is_file(),"MISSING_FROZEN_NATIVE_PARENT")
    receipt=json.loads(receipt_path.read_text())
    require(sha(source)==receipt["movies"]["causal_timeline"]["sha256"],
            "SOURCE_MP4_SHA_MISMATCH")
    counts=receipt["timeline"]["durations_frames"]
    require(len(counts)==5 and sum(counts)==media_probe(source)["frames"],
            "SOURCE_TIMELINE_INVALID")
    source_audio=aac_sha(source)
    out.mkdir(parents=True)
    rows=[];fulls=[]
    for i,(typed,decision) in enumerate(parsed):
        tag="candidate_"+str(i+1)
        silent=out/(tag+"_silent.mp4")
        video=out/(tag+".mp4")
        encode_frames(decision,counts,silent)
        subprocess.run(["ffmpeg","-nostdin","-y","-loglevel","error",
                        "-i",str(silent),"-i",str(source),
                        "-map","0:v:0","-map","1:a:0",
                        "-c:v","copy","-c:a","copy",str(video)],
                       timeout=120,check=True)
        md=media_probe(video)
        require(md["frames"]==sum(counts),"CANDIDATE_FRAME_MISMATCH")
        require(aac_sha(video)==source_audio,"SOURCE_AAC_MISMATCH")
        decode_all(video)
        row={"case_id":case,"candidate_index":i+1,"wire_sha256":sha256(raw_candidates[i]).hexdigest(),
             "candidate_provenance":"HOST_TEST_ONLY_NOT_LLM",
             "native_video_sha256":sha(video),"native_frames":md["frames"],
             "native_audio_sha256":source_audio,
             "visual_focus":decision["focus_mode"],
             "motion_strategy":decision["transformation_profile"],
             "has_dynamic_effect":"NOT_YET_MEASURED",
             "model_creativity":"NOT_TESTED","human_quality":"UNRATED",
             "learner_gain":"NOT_MEASURED","publication":"BLOCKED"}
        rows.append(row)
    bounds=receipt["timeline"]["beat_boundaries_s"]
    n=counts[2]
    sec=bounds[2]+(round(.48*n)+.5)/FPS
    stills=[frame(out/f"candidate_{i}.mp4",sec) for i in (1,2)]
    change=mean_diff(*stills)
    require(change>0.2,"NATIVE_DECISION_NOT_OBSERVABLE")
    for i,im in enumerate(stills,1):
        im.save(out/f"candidate_{i}_decoded_transform_frame.png")
    # Compare certified before/after snapshots of the witness, not whole-film motion score.
    for i in (1,2):
        before=frame(out/f"candidate_{i}.mp4",bounds[2]+(.12*n+.5)/FPS)
        after=frame(out/f"candidate_{i}.mp4",bounds[3]+.25)
        d=mean_diff(before,after)
        require(d>.4,"NO_MEANINGFUL_NATIVE_BEFORE_AFTER")
        rows[i-1]["native_before_after_MAD"]=round(d,4)
        rows[i-1]["has_dynamic_effect"]="VISIBLE_NOT_QUALITY"
    packet={
        "checkpoint":"V3-63","case_id":case,"parent_native_sha256":sha(source),
        "parent_native_audio_packet_sha256":source_audio,
        "native_candidate_count":2,"native_decoded_frames_each":sum(counts),
        "cross_candidate_frame_MAD_at_transform":round(change,4),
        "candidates":rows,"genuine_model_authorship":"NOT_TESTED_NO_PROVIDER_RESPONSE",
        "human_pedagogical_quality":"UNRATED","learning_gain":"NOT_MEASURED",
        "production":"BLOCKED"
    }
    (out/"v363_receipt.json").write_text(json.dumps(packet,indent=2)+"\n")
    for silent in out.glob("*_silent.mp4"):silent.unlink()
    return packet
