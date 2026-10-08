"""V3-19 locally synthesized audible narration + source-grounded multi-scene lessons.

No external service, provider, pretrained model download, generated executable
code, or golden renderer scripts. espeak-ng / espeak produce *actual spoken WAV*.
Every subtitle is one measured spoken segment; no fabricated word/phoneme
timestamps or forced alignment claims. All rendered animation frames derive
from V3-06 oracle trace state and real measured audio lengths.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave

from PIL import Image,ImageDraw
from pydantic import BaseModel,ConfigDict,Field,model_validator

from app.domain.timeline import ResolvedSceneTiming,ResolvedTimeline,SubtitleCue
from app.pipeline.assembly import VideoAssembler,build_srt_content
from learnflow_v2.repair import compute_content_hash
from .blackboard_style import BLACK,CYAN,WHITE,cmu_font
from .binary_search_trace import certify_and_route_binary_search
from .integration_slice import run_integrated_binary_clip,IntegratedClipReceipt
from .offline_lesson_source import BinaryLessonSource
from .sequence_renderer import SequenceRenderProfile,draw_binary_search_frame,_layout
from .models import SemanticContractError

VERSION="v3-19-narrated-multi-scene-offline-v1"
FPS=12
W,H=640,360


def _block(code:str)->None:
    raise SemanticContractError("V3_19_"+code)


def _sha(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _exec(args:list[str],timeout:int=80)->subprocess.CompletedProcess:
    try:
        x=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                         check=False,timeout=timeout)
    except (OSError,subprocess.TimeoutExpired) as e:
        _block("TOOL_UNAVAILABLE_OR_TIMEOUT")
    if x.returncode:
        _block("MEDIA_TOOL_FAILED")
    return x


def _wav_audit(path:Path)->tuple[float,float,int,int]:
    if not path.is_file() or path.is_symlink():_block("MISSING_SPOKEN_AUDIO")
    try:
        with wave.open(str(path),"rb") as w:
            channels,rate,n,sw=w.getnchannels(),w.getframerate(),w.getnframes(),w.getsampwidth()
            raw=w.readframes(n)
    except (wave.Error,OSError,EOFError):
        _block("INVALID_SPEECH_WAV")
    if channels!=1 or sw!=2 or not 16000<=rate<=48000 or n==0 or len(raw)!=n*2:
        _block("UNSUPPORTED_OR_EMPTY_WAV")
    from array import array
    a=array("h");a.frombytes(raw)
    rms=math.sqrt(sum(int(x)*int(x) for x in a)/len(a))/32768
    if not math.isfinite(rms) or rms<.006:
        _block("SILENT_OR_LOW_ENERGY_NARRATION")
    return n/rate,rms,n,rate


def _tts_executable()->str:
    for name in ("espeak-ng","espeak"):
        tool=shutil.which(name)
        if tool:return tool
    _block("OFFLINE_LICENSED_SPEECH_PROVIDER_MISSING")


def _record(text:str,path:Path,tts:str)->tuple[float,float,str,int,int]:
    if not text or not text.strip() or "\n" in text or len(text)>145:
        _block("INVALID_SOURCE_GROUNDED_NARRATION")
    _exec([tts,"-v","en-us","-s","155","-a","140","-w",str(path),text])
    duration,rms,n,rate=_wav_audit(path)
    if not 1.0<duration<19:_block("NARRATION_DURATION_OUT_OF_BOUNDS")
    return duration,rms,_sha(path),n,rate


def _speech_lines(source:BinaryLessonSource)->list[dict]:
    v=source.trace.query.values;t=source.trace.query.target
    first=f"We will search a sorted array for {t}, using comparisons rather than inspecting every item."
    mechanism=("Start with the low and high bounds. Compare the middle value, "
               "then keep only the interval that can still hold the target.")
    parts=[
        dict(scene_id="intro",role="INTRODUCTION",step=0,text=first,
             beat_id="beat-01",segment_id="seg-01"),
        dict(scene_id="mechanism",role="EXPLANATION",step=0,text=mechanism,
             beat_id="beat-01",segment_id="seg-01"),
    ]
    for i,s in enumerate(source.trace.steps):
        beat=f"beat-{i+1:02d}"
        if s.phase=="COMPARE":
            if s.action=="DISCARD_LEFT":
                text=f"The middle value is {s.observed}, below {t}. Move the low bound to index {s.next_low}."
            elif s.action=="KEEP_LEFT":
                text=f"The middle value is {s.observed}, above {t}. Keep the left interval through index {s.next_high}."
            else:
                text=f"The middle value equals {t}. Record index {s.mid}, and check whether an earlier match exists."
        else:
            text=(f"The leftmost match for {t} is at index {source.trace.result_index}."
                  if source.trace.result_index is not None else
                  f"The target {t} does not occur in the sorted array.")
        parts.append(dict(scene_id=f"trace-{i+1:02d}",role="WORKED_EXAMPLE",
                          step=i,text=text,beat_id=beat,segment_id=f"seg-{i+1:02d}"))
    tail=("Binary search halves the remaining interval at each comparison. "
          "The number of comparisons grows logarithmically with the array length.")
    parts.append(dict(scene_id="recap",role="RECAP",step=len(source.trace.steps)-1,
                      text=tail,beat_id=f"beat-{len(source.trace.steps):02d}",
                      segment_id=f"seg-{len(source.trace.steps):02d}"))
    # Source script references are V3-05 certified; narration text is a
    # separate explicit authored teaching script tied to the same identities.
    if any(b["beat_id"] not in {x.beat_id for x in source.plan.beats} for b in parts):
        _block("NARRATION_BEAT_NOT_IN_CERTIFIED_PLAN")
    return parts


def _narrated_frame(*,source:BinaryLessonSource,spec:dict,
                  profile:SequenceRenderProfile,progress:float)->Image.Image:
    role=spec["role"]
    # This is the original V3-06 semantic renderer for EVERY frame,
    # not a video hold/loop, nor a fallback concept-card graphic.
    # Across an APPLY→OBSERVE or APPLY→RESULT cut, the settled oracle
    # state MUST persist. Replaying V3-06's 0→1 step tween in a new OBSERVE
    # scene would momentarily rewind LOW/HIGH/MID and violate continuity.
    # Only APPLY is allowed to animate between adjacent certified states.
    stable_scene=spec.get("event_kind") in ("OBSERVE","RESULT")
    image=draw_binary_search_frame(
        trace=source.trace,step_index=spec.get("visual_step",spec["step"]),
        progress=(1.0 if stable_scene else progress),
        subtitle="",profile=profile)
    d=ImageDraw.Draw(image)
    # Distinguish pedagogical scene roles without covering the array.
    d.rectangle((0,0,W,25),fill=BLACK)
    phase={"INTRODUCTION":"SEARCH IN A SORTED ARRAY",
           "EXPLANATION":"HOW BOUNDS CHANGE",
           "WORKED_EXAMPLE":"COMPARE THE MIDDLE",
           "RECAP":"WHAT WE LEARNED"}[role]
    d.text((12,5),phase,font=cmu_font(14),fill=CYAN)
    # Separate pedagogical visual transitions: the introduction
    # walks the SORTED source indices; the explanation moves the
    # bound/midpoint pointers; the recap revisits the TRUE oracle
    # comparison path. Never loop/hold a 3-second animation.
    centers=_layout(profile,len(source.trace.query.values))
    if role=="INTRODUCTION":
        index=min(len(centers)-1,int(progress*len(centers)))
        px=centers[index]
        d.rounded_rectangle((px-21,168,px+21,220),radius=7,
                            outline=CYAN,width=2)
    elif role=="RECAP":
        visited=[step.mid for step in source.trace.steps if step.mid is not None]
        upto=max(1,math.ceil(progress*len(visited)))
        for mid in visited[:upto]:
            px=centers[mid]
            d.ellipse((px-8,148,px+8,164),outline=CYAN,width=2)
    # Reserve a strict two-zone hierarchy: semantic action lives
    # at Y=252..270, actual burned subtitles only at Y>=295. The
    # original V3-06 bottom labels would collide with subtitles;
    # intentionally mask and re-express the certified action.
    d.rectangle((0,244,W,H),fill=BLACK)
    d.line((24,245,W-24,245),fill=(45,50,58),width=1)
    step=source.trace.steps[spec["step"]]
    event_kind=spec.get("event_kind")
    if event_kind=="OBSERVE":
        action="READ THE MIDPOINT — BOUNDS UNCHANGED"
    elif event_kind=="APPLY":
        if step.action=="DISCARD_LEFT":
            action=f"ADVANCE LOW TO {step.next_low}"
        elif step.action=="KEEP_LEFT":
            action=f"REDUCE HIGH TO {step.next_high}"
        else:
            action=f"RECORD CANDIDATE {step.mid} — CHECK EARLIER"
    else:
        action=(
        ("SORTED INPUT" if role=="INTRODUCTION" else "COMPARE THE MIDPOINT")
        if role in ("INTRODUCTION","EXPLANATION") else
        ("LEFTMOST MATCH: "+str(source.trace.result_index)
         if role=="RECAP" and source.trace.result_index is not None else
         ("TARGET NOT PRESENT" if role=="RECAP" else
          step.action.replace("_"," ")))
    )
    d.text((24,252),action,font=cmu_font(15),fill=CYAN)
    # Draw a small progress indicator based on elapsed spoken frames.
    d.rectangle((0,H-5,round(W*progress),H-1),fill=CYAN)
    return image


def _encode_scene(*,source:BinaryLessonSource,spec:dict,n:int,
                  output:Path,profile:SequenceRenderProfile)->None:
    if n<12 or n>260:_block("SCENE_FRAME_BUDGET")
    role=spec["role"]
    cmd=["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
         "-f","rawvideo","-pixel_format","rgb24","-video_size",f"{W}x{H}",
         "-framerate",str(FPS),"-i","pipe:0","-an","-c:v","libx264",
         "-threads","2","-preset","ultrafast","-pix_fmt","yuv420p",
         "-r",str(FPS),"-frames:v",str(n),str(output)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE)
    try:
        for j in range(n):
            progress=j/max(n-1,1)
            image=_narrated_frame(source=source,spec=spec,profile=profile,progress=progress)
            if proc.stdin is None:_block("FFMPEG_PIPE_CLOSED")
            proc.stdin.write(image.tobytes())
        proc.stdin.close()
        exit_code=proc.wait(timeout=80)
        if exit_code:
            _block("SCENE_ENCODER_FAILED")
    except Exception:
        if proc.stdin and not proc.stdin.closed:proc.stdin.close()
        if proc.poll() is None:proc.kill()
        proc.wait()
        raise
    if not output.is_file() or output.stat().st_size<1000:
        _block("SCENE_VIDEO_MISSING")


def _probe(path:Path)->dict:
    raw=_exec(["ffprobe","-v","error","-show_streams","-show_format",
               "-of","json",str(path)],timeout=40)
    return json.loads(raw.stdout)


class NarratedLessonReceipt(BaseModel):
    model_config=ConfigDict(frozen=True,extra="forbid")
    version:str=VERSION
    kind:str="OFFLINE_MULTISCENE_REAL_SPEECH_NOT_PUBLISHED"
    source_trace_sha256:str
    baseline_beat_manifest_sha256:str
    baseline_route_sha256:str
    prior_binary_preview_sha256:str
    speech_engine:str
    speech_version:str
    speech_voice:str="en-us"
    speech_origin:str="LOCAL_ESPEAK_SYNTHESIZED_WAV"
    speech_license_note:str="OFFLINE_ESPEAK_ENGINE_OS_DISTRIBUTION_GPL_VOICE_RIGHTS_REQUIRE_REVIEW"
    transcript_source:str="AUTHOR_DEFINED_CERTIFIED_TRACE_GROUNDED"
    segments:tuple[dict,...]
    total_frames:int
    duration_seconds:float
    video_sha256:str
    subtitle_sha256:str
    video_codec:str="h264"
    audio_codec:str="aac"
    spoken_audio_verified:bool=True
    subtitles_burned:bool=True
    segment_alignment:str="MEASURED_AUDIO_SAMPLES_SCENE_BOUNDARIES"
    word_alignment:str="UNMEASURED_NOT_FORCED_ALIGNMENT"
    real_human_lexical_review:str="UNMEASURED"
    global_signal_consumption:str="PARTIAL_DEFERRED"
    publication:str="PUBLISH_BLOCKED"
    real_lesson_quality:str="UNMEASURED"
    event_boundary_alignment:str="UNMEASURED_SCENE_ONLY"
    event_proof_sha256:str|None=None
    report_sha256:str

    @model_validator(mode="after")
    def _guard(self):
        cursor=0
        seen=set()
        if self.total_frames<24 or self.duration_seconds<=0:
            raise ValueError("V3_19_INVALID_TIMELINE")
        for seg in self.segments:
            if (seg["scene_id"] in seen or
                seg["frame_start"]!=cursor or
                seg["frame_end_exclusive"]<=cursor or
                seg["source_trace_sha256"]!=self.source_trace_sha256 or
                not seg["text"].strip() or
                seg["claim_refs"]!=["claim-01"] or
                seg["object_ids"]!=["array-01"] or
                abs(seg["seconds_start"]-cursor/FPS)>1e-6 or
                abs(seg["seconds_end"]-seg["frame_end_exclusive"]/FPS)>1e-6 or
                abs(seg["subtitle_start"]-seg["seconds_start"])>1e-6 or
                abs(seg["subtitle_end"]-seg["subtitle_start"]-
                    seg["raw_spoken_duration_seconds"])>1e-5 or
                seg["speech_energy_rms"]<.006):
                raise ValueError("V3_19_UNGROUNDED_SCENE_OR_AUDIO_BOUNDARY")
            seen.add(seg["scene_id"])
            cursor=seg["frame_end_exclusive"]
        if len(self.segments)<4 or abs(cursor-self.total_frames)>1:
            raise ValueError("V3_19_MULTISCENE_FRAME_CONTINUITY_FAILED")
        if self.event_boundary_alignment=="MEASURED_UTTERANCE_BOUNDARIES_NOT_WORD_LEVEL":
            if (not self.event_proof_sha256 or
                not any(s.get("event_kind")=="APPLY" for s in self.segments)):
                raise ValueError("V3_20_MISSING_PHYSICAL_EVENT_PROOF")
        elif (self.event_boundary_alignment!="UNMEASURED_SCENE_ONLY" or
              self.event_proof_sha256 is not None):
            raise ValueError("V3_20_INVALID_EVENT_ALIGNMENT_STATUS")
        if (self.publication!="PUBLISH_BLOCKED" or
            self.segment_alignment!="MEASURED_AUDIO_SAMPLES_SCENE_BOUNDARIES" or
            self.word_alignment!="UNMEASURED_NOT_FORCED_ALIGNMENT" or
            self.real_human_lexical_review!="UNMEASURED" or
            self.kind!="OFFLINE_MULTISCENE_REAL_SPEECH_NOT_PUBLISHED" or
            len(self.segments)<4 or
            self.report_sha256!=compute_content_hash(
                self.model_dump(mode="json",exclude={"report_sha256"}))):
            raise ValueError("V3_19_FORGED_PUBLICATION_OR_ALIGNMENT")
        return self


def build_narrated_lesson(*,source:BinaryLessonSource,out:Path,
                          fault:str|None=None,
                          event_aware:bool=False)->NarratedLessonReceipt:
    """Safe output commit: private staging, no overwrites, source replay."""
    if not out.is_dir() or out.is_symlink():_block("UNSAFE_OUTPUT_DIR")
    final=out/"narrated_binary_lesson.mp4"
    manifest=out/"narrated_binary_lesson.receipt.json"
    subs=out/"narrated_binary_lesson.srt"
    if any(p.exists() or p.is_symlink() for p in (final,manifest,subs)):
        _block("NO_CLOBBER_FINAL")
    tts=_tts_executable()
    version=_exec([tts,"--version"]).stdout.decode(errors="replace").splitlines()[0][:150]
    original=certify_and_route_binary_search(trace=source.trace,**source.params())
    profile=SequenceRenderProfile(width=W,height=H,fps=FPS,seconds_per_step=.75)
    from .event_alignment import authored_event_specs,certify_event_boundaries
    cases=authored_event_specs(source) if event_aware else _speech_lines(source)
    with tempfile.TemporaryDirectory(prefix=".v3_19_narration_",dir=out) as td:
        stage=Path(td)
        baseline_path=stage/"baseline"
        baseline_path.mkdir()
        earlier=run_integrated_binary_clip(source=source,out_dir=baseline_path,profile=profile)
        if not isinstance(earlier,IntegratedClipReceipt):
            _block("V3_18_SOURCE_NOT_CERTIFIED")
        if earlier.trace_sha256!=source.trace.trace_sha256:
            _block("ORACLE_TRACE_DRIFT")
        sound=stage/"audio";sound.mkdir()
        scene_files=[];timings=[];evidence=[];cum_frames=0
        for index,spec in enumerate(cases):
            segment_id=spec["scene_id"]
            raw=sound/f"{segment_id}.wav"
            actual_duration,rms,wav_sha,samples,rate=_record(spec["text"],raw,tts)
            # Each scene lasts only what its MEASURED spoken audio requires.
            # The extra <=1 frame ensures narration is never clipped; this
            # is not an invented subtitle or phoneme timing heuristic.
            frames=math.ceil(actual_duration*FPS)+1
            target_duration=frames/FPS
            padded=sound/f"{segment_id}.padded.wav"
            _exec(["ffmpeg","-hide_banner","-v","error","-nostdin","-y",
                   "-i",str(raw),"-af","apad","-t",f"{target_duration:.9f}",
                   "-ar","48000","-ac","1","-c:a","pcm_s16le",str(padded)])
            padded_duration,pad_rms,_,_= _wav_audit(padded)
            if abs(padded_duration-target_duration)>.002:
                _block("PADDED_AUDIO_DURATION_DRIFT")
            start=cum_frames/FPS;end=(cum_frames+frames)/FPS
            # Exactly ONE subtitle cue per spoken WAV; no guessed subword
            # timing and no proportional fallback from the legacy builder.
            cue=SubtitleCue(start_seconds=start,
                            end_seconds=start+actual_duration,text=spec["text"])
            timings.append(ResolvedSceneTiming(
                scene_id=segment_id,raw_audio_path=str(raw),
                padded_audio_path=str(padded),
                audio_duration_seconds=actual_duration,
                render_duration_seconds=target_duration,
                start_seconds=start,end_seconds=end,subtitle_cues=[cue]))
            scene=stage/f"scene-{index:02d}.mp4"
            _encode_scene(source=source,spec=spec,n=frames,output=scene,profile=profile)
            scenes=_probe(scene)["streams"]
            if len(scenes)!=1 or scenes[0]["codec_name"]!="h264" or int(scenes[0]["nb_frames"])!=frames:
                _block("SCENE_FRAME_OR_CODEC_CHANGED")
            scene_files.append(scene)
            evidence.append({
                **spec,
                "frame_start":cum_frames,"frame_end_exclusive":cum_frames+frames,
                "seconds_start":start,"seconds_end":end,
                "raw_spoken_duration_seconds":actual_duration,
                "raw_spoken_samples":samples,"spoken_sample_rate":rate,
                "speech_energy_rms":round(rms,5),
                "spoken_wav_sha256":wav_sha,
                "scene_video_sha256":_sha(scene),
                "subtitle_start":start,"subtitle_end":start+actual_duration,
                "claim_refs":["claim-01"],"object_ids":["array-01"],
                "source_trace_sha256":source.trace.trace_sha256,
                "speech_source":"ESPEAK_LOCAL_SYNTHESIS",
            })
            cum_frames+=frames
        timeline=ResolvedTimeline(
            scenes=timings,total_duration_seconds=cum_frames/FPS)
        raw_subs=build_srt_content(timeline)
        if len(raw_subs.split("-->"))-1!=len(cases):
            _block("SUBTITLE_MISSING_OR_DEDUPLICATED")
        if fault=="BAD_SUBTITLE_TIME":
            first=timings[0]
            first.subtitle_cues[0].start_seconds=first.end_seconds+1
        if fault=="BAD_BEAT_ID":
            evidence[2]["beat_id"]="beat-invented"
        if any(e["beat_id"] not in {b.beat_id for b in source.plan.beats}
               for e in evidence):
            _block("SCENE_BEAT_SOURCE_UNVERIFIED")
        for e,t in zip(evidence,timings,strict=True):
            if (t.subtitle_cues[0].start_seconds<t.start_seconds-1e-6 or
                t.subtitle_cues[0].end_seconds>t.end_seconds+1e-6 or
                t.subtitle_cues[0].text!=e["text"] or
                t.subtitle_cues[0].start_seconds!=e["subtitle_start"]):
                _block("SUBTITLE_OR_NARRATION_OUT_OF_SCENE")
        if fault=="MISSING_AUDIO":
            (sound/"intro.padded.wav").unlink()
        if fault=="AFTER_SCENES_RENDERED":
            _block("INJECTED_FAIL_AFTER_SCENES")
        staged_mp4=stage/"narrated.pending.mp4"
        assembler=VideoAssembler(
            fps=FPS,timeout_seconds=240,
            subtitle_force_style=(
                "Fontname=CMU Serif,Fontsize=14,PrimaryColour=&H00FFFFFF&,"
                "OutlineColour=&H00000000&,Outline=1,Shadow=0,MarginV=18,Alignment=2"
            ),
        )
        asyncio.run(assembler.assemble(
            job_id="v3_19_local_demo",scene_video_paths=scene_files,
            timeline=timeline,output_path=staged_mp4,subtitles_path=stage/"subtitles.srt"))
        if fault=="AFTER_ASSEMBLY_PARTIAL":
            _block("INJECTED_FAIL_AFTER_ASSEMBLY")
        info=_probe(staged_mp4)
        vs=[x for x in info["streams"] if x["codec_type"]=="video"]
        aud=[x for x in info["streams"] if x["codec_type"]=="audio"]
        if len(vs)!=1 or len(aud)!=1 or vs[0]["codec_name"]!="h264" or aud[0]["codec_name"]!="aac":
            _block("FINAL_REAL_SPEECH_AUDIO_VIDEO_STREAMS_MISSING")
        actual_frames=int(vs[0].get("nb_frames") or 0)
        if abs(actual_frames-cum_frames)>1:
            _block("FINAL_FRAME_TIMELINE_DRIFT")
        final_duration=float(info["format"]["duration"])
        if abs(final_duration-timeline.total_duration_seconds)>.16:
            _block("FINAL_AUDIO_VIDEO_DURATION_DRIFT")
        # Check final decoded sound is actually audible, not merely an AAC
        # stream of empty bytes or appended fake silence.
        pcm=_exec(["ffmpeg","-nostdin","-v","error","-i",str(staged_mp4),
                   "-map","0:a:0","-f","s16le","-ac","1","-ar","16000","pipe:1"],timeout=60).stdout
        from array import array
        a=array("h");a.frombytes(pcm[:len(pcm)//2*2])
        if len(a)<16000 or math.sqrt(sum(int(x)*int(x) for x in a)/len(a))/32768<.005:
            _block("FINAL_AUDIO_IS_SILENT")
        if not (stage/"subtitles.srt").is_file() or (stage/"subtitles.srt").read_text()!=raw_subs:
            _block("BURNED_SUBTITLE_SOURCE_DRIFT")
        if fault=="WRONG_AUDIO_ALIGNMENT":
            evidence[1]["seconds_start"]+=2
        for e,t in zip(evidence,timings,strict=True):
            if (abs(e["seconds_start"]-t.start_seconds)>1e-7 or
                abs(e["seconds_end"]-t.end_seconds)>1e-7 or
                abs(e["subtitle_end"]-e["subtitle_start"]-e["raw_spoken_duration_seconds"])>1e-5):
                _block("MEASURED_AUDIO_BEAT_ALIGNMENT_DRIFT")
        event_proof=(certify_event_boundaries(
            source=source,segments=tuple(evidence),fps=FPS
        ) if event_aware else None)
        if event_proof is not None:
            (stage/"event-proof.json").write_text(
                json.dumps(event_proof,indent=2)+"\n",encoding="utf-8")
        data=dict(
            event_boundary_alignment=("MEASURED_UTTERANCE_BOUNDARIES_NOT_WORD_LEVEL"
                                      if event_aware else "UNMEASURED_SCENE_ONLY"),
            event_proof_sha256=(event_proof["proof_sha256"] if event_proof else None),
            version=VERSION,kind="OFFLINE_MULTISCENE_REAL_SPEECH_NOT_PUBLISHED",
            source_trace_sha256=source.trace.trace_sha256,
            baseline_beat_manifest_sha256=earlier.source_beat_manifest_sha256,
            baseline_route_sha256=earlier.route_sha256,
            prior_binary_preview_sha256=earlier.report_sha256,
            speech_engine=Path(tts).name,speech_version=version,
            segments=tuple(evidence),total_frames=actual_frames,
            duration_seconds=final_duration,
            video_sha256=_sha(staged_mp4),
            subtitle_sha256=hashlib.sha256(raw_subs.encode()).hexdigest(),
        )
        preliminary=NarratedLessonReceipt.model_construct(**data)
        payload=preliminary.model_dump(mode="json",exclude={"report_sha256"})
        receipt=NarratedLessonReceipt.model_validate(
            payload|{"report_sha256":compute_content_hash(payload)})
        raw_receipt=stage/"receipt.json"
        raw_receipt.write_text(json.dumps(receipt.model_dump(mode="json"),
                                          indent=2,ensure_ascii=False)+"\n")
        linked=[]
        try:
            for a,b in ((staged_mp4,final),(stage/"subtitles.srt",subs),(raw_receipt,manifest)):
                os.link(a,b);linked.append(b)
            if event_aware:
                os.link(stage/"event-proof.json",
                        out/"narrated_binary_lesson.event_proof.json")
                linked.append(out/"narrated_binary_lesson.event_proof.json")
            if fault=="AFTER_FINAL_LINK":
                _block("INJECTED_FAIL_AFTER_FINAL_LINK")
        except Exception:
            for p in linked:p.unlink(missing_ok=True)
            raise
    return receipt


def verify_narrated_lesson(*,source:BinaryLessonSource,folder:Path,
                           receipt:NarratedLessonReceipt)->None:
    """Replay source, subtitles, video frames, and actual per-scene AAC voice.

    Word/phoneme alignment and spoken-content ASR fidelity remain UNMEASURED.
    """
    root=Path(folder)
    video=root/"narrated_binary_lesson.mp4"
    subtitles=root/"narrated_binary_lesson.srt"
    manifest=root/"narrated_binary_lesson.receipt.json"
    if any(not p.is_file() or p.is_symlink() for p in (video,subtitles,manifest)):
        _block("MISSING_FINAL_VIDEO_SUBS_OR_MANIFEST")
    if (_sha(video)!=receipt.video_sha256 or
        hashlib.sha256(subtitles.read_bytes()).hexdigest()!=receipt.subtitle_sha256):
        _block("STALE_AUDIO_VIDEO_OR_SUBTITLE_FILE")
    replay=NarratedLessonReceipt.model_validate_json(manifest.read_text(encoding="utf-8"))
    if receipt!=replay:_block("STALE_MANIFEST_OR_SOURCE")
    original=certify_and_route_binary_search(trace=source.trace,**source.params())
    if (receipt.source_trace_sha256!=source.trace.trace_sha256 or
        receipt.baseline_route_sha256!=original.route.decision_hash):
        _block("SOURCE_TRACE_OR_ROUTE_CHANGED")
    from .event_alignment import authored_event_specs,verify_event_proof
    is_event_aligned=(receipt.event_boundary_alignment==
                      "MEASURED_UTTERANCE_BOUNDARIES_NOT_WORD_LEVEL")
    expected=(authored_event_specs(source) if is_event_aligned
              else _speech_lines(source))
    if is_event_aligned:
        proof_path=root/"narrated_binary_lesson.event_proof.json"
        if not proof_path.is_file() or proof_path.is_symlink():
            _block("MISSING_PHYSICAL_EVENT_PROOF")
        proof=json.loads(proof_path.read_text(encoding="utf-8"))
        if proof.get("proof_sha256")!=receipt.event_proof_sha256:
            _block("EVENT_PROOF_REHASH_OR_STALE")
        verify_event_proof(source=source,segments=receipt.segments,
                           supplied=proof,fps=FPS)
    elif (root/"narrated_binary_lesson.event_proof.json").exists():
        _block("UNDECLARED_EVENT_PROOF")
    if len(expected)!=len(receipt.segments):_block("SCENE_COUNT_OR_SOURCE_CHANGED")
    for emitted,orig in zip(receipt.segments,expected,strict=True):
        if any(emitted[k]!=orig[k] for k in (
            "scene_id","role","step","text","beat_id","segment_id"
        ) if (not is_event_aligned or k in orig)) or (
            is_event_aligned and any(
                emitted.get(k)!=orig.get(k) for k in (
                    "event_id","event_kind","visual_step",
                    "expected_low","expected_high","expected_mid",
                ))):
            _block("NARRATION_OR_BEAT_SOURCE_CHANGED")
    srt=subtitles.read_text(encoding="utf-8")
    from app.pipeline.assembly import format_srt_timestamp
    for i,e in enumerate(receipt.segments,1):
        cue=(f"{i}\n{format_srt_timestamp(e['subtitle_start'])} --> "
             f"{format_srt_timestamp(e['subtitle_end'])}\n{e['text']}\n")
        if cue not in srt:_block("SUBTITLE_TEXT_OR_TIME_DRIFT")
    info=_probe(video)
    vids=[x for x in info["streams"] if x["codec_type"]=="video"]
    audio=[x for x in info["streams"] if x["codec_type"]=="audio"]
    if (len(vids)!=1 or len(audio)!=1 or
        vids[0]["codec_name"]!="h264" or audio[0]["codec_name"]!="aac"):
        _block("MISSING_REAL_VIDEO_OR_SPOKEN_AUDIO")
    if abs(int(vids[0]["nb_frames"])-receipt.total_frames)>1:
        _block("FRAME_COUNT_DRIFT")
    if abs(float(info["format"]["duration"])-receipt.duration_seconds)>.03:
        _block("AV_DURATION_DRIFT")
    # Decode ALL pixels, not just trust MP4 container metadata.
    raw=_exec(["ffmpeg","-nostdin","-v","error","-i",str(video),
               "-map","0:v:0","-f","rawvideo","-pix_fmt","rgb24","pipe:1"],timeout=150).stdout
    if (abs(len(raw)//(W*H*3)-receipt.total_frames)>1 or
        len(raw)%(W*H*3)):
        _block("DECODED_PIXEL_FRAME_INCOMPLETE")
    # Independent source/semantic pixel replay: each authored scene must
    # match the V3-06 oracle state rendered from the certified trace.
    # Verify three decoded frames per scene, excluding intentionally burned
    # caption zone (Y>=244). This rejects a nice-looking but wrong-state clip.
    from PIL import ImageChops,ImageStat
    profile=SequenceRenderProfile(width=W,height=H,fps=FPS,seconds_per_step=.75)
    all_frames=memoryview(raw)
    size=W*H*3
    for emitted,expected_spec in zip(receipt.segments,expected,strict=True):
        span=emitted["frame_end_exclusive"]-emitted["frame_start"]
        for idx in (0,span//2,span-1):
            frame_no=emitted["frame_start"]+idx
            raw_frame=bytes(all_frames[frame_no*size:(frame_no+1)*size])
            frame=Image.frombytes("RGB",(W,H),raw_frame)
            oracle=_narrated_frame(
                source=source,spec=expected_spec,profile=profile,
                progress=idx/max(span-1,1))
            compare=ImageChops.difference(
                frame.crop((0,0,W,239)),oracle.crop((0,0,W,239)))
            mae=sum(ImageStat.Stat(compare).mean)/3
            if mae>22.0:
                _block("DECODED_SCENE_ORACLE_SEMANTIC_PIXELS_CHANGED")
    # Verify actual decoded frames immediately adjacent to every
    # APPLY→OBSERVE/RESULT cut: the same certified visual step must not
    # replay its old LOW/HIGH/MID tween. This caught a real 20.000s
    # visual rewind missed by 3-anchor-per-scene tests.
    if is_event_aligned:
        for i,part in enumerate(receipt.segments[:-1]):
            following=receipt.segments[i+1]
            if (part.get("event_kind")!="APPLY" or
                following.get("event_kind") not in ("OBSERVE","RESULT")):
                continue
            if part["visual_step"]!=following["visual_step"]:
                _block("EVENT_SCENE_ORACLE_STEP_DISCONTINUITY")
            old_frame=part["frame_end_exclusive"]-1
            new_frame=following["frame_start"]
            if new_frame!=old_frame+1:
                _block("EVENT_SCENE_FRAME_GAP")
            images=[]
            for frame_num in (old_frame,new_frame):
                z=bytes(all_frames[frame_num*size:(frame_num+1)*size])
                images.append(Image.frombytes("RGB",(W,H),z).crop((0,80,W,235)))
            diff=ImageChops.difference(images[0],images[1])
            mae=sum(ImageStat.Stat(diff).mean)/3.0
            # The verified regression produced MAE=4.12 on frame 239→240;
            # a 5.0 threshold would incorrectly let that actual rewind pass.
            if mae>2.0:
                _block("EVENT_SCENE_BOUNDARY_REWINDS_STATE")
    # Visual QA: inspect decoded output (after SRT burn) to guarantee a
    # deliberate BLACK gutter between source action label (Y=252..270) and
    # real spoken subtitles (nominal Y>=300). Catch the V3-19 original
    # overlay bug which a successful FFmpeg exit cannot detect.
    decoded=memoryview(raw)
    pixels_per_frame=W*H*3
    for seg in receipt.segments:
        frame_idx=(seg["frame_start"]+seg["frame_end_exclusive"])//2
        frame=decoded[frame_idx*pixels_per_frame:(frame_idx+1)*pixels_per_frame]
        suspicious=0
        for y in range(280,295):
            strip=frame[(y*W+30)*3:(y*W+W-30)*3]
            suspicious+=sum(1 for x in strip if x>145)
        if suspicious>90:
            _block("SUBTITLE_OVERLAPS_ACTION_SAFE_ZONE")
    # Actual non-silent speech must be present in every final AAC scene.
    from array import array
    for e in receipt.segments:
        pcm=_exec(["ffmpeg","-nostdin","-v","error",
                   "-ss",f"{e['seconds_start']:.5f}","-t",
                   f"{e['raw_spoken_duration_seconds']:.5f}",
                   "-i",str(video),"-map","0:a:0","-ar","16000","-ac","1",
                   "-f","s16le","pipe:1"],timeout=30).stdout
        a=array("h");a.frombytes(pcm[:len(pcm)//2*2])
        if (len(a)<6000 or
            math.sqrt(sum(int(x)*int(x) for x in a)/len(a))/32768<.004):
            _block("FINAL_SEGMENT_AUDIO_SILENT_OR_MISALIGNED")
