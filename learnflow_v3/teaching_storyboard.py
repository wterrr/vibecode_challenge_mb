"""V3-24: teach the *reason* behind certified leftmost Binary Search.

Independent offline video retrofit of V3-22, not upscale/LLM-generated code.
Source WAV/event/audio and binary-search oracle are reused verbatim.
Do not interpret source-aligned event starts as word-level speech alignment or
engineering image quality as measured human learning.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageChops, ImageStat

from .blackboard_style import BLACK, CYAN, WHITE, cmu_font
from .lesson_quality import QualityEvidenceError, _frames, _probe
from .native_hd_lesson import (
    WIDTH, HEIGHT, FPS, PROFILE, _source_evidence, _native_frame, _find_part,
    _pacing, _wrapped, _require, _sha, _adts_sha,
)
from .sequence_renderer import _layout

VERSION = "v3-24-teaching-visuals-leftmost-offline-v1"
VIDEO = "v3_24_leftmost_teaching_720p.mp4"
RECEIPT = "v3_24_leftmost_teaching.receipt.json"
CAPTION_FONT = 32
POINTER_FONT = 32
INDEX_FONT = 29

def teaching_callout(source, part: dict) -> tuple[str, str, str]:
    step = source.trace.steps[part["step"]]
    index = part["step"] + 1
    kind = part["event_kind"]
    target = source.trace.query.target
    result = source.trace.result_index
    if kind == "INTRO":
        return "THE GOAL", f"Find the FIRST {target}, not just any match", "INTRO"
    if kind == "MECHANISM":
        return "THE RULE", "Compare the middle. Keep only the possible range.", "MECHANISM"
    if kind == "RECAP":
        return "TAKEAWAY", "An equal midpoint is a candidate. Check left.", "RECAP"
    if kind == "RESULT":
        return "ANSWER", f"First {target} is at index {result}" if result is not None else f"{target} is not in this array", "RESULT"
    if step.action == "DISCARD_LEFT":
        return (f"COMPARISON {index}", f"{step.observed} is below {target}. Look to the right.", "OBSERVE") if kind=="OBSERVE" else (
            f"UPDATE {index}", f"Move LOW to index {step.next_low}.", "DISCARD_LEFT")
    if step.action == "KEEP_LEFT":
        return (f"COMPARISON {index}", f"{step.observed} is above {target}. Look to the left.", "OBSERVE") if kind=="OBSERVE" else (
            f"UPDATE {index}", f"Keep indices through {step.next_high}.", "KEEP_LEFT")
    # A matching midpoint is NOT proven leftmost until the search ends.
    if step.action == "RECORD_CANDIDATE":
        return (f"COMPARISON {index}", f"{target} matches the middle. Could there be an earlier one?", "OBSERVE") if kind=="OBSERVE" else (
            f"UPDATE {index}", f"Index {step.mid} is a candidate. Search LEFT for the first.", "RECORD_CANDIDATE")
    raise QualityEvidenceError("V3_24_UNCERTIFIED_ORACLE_ACTION")


def _show_bright_label(draw: ImageDraw.ImageDraw, text: str, *,
                       center_x: int, center_y: int, color) -> None:
    font=cmu_font(POINTER_FONT)
    box=draw.textbbox((0,0),text,font=font)
    _require(box[2]-box[0] <= 125,"POINTER_LABEL_TOO_WIDE")
    draw.text((center_x,center_y),text,font=font,fill=color,
              anchor="mm",stroke_width=1,stroke_fill=BLACK)


def certified_visible_candidate(source, part: dict) -> int | None:
    """Candidate provenance follows what has been *spoken/applied*, never future trace."""
    kind=part["event_kind"]
    if kind in ("INTRO","MECHANISM"):
        return None
    if kind in ("RESULT","RECAP"):
        return source.trace.result_index
    step_index=part["step"]
    if kind=="OBSERVE":
        return (source.trace.steps[step_index-1].candidate_index
                if step_index>0 else None)
    if kind=="APPLY":
        return source.trace.steps[step_index].candidate_index
    raise QualityEvidenceError("V3_24_UNEXPECTED_EVENT_KIND")


def candidate_cell_geometry(centers:tuple[int,...], candidate:int,
                            profile=PROFILE)->tuple[tuple[int,int,int,int],int,int]:
    """Use the exact V3-06 native sequence-cell geometry for the green border.

    See sequence_renderer.draw_binary_search_frame slot calculation.
    Avoid fixed x±46/y341..425, which is wider and shorter than the
    actual gray cell at 720p and breaks for a different array density.
    """
    _require(bool(centers) and 0<=candidate<len(centers),
             "INVALID_CANDIDATE_CELL")
    sx,sy=profile.width/960,profile.height/540
    boxhalf=min(round(34*sx),
                round((centers[1]-centers[0])*0.42)
                if len(centers)>1 else round(34*sx))
    boxhalf=max(10,boxhalf)
    cy=round(288*sy)
    halfheight=round(34*sy)
    rect=(centers[candidate]-boxhalf,cy-halfheight,
          centers[candidate]+boxhalf,cy+halfheight)
    return rect,round(10*sy),max(2,round(2*sy))


def teaching_frame(source, part: dict, *, fraction: float,
                   caption_visible: bool) -> Image.Image:
    """Draw every native frame from source; no bitmap resize or card fallback."""
    img = _native_frame(source,part,fraction=fraction,caption_visible=False)
    d=ImageDraw.Draw(img)
    # Remove developer-only microcopy while leaving true semantic chart intact.
    d.rectangle((77,88,975,125),fill=BLACK)
    # The V3-06 source also draws a horizontal rule at y≈129. Clearing
    # only the text area previously cut that rule halfway across the video.
    # Erase the entire old rule below target/title, redraw one uninterrupted
    # separator across the canvas at a stable source-independent y=151.
    d.rectangle((48,126,WIDTH-48,152),fill=BLACK)
    micro="Every comparison narrows the search"
    d.text((80,92),micro,font=cmu_font(28),fill=(190,199,209))
    d.line((80,151,WIDTH-80,151),fill=(59,66,73),width=2)
    # Lift small pointer legends to reader-scale CMU text; retain the original
    # pixel positions and semantic dots (LOW/HIGH/MID do NOT change identity).
    center_values=_layout(PROFILE,len(source.trace.query.values))
    step=source.trace.steps[part["visual_step"]]
    prev=source.trace.steps[max(0,part["visual_step"]-1)]
    progress=_pacing(part.get("event_kind",""),fraction)
    alpha=(max(0.0,min(1.0,progress/.32)) if part["visual_step"] else 1.)
    alpha=alpha*alpha*(3-2*alpha)
    def position(now, old):
        value=old+(now-old)*alpha
        return round(center_values[0]+(center_values[-1]-center_values[0])*value/
                     max(1,len(center_values)-1))
    pointers=[
        ("LOW",position(step.low,prev.low),209,(80,204,234), (183,227)),
        ("HIGH",position(step.high,prev.high),261,(178,158,251),(236,280)),
    ]
    old_mid=prev.mid if prev.mid is not None else (prev.candidate_index or 0)
    new_mid=step.mid if step.mid is not None else step.candidate_index
    if new_mid is not None:
        name="MID" if step.phase=="COMPARE" else "FOUND"
        pointers.append((name,position(new_mid,old_mid),313,(247,201,77)
                         if name=="MID" else (100,234,165),(291,331)))
    for _,_,_,_,(top,bottom) in pointers:
        d.rectangle((0,top,WIDTH,bottom),fill=BLACK)
    for name,x,y,color,_ in pointers:
        _show_bright_label(d,name,center_x=x,center_y=y,color=color)
    # Redraw the index row with source-stable centers and >=29px labels.
    # Keep actual array-cell values and source-grounded elimination colors.
    d.rectangle((0,446,WIDTH,483),fill=BLACK)
    active=step.low,step.high
    for i,x in enumerate(center_values):
        live=active[0]<=i<=active[1]
        d.text((x,465),str(i),font=cmu_font(INDEX_FONT),
               fill=(183,201,223) if live else (117,136,154),anchor="mm")
    # Match the native gray sequence cell in width, height, corner radius and
    # border thickness. This outline is a color change, not a larger overlay.
    candidate=certified_visible_candidate(source,part)
    if candidate is not None:
        bounds,radius,stroke=candidate_cell_geometry(
            center_values,candidate,PROFILE)
        d.rounded_rectangle(bounds,radius=radius,
                            outline=(111,231,162),width=stroke)
    # Rework information hierarchy without changing original narrated WAV/SRT.
    d.rectangle((0,490,WIDTH,HEIGHT),fill=BLACK)
    d.line((48,495,WIDTH-48,495),fill=(63,73,79),width=2)
    key,explanation,semantic_action=teaching_callout(source,part)
    d.text((50,505),key,font=cmu_font(26),fill=CYAN)
    # Explicit legend for the green candidate outline. Without this,
    # source-correct green index 6 is difficult to interpret by novices.
    if candidate is not None:
        tag = (f"FIRST MATCH  /  INDEX {candidate}"
               if part["event_kind"] in ("RESULT","RECAP") else
               f"BEST SO FAR  /  INDEX {candidate}")
        d.text((WIDTH-52,506),tag,font=cmu_font(27),fill=(121,239,171),
               anchor="ra")
    headline_font=cmu_font(35)
    line=_wrapped(d,explanation,headline_font,WIDTH-104)
    _require(len(line)==1,"STORYLINE_HEADLINE_OVERFLOW")
    d.text((50,548),line[0],font=headline_font,fill=WHITE)
    if caption_visible:
        caption_font=cmu_font(CAPTION_FONT)
        lines=_wrapped(d,part["text"],caption_font,WIDTH-128)
        top=623 if len(lines)==2 else 640
        for i,text in enumerate(lines):
            bbox=d.textbbox((0,0),text,font=caption_font)
            x=(WIDTH-(bbox[2]-bbox[0]))//2
            d.text((x,top+40*i),text,font=caption_font,fill=WHITE,
                   stroke_width=2,stroke_fill=BLACK)
        _require(top+40*(len(lines)-1)+37<HEIGHT-14,
                 "CAPTION_SAFE_MARGIN_OVERFLOW")
    d.rectangle((0,HEIGHT-5,round(WIDTH*fraction),HEIGHT-2),fill=CYAN)
    return img


def _quality_guard(receipt:dict)->None:
    _require(
        receipt.get("checkpoint")=="V3-24"
        and receipt.get("render")=="NATIVE_SOURCE_GROUNDED_PEDAGOGY_NO_UPSCALE"
        and receipt.get("publication")=="BLOCKED"
        and receipt.get("human_comprehension")=="UNMEASURED"
        and receipt.get("human_visual_preference")=="UNMEASURED"
        and receipt.get("commercial_voice_rights")=="UNVERIFIED"
        and receipt.get("word_alignment")=="UNMEASURED"
        and receipt.get("font_small_pointer_px")==POINTER_FONT
        and receipt.get("font_array_index_px")==INDEX_FONT,
        "FORGED_OR_INVALID_QUALITY_CLAIM")


def verify_teaching_video(*,source_folder:Path,output:Path,receipt:dict)->dict:
    _quality_guard(receipt)
    _require(output.is_file() and not output.is_symlink(),"VIDEO_MISSING")
    baseline,reference,proof,source,original=_source_evidence(source_folder)
    _require(receipt["source_trace_sha256"]==source.trace.trace_sha256
             and receipt["source_event_proof_sha256"]==proof["proof_sha256"]
             and receipt["source_v3_20_video_sha256"]==_sha(original)
             and receipt["original_srt_sha256"]==_sha(source_folder/"after_v3_20.srt")
             and receipt["original_aac_packet_sha256"]==_adts_sha(original)
             and receipt["original_aac_packet_sha256"]==_adts_sha(output)
             and receipt["video_sha256"]==_sha(output),"UNBOUND_VIDEO_OR_AUDIO")
    v,a=_probe(output)
    _require(v["width"]==WIDTH and v["height"]==HEIGHT
             and v["r_frame_rate"]=="24/1"
             and int(v["nb_frames"])==reference["total_frames"]*2
             and v["codec_name"]=="h264" and a["codec_name"]=="aac",
             "NOT_NATIVE_720P_24FPS")
    anchors=sorted(set([
        k for p in reference["segments"] for k in
        (p["frame_start"]*2,p["frame_start"]*2+1,
         (p["frame_start"]+p["frame_end_exclusive"])*1,
         p["frame_end_exclusive"]*2-1)]))
    # Source-verified decoded pixel replay over all 10 events, bounded batches
    # preserve V3-21's <35-frame sampling safeguard.
    samples=[]
    for offset in range(0,len(anchors),24):
        samples+=_frames(output,WIDTH,HEIGHT,anchors[offset:offset+24])
    samples=dict(zip(anchors,samples,strict=True))
    replay=[]
    for k,decoded in samples.items():
        p=_find_part(reference["segments"],k//2)
        start=p["frame_start"]*2
        span=(p["frame_end_exclusive"]-p["frame_start"])*2
        t=(k-start)/max(span-1,1)
        caption=(p["subtitle_start"]<=k/FPS<p["subtitle_end"])
        expected=teaching_frame(source,p,fraction=t,caption_visible=caption)
        diff=ImageChops.difference(expected,decoded)
        mae=sum(ImageStat.Stat(diff).mean)/3
        _require(mae<15.0,"DECODED_SEMANTIC_FRAME_MISMATCH")
        replay.append({"frame":k,"seconds":round(k/FPS,3),
                       "kind":p["event_kind"],"mae":round(mae,4)})
    boundaries=[]
    for before,after in zip(reference["segments"],reference["segments"][1:]):
        if before["event_kind"]!="APPLY" or after["event_kind"] not in ("OBSERVE","RESULT"):
            continue
        b=before["frame_end_exclusive"]*2-1
        n=after["frame_start"]*2
        _require(n==b+1 and before["visual_step"]==after["visual_step"],
                 "EVENT_TRACE_IDENTITY_DRIFT")
        roi=(0,178,WIDTH,440)
        delta=ImageChops.difference(samples[b].crop(roi),samples[n].crop(roi))
        mae=sum(ImageStat.Stat(delta).mean)/3
        _require(mae<2,"POINTER_OR_CANDIDATE_REWIND")
        boundaries.append({"from":b,"to":n,"seconds":round(n/FPS,3),
                           "roi_mae":round(mae,5)})
    _require(len(boundaries)==3,"NOT_THREE_SOURCE_CERTIFIED_TRANSITIONS")
    # Verify narrative itself on the correct step without using image OCR.
    actions=[teaching_callout(source,p) for p in reference["segments"]]
    _require(
        any("candidate" in text.lower() and "LEFT" in text for _,text,_ in actions)
        and any("FIRST" in text for _,text,_ in actions)
        and all("immutable item" not in text.lower() for _,text,_ in actions),
        "DIDACTIC_STORYBOARD_NOT_SOURCE_GROUNDED")
    return {"decoded_source_frame_probes":replay,
            "max_expected_decoded_rgb_mae":max(x["mae"] for x in replay),
            "settled_transition_checks":boundaries}


def render_teaching_video(*,source_folder:Path,out:Path)->dict:
    _require(out.is_dir() and not out.is_symlink(),"UNSAFE_OUTPUT_DIR")
    final=out/VIDEO
    document=out/RECEIPT
    _require(not final.exists() and not document.exists(),"NO_CLOBBER")
    baseline,source_receipt,proof,source,original=_source_evidence(source_folder)
    frames=source_receipt["total_frames"]*2
    with tempfile.TemporaryDirectory(prefix=".v3_24_teaching_",dir=out) as folder:
        stage=Path(folder)
        pending=stage/"teaching.mp4"
        cmd=["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
             "-f","rawvideo","-pix_fmt","rgb24","-s",f"{WIDTH}x{HEIGHT}",
             "-r",str(FPS),"-i","pipe:0","-i",str(original),
             "-map","0:v:0","-map","1:a:0",
             "-c:v","libx264","-threads","2","-preset","ultrafast",
             "-crf","20","-pix_fmt","yuv420p","-r",str(FPS),
             "-frames:v",str(frames),"-c:a","copy",str(pending)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,
                              stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            for index in range(frames):
                p=_find_part(source_receipt["segments"],index//2)
                start=p["frame_start"]*2
                count=(p["frame_end_exclusive"]-p["frame_start"])*2
                fraction=(index-start)/max(count-1,1)
                caption=(p["subtitle_start"]<=index/FPS<p["subtitle_end"])
                proc.stdin.write(teaching_frame(
                    source,p,fraction=fraction,caption_visible=caption).tobytes())
            proc.stdin.close()
            _require(proc.wait(timeout=400)==0,"FFMPEG_ENCODE_ERROR")
        except Exception:
            if proc.stdin is not None and not proc.stdin.closed:
                proc.stdin.close()
            if proc.poll() is None:proc.kill()
            proc.wait()
            raise
        receipt={
            "checkpoint":"V3-24","version":VERSION,
            "render":"NATIVE_SOURCE_GROUNDED_PEDAGOGY_NO_UPSCALE",
            "source_v3_20_video_sha256":_sha(original),
            "source_trace_sha256":source.trace.trace_sha256,
            "source_event_proof_sha256":proof["proof_sha256"],
            "original_srt_sha256":_sha(source_folder/"after_v3_20.srt"),
            "original_aac_packet_sha256":_adts_sha(original),
            "video_sha256":_sha(pending),"width":WIDTH,"height":HEIGHT,
            "fps":FPS,"frames":frames,
            "font_small_pointer_px":POINTER_FONT,
            "font_array_index_px":INDEX_FONT,
            "caption_px":CAPTION_FONT,
            "storyboard":"LEFTMOST_CANDIDATE_AND_SEARCH_LEFT_SOURCE_BOUND",
            "event_alignment":"SOURCE_PHYSICAL_UTTERANCE_BOUNDARIES_NOT_WORD_LEVEL",
            "word_alignment":"UNMEASURED",
            "human_comprehension":"UNMEASURED",
            "human_visual_preference":"UNMEASURED",
            "commercial_voice_rights":"UNVERIFIED",
            "publication":"BLOCKED","paid_provider_calls":0,
        }
        evidence=verify_teaching_video(source_folder=source_folder,
                                      output=pending,receipt=receipt)
        receipt.update(evidence)
        draft=stage/"receipt.json"
        draft.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
        linked=[]
        try:
            for a,b in ((pending,final),(draft,document)):
                os.link(a,b)
                linked.append(b)
        except Exception:
            for p in linked:p.unlink(missing_ok=True)
            raise
    return receipt
