"""V3-22 native 720p / 24fps source-grounded narrated lesson retrofit.

No upscaling from 360p. Reuses real original V3-20 AAC packets, SRT text,
source trace and certified utterance/event proof. The new *independent* output
remains a private offline candidate; voice/learning/release NOT certified.
"""
from __future__ import annotations

from array import array
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageChops, ImageStat

from .blackboard_style import BLACK, CYAN, WHITE, cmu_font
from .event_alignment import verify_event_proof
from .lesson_quality import QualityEvidenceError, audit_media, parse_srt, _frames, _probe
from .offline_lesson_source import build_binary_lesson_source
from .sequence_renderer import SequenceRenderProfile, _layout, draw_binary_search_frame

VERSION = "v3-22-native-720p-24fps-v1"
WIDTH, HEIGHT, FPS = 1280, 720, 24
PROFILE = SequenceRenderProfile(width=WIDTH, height=HEIGHT, fps=FPS, seconds_per_step=.75)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise QualityEvidenceError("V3_22_" + code)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cmd(args: list[str], *, timeout: int=240) -> bytes:
    result = subprocess.run(args, capture_output=True, check=False, timeout=timeout)
    _require(result.returncode == 0, "FFMPEG_OR_PROBE_FAILED")
    return result.stdout


def _adts_sha(path: Path) -> str:
    """Hash actual AAC packets, not decoded approximate acoustic similarity."""
    return hashlib.sha256(_cmd([
        "ffmpeg", "-nostdin", "-v", "error", "-i", str(path),
        "-map", "0:a:0", "-c:a", "copy", "-f", "adts", "pipe:1",
    ], timeout=45)).hexdigest()


def _pacing(kind: str, elapsed_fraction: float) -> float:
    fraction = max(0.0, min(1.0, elapsed_fraction))
    if kind == "OBSERVE" or kind == "RESULT":
        return 1.0
    if kind == "APPLY":
        # Observable hold → ease → settle; only within the true APPLY utterance.
        # The original V3-06 tween completes when progress reaches 0.32.
        return 0.32 * max(0.0, min(1.0, (fraction-.18)/.62))
    return fraction


def _action(source, part: dict) -> str:
    kind = part.get("event_kind")
    if kind == "OBSERVE":
        return "READ THE MIDPOINT  /  BOUNDS UNCHANGED"
    step = source.trace.steps[part["step"]]
    if kind == "APPLY":
        if step.action == "DISCARD_LEFT":
            return "ADVANCE LOW TO " + str(step.next_low)
        if step.action == "KEEP_LEFT":
            return "REDUCE HIGH TO " + str(step.next_high)
        return "RECORD CANDIDATE " + str(step.mid) + "  /  CHECK EARLIER"
    role = part["role"]
    if role == "INTRODUCTION":
        return "SORTED INPUT  /  SEARCH THE TARGET"
    if role == "EXPLANATION":
        return "COMPARE THE MIDPOINT  /  KEEP THE VALID INTERVAL"
    if role == "RECAP":
        if source.trace.result_index is None:
            return "SEARCH COMPLETE  /  TARGET ABSENT"
        return "LEFTMOST MATCH  /  INDEX " + str(source.trace.result_index)
    return "CERTIFIED SEARCH RESULT"


def _wrapped(draw, text: str, font, max_width: int) -> tuple[str, ...]:
    # Never clip, truncate or hide source narration; refuse >2 lines.
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = word if not current else current + " " + word
        width = draw.textbbox((0,0), candidate, font=font)[2]
        if width <= max_width:
            current = candidate
        else:
            _require(current != "" and
                     draw.textbbox((0,0), word, font=font)[2] <= max_width,
                     "UNBREAKABLE_CAPTION_WORD")
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    _require(1 <= len(lines) <= 2, "CAPTION_NEEDS_MORE_THAN_TWO_LINES")
    return tuple(lines)


def _native_frame(source, part: dict, *, fraction: float,
                  caption_visible: bool) -> Image.Image:
    kind = part.get("event_kind", "")
    progress = _pacing(kind, fraction)
    result = draw_binary_search_frame(
        trace=source.trace, step_index=part["visual_step"],
        progress=progress, subtitle="", profile=PROFILE)
    d = ImageDraw.Draw(result)
    # Rendering the board at 1280×720 makes all core labels native CMU text.
    # Reclaim the lower area only; preserve board, bounds, and true array IDs.
    d.rectangle((0,488,WIDTH,HEIGHT), fill=BLACK)
    d.line((48,495,WIDTH-48,495),fill=(53,53,53),width=2)
    action = _action(source, part)
    action_font = cmu_font(32)
    action_bbox = d.textbbox((0,0),action,font=action_font)
    _require(action_bbox[2] <= WIDTH-96, "ACTION_TEXT_OVERFLOW")
    d.text((48,507),action,font=action_font,fill=CYAN)
    if part["role"] == "INTRODUCTION":
        centers = _layout(PROFILE,len(source.trace.query.values))
        index = min(len(centers)-1,int(fraction*len(centers)))
        x=centers[index]
        d.rounded_rectangle((x-42,336,x+42,440),radius=13,outline=CYAN,width=3)
    elif part["role"] == "RECAP":
        centers = _layout(PROFILE,len(source.trace.query.values))
        visited = [s.mid for s in source.trace.steps if s.mid is not None]
        count=max(1,math.ceil(fraction*len(visited)))
        for mid in visited[:count]:
            x=centers[mid]
            d.ellipse((x-14,294,x+14,322),outline=CYAN,width=3)
    if caption_visible:
        font=cmu_font(32)
        rows=_wrapped(d,part["text"],font,WIDTH-128)
        top=614 if len(rows)==2 else 632
        for i,line in enumerate(rows):
            bbox=d.textbbox((0,0),line,font=font)
            x=(WIDTH-(bbox[2]-bbox[0]))//2
            y=top+i*42
            # Independent, non-color-only readable caption outline.
            d.text((x,y),line,font=font,fill=WHITE,stroke_width=2,
                   stroke_fill=(0,0,0))
        _require(top+(len(rows)-1)*42+40 <= HEIGHT-22, "CAPTION_OUTSIDE_SAFE_BAND")
    # Frame progress bar is useful without fabricating word-boundary timing.
    d.rectangle((0,HEIGHT-5,round(WIDTH*fraction),HEIGHT-2),fill=CYAN)
    return result


def _source_evidence(folder: Path) -> tuple[dict,dict,dict,object,Path]:
    baseline = audit_media(folder)
    _require(baseline["integrity_gate"]=="PASS", "BASELINE_NOT_CERTIFIED")
    comp=json.loads((folder/"v3_20_before_after_qa.json").read_text())
    rec=json.loads((folder/"after_v3_20.receipt.json").read_text())
    proof=json.loads((folder/"after_v3_20.event_proof.json").read_text())
    request=comp["same_source_input"]
    _require(request["family"]=="WORKED_EXAMPLE_BOARD", "UNSUPPORTED_FAMILY")
    source=build_binary_lesson_source(
        values=tuple(request["values"]),target=request["target"])
    verify_event_proof(source=source,segments=tuple(rec["segments"]),supplied=proof)
    _require(baseline["after"]["width"]==640 and
             baseline["after"]["height"]==360 and
             baseline["after"]["fps"]==12 and
             len(rec["segments"])==10, "UNEXPECTED_SOURCE_TIMELINE")
    cues=parse_srt(folder/"after_v3_20.srt")
    _require(len(cues)==len(rec["segments"]), "CAPTION_COUNT_CHANGED")
    for cue,segment in zip(cues,rec["segments"],strict=True):
        _require(cue[2]==segment["text"] and
                 abs(cue[0]-segment["subtitle_start"])<.002 and
                 abs(cue[1]-segment["subtitle_end"])<.002,
                 "AUTHOR_AUDIO_CAPTION_DRIFT")
    base_video=folder/"after_v3_20_real_audio_video.mp4"
    return baseline,rec,proof,source,base_video


def _find_part(segments: list[dict], source_frame: int) -> dict:
    for part in segments:
        if part["frame_start"] <= source_frame < part["frame_end_exclusive"]:
            return part
    raise QualityEvidenceError("V3_22_FRAME_EVENT_GAP")


def verify_hd(*, source_folder: Path, output: Path, receipt: dict) -> dict:
    _require(
        receipt.get("publication")=="BLOCKED"
        and receipt.get("human_legibility")=="UNMEASURED"
        and receipt.get("human_learning")=="UNMEASURED"
        and receipt.get("word_alignment")=="UNMEASURED"
        and receipt.get("commercial_voice_rights")=="UNVERIFIED",
        "FORGED_QUALITY_RELEASE_CLAIM")
    _require(
        receipt.get("render")=="NATIVE_1280X720_24FPS_ORACLE_FRAMES_NOT_UPSCALE"
        and receipt.get("caption_px",0)>=32
        and receipt.get("action_px",0)>=32
        and receipt.get("pacing")=="APPLY_ONLY_HOLD_18_PERCENT_EASE_62_PERCENT_SETTLE_20_PERCENT",
        "HD_RENDER_CONTRACT_DRIFT")
    _, source_rec, proof, source, original=_source_evidence(source_folder)
    _require(output.is_file() and not output.is_symlink()
             and _sha(output)==receipt["video_sha256"], "HD_VIDEO_HASH_CHANGED")
    v,a=_probe(output)
    count=int(v["nb_frames"])
    _require(v["codec_name"]=="h264" and a["codec_name"]=="aac"
             and int(v["width"])==WIDTH and int(v["height"])==HEIGHT
             and v["r_frame_rate"]=="24/1"
             and count==source_rec["total_frames"]*2
             and receipt["frames"]==count, "NOT_TRUE_NATIVE_720P_24FPS")
    _require(receipt["source_video_sha256"]==_sha(original)
             and receipt["event_proof_sha256"]==proof["proof_sha256"]
             and receipt["source_trace_sha256"]==source.trace.trace_sha256,
             "UNBOUND_HD_SOURCE")
    _require(receipt.get("subtitle_source_sha256")==
             _sha(Path(source_folder)/"after_v3_20.srt"),
             "SUBTITLE_SOURCE_SHA_DRIFT")
    _require(receipt["audio_adts_sha256"]==_adts_sha(original)
             ==_adts_sha(output), "AAC_PACKETS_WERE_CHANGED")
    chosen=[]
    for part in source_rec["segments"]:
        first=part["frame_start"]*2
        last=part["frame_end_exclusive"]*2-1
        chosen.extend([first,first+min(4,last-first), (first+last)//2,last])
    chosen=sorted(set(chosen))
    images=_frames(output,WIDTH,HEIGHT,chosen)
    pixels=dict(zip(chosen,images,strict=True))
    comparisons=[]
    for idx in chosen:
        part=_find_part(source_rec["segments"],idx//2)
        frame_begin=2*part["frame_start"]
        frame_count=2*(part["frame_end_exclusive"]-part["frame_start"])
        fraction=(idx-frame_begin)/max(frame_count-1,1)
        clock=idx/FPS
        caption=(part["subtitle_start"] <= clock < part["subtitle_end"])
        expected=_native_frame(source,part,fraction=fraction,caption_visible=caption)
        # Text/caption are independently checked by source-derived RGB replay
        # after H264 compression. Upscaled 360p pixels fail this native target.
        diff=ImageChops.difference(pixels[idx],expected)
        mae=sum(ImageStat.Stat(diff).mean)/3
        _require(mae<15.0, "DECODED_FRAME_NOT_NATIVE_SOURCE_RENDER")
        comparisons.append({"frame":idx,"at_seconds":round(clock,3),
                            "full_frame_rgb_mae":round(mae,4),
                            "event_kind":part["event_kind"]})
    # Verify the settled source state does not visibly rewind at each cut.
    boundaries=[]
    for before,after in zip(source_rec["segments"],source_rec["segments"][1:]):
        if before["event_kind"]!="APPLY" or after["event_kind"] not in ("OBSERVE","RESULT"):
            continue
        p=before["frame_end_exclusive"]*2-1
        q=after["frame_start"]*2
        _require(q==p+1 and before["visual_step"]==after["visual_step"],
                 "SOURCE_EVENT_CONTINUITY_INVALID")
        a,b=pixels[p],pixels[q]
        roi=(0,160,WIDTH,470)
        mae=sum(ImageStat.Stat(ImageChops.difference(
            a.crop(roi),b.crop(roi))).mean)/3
        _require(mae<2.0, "HD_POINTER_REWIND")
        boundaries.append({"from_frame":p,"to_frame":q,
                           "at_seconds":round(q/FPS,3),"mae":round(mae,5)})
    _require(len(boundaries)==3, "EXPECTED_THREE_SOURCE_CHANGES")
    return {"frame_samples":comparisons,"pointer_continuity":boundaries,
            "max_decoded_expected_mae":max(x["full_frame_rgb_mae"] for x in comparisons)}


def render_hd(*,source_folder:Path,output_dir:Path)->dict:
    """One explicitly invoked, private, no-clobber offline 720p candidate."""
    root=Path(output_dir)
    _require(root.is_dir() and not root.is_symlink(), "UNSAFE_OUTPUT_DIR")
    video=root/"v3_22_binary_search_native_720p.mp4"
    receipt_path=root/"v3_22_native_hd_receipt.json"
    _require(not video.exists() and not receipt_path.exists(), "OUTPUT_NO_CLOBBER")
    _, original_rec, proof, source, original=_source_evidence(source_folder)
    nframes=original_rec["total_frames"]*2
    # The video image is regenerated from oracle at native resolution, not scaled
    # from original MP4. AAC is stream-copied so voice source is unchanged.
    with tempfile.TemporaryDirectory(prefix=".v3_22_native_",dir=root) as tmp:
        pending=Path(tmp)/"video.mp4"
        cmd=["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
             "-f","rawvideo","-pix_fmt","rgb24","-s",f"{WIDTH}x{HEIGHT}",
             "-r",str(FPS),"-i","pipe:0","-i",str(original),
             "-map","0:v:0","-map","1:a:0","-c:v","libx264",
             "-threads","2","-preset","ultrafast","-crf","20",
             "-pix_fmt","yuv420p","-r",str(FPS),"-frames:v",str(nframes),
             "-c:a","copy",str(pending)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,
                              stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            for index in range(nframes):
                # Source physical boundary 12 fps maps exactly to 24fps.
                part=_find_part(original_rec["segments"],index//2)
                start=part["frame_start"]*2
                stop=part["frame_end_exclusive"]*2
                fraction=(index-start)/max(stop-start-1,1)
                clock=index/FPS
                caption=(part["subtitle_start"]<=clock<part["subtitle_end"])
                frame=_native_frame(source,part,fraction=fraction,
                                    caption_visible=caption)
                proc.stdin.write(frame.tobytes())
            proc.stdin.close()
            _require(proc.wait(timeout=300)==0, "NATIVE_HD_ENCODER_FAILED")
        except Exception:
            if proc.stdin is not None and not proc.stdin.closed:
                proc.stdin.close()
            if proc.poll() is None:
                proc.kill()
            proc.wait()
            raise
        receipt={
            "checkpoint":"V3-22","version":VERSION,
            "render":"NATIVE_1280X720_24FPS_ORACLE_FRAMES_NOT_UPSCALE",
            "frames":nframes,"width":WIDTH,"height":HEIGHT,"fps":FPS,
            "source_video_sha256":_sha(original),
            "source_trace_sha256":source.trace.trace_sha256,
            "event_proof_sha256":proof["proof_sha256"],
            "subtitle_source_sha256":_sha(source_folder/"after_v3_20.srt"),
            "video_sha256":_sha(pending),
            "audio_adts_sha256":_adts_sha(original),
            "caption_typeface":"CMU Serif / OS fonts-cmu",
            "caption_px":32,"action_px":32,
            "pacing":"APPLY_ONLY_HOLD_18_PERCENT_EASE_62_PERCENT_SETTLE_20_PERCENT",
            "word_alignment":"UNMEASURED",
            "human_legibility":"UNMEASURED",
            "human_learning":"UNMEASURED",
            "commercial_voice_rights":"UNVERIFIED",
            "student_ready":"REVIEW_REQUIRED",
            "publication":"BLOCKED","paid_provider_calls":0,
        }
        tested=verify_hd(source_folder=source_folder,output=pending,receipt=receipt)
        receipt.update(tested)
        doc=Path(tmp)/"receipt.json"
        doc.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
        try:
            os.link(pending,video)
            os.link(doc,receipt_path)
        except Exception:
            video.unlink(missing_ok=True)
            receipt_path.unlink(missing_ok=True)
            raise
    return receipt
