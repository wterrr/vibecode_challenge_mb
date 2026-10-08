"""V3-20: source-derived, separately spoken semantic utterance boundaries.

No guessed word/phoneme timing and no false forced alignment:
one explicitly authored semantic event = one independently synthesized WAV.
The actual sample-count-derived scene boundary places a source-certified visual
state transition at the *start of that event's utterance*. Intro, mechanism and
recap have bounded context visuals. We cannot establish transcript-as-heard by
this method and therefore do not certify independent lexical correctness.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from learnflow_v2.repair import compute_content_hash
from .binary_search_trace import verify_binary_search_trace
from .models import SemanticContractError
from .offline_lesson_source import BinaryLessonSource


class SemanticEvent(BaseModel):
    model_config=ConfigDict(frozen=True,extra="forbid")
    event_id:str
    scene_id:str
    role:str
    event_kind:str
    step:int
    visual_step:int
    beat_id:str
    segment_id:str
    text:str
    expected_low:int
    expected_high:int
    expected_mid:int|None
    source_trace_sha256:str


def authored_event_specs(source:BinaryLessonSource)->tuple[dict,...]:
    """Split only comparisons into OBSERVE and APPLY utterances, not arbitrary words.

    Each boundary is physically measurable from a separately synthesized WAV.
    The renderer must not show the subsequent LOW/HIGH/MID until APPLY starts.
    """
    verify_binary_search_trace(source.trace)
    from .narrated_lesson import _speech_lines
    original=_speech_lines(source)
    rows=[]
    for spec in original:
        s=source.trace.steps[spec["step"]]
        if spec["role"]!="WORKED_EXAMPLE" or s.phase!="COMPARE":
            kind={"INTRODUCTION":"INTRO","EXPLANATION":"MECHANISM",
                  "RECAP":"RECAP","WORKED_EXAMPLE":"RESULT"}[spec["role"]]
            rows.append(dict(spec,event_id=f"{spec['scene_id']}-{kind.lower()}",
                             event_kind=kind,visual_step=spec["step"]))
            continue
        next_index=spec["step"]+1
        if next_index>=len(source.trace.steps):
            raise SemanticContractError("V3_20_MISSING_NEXT_ORACLE_STATE")
        nxt=source.trace.steps[next_index]
        if s.action=="DISCARD_LEFT":
            observe=f"The middle value is {s.observed}, below {source.trace.query.target}."
            action=f"Move the low bound to index {s.next_low}."
            expected_action="DISCARD_LEFT"
        elif s.action=="KEEP_LEFT":
            observe=f"The middle value is {s.observed}, above {source.trace.query.target}."
            action=f"Keep the left interval through index {s.next_high}."
            expected_action="KEEP_LEFT"
        else:
            observe=f"The middle value equals {source.trace.query.target}."
            action=f"Record index {s.mid}, and check whether an earlier match exists."
            expected_action="RECORD_CANDIDATE"
        if (s.action!=expected_action or nxt.low!=s.next_low or nxt.high!=s.next_high):
            raise SemanticContractError("V3_20_ORACLE_NEXT_STATE_MISMATCH")
        for kind,text,visual_index in (
            ("OBSERVE",observe,spec["step"]),
            ("APPLY",action,next_index),
        ):
            rows.append(dict(spec,scene_id=f"{spec['scene_id']}-{kind.lower()}",
                             event_id=f"step-{spec['step']+1:02d}-{kind.lower()}",
                             event_kind=kind,text=text,visual_step=visual_index))
    seen=set()
    for i,row in enumerate(rows):
        if (row["scene_id"] in seen or not row["text"].endswith(".")
            or len(row["text"])>145 or row["beat_id"] not in
            {b.beat_id for b in source.plan.beats}):
            raise SemanticContractError("V3_20_EVENT_SOURCE_OR_ID_INVALID")
        seen.add(row["scene_id"])
        step=source.trace.steps[row["visual_step"]]
        row["expected_low"]=step.low
        row["expected_high"]=step.high
        row["expected_mid"]=step.mid
        row["source_trace_sha256"]=source.trace.trace_sha256
    return tuple(rows)


def certify_event_boundaries(*,source:BinaryLessonSource,
                              segments:tuple[dict,...],
                              fps:int=12)->dict:
    """Fail-closed immutable event→real WAV duration→video boundary attestation.

    Both source and final video manifest are checked separately. This does not
    infer speech word onsets, rate ASR, or claim human perceptual sync PASS.
    """
    expected=authored_event_specs(source)
    if len(expected)!=len(segments):
        raise SemanticContractError("V3_20_MISSING_OR_EXTRA_SEMANTIC_EVENT")
    events=[]
    previous_frame=0
    for event,part in zip(expected,segments,strict=True):
        for name in ("scene_id","event_id","event_kind","role","step","visual_step",
                     "beat_id","segment_id","text","expected_low","expected_high",
                     "expected_mid","source_trace_sha256"):
            if event[name]!=part.get(name):
                raise SemanticContractError("V3_20_EVENT_OR_SOURCE_DRIFT_"+name.upper())
        if part["frame_start"]!=previous_frame:
            raise SemanticContractError("V3_20_NONCONTIGUOUS_EVENT_FRAMES")
        if not (part["raw_spoken_samples"]>0 and 16000<=part["spoken_sample_rate"]<=48000):
            raise SemanticContractError("V3_20_INVALID_PCM_EVIDENCE")
        duration=part["raw_spoken_samples"]/part["spoken_sample_rate"]
        if abs(duration-part["raw_spoken_duration_seconds"])>1e-7:
            raise SemanticContractError("V3_20_FABRICATED_AUDIO_DURATION")
        start=part["frame_start"]/fps
        if abs(start-part["seconds_start"])>1e-6 or abs(start-part["subtitle_start"])>1e-6:
            raise SemanticContractError("V3_20_EVENT_AUDIO_FRAME_SHIFT")
        if abs(part["subtitle_end"]-(start+duration))>1e-5:
            raise SemanticContractError("V3_20_SUBTITLE_AUDIO_BOUNDARY_DRIFT")
        if part["frame_end_exclusive"]-part["frame_start"]!=__import__("math").ceil(duration*fps)+1:
            raise SemanticContractError("V3_20_INCORRECT_RENDER_FRAME_BUDGET")
        if part.get("speech_energy_rms",0)<.006:
            raise SemanticContractError("V3_20_SILENT_EVENT_AUDIO")
        if not part.get("spoken_wav_sha256"):
            raise SemanticContractError("V3_20_MISSING_WAV_SOURCE_HASH")
        previous_frame=part["frame_end_exclusive"]
        events.append({
            "event_id":event["event_id"],"event_kind":event["event_kind"],
            "beat_id":event["beat_id"],"segment_id":event["segment_id"],
            "claim_ids":["claim-01"],"object_ids":["array-01"],
            "expected_oracle_step":event["visual_step"],
            "low":event["expected_low"],"high":event["expected_high"],
            "mid":event["expected_mid"],"utterance":event["text"],
            "physical_wav_sha256":part["spoken_wav_sha256"],
            "spoken_pcm_samples":part["raw_spoken_samples"],
            "sample_rate":part["spoken_sample_rate"],
            "audio_and_event_start_seconds":start,
            "event_frame_start":part["frame_start"],
            "event_frame_end_exclusive":part["frame_end_exclusive"],
            "audio_utterance_end_seconds":part["subtitle_end"],
        })
    if not any(e["event_kind"]=="APPLY" for e in events):
        raise SemanticContractError("V3_20_NO_STATE_UPDATE_EVENTS")
    if any(e["event_frame_start"]<0 for e in events):
        raise SemanticContractError("V3_20_NEGATIVE_BOUNDARY")
    proof={
        "version":"v3-20-physical-utterance-boundaries-v1",
        "state":"MEASURED_SEGMENTED_UTTERANCE_BOUNDARIES_NOT_WORD_FORCED_ALIGNMENT",
        "source_trace_sha256":source.trace.trace_sha256,
        "event_count":len(events),
        "trace_comparisons":sum(s.phase=="COMPARE" for s in source.trace.steps),
        "events":events,
        "spoken_text_lexical_asr":"UNMEASURED",
        "word_phoneme_alignment":"UNMEASURED",
        "human_pedagogy_or_visual_preference":"UNMEASURED",
        "published":False,
    }
    proof["proof_sha256"]=compute_content_hash(proof)
    return proof


def verify_event_proof(*,source:BinaryLessonSource,segments:tuple[dict,...],
                        supplied:dict,fps:int=12)->None:
    expected=certify_event_boundaries(source=source,segments=segments,fps=fps)
    if supplied!=expected:
        raise SemanticContractError("V3_20_STALE_OR_SELF_REHASHED_EVENT_PROOF")
