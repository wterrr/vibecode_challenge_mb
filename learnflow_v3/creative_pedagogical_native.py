"""V3-62 finite native storytelling compiler: persistent objects, earned reveals.

Rendering from immutable host facts only; no model-provided executable code,
no copied Manim/3Blue1Brown scenes and no word-alignment inference.
"""
from __future__ import annotations
import io
import json
import math
import shutil
import subprocess
import wave
from hashlib import sha256
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageStat
from .creative_pedagogical_director import (
    CASES, ACTS, TITLES, validate, candidate, witness, receipt, Blocked
)

W,H,FPS=1280,720,15
BG=(10,12,19); WHITE=(239,241,248); INK=(164,180,197)
MINT=(75,219,200); AMBER=(244,186,89); MAGENTA=(231,108,125)
FAINT=(57,70,88); PANEL=(24,33,43)
STYLE_IDS={"focus_first":"F","witness_first":"W"}

def require(ok,why):
    if not ok:raise Blocked("V362_"+why)

def font(size):
    for fp in ("/usr/share/fonts/truetype/cmu/cmunrm.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"):
        if Path(fp).is_file():return ImageFont.truetype(fp,size)
    return ImageFont.load_default()

def tx(d,xy,string,size=28,fill=WHITE,anchor=None):
    d.text(xy,str(string),font=font(size),fill=fill,anchor=anchor)

def line_wrap(d,text,max_width,size):
    result=[];current=""
    for word in text.split():
        trial=(current+" "+word).strip()
        if current and d.textbbox((0,0),trial,font=font(size))[2]>max_width:
            result.append(current);current=word
        else:current=trial
    if current:result.append(current)
    require(len(result)<=3,"NARRATION_VISUAL_OVERFLOW")
    return result

def lerp(a,b,t):return a+(b-a)*t
def smooth(t):return t*t*(3-2*t)

def scene_objects(story,act,progress):
    f=validate(story)
    cid=story.case_id
    p=smooth(progress)
    landed=act>=3
    if cid==CASES[0]:
        return {"visual_family":"PARTITION_GRID","eight_objects":
          tuple({"id":f"outcome_{i}","event":i<3,
            "complement_progress":1 if landed else
                max(0,min(1,p*5-(i-3))) if act==2 and i>=3 else 0}
           for i in range(8)),
            "result_visible":landed,"total":8,"selected":3,"complement":5}
    if cid==CASES[1]:
        traveled=(12 if landed else 12*p if act==2 else 0)
        return {"visual_family":"DISTANCE_TRACK","marker_id":"moving_marker",
          "marker_m":traveled,"speed":3,"duration":4,
          "result_visible":landed,"ticks_completed":(
              4 if landed else int(min(4,math.floor(traveled/3+1e-8))))}
    atoms=("H0","H1","H2","H3","O0","O1")
    initial=((237,304),(315,304),(237,402),(315,402),(883,344),(965,344))
    target=((401,328),(511,328),(726,328),(836,328),(456,418),(781,418))
    point=target if landed else tuple(
        (lerp(start[0],end[0],p),lerp(start[1],end[1],p))
        for start,end in zip(initial,target)) if act==2 else initial
    return {"visual_family":"ATOM_INVENTORY",
        "atoms":tuple({"id":a,"element":a[0],"x":round(pos[0],3),"y":round(pos[1],3)}
                 for a,pos in zip(atoms,point)),
        "result_visible":landed,"atom_counts":{"H":4,"O":2},
        "chemical_kinetics":"NOT_CLAIMED"}

def visible_state(story,act,progress,control=False):
    s=scene_objects(story,act,progress)
    if control:return scene_objects(story,3,1.0)
    return s

def render_frame(story,act,progress,*,control=False):
    validate(story)
    state=visible_state(story,act,progress,control)
    im=Image.new("RGB",(W,H),BG)
    d=ImageDraw.Draw(im)
    # Strong editorial hierarchy: a single question, persistent visual, earned result.
    tx(d,(72,36),"LEARNFLOW   /   WHY IT WORKS",19,MINT)
    tx(d,(72,78),TITLES[story.case_id],38,WHITE)
    d.line((72,142,1208,142),fill=FAINT,width=2)
    tx(d,(1205,44),f"{act+1:02d} / 05",22,INK,anchor="ra")
    labels=("ASK","GIVEN","CHANGE","VERIFY","TAKEAWAY")
    tx(d,(76,164),labels[act],22,AMBER)
    tx(d,(1208,164),story.acts[act].highlight,24,MINT,anchor="ra")
    if story.case_id==CASES[0]:
        # Eight persistent outcomes. Never make the complement disappear.
        x0=173;y=309;gap=118;size=86
        for i,item in enumerate(state["eight_objects"]):
            left=x0+i*gap
            if item["event"]:
                fill=MINT
                fg=BG
            else:
                k=item["complement_progress"]
                fill=tuple(round(lerp(PANEL[j],AMBER[j],k)) for j in range(3))
                fg=BG if k>=.85 else INK
            d.rounded_rectangle((left,y,left+size,y+size),radius=20,
                                fill=fill,outline=FAINT,width=3)
            tx(d,(left+size/2,y+size/2),str(i+1),31,fg,anchor="mm")
        d.line((173,443,1153,443),fill=FAINT,width=3)
        d.arc((173,452,526,505),0,180,fill=MINT,width=5)
        tx(d,(349,519),"3 belong to the event",24,MINT,anchor="mm")
        if state["result_visible"]:
            d.arc((535,452,1153,505),0,180,fill=AMBER,width=5)
            tx(d,(844,519),"5 are in the complement",24,AMBER,anchor="mm")
            tx(d,(648,260),"3/8 + 5/8 = 1",45,WHITE,anchor="mm")
        elif act>=1:
            tx(d,(649,260),"8 outcomes, same total",29,INK,anchor="mm")
    elif story.case_id==CASES[1]:
        x0=175;x1=1105;y=412
        d.line((x0,y,x1,y),fill=FAINT,width=10)
        for i in range(5):
            x=x0+(x1-x0)*i/4
            d.line((x,y-21,x,y+21),fill=INK,width=3)
            if i<=state["ticks_completed"] or i==0:
                tx(d,(x,y+58),str(3*i)+" m",26,MINT,anchor="mm")
        # Never teleport marker to result before the motion/visible proof.
        x=round(x0+(x1-x0)*state["marker_m"]/12)
        d.line((x0,y,x,y),fill=MINT,width=12)
        d.ellipse((x-22,y-22,x+22,y+22),fill=AMBER,outline=WHITE,width=3)
        d.line((x,y-35,x,y-81),fill=AMBER,width=4)
        tx(d,(x,y-103),f"{state['marker_m']:.1f} m" if act==2 else
           "start" if not state["result_visible"] else "12 m",31,AMBER,anchor="mm")
        if state["result_visible"]:
            tx(d,(640,274),"4 seconds  ×  3 m/s  =  12 m",42,WHITE,anchor="mm")
        else:
            tx(d,(640,274),"Speed stays fixed: 3 m/s",33,INK,anchor="mm")
    else:
        atoms=state["atoms"]
        coords={a["id"]:(a["x"],a["y"]) for a in atoms}
        def bond(one,two,color=INK):
            x,y=coords[one];X,Y=coords[two]
            d.line((x,y,X,Y),fill=color,width=12)
        if act<=1 and not control:
            for e in (("H0","H1"),("H2","H3"),("O0","O1")):bond(*e)
        if state["result_visible"]:
            for e in (("H0","O0"),("H1","O0"),("H2","O1"),("H3","O1")):bond(*e)
        for a in atoms:
            x,y=a["x"],a["y"];rad=38 if a["element"]=="H" else 46
            color=MINT if a["element"]=="H" else MAGENTA
            d.ellipse((x-rad,y-rad,x+rad,y+rad),fill=color,outline=WHITE,width=2)
            tx(d,(x,y),a["element"],35,BG,anchor="mm")
        tx(d,(640,231),"6 persistent atoms  ·  4 H and 2 O",32,INK,anchor="mm")
        if state["result_visible"]:
            tx(d,(640,519),"2 H2 + O2    →    2 H2O",44,WHITE,anchor="mm")
        else:
            tx(d,(640,519),"Same atom identities; no reaction-path claim",24,INK,anchor="mm")
    # Narration is segment-level only; text is a subtitle, not word-synced.
    d.line((72,575,1208,575),fill=FAINT,width=2)
    for j,t in enumerate(line_wrap(d,story.acts[act].narration,1110,24)):
        tx(d,(76,592+31*j),t,24,WHITE)
    for j in range(5):
        x=76+232*j
        d.rounded_rectangle((x,695,x+205,702),radius=3,
          fill=MINT if j<=act else FAINT)
    return im

def media_probe(path):
    data=json.loads(subprocess.check_output([
        "ffprobe","-v","error","-count_frames","-show_entries",
        "stream=codec_type,codec_name,width,height,r_frame_rate,nb_read_frames,duration",
        "-of","json",str(path)],timeout=35))
    streams={s["codec_type"]:s for s in data["streams"]}
    video=streams["video"];audio=streams["audio"]
    require(video["codec_name"]=="h264" and audio["codec_name"]=="aac" and
            video["width"]==W and video["height"]==H and
            video["r_frame_rate"]=="15/1","NATIVE_CODEC_OR_GEOMETRY")
    return {"frames":int(video["nb_read_frames"]),
       "duration_s":float(video["duration"]),
       "audio_duration_s":float(audio["duration"])}

def sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()

def aac_sha(path):
    data=subprocess.check_output(["ffmpeg","-nostdin","-v","error",
        "-i",str(path),"-map","0:a:0","-c:a","copy","-f","adts","-"],timeout=40)
    return sha256(data).hexdigest()

def frame(path,second):
    data=subprocess.check_output(["ffmpeg","-nostdin","-v","error",
        "-ss",f"{second:.3f}","-i",str(path),"-vframes","1",
        "-f","image2pipe","-vcodec","png","-"],timeout=50)
    obj=Image.open(io.BytesIO(data));obj.load()
    return obj.convert("RGB")

def diff(a,b):
    return sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3

def speak(text,path):
    exe=shutil.which("espeak-ng") or shutil.which("espeak")
    require(exe is not None,"OFFLINE_TTS_MISSING")
    subprocess.run([exe,"-s","185","-v","en","-w",str(path),text],
        check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=60)
    with wave.open(str(path),"rb") as w:
        par=(w.getnchannels(),w.getsampwidth(),w.getframerate())
        pcm=w.readframes(w.getnframes())
    require(par[0]==1 and par[1]==2,"TTS_AUDIO_FORMAT_DRIFT")
    return pcm,par

def encode_video(story,out,counts,control=False):
    ff=["ffmpeg","-nostdin","-y","-hide_banner","-loglevel","error",
        "-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}",
        "-r",str(FPS),"-i","-","-an","-c:v","libx264",
        "-preset","ultrafast","-crf","27","-pix_fmt","yuv420p",str(out)]
    proc=subprocess.Popen(ff,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for i,n in enumerate(counts):
            for j in range(n):
                phase=min(1.0,j/max(1,int(n*.70)))
                proc.stdin.write(render_frame(story,i,phase,control=control).tobytes())
        proc.stdin.close();proc.stdin=None
        err=proc.stderr.read().decode(errors="replace")
        ret=proc.wait(timeout=360)
        require(ret==0,"NATIVE_ENCODING_FAILURE:"+err[-300:])
    except BaseException:
        proc.kill();proc.wait()
        raise

def decode_all(movie):
    subprocess.run(["ffmpeg","-nostdin","-v","error","-xerror",
        "-i",str(movie),"-map","0:v:0","-f","null","-"],
        check=True,timeout=180,capture_output=True)

def build_pair(story,out):
    validate(story)
    out=Path(out)
    require(not out.exists(),"OUTPUT_EXISTS")
    out.mkdir(parents=True)
    waveparts=[];counts=[];params0=None
    for i,beat in enumerate(story.acts):
        pcm,par=speak(beat.narration,out/f"speech_{i}.wav")
        require(params0 is None or params0==par,"TTS_SEGMENT_FORMAT_DRIFT")
        params0=par
        pad=round(par[2]*0.6)
        waveparts.append(pcm+b"\0\0"*pad)
        counts.append(max(32,round((len(pcm)/2/par[2]+.6)*FPS)))
    voice=out/"narration.wav"
    with wave.open(str(voice),"wb") as wavefile:
        wavefile.setnchannels(1);wavefile.setsampwidth(2)
        wavefile.setframerate(params0[2]);wavefile.writeframes(b"".join(waveparts))
    timeline={"durations_frames":counts,"total_frames":sum(counts),
        "beat_boundaries_s":[round(sum(counts[:k])/FPS,3) for k in range(6)],
        "word_aligned":False}
    movies={}
    for mode in ("causal_timeline","end_state_hold"):
        raw=out/(mode+"_silent.mp4")
        encode_video(story,raw,counts,control=mode=="end_state_hold")
        target=out/(mode+".mp4")
        if mode=="causal_timeline":
            # Always preserve BOTH narration tracks identically after first mux.
            subprocess.run(["ffmpeg","-nostdin","-y","-v","error",
               "-i",str(raw),"-i",str(voice),"-map","0:v:0","-map","1:a:0",
               "-c:v","copy","-c:a","aac","-b:a","128k",str(target)],
               check=True,timeout=110)
        else:
            ref=out/"causal_timeline.mp4"
            subprocess.run(["ffmpeg","-nostdin","-y","-v","error",
               "-i",str(raw),"-i",str(ref),"-map","0:v:0","-map","1:a:0",
               "-c:v","copy","-c:a","copy",str(target)],
               check=True,timeout=110)
        metadata=media_probe(target)
        require(metadata["frames"]==sum(counts),"NATIVE_FRAME_PARITY_FAILED")
        decode_all(target)
        movies[mode]={"sha256":sha(target),"audio_packet_sha256":aac_sha(target),
           "native_decoded_frames":metadata["frames"],
           "native_video_duration_s":metadata["duration_s"],
           "size_bytes":target.stat().st_size}
    require(movies["causal_timeline"]["audio_packet_sha256"]==
            movies["end_state_hold"]["audio_packet_sha256"],
            "CONTROL_NARRATION_NOT_BITWISE_MATCHED")
    # After the transformation, text and objects must really occupy pixels.
    starts=timeline["beat_boundaries_s"]
    a=frame(out/"causal_timeline.mp4",starts[2]+.25)
    b=frame(out/"causal_timeline.mp4",starts[3]+.35)
    control=frame(out/"end_state_hold.mp4",starts[2]+.25)
    d=diff(a,b)
    require(d>.4,"NO_NATIVE_SEMANTIC_TRANSFORMATION")
    # Answer-first control differs at the same pre-witness moment.
    against=diff(a,control)
    require(against>.35,"CAUSAL_REVEAL_NOT_DISTINGUISHABLE")
    data={
      "checkpoint":"V3-62","case_id":story.case_id,"ledger_sha":story.evidence_sha256,
      "origin":"HOST_AUTHORED_DETERMINISTIC_NOT_LLM",
      "source_story":receipt(story),"timeline":timeline,"movies":movies,
      "causal_pre_to_witness_decoded_mean_RGB_abs_diff":round(d,4),
      "early_control_vs_causal_decoded_mean_RGB_abs_diff":round(against,4),
      "matched_audio_AAC":True,"matched_physical_frames":True,
      "narration_alignment":"SEGMENT_ONLY_NOT_WORD_ALIGNED",
      "human_quality":"UNRATED","learning_gain":"NOT_MEASURED",
      "agent_creativity":"NOT_TESTED","production":"BLOCKED"}
    (out/"receipt.json").write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    return data
