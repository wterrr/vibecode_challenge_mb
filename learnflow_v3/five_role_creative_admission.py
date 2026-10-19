"""V3-63 research-only five-role model-shaped creative decision admission.

A user-supplied JSON candidate is NEVER treated as proven model-authored.
Only the three frozen V3-62 host ledgers and renderer capabilities are admitted.
No arbitrary Python/text assertions/numbers or publication privileges are accepted.
"""
from __future__ import annotations
from hashlib import sha256
import json
from typing import Literal
from pydantic import BaseModel,ConfigDict,ValidationError,Field
from learnflow_v3.creative_pedagogical_director import (
    CASES,LAYOUTS,REFERENTS,candidate as host_story,digest,exact_facts
)

VERSION="v3-63-five-role-creative-decision-wire-v1"
MAX_BYTES=16384
ROLE_NAMES=("cognitive_designer","narrative_designer","visual_thinker","motion_director","visual_critic")
# Approved learning hypotheses are research hypotheses, not measured learner misconceptions.
CATALOG={
 CASES[0]:{"misconceptions":("complement_changes_total","outside_event_has_no_outcomes"),
           "probes":("count_remaining","confirm_whole_unchanged"),
           "risk":"losing_outcome_identity"},
 CASES[1]:{"misconceptions":("distance_equals_speed_only","motion_teleports_to_result"),
           "probes":("count_equal_ticks","compare_position_after_seconds"),
           "risk":"early_distance_result"},
 CASES[2]:{"misconceptions":("atoms_are_consumed","animation_is_reaction_mechanism"),
           "probes":("count_H_and_O","trace_atom_identities"),
           "risk":"implied_reaction_mechanism"}
}
class BaseStrict(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True,frozen=True)

class Cognitive(BaseStrict):
    misconception_id:str=Field(min_length=5,max_length=64)
    probe_id:str=Field(min_length=5,max_length=64)
    source_scope:Literal["HYPOTHESIZED_FROM_TASK"]

class Narrative(BaseStrict):
    opening_focus:Literal["problem_first","contrast_first"]
    closure_focus:Literal["invariant_first","transfer_question"]
    text_provenance:Literal["HOST_NARRATION_UNCHANGED"]

class Visual(BaseStrict):
    representation:str=Field(min_length=4,max_length=64)
    persistent_ref:str=Field(min_length=4,max_length=64)
    focus_mode:Literal["active_object","invariant"]

class Motion(BaseStrict):
    transformation_profile:Literal["continuous","stepwise"]
    precondition_hold:Literal["short","deliberate"]
    reveal_at:Literal["WITNESS"]
    narration_relation:Literal["SEGMENT_ORDER_ONLY"]

class Critic(BaseStrict):
    witness_contract:Literal["NATIVE_BEFORE_AFTER_PLUS_HOST_INVARIANT"]
    risk_id:str=Field(min_length=5,max_length=64)
    early_answer:Literal["BLOCK"]
    human_quality:Literal["UNRATED"]

class FiveRoleCandidate(BaseStrict):
    protocol_version:Literal["v3-63-five-role-creative-decision-wire-v1"]
    case_id:Literal[
      "probability_complement_3_of_8","constant_speed_distance","water_reaction_balance"
    ]
    evidence_sha256:str=Field(pattern=r"^[a-f0-9]{64}$")
    cognitive_designer:Cognitive
    narrative_designer:Narrative
    visual_thinker:Visual
    motion_director:Motion
    visual_critic:Critic

def host_decision(candidate:FiveRoleCandidate)->dict:
    case=candidate.case_id
    approved=CATALOG[case]
    if candidate.evidence_sha256!=digest(exact_facts(case)):
        raise ValueError("V363_FROZEN_HOST_LEDGER_MISMATCH")
    c=candidate.cognitive_designer
    if c.misconception_id not in approved["misconceptions"]:
        raise ValueError("V363_UNSOURCED_MISCONCEPTION")
    if c.probe_id not in approved["probes"]:
        raise ValueError("V363_UNKNOWN_PROBE")
    v=candidate.visual_thinker
    if v.representation!=LAYOUTS[case] or v.persistent_ref!=REFERENTS[case]:
        raise ValueError("V363_CROSS_ROLE_REFERENT_OR_LAYOUT_MISMATCH")
    if candidate.visual_critic.risk_id!=approved["risk"]:
        raise ValueError("V363_CRITIC_NOT_GROUNDED")
    # Host narration, source claims and invariant cannot be affected by this wire.
    story_style=("focus_first" if candidate.narrative_designer.opening_focus==
                 "problem_first" else "witness_first")
    story=host_story(case,story_style)
    return {"story":story,"case_id":case,"visual_style":story_style,
        "focus_mode":v.focus_mode,
        "transformation_profile":candidate.motion_director.transformation_profile,
        "precondition_hold":candidate.motion_director.precondition_hold,
        "opening_focus":candidate.narrative_designer.opening_focus,
        "closure_focus":candidate.narrative_designer.closure_focus,
        "risk_id":approved["risk"],"source":"EXTERNAL_CANDIDATE_UNVERIFIED_OR_HOST_TEST",
        "model_authoring":"NOT_VERIFIED","learner_effect":"NOT_MEASURED",
        "human_quality":"UNRATED","release":"BLOCKED"}

def parse_unique_json(data:bytes):
    if type(data) is not bytes or not 0<len(data)<=MAX_BYTES:
        raise ValueError("V363_BAD_OR_OVERSIZE_WIRE")
    def refuse_constant(_):
        raise ValueError("V363_NONFINITE_JSON")
    def unique_pairs(pairs):
        out={}
        for k,v in pairs:
            if k in out: raise ValueError("V363_DUPLICATE_JSON_KEY")
            out[k]=v
        return out
    try:
        return json.loads(data.decode("utf-8"),parse_constant=refuse_constant,
                          object_pairs_hook=unique_pairs)
    except (UnicodeError,TypeError,json.JSONDecodeError) as exc:
        raise ValueError("V363_MALFORMED_JSON") from exc

def admit(data:bytes)->tuple[FiveRoleCandidate,dict]:
    obj=parse_unique_json(data)
    try:
        candidate=FiveRoleCandidate.model_validate(obj,strict=True)
    except ValidationError as exc:
        # Never log raw model-supplied candidate or private narrator data.
        raise ValueError("V363_ROLE_WIRE_SCHEMA_BLOCKED") from None
    return candidate,host_decision(candidate)

def test_only_packet(case_id:str, variant:int)->bytes:
    """HOST TEST fixture, explicitly NOT a model or human authored candidate."""
    if case_id not in CASES or variant not in (0,1):
        raise ValueError("V363_TEST_FIXTURE_OUT_OF_SUPPORT")
    cat=CATALOG[case_id]
    obj={"protocol_version":VERSION,"case_id":case_id,
      "evidence_sha256":digest(exact_facts(case_id)),
      "cognitive_designer":{"misconception_id":cat["misconceptions"][variant],
                            "probe_id":cat["probes"][variant],
                            "source_scope":"HYPOTHESIZED_FROM_TASK"},
      "narrative_designer":{"opening_focus":
          ("problem_first","contrast_first")[variant],
          "closure_focus":("invariant_first","transfer_question")[variant],
          "text_provenance":"HOST_NARRATION_UNCHANGED"},
      "visual_thinker":{"representation":LAYOUTS[case_id],
        "persistent_ref":REFERENTS[case_id],
        "focus_mode":("invariant","active_object")[variant]},
      "motion_director":{"transformation_profile":
        ("continuous","stepwise")[variant],
        "precondition_hold":("short","deliberate")[variant],
        "reveal_at":"WITNESS","narration_relation":"SEGMENT_ORDER_ONLY"},
      "visual_critic":{"witness_contract":"NATIVE_BEFORE_AFTER_PLUS_HOST_INVARIANT",
        "risk_id":cat["risk"],"early_answer":"BLOCK","human_quality":"UNRATED"}}
    return json.dumps(obj,sort_keys=True,separators=(",",":")).encode()
