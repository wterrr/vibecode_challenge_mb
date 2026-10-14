"""V3-64 host-owned identity-preserving 12-square native compiler.

The model may choose composition, conceptual focus and identity-safe morph;
its text is spoken as a DRAFT requiring later human semantic/audio review.
No executable code, generated facts, or third-party media is admitted.
"""
from __future__ import annotations
import io,json,math,shutil,subprocess,wave
from hashlib import sha256
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageStat
from .v364_heldout_storyboard import accept,UNIT_IDS,TOPIC,digest

W,H,FPS=1280,720,15
BG=(10,13,20);WHITE=(242,244,249);LIGHT=(180,192,211)
CYAN=(73,220,202);GOLD=(255,188,82);DARK=(39,55,76)
class NativeFail(ValueError):pass
def need(p,reason):
    if not p: raise NativeFail("V364_"+reason)
def font(size):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"):
        if Path(path).exists():return ImageFont.truetype(path,size)
    return ImageFont.load_default()
def tx(d,position,content,size=28,color=WHITE,anchor=None):
    d.text(position,str(content),font=font(size),fill=color,anchor=anchor)
def rows_cols(columns):
    return 12//columns, columns
def grid_positions(columns,side_by_side=False):
    rows=12//columns
    gap=105
    x0=(160 if side_by_side else (W-(columns-1)*gap)/2)
    y0=300 if rows==3 else 285
    return {f"unit_{i:02d}":(int(x0+(i%columns)*gap),
                               int(y0+(i//columns)*gap)) for i in range(12)}
def interp(a,b,p):
    eased=p*p*(3-2*p)
    return a+(b-a)*eased
def state(candidate,act,progress):
    accept(candidate)
    need(0<=progress<=1 and math.isfinite(progress),"BAD_FRAME_PROGRESS")
    start=grid_positions(4,candidate["visual_thinker"]["composition"]=="side_by_side")
    goal=grid_positions(3,candidate["visual_thinker"]["composition"]=="side_by_side")
    method=candidate["motion_director"]["method"]
    if act<2:p=0
    elif act>2:p=1
    elif method=="smooth_morph":p=progress
    else:p=max(0.,min(1.,(progress*12-(0.0))/12))
    # Stagger individual token transforms, while respecting SAME IDs at every frame.
    result={}
    for i,uid in enumerate(UNIT_IDS):
        t=p
        if act==2 and method=="staggered_morph":
            t=max(0.,min(1.,(progress-i*.031)/(1-11*.031)))
        a,b=start[uid],goal[uid]
        result[uid]=(round(interp(a[0],b[0],t),2),round(interp(a[1],b[1],t),2))
    return result
def line_wrap(draw,text,size=22,max_width=1050):
    out=[];line=""
    for word in text.split():
        q=(line+" "+word).strip()
        if line and draw.textbbox((0,0),q,font=font(size))[2]>max_width:
            out.append(line);line=word
        else:line=q
    if line:out.append(line)
    need(len(out)<=4,"SUBTITLE_OVERFLOW")
    return out
def render(candidate,beat,p):
    accept(candidate)
    b=candidate["beats"][beat]
    image=Image.new("RGB",(W,H),BG)
    draw=ImageDraw.Draw(image)
    tx(draw,(60,35),"LEARNFLOW  /  WHY THE COUNT DOES NOT CHANGE",21,CYAN)
    tx(draw,(60,80),"Can 3 × 4 become 4 × 3 without losing anything?",38,WHITE)
    draw.line((60,145,1220,145),fill=DARK,width=2)
    tx(draw,(1214,40),f"{beat+1:02d} / 05",23,LIGHT,anchor="ra")
    tx(draw,(72,169),b["stage"],20,GOLD)
    decision=candidate["visual_thinker"]
    positions=state(candidate,beat,p)
    focus=b["visual_focus"]
    for i,uid in enumerate(UNIT_IDS):
        x,y=positions[uid]
        x=int(x);y=int(y)
        emphasis=focus=="all_twelve" or (focus=="highlight_first_row" and i<4) or \
          (focus=="track_corner" and i in (0,3,8,11))
        col=CYAN if emphasis else (101,125,146)
        draw.rounded_rectangle((x-35,y-35,x+35,y+35),radius=12,
                               fill=col,outline=WHITE if emphasis else DARK,width=2)
        tx(draw,(x,y),str(i+1),24,BG,anchor="mm")
        if focus=="track_corner" and uid=="unit_00":
            draw.ellipse((x-46,y-46,x+46,y+46),outline=GOLD,width=4)
    if beat>=3 and b["show_numeric_conclusion"]:
        tx(draw,(640,237),"3 × 4 = 4 × 3 = 12",39,GOLD,anchor="mm")
    else:
        text=("3 rows × 4 columns" if beat<2 else
              "same squares — regrouping in progress")
        tx(draw,(640,241),text,27,LIGHT,anchor="mm")
    if decision["composition"]=="side_by_side":
        tx(draw,(96,490),"Every object retains its own identity",22,LIGHT)
    if candidate["narrative_designer"]["opening"]=="notice_paradox":
        draw.rounded_rectangle((850,505,1174,545),radius=9,outline=GOLD,width=2)
        tx(draw,(870,513),"Look carefully at the count",18,GOLD)
    draw.line((60,571,1220,571),fill=DARK,width=2)
    for line_no,line in enumerate(line_wrap(draw,b["caption"],24)):
        tx(draw,(72,588+30*line_no),line,24,WHITE)
    for i in range(5):
        x=74+i*231
        draw.rounded_rectangle((x,690,x+206,700),radius=3,
              fill=CYAN if i<=beat else DARK)
    return image

def file_sha(path:Path):
    h=sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1048576),b""):h.update(block)
    return h.hexdigest()
def probe(movie):
    data=json.loads(subprocess.check_output(
     ["ffprobe","-v","error","-count_frames","-show_entries",
      "stream=codec_type,codec_name,width,height,r_frame_rate,nb_read_frames,duration",
      "-of","json",str(movie)],timeout=45))
    streams={x["codec_type"]:x for x in data["streams"]}
    v,a=streams["video"],streams["audio"]
    need(v["codec_name"]=="h264" and a["codec_name"]=="aac" and
         v["width"]==W and v["height"]==H and v["r_frame_rate"]=="15/1",
         "WRONG_NATIVE_CODEC")
    return int(v["nb_read_frames"])
def decode_movie(movie):
    subprocess.run(["ffmpeg","-nostdin","-v","error","-xerror","-i",
      str(movie),"-map","0:v:0","-f","null","-"],timeout=150,
      check=True,capture_output=True)
def snap(movie,t):
    data=subprocess.check_output(["ffmpeg","-nostdin","-v","error","-ss",
      str(t),"-i",str(movie),"-vframes","1","-f","image2pipe",
      "-vcodec","png","-"],timeout=45)
    x=Image.open(io.BytesIO(data));x.load()
    return x.convert("RGB")
def mdiff(a,b):
    return sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3
def speech_wav(script,path):
    engine=shutil.which("espeak-ng") or shutil.which("espeak")
    need(bool(engine),"OFFLINE_TTS_MISSING")
    subprocess.run([engine,"-s","180","-v","en","-w",str(path),script],
                   check=True,timeout=65,capture_output=True)
    with wave.open(str(path),"rb") as wf:
        par=(wf.getnchannels(),wf.getsampwidth(),wf.getframerate())
        raw=wf.readframes(wf.getnframes())
    need(par[0]==1 and par[1]==2,"TTS_NOT_16BIT_MONO")
    return raw,par
def common_timeline(a,b,tmp):
    sources=[]
    pars=None
    for who,item in (("host",a),("model",b)):
        arr=[]
        for i,act in enumerate(item["beats"]):
            pcm,par=speech_wav(act["caption"],tmp/f"{who}_{i}.wav")
            need(pars is None or pars==par,"TTS_PARAM_MISMATCH")
            pars=par;arr.append(pcm)
        sources.append(arr)
    lengths=[max(len(sources[0][i]),len(sources[1][i])) for i in range(5)]
    counts=[max(60,math.ceil((L/2/pars[2]+.9)*FPS)) for L in lengths]
    return sources,pars,counts
def write_audio(pcms,par,counts,dest):
    frame_rate=par[2]
    with wave.open(str(dest),"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(frame_rate)
        for pcm,count in zip(pcms,counts):
            target=int(count/FPS*frame_rate)
            need(len(pcm)//2<=target,"NARRATION_LONGER_THAN_VISUAL_SEGMENT")
            w.writeframes(pcm+b"\0\0"*(target-len(pcm)//2))
def frame_stream(candidate,counts,silent):
    args=["ffmpeg","-nostdin","-y","-hide_banner","-loglevel","error",
          "-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),
          "-i","-","-an","-c:v","libx264","-preset","ultrafast","-crf","28",
          "-pix_fmt","yuv420p",str(silent)]
    proc=subprocess.Popen(args,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for i,n in enumerate(counts):
            for j in range(n):
                t=min(1.,j/max(1,int(n*.78)))
                proc.stdin.write(render(candidate,i,t).tobytes())
        proc.stdin.close();proc.stdin=None
        err=proc.stderr.read().decode(errors="replace")
        ret=proc.wait(timeout=300)
        need(ret==0,"FFMPEG_ENCODE_FAILED_"+err[-120:])
    except BaseException:
        proc.kill();proc.wait()
        raise

def build_comparison(baseline,candidate,dest:Path):
    accept(baseline);accepted=accept(candidate)
    need(not dest.exists(),"OUTPUT_EXISTS")
    dest.mkdir(parents=True)
    src,par,counts=common_timeline(baseline,candidate,dest)
    assert len(counts)==5
    res=[]
    for label,item,audio in zip(("host_TEST_ONLY","model_unverified"),(baseline,candidate),src):
        raw=dest/f"{label}_silent.mp4"
        output=dest/f"{label}.mp4"
        wav=dest/f"{label}.wav"
        write_audio(audio,par,counts,wav)
        frame_stream(item,counts,raw)
        subprocess.run(["ffmpeg","-nostdin","-y","-v","error","-i",str(raw),
          "-i",str(wav),"-map","0:v:0","-map","1:a:0","-c:v","copy",
          "-c:a","aac","-b:a","128k",str(output)],check=True,timeout=120)
        n=probe(output)
        need(n==sum(counts),"FRAME_COUNT_DISAGREEMENT")
        decode_movie(output)
        res.append({"name":label+".mp4","sha256":file_sha(output),
            "native_frames":n,"video_codec":"h264","audio_codec":"aac",
            "audio_is_same_across_treatments":False})
    t1=sum(counts[:2])/FPS + (counts[2]*.45/FPS)
    t2=sum(counts[:3])/FPS + .4
    source=snap(dest/"host_TEST_ONLY.mp4",t1)
    target=snap(dest/"model_unverified.mp4",t1)
    early=snap(dest/"model_unverified.mp4",sum(counts[:1])/FPS+.2)
    later=snap(dest/"model_unverified.mp4",t2)
    native_delta=mdiff(source,target)
    witness=mdiff(early,later)
    source.save(dest/"host_midpoint.png")
    target.save(dest/"candidate_midpoint.png")
    later.save(dest/"candidate_witness.png")
    need(witness>.25,"NO_NATIVE_SEMANTIC_WITNESS")
    results={"checkpoint":"V3-64","topic":TOPIC,"host_ledger_sha256":accepted["host_ledger_sha256"],
      "source_story_sha256":digest(baseline),"candidate_story_sha256":digest(candidate),
      "actual_candidate_requires_provider_provenance":True,
      "native_mp4s":res,"matched_video_frame_counts":True,
      "audio_bitwise_matched":False,"comparison_confounded_by_different_narration":True,
      "candidate_vs_baseline_midpoint_MAD":round(native_delta,4),
      "early_to_witness_MAD":round(witness,4),
      "persistent_units":list(UNIT_IDS),"source_math":"3×4=4×3=12",
      "human_pedagogical_quality":"UNRATED",
      "generalization":"ONE_NEW_TOPIC_NOT_POPULATION_PROOF",
      "learning_gain":"NOT_MEASURED","production":"BLOCKED"}
    (dest/"v364_native_receipt.json").write_text(json.dumps(results,indent=2)+"\n")
    for f in dest.glob("*_silent.mp4"):f.unlink()
    for f in dest.glob("*.wav"):f.unlink()
    return results
