#!/usr/bin/env python3
"""V3-57 host-only native 3-family demo: reproducible, no provider/model HTTP."""
from __future__ import annotations
import argparse,hashlib,io,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from PIL import Image,ImageChops,ImageStat
from learnflow_v3.pedagogical_storytelling_slice import (
    STEPS,FPS,WIDTH,HEIGHT,facts,plan,validate,render_native)

REG=ROOT/"benchmarks/learnflowbench/v3/v3_57_pedagogical_slice_preregister.json"
PARENT="38a8ba0c69a58ac18ad3296f6e847cbdeb6dbe91"
ORDER=("attention_reversed_query","fraction_equivalence","process_heldout_unknown")

def require(c,code):
 if not c:raise AssertionError("V357_"+code)

def check_registration():
 d=json.loads(REG.read_text())
 require(d["checkpoint"]=="V3-57" and d["parent_sha"]==PARENT and
  d["registered_before_implementation"] is True and
  d["acceptance"]["zero_model_api_calls"] and
  d["acceptance"]["no_v2_core_mods"] and
  d["acceptance"]["production"]=="BLOCKED","PREREG")
 require(tuple(x["id"] for x in d["frozen_input_cases"])==ORDER,"CASE_SET")
 for item in d["frozen_input_cases"]:
  p=plan(item["id"])
  require(tuple(item["steps"])==STEPS[p.case_id],"STAGE_CHANGE")
 require(d["frozen_input_cases"][0]["query"]==[0,1] and
         d["frozen_input_cases"][1]["initial"]==[2,3] and
         d["frozen_input_cases"][2]["outcome"]=="UNKNOWN_NOT_VERIFIED",
         "EVIDENCE_DRIFT")
 return d

def parity_with_reused_ledgers():
 # Source truth from prior V3-52 and V3-49 is authoritative where installed.
 from learnflow_v3.semantic_attention_motion import Case,facts as older_facts
 from learnflow_v3.grounded_fraction_claims import FractionTopic,ground,verify
 q=Case(topic_id="heldout_query_matches_token_b",
        query=(0,1),keys=((1,0),(0,1)),values=((1,0),(0,1)),dim=2)
 older=older_facts(q);current=facts(ORDER[0])
 for key in ("weights","context"):
  require(all(abs(a-b)<1e-9 for a,b in zip(older[key],current[key])),
          "ATTENTION_LEDGER_PARITY")
 fr=ground(FractionTopic(topic_id="v357fraction",
     numerator=2,denominator=3,factor=2,target_numerator=4,target_denominator=6))
 verify(fr)
 require(facts(ORDER[1])["same_area"] is True,"FRACTION_LEDGER_PARITY")
 require(facts(ORDER[2])["condition"]=="UNKNOWN_NOT_VERIFIED",
         "PROCESS_UNKNOWN_NOT_PRESERVED")

def probe(path):
 z=json.loads(subprocess.check_output(["ffprobe","-v","error",
    "-show_entries","stream=codec_type,codec_name,width,height,r_frame_rate",
    "-show_entries","format=duration","-of","json",str(path)],timeout=20))
 stream={x["codec_type"]:x for x in z["streams"]}
 require(stream["video"]["codec_name"]=="h264" and
    stream["video"]["width"]==WIDTH and stream["video"]["height"]==HEIGHT and
    stream["video"]["r_frame_rate"]==f"{FPS}/1" and
    stream["audio"]["codec_name"]=="aac","NATIVE_CODEC")
 return float(z["format"]["duration"])

def frame(path,sec):
 data=subprocess.check_output(["ffmpeg","-nostdin","-v","error",
  "-ss",f"{sec:.3f}","-i",str(path),"-vframes","1","-vf","scale=640:360",
  "-f","image2pipe","-vcodec","png","-"],timeout=45)
 im=Image.open(io.BytesIO(data));im.load()
 return im.convert("RGB")

def native_witnesses(path,r):
 change=[]
 for b in r["beat_receipts"][1:4]:
  st,en=b["start_s"],b["end_s"]
  begin=frame(path,st+0.12)
  end=frame(path,st+(en-st)*0.55)
  stat=ImageStat.Stat(ImageChops.difference(begin,end))
  mad=sum(stat.mean)/3
  change.append({"beat":b["beat_id"],"operation":b["operation"],
      "native_frame_mean_abs_rgb_diff":round(mad,4),
      "semantic_motion_expected":True})
 require(any(x["native_frame_mean_abs_rgb_diff"]>0.25 for x in change),
         "NO_VISIBLE_NATIVE_SEMANTIC_MOTION")
 return change

def run(output):
 reg=check_registration()
 parity_with_reused_ledgers()
 output=Path(output)
 if output.exists():raise RuntimeError("V357_FRESH_OUTPUT_REQUIRED")
 output.mkdir(parents=True)
 rows=[]
 for case in ORDER:
  receipt=render_native(plan(case),output/case)
  path=output/case/"pedagogical_slice.mp4"
  require(path.is_file() and path.stat().st_size>10000,"MEDIA_MISSING")
  digest=hashlib.sha256(path.read_bytes()).hexdigest()
  require(receipt["native_mp4_sha256"]==digest,"NATIVE_SHA")
  duration=probe(path)
  witnesses=native_witnesses(path,receipt)
  receipt["container_duration_s"]=round(duration,3)
  receipt["native_frame_witnesses"]=witnesses
  (output/case/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
  rows.append(receipt)
 result={"checkpoint":"V3-57","parent_sha":PARENT,
   "prereg_sha256":hashlib.sha256(REG.read_bytes()).hexdigest(),
   "source":"HOST_SYNTHETIC_NOT_MODEL_AUTHORED",
   "cases":rows,"technical_native_movie_count":len(rows),
   "technical_media_gate":"PASS_ON_THE_EXECUTED_HOST",
   "pedagogical_human_quality":"UNRATED_NO_GO",
   "autonomous_model_idea_generation":"NOT_TESTED",
   "word_level_alignment":"UNMEASURED",
   "fair_v355_improvement":"NOT_TESTED",
   "paid_model_calls":0,"production":"BLOCKED"}
 (output/"v357_receipt.json").write_text(json.dumps(result,indent=2)+"\n")
 return result

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--output-dir",type=Path,required=True)
 a=p.parse_args()
 print(json.dumps(run(a.output_dir),indent=2))
