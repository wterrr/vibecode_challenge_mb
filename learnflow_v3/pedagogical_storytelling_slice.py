"""V3-57: finite host-owned semantic-teaching vertical slice, NOT LLM creativity.

Host-calculated fraction and QKV proofs; UNKNOWN process gate. Original
three native MP4s are locally produced with this bounded Pillow/espeak/FFmpeg
pipeline, not 3B1B media. No provider API, arbitrary Python or production use.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from fractions import Fraction
from hashlib import sha256
import json,math,subprocess,wave,shutil
from PIL import Image,ImageDraw,ImageFont

WIDTH,HEIGHT,FPS=1280,720,15
BLACK=(9,11,18);WHITE=(236,239,244);SOFT=(160,173,191)
CYAN=(75,214,209);AMBER=(244,183,75);GREEN=(134,213,140)
STEPS={
 "attention_reversed_query":("QUESTION_HOLD","SCORE_SELECTION","SOFTMAX_NORMALIZATION","CONTENT_TRANSPORT","CLOSURE"),
 "fraction_equivalence":("QUESTION_HOLD","AREA_PARTITION","SUBDIVIDE","EQUIVALENCE_LINK","CLOSURE"),
 "process_heldout_unknown":("QUESTION_HOLD","STATE_SETUP","STATE_TRANSITION","CONDITION_PROBE","CLOSURE")}
CLAIMS={
 "attention_reversed_query":("A1","A2","A3","A4","A4"),
 "fraction_equivalence":("F1","F1","F2","F3","F3"),
 "process_heldout_unknown":("P1","P1","P2","P3","P3")}
WORDS={
 "attention_reversed_query":(
 "How can the query select the right source of context?",
 "Compare each key with the query. The second score is greater.",
 "Apply softmax. Both weights add up to one, not two.",
 "Transport each value in proportion to its relevance weight.",
 "The contextual result favors the second value. The mathematics, not the colors, determines this."),
 "fraction_equivalence":(
 "Can two thirds become four sixths without changing the amount?",
 "We start with two of three equal parts shaded.",
 "Split each original part in two. Count four shaded parts out of six.",
 "The area stays constant because we subdivided the same whole.",
 "Two thirds and four sixths are equivalent. The shared area is our witness."),
 "process_heldout_unknown":(
 "When can a process claim its condition was satisfied?",
 "First, preserve each state and its directed connections.",
 "Follow the transition to the decision point without changing its identity.",
 "This condition has not been verified. We cannot label it pass or fail.",
 "Keep the outcome unknown until independent condition evidence arrives.")}
REFERENT={"attention_reversed_query":"context_token_b",
 "fraction_equivalence":"same_whole","process_heldout_unknown":"condition_gate"}

@dataclass(frozen=True)
class Beat:
 index:int
 operation:str
 claim_id:str
 referent_id:str
 narration:str
 witness_type:str

@dataclass(frozen=True)
class Plan:
 case_id:str
 evidence_sha256:str
 beats:tuple[Beat,...]
 origin:str="HOST_SYNTHETIC_NOT_MODEL_AUTHORED"

def hash_obj(o):
 return sha256(json.dumps(o,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def facts(case_id):
 if case_id=="attention_reversed_query":
  q=(0,1);keys=((1,0),(0,1));values=((1,0),(0,1))
  scores=[sum(a*b for a,b in zip(q,k))/math.sqrt(2) for k in keys]
  e=[math.exp(x-max(scores)) for x in scores]
  weights=[x/sum(e) for x in e]
  context=[sum(weights[i]*values[i][j] for i in range(2)) for j in range(2)]
  assert weights[1]>weights[0] and abs(sum(weights)-1)<1e-12
  return {"query":q,"keys":keys,"values":values,"scores":scores,"weights":weights,"context":context}
 if case_id=="fraction_equivalence":
  assert Fraction(2,3)==Fraction(4,6)
  return {"source":(2,3),"target":(4,6),"factor":2,"same_area":True}
 if case_id=="process_heldout_unknown":
  return {"nodes":("START","ACTION","CHECK"),"edges":(("START","ACTION"),("ACTION","CHECK")),
   "condition":"UNKNOWN_NOT_VERIFIED","success_claim":False}
 raise ValueError("V357_UNSUPPORTED_FAMILY")

def plan(case_id):
 ev=facts(case_id)
 beats=tuple(Beat(i,op,CLAIMS[case_id][i],REFERENT[case_id],WORDS[case_id][i],
  "STATIC_COMPARISON" if i==0 else "NATIVE_SEMANTIC_TRANSFORMATION")
  for i,op in enumerate(STEPS[case_id]))
 result=Plan(case_id,hash_obj(ev),beats)
 validate(result)
 return result

def validate(p):
 if not isinstance(p,Plan) or p.origin!="HOST_SYNTHETIC_NOT_MODEL_AUTHORED":
  raise ValueError("V357_HOST_ONLY_PLAN")
 if p.case_id not in STEPS or p.evidence_sha256!=hash_obj(facts(p.case_id)):
  raise ValueError("V357_EVIDENCE_DRIFT")
 if len(p.beats)!=5 or tuple(b.operation for b in p.beats)!=STEPS[p.case_id]:
  raise ValueError("V357_BEAT_ORDER")
 for i,b in enumerate(p.beats):
  if (b.index!=i or b.claim_id!=CLAIMS[p.case_id][i] or
      b.referent_id!=REFERENT[p.case_id] or b.narration!=WORDS[p.case_id][i] or
      b.witness_type!=("STATIC_COMPARISON" if i==0 else "NATIVE_SEMANTIC_TRANSFORMATION")):
   raise ValueError("V357_UNGROUNDED_BEAT")
 return facts(p.case_id)

def font(n):
 for path in ("/usr/share/fonts/truetype/cmu/cmunrm.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
  if Path(path).is_file():return ImageFont.truetype(path,n)
 return ImageFont.load_default()

def text(d,xy,s,n=27,color=WHITE,anchor=None):
 d.text(xy,s,font=font(n),fill=color,anchor=anchor)

def render_image(p,idx,progress):
 ev=validate(p);progress=max(0.,min(1.,progress))
 frame=Image.new("RGB",(WIDTH,HEIGHT),BLACK);d=ImageDraw.Draw(frame)
 heading={"attention_reversed_query":"Attention: relevance to context",
          "fraction_equivalence":"Fractions: preserve the same whole",
          "process_heldout_unknown":"Process: evidence before a verdict"}[p.case_id]
 text(d,(74,48),"LEARNFLOW   /   EVIDENCE-BOUND TEACHING",19,CYAN)
 text(d,(74,92),heading,42)
 text(d,(1175,57),f"{idx+1:02d} / 05",23,SOFT,anchor="ra")
 d.line((74,159,1206,159),fill=(61,65,77),width=2)
 words=p.beats[idx].narration.split();lines=[];current=""
 for word in words:
  new=(current+" "+word).strip()
  if d.textbbox((0,0),new,font=font(23))[2]>1120 and current:
   lines.append(current);current=word
  else:current=new
 if current:lines.append(current)
 if len(lines)>2:raise ValueError("V357_NARRATION_OVERFLOW")
 for k,line in enumerate(lines):text(d,(74,592+31*k),line,23)
 text(d,(74,653),f"CLAIM {p.beats[idx].claim_id}  |  REF {p.beats[idx].referent_id}  |  {p.beats[idx].operation}",17,SOFT)
 for j in range(5):
  x=74+j*232
  d.rounded_rectangle((x,686,x+205,693),radius=3,fill=CYAN if j<=idx else (45,49,62))
 if p.case_id=="fraction_equivalence":
  n=3 if idx<=1 else 6
  x0,y0,x1,y1=160,255,1115,425
  d.rounded_rectangle((x0-10,y0-10,x1+10,y1+10),radius=22,outline=SOFT,width=2)
  width=(x1-x0)/n
  for j in range(n):
   left=int(x0+j*width);right=int(x0+(j+1)*width)-3
   d.rectangle((left,y0,right,y1),fill=CYAN if j<(2 if n==3 else 4) else (37,46,62))
  if idx==2:
   for half in range(1,6,2):
    x=int(x0+half*(x1-x0)/6)
    d.line((x,y0,x,y0+(y1-y0)*progress),fill=AMBER,width=7)
  if idx>=3:d.line((x0,448,x0+int((x1-x0)*(progress if idx==3 else 1)),448),fill=GREEN,width=5)
  text(d,(635,483),"2 / 3" if idx<=1 else "4 / 6",46,anchor="mm")
  if idx>=3:text(d,(635,548),"Same shaded area — equal fraction",25,GREEN,anchor="mm")
  if idx==0:text(d,(635,211),"What could change without changing the whole?",25,AMBER,anchor="mm")
 elif p.case_id=="attention_reversed_query":
  weights=ev["weights"];scores=ev["scores"];ctx=ev["context"]
  for x,s,col in ((270,"QUERY [0,1]",CYAN),(635,"KEY A [1,0]",SOFT),(1000,"KEY B [0,1]",AMBER)):
   d.rounded_rectangle((x-146,235,x+146,314),outline=col,radius=12,width=3)
   text(d,(x,273),s,25,col,anchor="mm")
  if idx>=1:
   d.line((415,278,488,278),fill=SOFT,width=4)
   d.line((785,278,851,278),fill=AMBER,width=4)
   for y,val,title,col,scale in (
       (365,scores[0],f"score A = {scores[0]:.3f}",SOFT,0.01),
       (441,scores[1],f"score B = {scores[1]:.3f}",AMBER,progress if idx==1 else 1)):
    x=325;w=630
    d.rounded_rectangle((x,y,x+w,y+46),radius=12,outline=(83,92,111),width=2)
    fw=int(max(0,min(1,val*scale))*w)
    if fw:d.rounded_rectangle((x,y,x+fw,y+46),radius=12,fill=col)
    text(d,(x,y-42),title,24,SOFT)
  if idx>=2:
   text(d,(110,380),f"w(A) = {weights[0]:.3f}",22,CYAN)
   text(d,(110,456),f"w(B) = {weights[1]:.3f}",22,AMBER)
   d.ellipse((957,446,997,486),fill=AMBER)
   if idx==2:
    d.rounded_rectangle((390,516,910,535),outline=SOFT,radius=7,width=2)
    width=max(1,int(520*weights[1]*progress))
    d.rounded_rectangle((390,516,390+width,535),radius=7,fill=AMBER)
  if idx==3:d.line((360,510,360+int(570*progress),510),fill=GREEN,width=9)
  if idx>=3:text(d,(670,545),f"context = [{ctx[0]:.3f}, {ctx[1]:.3f}]",29,GREEN,anchor="mm")
  if idx==0:text(d,(640,526),"Which value will carry more information?",25,AMBER,anchor="mm")
 else:
  nodes=(("START",230),("ACTION",640),("CHECK",1050))
  for j,(name,x) in enumerate(nodes):
   color=(GREEN if idx>=2 and j==1 else CYAN if j==0 else
          AMBER if j==2 and idx>=3 else (55,67,86))
   d.rounded_rectangle((x-130,283,x+130,393),radius=24,fill=color)
   text(d,(x,338),name,31,BLACK,anchor="mm")
   if j<2:d.line((x+140,337,nodes[j+1][1]-141,337),fill=SOFT,width=5)
  if idx==2:
   x=int(220+390*progress)
   d.line((230,426,x,426),fill=GREEN,width=14)
   d.ellipse((x-15,406,x+35,456),fill=GREEN)
  if idx==3:
   d.arc((915-int(75*progress),255-int(50*progress),1185+int(75*progress),421+int(50*progress)),0,360,fill=AMBER,width=6)
  if idx>=3:text(d,(635,482),"Outcome: UNKNOWN, not PASS or FAIL",29,AMBER,anchor="mm")
  elif idx==0:text(d,(635,490),"What evidence would be needed at CHECK?",26,AMBER,anchor="mm")
 return frame

def speak(s,path):
 tts=shutil.which("espeak-ng") or shutil.which("espeak")
 if not tts:raise RuntimeError("V357_NATIVE_TTS_MISSING")
 subprocess.run([tts,"-s","168","-v","en","-w",str(path),s],
   check=True,timeout=30,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 with wave.open(str(path),"rb") as w:
  params=(w.getnchannels(),w.getsampwidth(),w.getframerate())
  pcm=w.readframes(w.getnframes())
 if params[0]!=1 or params[1]!=2:raise ValueError("V357_TTS_FORMAT")
 return pcm,params

def render_native(p,out):
 validate(p);out=Path(out)
 if out.exists():raise ValueError("V357_FRESH_OUTPUT_REQUIRED")
 out.mkdir(parents=True)
 parts=[];counts=[];params0=None;timings=[]
 for i,b in enumerate(p.beats):
  pcm,params=speak(b.narration,out/f"beat_{i}.wav")
  if params0 is not None and params!=params0:raise ValueError("V357_TTS_FORMAT_DRIFT")
  params0=params
  samples=len(pcm)//2;pad=round(params[2]*0.55)
  parts.append(pcm+b"\x00\x00"*pad)
  counts.append(max(25,round((samples/params[2]+0.55)*FPS)))
 audio=out/"host_speech.wav"
 with wave.open(str(audio),"wb") as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(params0[2])
  w.writeframes(b"".join(parts))
 raw=out/"frames_only.mp4"
 cmd=["ffmpeg","-nostdin","-y","-hide_banner","-loglevel","error",
      "-f","rawvideo","-pix_fmt","rgb24","-s",f"{WIDTH}x{HEIGHT}",
      "-r",str(FPS),"-i","-","-an","-c:v","libx264",
      "-preset","ultrafast","-crf","27","-pix_fmt","yuv420p",str(raw)]
 with subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE) as proc:
  for i,frames in enumerate(counts):
   for j in range(frames):
    t=min(1.0,j/max(1,int(frames*.58)))
    proc.stdin.write(render_image(p,i,t).tobytes())
   timings.append({"beat_id":f"{p.case_id}_{i}",
     "operation":p.beats[i].operation,"claim_id":p.beats[i].claim_id,
     "referent_id":p.beats[i].referent_id,
     "start_s":round(sum(counts[:i])/FPS,3),
     "end_s":round(sum(counts[:i+1])/FPS,3),
     "narration_segment_audio_is_synthetic":True,
     "word_level_alignment":"UNMEASURED"})
  proc.stdin.close();proc.stdin=None
  err=proc.stderr.read().decode(errors="replace");code=proc.wait()
  if code:raise RuntimeError("V357_FFMPEG_FRAMES_FAILED "+err[-500:])
 dest=out/"pedagogical_slice.mp4"
 subprocess.run(["ffmpeg","-nostdin","-y","-hide_banner","-loglevel","error",
  "-i",str(raw),"-i",str(audio),"-c:v","copy","-c:a","aac",
  "-b:a","128k","-shortest",str(dest)],check=True,timeout=90)
 digest=sha256(dest.read_bytes()).hexdigest()
 receipt={"checkpoint":"V3-57","case_id":p.case_id,
 "source":"HOST_SYNTHETIC_NOT_MODEL_AUTHORED","evidence_sha256":p.evidence_sha256,
 "native_mp4_sha256":digest,"native_frames":sum(counts),"expected_fps":FPS,
 "expected_resolution":[WIDTH,HEIGHT],"beat_receipts":timings,
 "rendered_native_movie":str(dest),"zero_model_calls":True,
 "creative_quality":"UNRATED","learner_effect":"NOT_MEASURED",
 "speech_word_alignment":"UNMEASURED","production":"BLOCKED"}
 (out/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
 return receipt
