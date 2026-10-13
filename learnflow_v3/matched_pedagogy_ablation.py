"""V3-58 opt-in within-case motion ablation + blind review packet.

Same V3-57 approved five-beat source plan, SAME original AAC audio packets
and same real encoded video frame count; hold end-state of each beat constant.
Ablation changes timing/reveal as well as motion: it is NOT a cognitive outcome.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import csv
import io
import json
import shutil
import subprocess
from PIL import Image,ImageChops,ImageStat

from learnflow_v3.pedagogical_storytelling_slice import (
    WIDTH,HEIGHT,FPS,STEPS,plan,validate,render_image
)
from learnflow_v3.creative_manim_ablation import Blocked

VERSION="v3-58-matched-native-pedagogy-ablation-v1"
IDS=tuple(STEPS)
CRITERIA=("clarity","causal_witness","semantic_continuity","legibility","pacing")
RATINGS_FIELDS=("rater_id","case_id","clip_id",*CRITERIA,"confidence","failure_notes")
QUALITY="UNRATED_NO_EXTERNAL_HUMAN_REVIEW"


def require(test,code):
    if not test: raise Blocked("V358_"+code)

def sha(path):
    h=sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def cmd(args,timeout=240):
    return subprocess.check_output(args,timeout=timeout,stderr=subprocess.PIPE)

def probe(path):
    d=json.loads(cmd(["ffprobe","-v","error","-count_frames",
        "-show_entries","stream=codec_type,codec_name,width,height,r_frame_rate,nb_frames,nb_read_frames,duration",
        "-of","json",str(path)]))
    streams={x["codec_type"]:x for x in d["streams"]}
    v=streams["video"];a=streams["audio"]
    require(v["codec_name"]=="h264" and a["codec_name"]=="aac","MEDIA_CODEC")
    require((v["width"],v["height"],v["r_frame_rate"])==(WIDTH,HEIGHT,f"{FPS}/1"),
            "MEDIA_GEOMETRY")
    count=int(v.get("nb_read_frames") or v["nb_frames"])
    require(count>=100,"MEDIA_NOT_FULL")
    return {"video_frames":count,"video_duration_s":float(v["duration"]),
            "audio_duration_s":float(a["duration"]), "fps":FPS,
            "width":WIDTH,"height":HEIGHT,"audio_codec":"aac","video_codec":"h264"}

def aac_sha(path):
    # ADTS elementary AAC packet hash; container SHA and AAC packet hashes differ.
    data=cmd(["ffmpeg","-nostdin","-v","error","-i",str(path),"-map","0:a:0",
        "-c:a","copy","-f","adts","-"])
    return sha256(data).hexdigest()

def frame(path,sec):
    data=cmd(["ffmpeg","-nostdin","-v","error","-ss",f"{sec:.3f}",
        "-i",str(path),"-frames:v","1","-vf","scale=320:180",
        "-f","image2pipe","-vcodec","png","-"],timeout=40)
    im=Image.open(io.BytesIO(data));im.load()
    return im.convert("RGB")

def mean_diff(a,b):
    return sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3

def source_case(video,receipt):
    video=Path(video);receipt=Path(receipt)
    require(video.is_file() and receipt.is_file(),"SOURCE_MEDIA_MISSING")
    d=json.loads(receipt.read_text(encoding="utf-8"))
    case=d.get("case_id");require(case in IDS,"UNREGISTERED_CASE")
    p=plan(case);validate(p)
    require(d.get("source")=="HOST_SYNTHETIC_NOT_MODEL_AUTHORED" and
            d.get("evidence_sha256")==p.evidence_sha256 and
            d.get("zero_model_calls") is True and
            d.get("production")=="BLOCKED","SOURCE_EVIDENCE_DRIFT")
    require(d.get("native_mp4_sha256")==sha(video),"SOURCE_HASH_DRIFT")
    bounds=d.get("beat_receipts",[])
    require(len(bounds)==5 and
            [x["operation"] for x in bounds]==list(STEPS[case]),"BEAT_ORDER")
    fact=probe(video)
    receipt_frames=d["native_frames"]
    # Observed V3-57 mux uses -shortest: actual encoded movie has one fewer frame.
    require(receipt_frames-fact["video_frames"] in (0,1),
            "UNEXPECTED_RECEIPT_FRAME_DISCREPANCY")
    return p,d,fact

def render_static_control(source_video,source_receipt,out):
    out=Path(out)
    require(not out.exists(),"OUTPUT_MUST_BE_FRESH")
    p,d,fact=source_case(source_video,source_receipt)
    out.mkdir(parents=True)
    seq=["ffconcat version 1.0"]
    for i,b in enumerate(d["beat_receipts"]):
        name=f"beat_{i}.png"
        render_image(p,i,1.0).save(out/name)
        seq.extend([f"file '{name}'",f"duration {b['end_s']-b['start_s']:.9f}"])
    seq.append("file 'beat_4.png'")
    (out/"stills.ffconcat").write_text("\n".join(seq)+"\n",encoding="utf-8")
    static_video=out/"static_video_only.mp4"
    subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-f","concat",
        "-safe","0","-i",str(out/"stills.ffconcat"),"-r",str(FPS),
        "-frames:v",str(fact["video_frames"]),"-c:v","libx264",
        "-preset","veryfast","-crf","26","-pix_fmt","yuv420p",str(static_video)],
        check=True,timeout=300)
    result=out/"static_control.mp4"
    # No -shortest: the V3-57 original video had an unreported last-frame trim.
    subprocess.run(["ffmpeg","-nostdin","-v","error","-y",
        "-i",str(static_video),"-i",str(source_video),
        "-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","copy",
        "-frames:v",str(fact["video_frames"]),str(result)],check=True,timeout=80)
    other=probe(result)
    require(other["video_frames"]==fact["video_frames"],"FRAME_MATCH")
    require(abs(other["video_duration_s"]-fact["video_duration_s"])<=1/FPS,
            "TIME_MATCH")
    src_aac=aac_sha(source_video);dst_aac=aac_sha(result)
    require(src_aac==dst_aac,"AUDIO_PACKETS_DIFFER")
    # Check each beat's static end-state actually occurs in the encoded result.
    state_evidence=[]
    for i,b in enumerate(d["beat_receipts"]):
        sample=min(fact["video_duration_s"]-.12,
                   b["start_s"]+max(.3,(b["end_s"]-b["start_s"])*.52))
        decoded=frame(result,sample)
        expected=render_image(p,i,1.0).resize((320,180)).convert("RGB")
        err=mean_diff(decoded,expected)
        require(err<18,"STATIC_SCENE_NOT_RENDERED")
        state_evidence.append({"beat_index":i,"host_claim_id":p.beats[i].claim_id,
            "semantic_ref":p.beats[i].referent_id,"decoded_state_mae":round(err,4)})
    return {"checkpoint":"V3-58","case_id":p.case_id,
      "source_origin":d["source"],"host_evidence_sha256":p.evidence_sha256,
      "candidate_motion_sha256":sha(source_video),"control_static_sha256":sha(result),
      "source_receipt_frames":d["native_frames"],
      "source_actually_decoded_frames":fact["video_frames"],
      "receipt_frame_delta":d["native_frames"]-fact["video_frames"],
      "fps":FPS,"resolution":[WIDTH,HEIGHT],
      "source_audio_packet_sha256":src_aac,"control_audio_packet_sha256":dst_aac,
      "source_duration_s":fact["video_duration_s"],
      "control_duration_s":other["video_duration_s"],
      "static_beat_state_checks":state_evidence,
      "intervention":"END_STATE_HELD_WITHIN_BEAT",
      "caveat":"Static control reveals end-state earlier; no learner causal outcome inferred.",
      "native_word_alignment":"UNMEASURED","model_authoring":"NOT_TESTED",
      "quality":QUALITY,"production":"BLOCKED",
      "source_video":str(source_video),"control_video":str(result)}

def make_review_packet(cases,out,parent_sha):
    out=Path(out);require(not out.exists(),"PACKET_EXISTS")
    out.mkdir(parents=True)
    key={"checkpoint":"V3-58","parent_sha":parent_sha,
         "quality":QUALITY,"case_treatments":{}}
    rows=[]
    for c in cases:
        cid=c["case_id"]
        # In a matched within-case pair, positions are deterministic and hidden
        # from the reviewer. Must NOT be characterized as double-blind.
        order=int(sha256((parent_sha+cid).encode()).hexdigest()[0],16)%2
        source=Path(c["source_video"]);control=Path(c["control_video"])
        treatments=["motion","static"] if order else ["static","motion"]
        mapping={"motion":source,"static":control}
        key["case_treatments"][cid]={}
        for j,treatment in enumerate(treatments):
            clip_id=f"{cid}_"+("A" if j==0 else "B")
            name=clip_id+".mp4"
            shutil.copyfile(mapping[treatment],out/name)
            key["case_treatments"][cid][name]={
              "treatment":treatment,"sha256":sha(out/name)}
            rows.append({"rater_id":"","case_id":cid,"clip_id":name,
                **{criterion:"" for criterion in CRITERIA},
                "confidence":"","failure_notes":""})
    with (out/"blank_review.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=RATINGS_FIELDS)
        writer.writeheader();writer.writerows(rows)
    (out/"REVIEWER_INSTRUCTIONS.txt").write_text(
      "V3-58 independent quality review. Clip IDs are position labels, not quality ranks.\n"
      "Rate each of 6 clips (3 topic-pairs) on clarity, causal witness, semantic continuity,\n"
      "legibility and pacing (1=very poor to 5=excellent), or leave blank if unratable.\n"
      "Record observations, clip+seconds, and whether an early reveal harms explanation.\n"
      "Do not open the admin key until all ratings are locked.\n"
      "No ratings have been collected by the project team; these are blank fields.\n"
      "Audio, length, topic and host facts are held constant within each pair;\n"
      "only intra-beat motion/reveal changes, so this is not pure motion-only causality.\n",
      encoding="utf-8")
    return key

def evaluate_submissions(rows,key,minimum_raters=3):
    if not rows:
        return {"review_quality":"UNRATED_NO_EXTERNAL_HUMAN_REVIEW",
            "independent_reviewers":0,"human_learning_effect":"NOT_MEASURED",
            "quality_gate":"NO_GO_NO_REVIEWERS"}
    seen=set();expected={(case,clip) for case,data in key["case_treatments"].items()
                for clip in data}
    review_ids=set()
    for r in rows:
        rat=r.get("rater_id","").strip()
        require(bool(rat),"REVIEWER_ID_MISSING")
        pair=(r.get("case_id"),r.get("clip_id"))
        require(pair in expected and (rat,pair) not in seen,"REVIEW_ID_OR_CASE_INVALID")
        seen.add((rat,pair));review_ids.add(rat)
        for criterion in CRITERIA:
            value=r.get(criterion,"")
            require(value=="" or str(value) in ("1","2","3","4","5"),
                "INVALID_RATING")
    for rat in review_ids:
        require({pair for reviewer,pair in seen if reviewer==rat}==expected,
                "INCOMPLETE_REVIEW_PACKET")
    if len(review_ids)<minimum_raters:
        return {"review_quality":"INSUFFICIENT_INDEPENDENT_REVIEWERS",
            "independent_reviewers":len(review_ids),"human_learning_effect":"NOT_MEASURED",
            "quality_gate":"NO_GO_NO_COMPLETE_PANEL"}
    return {"review_quality":"SUBMITTED_RATINGS_REQUIRE_BLIND_AUDIT",
        "independent_reviewers":len(review_ids),"human_learning_effect":"NOT_MEASURED",
        "quality_gate":"REVIEW_DATA_AVAILABLE_NOT_CAUSAL_LEARNING_PROOF"}
