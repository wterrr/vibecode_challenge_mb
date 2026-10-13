"""V3-59: research-only, host-verified causal reveal of existing V3-57 facts.

NEVER changes frozen V3-57/V3-58 baselines, original narration, evidence
ledger, speech alignment, production pipeline or agent-authorship status.
No model-generated executable code is accepted.
"""
from __future__ import annotations

import io
import json
import math
import subprocess
from pathlib import Path
from PIL import ImageDraw, ImageChops, ImageStat
from learnflow_v3.pedagogical_storytelling_slice import (
    BLACK, CYAN, AMBER, GREEN, SOFT, WHITE, WIDTH, HEIGHT, FPS,
    STEPS, facts, plan, validate, render_image, text
)
from learnflow_v3.matched_pedagogy_ablation import (
    require, sha, probe, aac_sha, source_case, frame, mean_diff
)

# Frozen, research-only transition state thresholds; not measured speech times.
FRACTION_GUIDE_START = .16
FRACTION_REVEAL = .79
ATTENTION_WEIGHT_REVEAL = 1.0
PROCESS_ACTION_ARRIVAL = 1.0


def witness(case_id: str, beat_index: int, progress: float) -> dict:
    """Semantic state is computed from verified host facts, never inferred from pixels."""
    require(case_id in STEPS and 0 <= beat_index < 5, "UNKNOWN_PLAN")
    require(isinstance(progress, (int, float)) and math.isfinite(progress)
            and 0 <= progress <= 1, "INVALID_PROGRESS")
    ev = facts(case_id)
    state = {"case_id": case_id, "beat_index": beat_index,
             "operation": STEPS[case_id][beat_index],
             "origin": "HOST_SYNTHETIC_NOT_MODEL_AUTHORED"}
    if case_id == "fraction_equivalence" and beat_index == 2:
        revealed = progress >= FRACTION_REVEAL
        state.update(partitions=6 if revealed else 3,
                     shaded_parts=4 if revealed else 2,
                     fraction="4/6" if revealed else "2/3",
                     split_guides_complete=revealed,
                     preserved_area="2/3")
    elif case_id == "process_heldout_unknown" and beat_index == 2:
        state.update(action_active=progress >= PROCESS_ACTION_ARRIVAL,
                     marker_center_x=round(370+270*progress),
                     marker_center_y=337,
                     action_center_x=640,
                     action_arrival_verified=progress >= PROCESS_ACTION_ARRIVAL and round(370+270*progress)==640,
                     condition="UNKNOWN_NOT_VERIFIED", success_claim=False)
    elif case_id == "attention_reversed_query" and beat_index == 2:
        state.update(weights_visible=progress >= ATTENTION_WEIGHT_REVEAL,
                     weights_sum=round(sum(ev["weights"]), 12),
                     normalization="exp(score_i) / sum_j exp(score_j)")
    else:
        state["unchanged_original_beat"] = True
    return state


def render_image_causal(p, beat_index: int, progress: float):
    """Use parent renderer as a frozen input; revise ONLY three certified reveals."""
    validate(p)
    state = witness(p.case_id, beat_index, progress)
    im = render_image(p, beat_index, progress)
    d = ImageDraw.Draw(im)
    if p.case_id == "fraction_equivalence" and beat_index == 2:
        # Rebuild only the content region; beat narration/claim footer stay intact.
        d.rectangle((142, 230, 1142, 562), fill=BLACK)
        x0, y0, x1, y1 = 160, 255, 1115, 425
        d.rounded_rectangle((x0-10, y0-10, x1+10, y1+10),
                            radius=22, outline=SOFT, width=2)
        n = state["partitions"]
        shaded = state["shaded_parts"]
        cellwidth = (x1 - x0) / n
        for j in range(n):
            left = int(x0 + j * cellwidth)
            right = int(x0 + (j+1) * cellwidth) - 3
            d.rectangle((left, y0, right, y1),
                        fill=CYAN if j < shaded else (37, 46, 62))
        # Grow half-part guides on 3 original partitions BEFORE showing six.
        length = max(0.0, min(1.0,
                 (progress-FRACTION_GUIDE_START) /
                 (FRACTION_REVEAL-FRACTION_GUIDE_START)))
        for j in range(3):
            x = round(x0 + (j+.5)*(x1-x0)/3)
            end = y0 + round((y1-y0)*length)
            if end > y0:
                d.line((x,y0,x,end), fill=AMBER, width=5)
        text(d,(635,483),"4 / 6" if n==6 else "2 / 3",46,anchor="mm")
        if n==6:
            text(d,(635,537),"Split each third in two; shaded area is unchanged",
                 24,GREEN,anchor="mm")
        else:
            text(d,(635,537),"Each of the three parts will become two",
                 24,AMBER,anchor="mm")
    elif p.case_id == "process_heldout_unknown" and beat_index == 2:
        # Override V3-57's marker at y=426 (it stopped before ACTION),
        # re-anchor movement to the actual START→ACTION graph edge at y=337.
        # ACTION activates only when marker CENTER reaches node CENTER x=640.
        d.rectangle((207,402,678,462),fill=BLACK)
        color = GREEN if state["action_active"] else (55,67,86)
        d.rounded_rectangle((510,283,770,393),radius=24,fill=color)
        text(d,(640,338),"ACTION",31,BLACK,anchor="mm")
        x=state["marker_center_x"]
        d.line((370,337,x,337),fill=AMBER,width=7)
        d.ellipse((x-13,324,x+13,350),
                  fill=WHITE,outline=AMBER,width=3)
    elif p.case_id == "attention_reversed_query" and beat_index == 2:
        # Remove parent early result labels at x=110, preserving score bars x>=325.
        d.rectangle((94,356,321,493), fill=BLACK)
        if state["weights_visible"]:
            ev = facts(p.case_id)
            text(d,(107,382),f"w(A) = {ev['weights'][0]:.3f}",21,CYAN)
            text(d,(107,461),f"w(B) = {ev['weights'][1]:.3f}",21,AMBER)
            text(d,(390,561),"softmax: exp(score) / sum(exp(scores))",
                 20,GREEN)
        else:
            text(d,(106,382),"Normalize scores",21,WHITE)
            text(d,(106,461),"before weights",21,SOFT)
    return im


def verify_reveal_progression(p):
    """Independent exact semantic assertions plus visible ROI pixel-change checks."""
    validate(p)
    cid = p.case_id
    if cid == "fraction_equivalence":
        a=witness(cid,2,0);mid=witness(cid,2,.6);end=witness(cid,2,1)
        require((a["partitions"],a["shaded_parts"],a["fraction"]) ==
                (3,2,"2/3"),"FRACTION_EARLY_REVEAL")
        require((mid["partitions"],mid["fraction"]) ==
                (3,"2/3"),"FRACTION_RESULT_BEFORE_GUIDES")
        require((end["partitions"],end["shaded_parts"],end["fraction"]) ==
                (6,4,"4/6") and end["split_guides_complete"],
                "FRACTION_NO_SUBDIVISION")
        require(end["shaded_parts"]/end["partitions"] ==
                a["shaded_parts"]/a["partitions"],"FRACTION_AREA_CHANGED")
        roi=(150,245,1130,550)
    elif cid == "process_heldout_unknown":
        a=witness(cid,2,.1);mid=witness(cid,2,.9);end=witness(cid,2,1)
        require(not a["action_active"] and not mid["action_active"] and
                end["action_active"] and
                a["marker_center_x"]==397 and
                mid["marker_center_x"]<end["marker_center_x"] and
                end["marker_center_x"]==end["action_center_x"] and
                end["action_arrival_verified"],
                "ACTION_EARLY_ACTIVATION")
        require(end["condition"]=="UNKNOWN_NOT_VERIFIED" and
                end["success_claim"] is False,"PROCESS_FALSE_PASS")
        roi=(520,295,760,385)
    else:
        a=witness(cid,2,.1);mid=witness(cid,2,.75);end=witness(cid,2,1)
        require(not a["weights_visible"] and not mid["weights_visible"] and
                end["weights_visible"],"ATTENTION_EARLY_WEIGHT_REVEAL")
        require(abs(end["weights_sum"]-1)<1e-10,
                "ATTENTION_UNNORMALIZED")
        roi=(100,359,315,490)
    old=render_image_causal(p,2,.1).crop(roi)
    new=render_image_causal(p,2,1).crop(roi)
    delta=sum(ImageStat.Stat(ImageChops.difference(old,new)).mean)/3
    require(delta>.1,"NOT_VISIBLE_IN_PIXELS")
    return {"case_id":cid, "semantic_gate":"PASS_HOST_ONLY",
            "native_pillow_region_MAE":round(delta,4),
            "model_authorship":"NOT_TESTED","human_quality":"UNRATED"}


def build_revision(source_video, source_receipt, out_dir):
    """Render actual source-frame-matched H264 and copy original AAC bitstream."""
    out=Path(out_dir)
    require(not out.exists(),"FRESH_OUTPUT_REQUIRED")
    p,receipt,source_meta=source_case(source_video,source_receipt)
    cert=verify_reveal_progression(p)
    bounds=receipt["beat_receipts"]
    counts=[round((b["end_s"]-b["start_s"])*FPS) for b in bounds]
    # Correct the known -shortest original 1-frame last-beat discrepancy ONLY.
    delta=sum(counts)-source_meta["video_frames"]
    require(delta in (0,1) and
            sum(counts)==receipt["native_frames"],"FRAME_TIMELINE_DRIFT")
    counts[-1]-=delta
    require(counts[-1]>0,"TRUNCATED_FINAL_BEAT")
    out.mkdir(parents=True)
    silent=out/"causal_video_only.mp4"
    ff=["ffmpeg","-nostdin","-y","-hide_banner","-loglevel","error",
        "-f","rawvideo","-pix_fmt","rgb24","-s",
        f"{WIDTH}x{HEIGHT}","-r",str(FPS),"-i","-","-an",
        "-c:v","libx264","-preset","ultrafast","-crf","27",
        "-pix_fmt","yuv420p",str(silent)]
    proc=subprocess.Popen(ff,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for i,n in enumerate(counts):
            for j in range(n):
                progress=min(1.0,j/max(1,int(n*.58)))
                proc.stdin.write(render_image_causal(p,i,progress).tobytes())
        proc.stdin.close()
        err=proc.stderr.read().decode(errors="replace")
        code=proc.wait(timeout=180)
        require(code==0,"NATIVE_VIDEO_ENCODE_FAILED_"+err[-150:])
    except BaseException:
        proc.kill()
        proc.wait()
        raise
    movie=out/"causal_revision.mp4"
    subprocess.run(["ffmpeg","-nostdin","-y","-loglevel","error",
                    "-i",str(silent),"-i",str(source_video),
                    "-map","0:v:0","-map","1:a:0",
                    "-c:v","copy","-c:a","copy",str(movie)],
                   check=True,timeout=120)
    actual=probe(movie)
    require(actual["video_frames"]==source_meta["video_frames"],
            "FRAME_PARITY_FAILED")
    require(abs(actual["video_duration_s"]-source_meta["video_duration_s"])
            <1/FPS,"DURATION_PARITY_FAILED")
    audio_source=aac_sha(source_video);audio_new=aac_sha(movie)
    require(audio_source==audio_new,"AUDIO_STREAM_CHANGED")
    # Samples use certified frame indices, never narration word align guesses.
    native=[]
    for i in (2,):
        n=counts[i]
        for relative in (.1,.5,1.0):
            j=min(n-1,round(relative*max(1,int(n*.58))))
            true_progress=min(1.0,j/max(1,int(n*.58)))
            sec=(sum(counts[:i])+j+.1)/FPS
            decoded=frame(movie,sec)
            expected=render_image_causal(p,i,true_progress).resize((320,180))
            err=mean_diff(decoded,expected)
            require(err<19,"NATIVE_FRAME_NOT_EXPECTED_STATE")
            native.append({"case_id":p.case_id,"beat":i,
                           "frame_index":sum(counts[:i])+j,
                           "host_progress":round(true_progress,4),
                           "decoded_host_MAE_255":round(err,4)})
    result={
        "checkpoint":"V3-59","case_id":p.case_id,
        "parent_source_sha256":sha(source_video),
        "causal_revision_sha256":sha(movie),
        "original_AAC_SHA256":audio_source,
        "revision_AAC_SHA256":audio_new,
        "physical_frames_source":source_meta["video_frames"],
        "physical_frames_revision":actual["video_frames"],
        "known_parent_receipt_frame_delta":delta,
        "host_ledger_sha256":p.evidence_sha256,
        "semantic_gate":cert,
        "decoded_frame_witnesses":native,
        "media_path":str(movie),
        "authorship":"HOST_SYNTHETIC_NOT_MODEL_AUTHORED",
        "word_alignment":"UNMEASURED",
        "independent_pedagogical_quality":"UNRATED_NO_REVIEWERS",
        "learning_effect":"NOT_MEASURED",
        "model_api_posts":0,"production":"BLOCKED"}
    (out/"receipt.json").write_text(json.dumps(result,indent=2)+"\n")
    return result
