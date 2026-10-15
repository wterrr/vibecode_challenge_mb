"""V3-86 finite pedagogy/narration contract grounded in V3-85 typed affine facts.

Six distinct *actually synthesized* eSpeak utterances for each two-beat lesson.
They identify their semantic events, original claims, intended visual phase.
Time comes from real generated WAV samples; never fake per-word timestamps or ASR.
"""
from __future__ import annotations
import hashlib
import json
import re

from learnflow_v3.v385_affine_visual_semantics import need,role_contract

PHASES=("ORIENT","TRANSFORM","INTERPRET")
ALLOWED_ROLES={"input_output_line","velocity_vs_elapsed_time"}
MAX_PHRASE_CHARS=700


def _say(role,values,index):
    v=values
    if role=="velocity_vs_elapsed_time":
        if index==0:
            return (
                "Read this as a velocity versus elapsed time graph. "
                "Time is along the horizontal axis, and velocity is on the vertical axis. "
                "The moving dot represents a value on the chart, not the object's physical path.",
                f"The constant acceleration is {v['rate']} and elapsed time is {v['independent']}. "
                f"Multiplying them gives a change in velocity of {v['change']}. "
                "Watch how the rising line makes that change visible on the velocity axis.",
                f"The slope expresses how velocity changes with elapsed time. "
                f"Here the change is {v['change']}, and the highlighted rise is a change in velocity. "
                "It does not measure the distance traveled by the object.",
            )
        return (
            f"Now include the starting velocity of {v['initial']}. "
            "The line begins at this vertical intercept rather than at zero. "
            "The horizontal axis still represents elapsed time.",
            f"Add the starting velocity {v['initial']} to the change {v['change']}. "
            f"The final velocity is {v['final']}. "
            "Follow the plotted line to the endpoint; its height represents velocity.",
            f"We began with velocity {v['initial']} and reached velocity {v['final']}. "
            "The acceleration gives the slope of the velocity time graph. "
            "The marker describes a graph value, never the object's location.",
        )
    if role=="input_output_line":
        if index==0:
            return (
                "This is an input versus output graph. "
                "The horizontal axis shows the chosen input, and the vertical axis shows the output. "
                "The line reveals how the output changes as the input increases.",
                f"The slope is {v['rate']} and the selected input is {v['independent']}. "
                f"Multiplying them gives an output change of {v['change']}. "
                "Watch the slanted line and the vertical rise from the zero baseline.",
                f"The slope tells us how much output grows with the input. "
                f"For this selected input the change is {v['change']}. "
                "That rise comes from multiplying the slope by the input, not from the starting offset.",
            )
        return (
            f"Now add the initial output of {v['initial']}. "
            "It becomes the vertical intercept where our input output line begins. "
            "We keep the same relationship between changes in input and output.",
            f"Start at output {v['initial']} and add the change {v['change']}. "
            f"The resulting output is {v['final']}. "
            "Follow the line to the highlighted plotted endpoint.",
            f"The graph begins at output {v['initial']} when the input is zero. "
            f"At input {v['independent']}, the output is {v['final']}. "
            "The intercept sets the starting height, while the slope controls how quickly output rises.",
        )
    raise ValueError("V386_UNSUPPORTED_SEMANTIC_ROLE")


def semantic_phases(row,bundle,role):
    # Original question, source and proof chain must be bound BEFORE narration.
    checked=role_contract(row,bundle)
    need(checked==role,"V386_VISUAL_ROLE_RECEIPT_TAMPER")
    trace=bundle["trace"]
    need(len(trace["events"])==2 and role["role"] in ALLOWED_ROLES,
         "V386_UNSUPPORTED_LESSON_GRAPH")
    need(role["claim_ids"]==[e["claim_id"] for e in trace["events"]],
         "V386_CLAIM_ID_SEQUENCE_UNGROUNDED")
    result=[]
    for i,event in enumerate(trace["events"]):
        lines=_say(role["role"],role["verified_values"],i)
        need(len(lines)==3,"V386_PHASE_COUNT_DRIFT")
        for j,(kind,narration) in enumerate(zip(PHASES,lines,strict=True)):
            need(100<=len(narration)<=MAX_PHRASE_CHARS
                 and re.fullmatch(r"[A-Za-z0-9 .,;'-]+",narration) is not None,
                 "V386_UNSAFE_OR_TOO_SHORT_AUDIO_UTTERANCE")
            result.append({
                "phase_id":f"operator{i+1}.{kind.lower()}",
                "semantic_beat_index":i,
                "phase_index":j,
                "phase_kind":kind,
                "claim_id":event["claim_id"],
                "source_sha256":role["source_sha256"],
                "semantic_role":role["role"],
                "narration":narration,
                "narration_sha256":hashlib.sha256(narration.encode()).hexdigest(),
                "visual_intent":({
                    "ORIENT":"SHOW_SEMANTIC_AXES_AND_INITIAL_GRAPH_REFERENCE",
                    "TRANSFORM":"DRAW_RATE_CURVE_AND_VISUAL_DELTA",
                    "INTERPRET":"SHOW_EXACT_RESULT_AND_HIGHLIGHT_GRAPH_STATE",
                })[kind],
                "origin":"DETERMINISTIC_HOST_FROM_VERIFIED_FACTS_NOT_MODEL",
                "word_timestamps":"NOT_AVAILABLE_NOT_FABRICATED",
            })
    need(len(result)==6,"V386_MISSING_SPEECH_PHASES")
    need([r["phase_kind"] for r in result]==list(PHASES)*2,
         "V386_PHASE_ORDER_DRIFT")
    return result


def align_real_wav(phases,beat_rows):
    """Link actual per-utterance WAV-derived frame ranges to semantic visual decisions."""
    need(len(phases)==len(beat_rows)==6,"V386_WAV_EVENT_COUNT_CHANGED")
    receipts=[]
    next_frame=0
    for phase,beat in zip(phases,beat_rows,strict=True):
        count=beat["frames"]
        need(type(count) is int and count>=60,"V386_AUDIO_SEGMENT_TOO_SHORT")
        need(beat["index"]==len(receipts) and
             beat["frame_start"]==next_frame and
             beat["claim_ids"]==[phase["claim_id"]] and
             beat["narration"]==phase["narration"],
             "V386_VOICE_SEGMENT_CLAIM_OR_TIMELINE_DRIFT")
        need(beat["wav_samples"]>0 and beat["wav_rate"]>=8000,
             "V386_MISSING_PHYSICAL_WAV_DATA")
        receipt={
            "phase_id":phase["phase_id"],
            "phase_kind":phase["phase_kind"],
            "semantic_beat_index":phase["semantic_beat_index"],
            "claim_id":phase["claim_id"],
            "narration_sha256":phase["narration_sha256"],
            "frame_start":next_frame,
            "frames":count,
            "frame_end_exclusive":next_frame+count,
            "wav_samples":beat["wav_samples"],
            "wav_rate":beat["wav_rate"],
            "timing_ground_truth":"SYNTHESIZED_PCM_AND_EXACT_AUDIO_FRAME_BUDGET",
            "word_level_alignment":"NOT_MEASURED",
        }
        receipts.append(receipt)
        next_frame+=count
    need(len({r["phase_id"] for r in receipts})==6,
         "V386_DUPLICATE_PHASE_ID")
    return receipts
