"""V3-27 source-locked six-domain reachability and *bounded* narrated math adapter.

Read-only frozen corpus + separate developer selection. All six rows get an
attempt; unsupported families ABSTAIN, never fall back to CONCEPT_CARD.
A certified generic linear-graph teaching illustration may be rendered with
measured local WAV and real AAC/H264; it is NOT a full Research/Script/Visual
Director-agent lesson, approved release or V3-16 confirmatory experiment.
"""
from __future__ import annotations
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import wave

from PIL import Image, ImageDraw, ImageChops, ImageStat
from learnflow_v2.repair import compute_content_hash
from learnflow_v2.scenegraph import SceneGraph
from .blackboard_style import BLACK, WHITE, CYAN, cmu_font
from .math_renderer import FunctionGraph, GraphPoint, graph_source, draw_function_frame, polynomial_value, verify_function_graph
from .sequence_renderer import SequenceRenderProfile, _ffmpeg_anchor, _mean_absolute_error

VERSION="v3-27-six-domain-locked-honest-coverage-v1"
DIMENSIONS=(1280,720)
FPS=18
SOURCE="benchmarks/learnflowbench/corpus_v1.json"
SELECTION="benchmarks/learnflowbench/v3/v3_27_locked_development_topics.json"
FROZEN="benchmarks/learnflowbench/v3/preregistered_pilot_v1.json"
ORDER=("cs","math","physics","biology","chemistry","history_general")
FORBIDDEN={"lfb-005-cs"}
REASON={
 "cs":"ABSTAIN_UNCERTIFIED_CODE_AND_TEACHING_SCRIPT",
 "physics":"ABSTAIN_NO_PHYSICAL_STATE_SOURCE_OR_CERTIFIED_RENDER_ADAPTER",
 "biology":"ABSTAIN_NO_BIOLOGY_SEMANTIC_OBJECT_AND_SOURCE_PROOF",
 "chemistry":"ABSTAIN_NO_MOLECULAR_EQUILIBRIUM_SCENE_CERTIFICATE",
 "history_general":"ABSTAIN_NO_CITED_CHRONOLOGY_AND_CAUSAL_SCRIPT",
}
REACHABILITY={
 "Research":"STANDALONE_HERMES_NO_MULTIDOMAIN_SOURCE_CONSUMER",
 "Script":"STANDALONE_HERMES_NO_CERTIFIED_MULTIDOMAIN_SCRIPT",
 "Pedagogy":"STANDALONE_V3_09_PLAN_NO_GENERAL_RENDER_HANDOFF",
 "Visual_Director":"SEMANTIC_ROUTER_SELECTS_UNRENDERABLE_WITHOUT_FAMILY_ADAPTER",
 "Code_Process":"STANDALONE_V3_07_SOURCE_CERTIFIED_NO_GENERAL_NARRATOR",
 "Math":"STANDALONE_V3_08_CERTIFIED_GRAPH_AND_ALGEBRA",
 "State_Machine":"STANDALONE_V3_15_AUTHOR_CURATED_CANDIDATE_ONLY",
 "Narration":"V3_19_BINARY_SEARCH_ONLY_PLUS_BOUNDED_V3_27_MATH_ADAPTER",
 "Final_Assembly":"V3_19_BINARY_SEARCH_ONLY_PLUS_BOUNDED_V3_27_MATH_ADAPTER",
 "Quality_Gate":"SOURCE_AND_PIXEL_EVIDENCE_NOT_INDEPENDENT_HUMAN_LEARNING",
 "Production_Route":"NOT_REGISTERED_FROZEN_V2_DEFAULT",
}
def guard(cond:bool,reason:str)->None:
    if not cond:raise ValueError("V3_27_"+reason)
def digest(path:Path)->str:
    return sha256(path.read_bytes()).hexdigest()
def read_source(root:Path)->tuple[list[dict],dict]:
    raw=json.loads((root/SOURCE).read_text(encoding="utf-8"))
    proto=json.loads((root/FROZEN).read_text(encoding="utf-8"))
    manifest=json.loads((root/SELECTION).read_text(encoding="utf-8"))
    guard(raw["frozen"] is True and len(raw["topics"])==100,"CORPUS_NOT_FROZEN")
    guard(manifest["source_corpus_sha256"]==proto["source"]["corpus_sha256"]
          and manifest["immutable_selection"] is True and not manifest["allow_substitution"]
          and len(manifest["cases"])==6,"SELECTION_OR_CORPUS_NOT_LOCKED")
    locked=set(proto["sampling"]["topic_ids"])|set(proto["sampling"]["excluded_diagnostic_ids"])|FORBIDDEN
    topics={x["topic_id"]:x for x in raw["topics"]}
    rows=[]
    for domain in ORDER:
        candidates=sorted((v for v in raw["topics"] if v["domain"]==domain
                           and v["topic_id"] not in locked),key=lambda v:v["topic_id"])
        guard(len(candidates)>1,"NOT_ENOUGH_AVAILABLE_TOPICS")
        selected=candidates[1]
        rule=next((x for x in manifest["cases"] if x["domain"]==domain),None)
        guard(rule is not None and rule["topic_id"]==selected["topic_id"]
              and selected["topic_id"] not in locked
              and sha256(selected["query"].encode("utf-8")).hexdigest()==rule["query_sha256"],
              "TOPIC_SELECTION_DRIFT")
        rows.append({**selected,"query_sha256":rule["query_sha256"],
                     "input_hash":compute_content_hash(selected)})
    guard(len({x["topic_id"] for x in rows})==6,"DUPLICATE_SOURCE_TOPICS")
    return rows,manifest

def make_linear_graph(*,slope:int,intercept:int,domain:tuple[int,int]=(-2,2)):
    """Any bounded integer line, not a fixture or hard-coded topic video."""
    guard(type(slope) is int and type(intercept) is int and -2<=slope<=2
          and -2<=intercept<=2 and slope!=0,"INVALID_LINEAR_COEFFICIENT")
    coefficients=(intercept,slope,0)
    points=tuple(GraphPoint(point_id=f"point-{i}",x=x,
                            y=int(polynomial_value(coefficients,x)))
                 for i,x in enumerate(range(domain[0],domain[1]+1)))
    graph=SceneGraph.model_validate({
        "scene_id":"v3-27-linear-function",
        "purpose":"DEMONSTRATE",
        "layout_intent":{"type":"ILLUSTRATION","reading_direction":"LEFT_TO_RIGHT"},
        "nodes":[{"id":"linear-graph","kind":"CHART","label":"Linear function",
                  "content":graph_source(coefficients,domain)}],
        "relations":[]})
    spec=FunctionGraph(scenegraph_sha256=compute_content_hash(graph),
                       coefficients=coefficients,x_domain=domain,steps=points)
    verify_function_graph(spec,graph)
    for a,b in zip(points,points[1:]):
        guard(b.y-a.y==slope*(b.x-a.x),"MATH_SLOPE_PROOF_FAILED")
    return graph,spec

def spoken_integer(value:int)->str:
    return ("minus "+str(abs(value))) if value<0 else str(value)
def semantic_narration(spec:FunctionGraph)->list[dict]:
    guard(len(spec.steps)>=3 and spec.coefficients[2]==0,
          "ONLY_CERTIFIED_LINEAR_GRAPH")
    m,c=spec.coefficients[1],spec.coefficients[0]
    p=spec.steps
    result=[
       ("GOAL",0,f"Let us explore slope on a straight line. For this example, y equals {spoken_integer(m)} times x plus {spoken_integer(c)}."),
       ("RULE",0,"Slope is the change in y divided by the change in x. Watch the plotted points."),
    ]
    for i,item in enumerate(p):
        result.append(("POINT",i,
                       f"When x is {spoken_integer(item.x)}, y is {spoken_integer(item.y)}."))
    result.append(("CHECK",len(p)-1,
                   f"From x equals zero to x equals one, y rises by {spoken_integer(m)}. What is the slope?"))
    result.append(("RECAP",len(p)-1,
                   f"The slope is {spoken_integer(m)}. Each one step in x changes y by {spoken_integer(m)}."))
    guard(len(result)==len(p)+4,"MISSING_LESSON_SEGMENTS")
    return [{"kind":kind,"visual_step":i,"text":text,
             "source_point_id":p[i].point_id,"source_value":p[i].y}
            for kind,i,text in result]

def _render_frame(spec,graph,beat,phase:float,profile:SequenceRenderProfile)->Image.Image:
    frame=draw_function_frame(spec,graph,beat["visual_step"],profile,progress=phase)
    draw=ImageDraw.Draw(frame)
    # A generic graph as v(t) without axes/units misleads Physics learners.
    # This domain presentation is limited to the *source-certified* exact
    # integer line and gets the same after-codec decoded-frame replay.
    if beat.get("domain_display") in ("MATH_LINEAR_SLOPE","PHYSICS_VELOCITY_TIME"):
        w,h=profile.width,profile.height
        slope=beat["source_slope"]; intercept=beat["source_intercept"]
        domain=beat["domain_display"]
        guard(type(slope) is int and type(intercept) is int
              and tuple(spec.coefficients)==(intercept,slope,0),
              "DISPLAY_SOURCE_MODEL_DRIFT")
        draw.rectangle((0,0,w,round(h*.270)),fill=BLACK)
        is_physics=domain=="PHYSICS_VELOCITY_TIME"
        heading=("Velocity changes under constant acceleration" if is_physics
                 else "Slope is the rate of change")
        formula=(f"v(t) = {slope}t + {intercept}     a = {slope} m/s²"
                 if is_physics else f"y = {slope}x + {intercept}")
        large=cmu_font(43);small=cmu_font(29)
        guard(draw.textbbox((0,0),heading,font=large)[2]<w-150
              and draw.textbbox((0,0),formula,font=small)[2]<w-150,
              "DISPLAY_DOMAIN_HEADING_OVERFLOW")
        draw.text((round(w*.06),round(h*.055)),heading,font=large,fill=WHITE)
        draw.line((round(w*.06),round(h*.18),round(w*.94),round(h*.18)),
                  fill=(64,64,64),width=2)
        draw.text((round(w*.06),round(h*.205)),formula,font=small,fill=CYAN)
        axisfont=cmu_font(22)
        draw.text((round(w*.84),round(h*.565)),
                  "time (s)" if is_physics else "input x",
                  font=axisfont,fill=WHITE)
        draw.text((round(w*.525),round(h*.275)),
                  "velocity (m/s)" if is_physics else "output y",
                  font=axisfont,fill=WHITE)
    # Replace the original V3-08 bottom microcopy to reserve a true caption
    # zone; do not erase the graph plot, axes or stable object centers.
    w,h=profile.width,profile.height
    # V3-08 draws an engineer-only green 'Point point-N' label around
    # y≈.83h. A footer beginning at .865h leaves half the old text visible
    # on the caption divider. Clear the entire legacy annotation band, NOT
    # the mathematical axes/curve, and reserve a clean bottom transcript zone.
    draw.rectangle((0,round(h*.812),w,h),fill=BLACK)
    draw.line((round(w*.045),round(h*.83),round(w*.955),round(h*.83)),
              fill=(58,65,74),width=2)
    f=cmu_font(30)
    text=beat["text"]
    words=text.split()
    lines=[]
    current=""
    for word in words:
        candidate=(current+" "+word).strip()
        if draw.textbbox((0,0),candidate,font=f)[2] < w-160:current=candidate
        else:
            lines.append(current);current=word
    if current:lines.append(current)
    guard(0<len(lines)<=2,"TOO_LONG_CAPTION")
    for idx,line in enumerate(lines):
        draw.text((w//2,round(h*.858)+idx*40),line,
                  font=f,fill=WHITE,anchor="mt")
    return frame

def _record_wav(text:str,path:Path)->tuple[int,bytes,int]:
    exe=shutil.which("espeak-ng") or shutil.which("espeak")
    guard(exe is not None,"LOCAL_TTS_UNAVAILABLE")
    cmd=[exe,"-v","en-us","-s","155","-w",str(path),text]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
    guard(p.returncode==0 and path.is_file(),"LOCAL_TTS_FAILED")
    with wave.open(str(path),"rb") as w:
        rate=w.getframerate();samples=w.getnframes();audio=w.readframes(samples)
        guard(w.getnchannels()==1 and w.getsampwidth()==2 and rate>=16000
              and samples>rate//2,"BAD_ACTUAL_PCM_SOURCE")
    return rate,audio,samples

def _probe(video:Path)->tuple[dict,dict]:
    obj=json.loads(subprocess.check_output(
        ["ffprobe","-v","error","-show_streams","-of","json",str(video)],
        text=True,timeout=30))
    streams=obj["streams"]
    v=next(x for x in streams if x["codec_type"]=="video")
    a=next(x for x in streams if x["codec_type"]=="audio")
    return v,a

def _qa(*,video:Path,srt:Path,profile:SequenceRenderProfile,
        beats:list[dict],spec,graph)->dict:
    v,a=_probe(video)
    guard(v["codec_name"]=="h264" and a["codec_name"]=="aac"
          and (v["width"],v["height"])==DIMENSIONS
          and v["r_frame_rate"]==f"{FPS}/1"
          and int(v["nb_frames"])==sum(b["frames"] for b in beats),
          "NOT_REAL_NATIVE_H264_AAC")
    frames=0;replays=[];movement=[]
    for b in beats:
        frames_count=b["frames"]
        frame=frames+frames_count//2
        expected=_render_frame(spec,graph,b,(frames_count//2+.5)/frames_count,profile)
        actual=_ffmpeg_anchor(video,at=(frame+.4)/FPS,profile=profile)
        mae=_mean_absolute_error(expected,actual)
        guard(mae<12,"DECODED_PIXEL_REPLAY_FAILED")
        replays.append({"frame":frame,"seconds":round(frame/FPS,3),
                        "step":b["visual_step"],"kind":b["kind"],
                        "decoded_expected_mae":round(mae,3)})
        frames+=frames_count
    # Verify measured AAC has actual non-silent PCM in *each authored beat*,
    # not fabricated speech timestamps. Bound from actual WAV samples.
    rms=[]
    from math import sqrt
    for b in beats:
        start=b["frame_start"]/FPS
        dur=b["raw_wav_samples"]/b["wav_rate"]
        raw=subprocess.check_output([
          "ffmpeg","-v","error","-nostdin",
          "-ss",str(start),"-t",str(max(.3,dur-.1)),
          "-i",str(video),"-vn","-f","s16le","-ac","1","-ar","16000","pipe:1"],
          timeout=45)
        from array import array
        samples=array("h");samples.frombytes(raw[:len(raw)//2*2])
        amplitude=sqrt(sum(z*z for z in samples[::30])/max(len(samples[::30]),1))/32768
        guard(amplitude>.003,"SILENT_AAC_AT_SPOKEN_BEAT")
        rms.append(round(amplitude,4))
    text=srt.read_text()
    guard(all(b["text"] in text for b in beats),"SOURCE_CAPTION_MISSING")
    return {"decoded_frame_anchors":replays,"max_decoded_mae":max(x["decoded_expected_mae"] for x in replays),
            "aac_rms_per_spoken_beat":rms,"source_point_ids":[b["source_point_id"] for b in beats],
            "caption_source":"EXACT_AUTHORED_UTTERANCE_PER_PHYSICAL_WAV_BEAT",
            "word_alignment":"UNMEASURED"}

def render_math(*,topic:dict,output:Path,compiled_spec=None,
                compiled_events:list[dict]|None=None,
                compiler_provenance:dict|None=None)->dict:
    """Generic graph playback, optionally driven by *validated script* beats.

    Default is frozen V3-27 author-template demo. In compiled mode, the
    V3-28 compiler already certified all Hermes/Pedagogy/visual input and
    same-point semantic bindings before passing source-authored spoken text.
    Rendering never invents narration, claim IDs or renderer family.
    """
    authored=compiled_events is None
    if authored:
        guard(topic["domain"]=="math"
              and "slope of a line" in topic["query"].casefold(),
              "NO_CERTIFIED_TOPIC_TO_MATH_ADAPTER")
    else:
        guard(topic["domain"] in ("math","physics")
              and compiled_spec is not None and compiler_provenance is not None
              and compiler_provenance.get("status")=="VALIDATED_SOURCE_BOUND_LINEAR_BEATS",
              "UNCERTIFIED_COMPILER_INPUT")
    guard(output.is_dir() and not output.is_symlink() and not list(output.iterdir()),
          "NONEMPTY_OUTPUT_FOLDER")
    graph,spec=(make_linear_graph(slope=1,intercept=1) if authored
                else compiled_spec)
    profile=SequenceRenderProfile(width=1280,height=720,fps=FPS,
                                   seconds_per_step=1.0)
    events=semantic_narration(spec) if authored else compiled_events
    guard(all(type(b["visual_step"]) is int and 0<=b["visual_step"]<len(spec.steps)
              and b["source_point_id"]==spec.steps[b["visual_step"]].point_id
              and b["source_value"]==spec.steps[b["visual_step"]].y
              for b in events),"COMPILED_BEAT_POINT_IDENTITY_DRIFT")
    video=output/("bounded_math_slope_narrated_720p.mp4" if authored
                 else "compiled_linear_narrated_720p.mp4")
    srt=output/("bounded_math_slope_narrated_720p.srt" if authored
               else "compiled_linear_narrated_720p.srt")
    receipt=output/("math_partial_lesson_evidence.json" if authored
                   else "compiled_linear_lesson_evidence.json")
    with tempfile.TemporaryDirectory(prefix=".v3_27_",dir=output) as td:
        stage=Path(td)
        beats=[];wav_rate=None;audio_parts=[]
        running=0
        for idx,event in enumerate(events):
            rate,pcm,samples=_record_wav(event["text"],stage/f"speech_{idx}.wav")
            guard(wav_rate is None or wav_rate==rate,"MIXED_TTS_SAMPLE_RATE")
            wav_rate=rate
            raw_duration=samples/rate
            count=math.ceil(raw_duration*FPS)+1
            # Physical samples are preserved; pad only silence to the exact
            # visually aligned frame boundary. Never claim word alignment.
            needed=math.ceil(count*rate/FPS)
            pad=max(0,needed-samples)
            audio_parts.append(pcm+b"\0\0"*pad)
            beats.append({**event,"frame_start":running,"frames":count,
                          "frame_end_exclusive":running+count,
                          "wav_rate":rate,"raw_wav_samples":samples,
                          "measured_utterance_duration":round(raw_duration,6)})
            running+=count
        joined=stage/"joined.wav"
        with wave.open(str(joined),"wb") as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(wav_rate)
            for data in audio_parts:w.writeframes(data)
        movie=stage/"scene.mp4"
        p=subprocess.Popen(["ffmpeg","-nostdin","-v","error","-y",
          "-f","rawvideo","-pix_fmt","rgb24","-s:v","1280x720",
          "-r",str(FPS),"-i","pipe:0","-i",str(joined),
          "-map","0:v:0","-map","1:a:0","-c:v","libx264","-preset","ultrafast",
          "-threads","2","-crf","20","-pix_fmt","yuv420p",
          "-r",str(FPS),"-frames:v",str(running),
          "-c:a","aac","-b:a","128k","-movflags","+faststart",str(movie)],
          stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            for b in beats:
                for f in range(b["frames"]):
                    im=_render_frame(spec,graph,b,(f+.5)/b["frames"],profile)
                    p.stdin.write(im.tobytes())
            p.stdin.close()
            errors=p.stderr.read();code=p.wait(timeout=240)
            guard(code==0 and movie.exists(),
                  "H264_ENCODING_FAILED:"+errors[-150:].decode(errors="replace"))
        except Exception:
            if p.stdin and not p.stdin.closed:p.stdin.close()
            if p.poll() is None:p.kill()
            p.wait()
            raise
        def srt_time(seconds:float)->str:
            ms=round(seconds*1000)
            return f"{ms//3600000:02}:{(ms//60000)%60:02}:{(ms//1000)%60:02},{ms%1000:03}"
        srt_text=""
        for idx,b in enumerate(beats):
            st=b["frame_start"]/FPS
            ed=st+b["raw_wav_samples"]/wav_rate
            srt_text+=f"{idx+1}\n{srt_time(st)} --> {srt_time(ed)}\n{b['text']}\n\n"
        staged_srt=stage/"source.srt"
        staged_srt.write_text(srt_text)
        proof=_qa(video=movie,srt=staged_srt,profile=profile,beats=beats,spec=spec,graph=graph)
        # Immutable artifact outputs; positive proof required before linking.
        os.link(movie,video);os.link(staged_srt,srt)
        result={"schema_version":VERSION,"topic_id":topic["topic_id"],
                "status":"PARTIAL_NARRATED_SPECIALIZED_RENDER_NOT_FULL_PIPELINE",
                "family":"FUNCTION_GRAPH","video_sha256":digest(video),
                "subtitle_sha256":digest(srt),"source_query_sha256":topic["query_sha256"],
                "input_hash":topic["input_hash"],"graph_sha256":compute_content_hash(graph),
                "spec_sha256":compute_content_hash(spec),"source_math_coefficients":list(spec.coefficients),
                "width":1280,"height":720,"fps":FPS,"frames":running,
                "beats":beats,"real_h264_aac":True,
                "local_espeak_rights":"COMMERCIAL_USE_UNVERIFIED",
                "source_grounding":("POLYNOMIAL_ARITHMETIC_CERTIFIED_NOT_EXTERNAL_RESEARCH"
                                    if authored else "HERMES_APPROVED_SOURCE_REFS_AND_EXACT_LINEAR_REPLAY"),
                "research_agent":"NOT_EXECUTED",
                "script_agent":("TEMPLATE_NOT_GENERAL_MODEL" if authored else "VERIFIED_INPUT_NOT_MODEL_GENERATED"),
                "pedagogy_agent":("NOT_EXECUTED" if authored else "V3_09_CONTRACT_COMPILER_EXECUTED"),
                "visual_director_agent":("NOT_EXECUTED" if authored else "VD_CONTRACT_GATE_EXECUTED_NO_LIVE_MODEL"),
                "compiler_provenance":(None if authored else compiler_provenance),
                "scene_graph":"V3_08_SOURCE_CERTIFIED_GENERIC_LINEAR_GRAPH",
                "teacher_quality":"UNMEASURED","production":"BLOCKED",
                "audible_human_transcript":"UNMEASURED",**proof}
        receipt.write_text(json.dumps(result,indent=2)+"\n")
        # Real contact sheet from *encoded output*, all beats without
        # cherry-picked screenshot exemplars.
        frames=[]
        for b in beats:
            k=b["frame_start"]+b["frames"]//2
            frames.append(_ffmpeg_anchor(video,at=(k+.4)/FPS,profile=profile))
        thumbw=640;thumbh=360
        canvas=Image.new("RGB",(thumbw*2,thumbh*math.ceil(len(frames)/2)),BLACK)
        for i,im in enumerate(frames):
            canvas.paste(im.resize((thumbw,thumbh)),((i%2)*thumbw,(i//2)*thumbh))
        canvas.save(output/("math_all_beats_decoded_contact_sheet.jpg" if authored
                            else "compiled_all_beats_decoded_contact_sheet.jpg"),quality=90)
        return result

def run_coverage(*,root:Path,output:Path)->dict:
    guard(output.is_dir() and not any(output.iterdir()),"OUTPUT_NOT_EMPTY")
    topics,manifest=read_source(root)
    rows=[]
    failures=0
    for topic in topics:
        case={k:topic[k] for k in ("topic_id","domain","difficulty","query",
              "query_sha256","input_hash")}
        sub=output/topic["topic_id"]
        sub.mkdir()
        if topic["domain"]=="math":
            try:
                result=render_math(topic=topic,output=sub)
                case.update(status=result["status"],renderer="FUNCTION_GRAPH",
                            video_sha256=result["video_sha256"],proof_status="BOUNDED_REAL_AV_PASS",
                            full_end_to_end=False,source_script_status="AUTHOR_TEMPLATE_NOT_RESEARCH")
            except Exception as e:
                # No dropped failures. Keep exact reason and audit denominator.
                failures+=1
                case.update(status="FAIL_ATTEMPTED_REAL_AV",failure_code=type(e).__name__+":"+str(e),
                            full_end_to_end=False)
        else:
            case.update(status="ABSTAIN",reason_code=REASON[topic["domain"]],
                        full_end_to_end=False,video_sha256=None,
                        no_concept_card_fallback=True)
        rows.append(case)
    guard(len(rows)==6 and [r["domain"] for r in rows]==list(ORDER),
          "INCOMPLETE_DENOMINATOR")
    successful=sum(x["status"].startswith("PARTIAL_") for x in rows)
    abstains=sum(x["status"]=="ABSTAIN" for x in rows)
    result={"checkpoint":"V3-27","selection_source_sha256":digest(root/SELECTION),
            "corpus_frozen_sha256_claim":manifest["source_corpus_sha256"],
            "dev_topics":rows,"denominator":6,"real_video_count":successful,
            "abstain_count":abstains,"failed_attempts":failures,
            "full_end_to_end_count":0,
            "full_end_to_end_gate":"NO_GO_MULTI_DOMAIN",
            "all_six_domain_complete_video":"NO",
            "capability_audit":REACHABILITY,
            "locked_v3_16_untouched":True,"used_paid_provider":False,
            "human_quality":"UNMEASURED",
            "commercial_voice_rights":"UNVERIFIED",
            "production":"BLOCKED",
            "next_single_gap":"GENERAL_SOURCE_SCRIPT_PEDAGOGY_TO_RENDERER_NARRATION_ADAPTER",
            "no_topic_substitutions":True}
    (output/"v3_27_six_domain_coverage.json").write_text(json.dumps(result,indent=2)+"\n")
    # Timestamped observations only for actually authored media; a missing
    # renderer has no invented video time. Every one of six gaps retained.
    issues=[]
    for row in rows:
        if row["status"]=="ABSTAIN":
            issues.append({"topic_id":row["topic_id"],"domain":row["domain"],
                           "timestamp_seconds":None,"category":"capability_gap",
                           "reason":row["reason_code"],"evidence":"SOURCE_DISPATCH_NO_VIDEO"})
        elif row["status"].startswith("PARTIAL_"):
            issues.append({"topic_id":row["topic_id"],"domain":row["domain"],
                           "timestamp_seconds":0.0,"category":"pipeline_integration",
                           "reason":"NO_GENERAL_RESEARCH_SCRIPT_PEDAGOGY_DIRECTOR_HANDOFF",
                           "evidence":"MATH_ONLY_RULE_BASED_NARRATED_SPECIALIZED_VIDEO"})
        else:
            issues.append({"topic_id":row["topic_id"],"domain":row["domain"],
                           "timestamp_seconds":None,"category":"execution_failure",
                           "reason":row.get("failure_code"),"evidence":"FAILED_ATTEMPT"})
    (output/"v3_27_issue_inventory.json").write_text(
        json.dumps({"issues":issues,"all_six_accounted":len(issues)==6,
                    "no_fake_video_timestamps_for_abstains":True},indent=2)+"\n")
    report=["# V3-27 six-domain frozen development coverage (actual attempt ledger)","",
            "| Domain | Topic ID | Status | Renderer / reason | MP4 |",
            "|---|---|---|---|---|"]
    for row in rows:
        video=(row.get("video_sha256") or "—")
        report.append("| "+row["domain"]+" | "+row["topic_id"]+" | "+
                      row["status"]+" | "+
                      (row.get("renderer") or row.get("reason_code") or
                       row.get("failure_code") or "—")+" | "+video+" |")
    report += ["","**Complete end-to-end PASS: 0/6. No substitutions, no card fallback.**",
               "Successful certified math video is a partial specialized narrated adapter,",
               "not the fully integrated Research→Script→Pedagogy→Visual Director pipeline.",
               "All human/production outcomes remain unmeasured/blocked."]
    (output/"v3_27_coverage_matrix.md").write_text("\n".join(report)+"\n")
    print(f"V3_27_COVERAGE=NO_GO full_e2e=0/6 partial_real_video={successful}/6 abstain={abstains}/6 failures={failures}/6",flush=True)
    return result
