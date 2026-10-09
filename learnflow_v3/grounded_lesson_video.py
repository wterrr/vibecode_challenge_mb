"""V3-32: five-stage causal animation and physically aligned real offline media.

Reuse native V3-30 eSpeak/FFmpeg/decoded replay, V3-07 typed state validation,
V3-31 blackboard font/panel language. This is not word-level alignment, no LLM
and no generic arbitrary Python executor.
"""
from __future__ import annotations
from array import array
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
import tempfile
import wave

from PIL import Image,ImageDraw

from learnflow_v3.blackboard_style import BLACK,WHITE,GREY,FAINT,YELLOW,CYAN,GREEN,cmu_font,assert_fits
from learnflow_v3.lesson_semantic_contract import STAGES,LessonSemanticContract,load_contract,verify_numeric_replay
from learnflow_v3.paid_cs_lesson import Blocked,FPS,SIZE
from learnflow_v3.multidomain_coverage import _record_wav,_probe
from learnflow_v3.sequence_renderer import SequenceRenderProfile,_ffmpeg_anchor,_mean_absolute_error
from learnflow_v2.repair import compute_content_hash

STEM="grounded_five_stage_cs_720p"
AUDIO_GATE=.003


def state_for(c:LessonSemanticContract,index:int)->dict:
    if index not in range(len(STAGES)):raise Blocked("V332_STAGE_OUT_OF_RANGE")
    e=c.example
    return {
        "stage":STAGES[index],
        "argument":e.argument if index>=1 else None,
        "parameter":e.argument if index>=2 else None,
        "expression":f"{e.argument} {e.operator} {e.constant} = {e.result}" if index>=3 else None,
        "return_value":e.result if index>=4 else None,
        "destination_value":e.result if index>=4 else None,
        "active_code_role":c.beats[index].active_code_role,
        "visual_state_key":c.beats[index].visual_state_key,
    }


def _print(draw,xy,value,font,*,fill=WHITE,max_width=None,anchor=None,role="TEXT"):
    if max_width is not None:
        assert_fits(draw,str(value),font,max_width,role=role)
    draw.text(xy,str(value),font=font,fill=fill,anchor=anchor)


def causal_waypoints(stage:str)->tuple[tuple[int,int],...] | None:
    """Route through the empty inter-panel gutter; never cross any text glyph."""
    return {
        "call":((699,435),(747,435),(747,240),(771,240)),
        "bind":((771,240),(747,240),(747,294),(771,294)),
        "evaluate":((771,294),(747,294),(747,348),(771,348)),
        "return":((771,348),(747,348),(747,465),(719,465),(719,434)),
    }.get(stage)


def path_progress(stage:str,phase:float)->list[tuple[int,int]]:
    points=causal_waypoints(stage)
    if points is None:return []
    lengths=[math.dist(a,b) for a,b in zip(points,points[1:])]
    progress=max(0,min(1,(phase-.12)/.76))
    budget=sum(lengths)*progress
    result=[points[0]]
    for (start,end),distance in zip(zip(points,points[1:]),lengths):
        if budget>=distance:
            result.append(end)
            budget-=distance
            continue
        t=budget/max(.00001,distance)
        result.append((round(start[0]+(end[0]-start[0])*t),
                       round(start[1]+(end[1]-start[1])*t)))
        break
    return result


def causal_path(stage:str,phase:float)->tuple[tuple[int,int],tuple[int,int],tuple[int,int]] | None:
    points=causal_waypoints(stage)
    if points is None:return None
    return points[0],points[-1],path_progress(stage,phase)[-1]


def draw_frame(c:LessonSemanticContract,index:int,phase:float,profile:SequenceRenderProfile,narration:str)->Image.Image:
    if (profile.width,profile.height)!=SIZE or not 0<=phase<=1:
        raise Blocked("V332_PROFILE_OR_PHASE")
    beat=c.beats[index]
    state=state_for(c,index)
    if beat.stage!=state["stage"] or beat.visual_state_key!=state["visual_state_key"]:
        raise Blocked("V332_BEAT_VISUAL_STATE_DRIFT")
    # Causal state is NOT allowed to appear before the physically timed event.
    # Beat fractions are planned relative to measured waveform duration, never
    # passed off as word/phoneme timestamps.
    revealed=phase>=beat.event_fraction
    visible=state if revealed else state_for(c,max(0,index-1))
    e=c.example
    im=Image.new("RGB",SIZE,BLACK)
    d=ImageDraw.Draw(im)
    heading,mono,small,caption=cmu_font(34),cmu_font(27,mono=True),cmu_font(21),cmu_font(24)
    _print(d,(64,28),"LEARNFLOW   /   COMPUTING   /   FUNCTION CALL",small,fill=GREY,max_width=1130)
    _print(d,(64,62),"Follow the value, not just the syntax",heading,max_width=1130)
    d.line((64,129,1214,129),fill=FAINT,width=2)
    d.rounded_rectangle((65,157,738,508),radius=12,fill=(12,13,17),outline=(47,50,54),width=2)
    d.rounded_rectangle((760,157,1214,508),radius=12,fill=(12,13,17),outline=(47,50,54),width=2)
    _print(d,(87,176),"PYTHON / SOURCE",small,fill=CYAN)
    _print(d,(788,176),"EXECUTION / STATE",small,fill=CYAN)
    code=[
       ("signature",1,f"def {e.function_name}({e.parameter}):",230),
       ("body",2,f"    return {e.parameter} {e.operator} {e.constant}",305),
       ("invocation",4,f"{e.destination} = {e.function_name}({e.argument})",419),
    ]
    for role,line_number,line,y in code:
        is_active=role==state["active_code_role"]
        if is_active:
            d.rounded_rectangle((78,y-13,720,y+43),radius=6,fill=(36,32,12))
            d.rectangle((78,y-13,83,y+43),fill=YELLOW)
            d.line((129,y+48,129+round(570*phase),y+48),fill=YELLOW,width=3)
        _print(d,(93,y),line_number,small,fill=GREY)
        _print(d,(138,y),line,mono,fill=YELLOW if is_active else WHITE,max_width=566,role="CODE")
    rows=[
      ("ARGUMENT",visible["argument"],.0),
      ("PARAMETER "+e.parameter,visible["parameter"],.0),
      ("EVALUATE",visible["expression"],.0),
      ("RETURN",visible["return_value"],.0),
      (e.destination.upper(),visible["destination_value"],.0)
    ]
    focus={"define":None,"call":0,"bind":1,"evaluate":2,"return":4}[beat.stage] if revealed else None
    for i,(label,value,_) in enumerate(rows):
        y=218+i*54
        if focus==i:
            d.rounded_rectangle((1005,y-9,1198,y+41),radius=9,
                                fill=(18,65,49),outline=GREEN,width=2)
        _print(d,(785,y),label,small,fill=GREY,max_width=210,role="ROW_LABEL")
        if value is None:value="—"
        _print(d,(1178,y),value,cmu_font(25,mono=True),fill=GREEN if value!="—" else GREY,
               max_width=190,anchor="ra",role="VALUE")
        if i<4:d.line((788,y+39,1190,y+39),fill=(37,40,45),width=1)
    # Causal animation crosses the code/state panels to show *what changes*.
    # Dedicated route area is the border between panels and the source/target.
    route=causal_waypoints(beat.stage)
    if route:
        # Highlight-only frames do not count: each causal route advances a
        # labeled input token through the gutter to its semantic destination.
        d.line(route,fill=(50,83,79),width=3,joint="curve")
        travelled=path_progress(beat.stage,phase)
        if len(travelled)>1:
            d.line(travelled,fill=CYAN,width=5,joint="curve")
        x,y=travelled[-1]
        d.ellipse((x-8,y-8,x+8,y+8),fill=YELLOW,outline=WHITE,width=2)
    d.line((65,552,1214,552),fill=FAINT,width=2)
    locations=(145,381,616,852,1093)
    for k,(x,label) in enumerate(zip(locations,STAGES)):
        active=k==index
        d.ellipse((x-7,544,x+7,558),
                  fill=YELLOW if active else GREEN if k<index else FAINT)
        _print(d,(x,566),label.upper(),cmu_font(18),
               fill=YELLOW if active else GREEN if k<index else GREY,anchor="mt",max_width=145)
    # WAV-timed, physically bounded segment caption, not invented word align.
    d.rectangle((0,605,1280,720),fill=BLACK)
    d.line((65,609,1214,609),fill=FAINT,width=2)
    segments=[];current=""
    for word in narration.split():
        candidate=(current+" "+word).strip()
        if d.textbbox((0,0),candidate,font=caption)[2]>1095 and current:
            segments.append(current);current=word
        else:current=candidate
    if current:segments.append(current)
    if not 1<=len(segments)<=2:raise Blocked("V332_CAPTION_OVERFLOW")
    for k,segment in enumerate(segments):
        _print(d,(640,637+k*33),segment,caption,anchor="mt",max_width=1095,role="CAPTION")
    return im


def _clock(s:float)->str:
    ms=round(s*1000)
    return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}"


def _checksum(p:Path)->str:
    return sha256(p.read_bytes()).hexdigest()


def _region_diff(a:Image.Image,b:Image.Image,region=(775,204,1198,504))->float:
    return _mean_absolute_error(a.crop(region),b.crop(region))


def assert_temporal_events(c:LessonSemanticContract,beats:list[dict],events:list[dict])->None:
    if len(beats)!=5 or len(events)!=5:raise Blocked("V332_BEAT_EVENT_CARDINALITY")
    previous=-1
    for index,(beat,evt,expected) in enumerate(zip(beats,events,STAGES)):
        if beat["stage"]!=expected or evt["stage"]!=expected or evt["beat_start_frame"]!=beat["frame_start"]:
            raise Blocked("V332_EVENT_OR_STAGE_MISMATCH")
        expected_frame=beat["frame_start"]+min(beat["frames"]-1,max(1,round(c.beats[index].event_fraction*beat["frames"])))
        if evt["frame"]!=expected_frame:
            raise Blocked("V332_EVENT_NOT_DERIVED_FROM_AUDIO_BEAT")
        if evt["frame"]<=previous or not (beat["frame_start"]<evt["frame"]<beat["frame_start"]+beat["frames"]):
            raise Blocked("V332_CAUSAL_TIMELINE_ORDER")
        if evt["event_id"]!="event-"+expected or evt["visual_state_key"]!="state-"+expected:
            raise Blocked("V332_EVENT_IDENTITY_MISMATCH")
        if abs(evt["seconds"]-evt["frame"]/FPS)>1e-7:
            raise Blocked("V332_EVENT_CLOCK_MISMATCH")
        previous=evt["frame"]


def render_offline(root:Path,out:Path,contract:LessonSemanticContract|None=None,audit:dict|None=None)->dict:
    if not out.is_dir() or out.is_symlink() or any(out.iterdir()):
        raise Blocked("V332_OUTPUT_NOT_EMPTY")
    if contract is None:
        contract,audit=load_contract(root)
    verify_numeric_replay(contract.example)
    p=SequenceRenderProfile(width=SIZE[0],height=SIZE[1],fps=FPS,seconds_per_step=1)
    with tempfile.TemporaryDirectory(prefix="v332_",dir=out) as tmp:
        stage=Path(tmp)
        beats=[];samples=[];offset=0;rate=None
        for idx,b in enumerate(contract.beats):
            r,pcm,n=_record_wav(b.spoken_text,stage/f"narration_{idx}.wav")
            if rate is not None and r!=rate:raise Blocked("V332_AUDIO_RATE_DRIFT")
            rate=r
            frames=math.ceil(n/r*FPS)+2
            padded=math.ceil(frames*r/FPS)
            samples.append(pcm+b"\x00\x00"*(padded-n))
            beats.append({"stage":b.stage,"claim_ids":list(b.claim_ids),
                "segment_id":f"seg-{b.stage}","spoken_text":b.spoken_text,
                "frame_start":offset,"frames":frames,"wav_samples":n,"wav_rate":r})
            offset+=frames
        events=[]
        for b,beat in zip(contract.beats,beats):
            ef=beat["frame_start"]+min(beat["frames"]-1,max(1,round(b.event_fraction*beat["frames"])))
            events.append({"event_id":b.semantic_event_id,"stage":b.stage,
                "visual_state_key":b.visual_state_key,"frame":ef,"seconds":ef/FPS,
                "beat_start_frame":beat["frame_start"],
                "alignment_kind":"WAV_DURATION_FRACTION_NOT_WORD_TIMESTAMPS"})
        assert_temporal_events(contract,beats,events)
        wavfile=stage/"synthesized.wav"
        with wave.open(str(wavfile),"wb") as wav:
            wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate)
            for pcm in samples:wav.writeframes(pcm)
        movie=stage/"encoded.mp4"
        cmd=["ffmpeg","-hide_banner","-nostdin","-v","error","-y","-f","rawvideo",
             "-pix_fmt","rgb24","-s:v","1280x720","-r",str(FPS),"-i","pipe:0",
             "-i",str(wavfile),"-map","0:v","-map","1:a","-c:v","libx264",
             "-threads","2","-preset","ultrafast","-crf","20",
             "-pix_fmt","yuv420p","-frames:v",str(offset),"-c:a","aac",
             "-b:a","128k","-movflags","+faststart",str(movie)]
        process=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            for idx,beat in enumerate(beats):
                for k in range(beat["frames"]):
                    phase=(k+.5)/beat["frames"]
                    frame=draw_frame(contract,idx,phase,p,beat["spoken_text"])
                    process.stdin.write(frame.tobytes())
            process.stdin.close()
            stderr=process.stderr.read()
            rc=process.wait(timeout=240)
            if rc!=0 or not movie.is_file():raise Blocked("V332_FFMPEG_ENCODING_FAILED")
        except Exception:
            if process.stdin and not process.stdin.closed:process.stdin.close()
            if process.poll() is None:process.kill()
            process.wait()
            raise
        video=out/(STEM+".mp4");video.write_bytes(movie.read_bytes())
        subtitles=[]; decoded=[];rms=[];earlylate=[]
        samples_images=[]
        for idx,beat in enumerate(beats):
            start=beat["frame_start"]/FPS;end=start+beat["wav_samples"]/beat["wav_rate"]
            subtitles.append(f"{idx+1}\n{_clock(start)} --> {_clock(end)}\n{beat['spoken_text']}\n")
            # Contact/replay frames are sampled AFTER each event reveal.
            # At the midpoint, a late RETURN event would still be hidden.
            within=min(beat["frames"]-2,max(1,math.floor(beat["frames"]*.78)))
            k=beat["frame_start"]+within
            frame=_ffmpeg_anchor(video,at=(k+.4)/FPS,profile=p)
            expected=draw_frame(contract,idx,(within+.5)/beat["frames"],p,beat["spoken_text"])
            err=_mean_absolute_error(frame,expected)
            if err>=8:raise Blocked("V332_DECODED_SOURCE_PIXEL_MISMATCH")
            decoded.append({"stage":beat["stage"],"frame":k,"decoded_mae":round(err,3)})
            samples_images.append(frame)
            raw=subprocess.check_output(["ffmpeg","-nostdin","-v","error","-ss",str(start),
                "-t",str(max(.3,end-start-.1)),"-i",str(video),"-vn","-f","s16le",
                "-ac","1","-ar","16000","pipe:1"],timeout=45)
            pcm=array("h");pcm.frombytes(raw[:len(raw)//2*2])
            sample=pcm[::30]
            value=math.sqrt(sum(x*x for x in sample)/max(1,len(sample)))/32768
            if value<AUDIO_GATE:raise Blocked("V332_AAC_AUDIBLE_BEAT_GATE")
            rms.append(round(value,5))
            f0=draw_frame(contract,idx,.10,p,beat["spoken_text"])
            f1=draw_frame(contract,idx,.90,p,beat["spoken_text"])
            motion=_mean_absolute_error(f0,f1)
            if motion<=.045:raise Blocked("V332_CAUSAL_ANIMATION_IS_STATIC")
            earlylate.append(round(motion,3))
        a,b=_probe(video)
        if (a["codec_name"]!="h264" or b["codec_name"]!="aac" or
            (int(a["width"]),int(a["height"]))!=SIZE or int(a["nb_frames"])!=offset):
            raise Blocked("V332_ACTUAL_AV_CODEC_OR_FRAMES")
        deltas=[_region_diff(a,b) for a,b in zip(samples_images,samples_images[1:])]
        if min(deltas)<=.8:raise Blocked("V332_STATE_NOT_VISIBLE_IN_DECODED_MP4")
        # Verify the event is causally materialized in ACTUAL encoded video.
        # Sample well before/after each fractional event inside its real beat.
        event_visual_delta=[]
        highlight_boxes={
            "call":(1007,218,1202,271),
            "bind":(1007,272,1202,326),
            "evaluate":(1007,325,1202,380),
            "return":(1007,432,1202,486),
        }
        for index in range(1,len(beats)):
            b=beats[index];evt=events[index]
            before_frame=max(b["frame_start"]+1,evt["frame"]-min(5,max(2,b["frames"]//9)))
            after_frame=min(b["frame_start"]+b["frames"]-2,evt["frame"]+min(5,max(2,b["frames"]//9)))
            if before_frame>=evt["frame"] or after_frame<=evt["frame"]:
                raise Blocked("V332_EVENT_VISUAL_SAMPLE_BOUNDS")
            before_img=_ffmpeg_anchor(video,at=(before_frame+.4)/FPS,profile=p)
            after_img=_ffmpeg_anchor(video,at=(after_frame+.4)/FPS,profile=p)
            roi=highlight_boxes[b["stage"]]
            delta=_mean_absolute_error(before_img.crop(roi),after_img.crop(roi))
            if delta<=.45:raise Blocked("V332_EVENT_HAS_NO_DECODED_STATE_REVEAL")
            event_visual_delta.append({"stage":b["stage"],"frame":evt["frame"],
                                       "actual_encoded_roi_delta":round(delta,3)})

        srt=out/(STEM+".srt");srt.write_text("\n".join(subtitles),encoding="utf-8")
        contact=Image.new("RGB",(1920,720),BLACK)
        for i,frame in enumerate(samples_images):
            contact.paste(frame.resize((640,360)),((i%3)*640,(i//3)*360))
        contact.save(out/(STEM+"_contact.jpg"),quality=92)
        evidence={
            "checkpoint":"V3-32","status":"BOUNDED_OFFLINE_GROUNDED_FIVE_BEAT_TECHNICAL_PASS",
            "topic_id":contract.topic_id,"production":"BLOCKED",
            "v332_provider_requests":0,"research_source":"HOST_DETERMINISTIC_SOURCE_TRACE_COMPILER",
            "rejected_v330_model_research":audit,
            "original_model_research_not_used_for_render":True,
            "independent_fact_semantics":"NOT_RUN",
            "human_teaching_quality":"NOT_RUN","rights_clearance":"NOT_RUN",
            "word_level_alignment":"NOT_CLAIMED",
            "contract_sha256":compute_content_hash(contract),"source_sha256":contract.source_sha256,
            "example":contract.example.model_dump(mode="json"),
            "research_explanations":list(contract.research_explanations),
            "stage_names":list(STAGES),
            "beat_events":events,"beat_times":beats,
            "decoded_checkpoints":"POST_EVENT_STABLE_78_PERCENT_OF_PHYSICAL_BEAT",
            "decoded_rgb_source_mae":decoded,"audio_aac_rms_per_beat":rms,
            "decoded_state_roi_deltas":[round(x,3) for x in deltas],
            "decoded_event_reveal_checks":event_visual_delta,
            "intra_beat_caused_motion_mae":earlylate,
            "video_sha256":_checksum(video),"subtitle_sha256":_checksum(srt),
            "width":SIZE[0],"height":SIZE[1],"fps":FPS,"frames":offset,
            "duration_seconds":offset/FPS,
            "full_six_domain_autonomy":"NOT_PROVEN","final_go_no_go":"NO_GO_FOR_PRODUCTION"}
        (out/"v3_32_evidence.json").write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf-8")
        (out/"v3_32_lesson_contract.json").write_text(contract.model_dump_json(indent=2)+"\n",encoding="utf-8")
        return evidence
