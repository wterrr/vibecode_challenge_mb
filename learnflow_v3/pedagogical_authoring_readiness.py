"""V3-58 research-only authoring-proposal acceptance. Does NOT call an LLM.

A syntactically legal candidate is not evidence that a model made good pedagogy.
Finite V3-57 host proofs, claims, referents and beat order remain authoritative.
"""
from __future__ import annotations
from hashlib import sha256
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from learnflow_v3.pedagogical_storytelling_slice import (
    STEPS, CLAIMS, REFERENT, plan, validate, facts
)

VERSION="v3-58-synthetic-model-facing-pedagogy-review-v1"
ORIGIN="OFFLINE_SYNTHETIC_NOT_MODEL_AUTHORED"
MOVEMENT=frozenset(("SCORE_SELECTION","SOFTMAX_NORMALIZATION",
    "CONTENT_TRANSPORT","SUBDIVIDE","EQUIVALENCE_LINK",
    "STATE_TRANSITION","CONDITION_PROBE"))
QUESTION="QUESTION_HOLD"
STATUS="UNKNOWN_NOT_VERIFIED"

class PedagogicalChoice(BaseModel):
    model_config=ConfigDict(strict=True,extra="forbid",frozen=True)
    beat_index:int=Field(ge=0,le=4)
    operation:str
    claim_id:str
    referent_id:str
    visual_justification:str=Field(min_length=18,max_length=280)
    witness_mode:Literal["OBSERVE_HOLD","SEMANTIC_MOTION"]
    display_lag_intent:Literal["UNKNOWN","LEAD","OVERLAP","FOLLOW"]="UNKNOWN"

class ProposedStory(BaseModel):
    model_config=ConfigDict(strict=True,extra="forbid",frozen=True)
    version:Literal["v3-58-synthetic-model-facing-pedagogy-review-v1"]
    origin:Literal["OFFLINE_SYNTHETIC_NOT_MODEL_AUTHORED"]
    case_id:Literal["attention_reversed_query","fraction_equivalence","process_heldout_unknown"]
    ledger_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    learner_problem:str=Field(min_length=18,max_length=250)
    closure_question:str=Field(min_length=16,max_length=250)
    observable_beats:tuple[PedagogicalChoice,...]=Field(min_length=5,max_length=5)
    allow_publish:Literal[False]=False

    @model_validator(mode="after")
    def preserve_authority(self):
        p=plan(self.case_id)
        validate(p)
        if self.ledger_sha256!=p.evidence_sha256:
            raise ValueError("V358_EVIDENCE_NOT_HOST_GROUNDED")
        for i,b in enumerate(self.observable_beats):
            expected=p.beats[i]
            if (b.beat_index!=i or b.operation!=expected.operation or
                b.claim_id!=expected.claim_id or
                b.referent_id!=expected.referent_id):
                raise ValueError("V358_FORGED_CLAIM_OR_BEAT_ORDER")
            mode="SEMANTIC_MOTION" if b.operation in MOVEMENT else "OBSERVE_HOLD"
            if b.witness_mode!=mode:
                raise ValueError("V358_FAKE_MOTION_WITNESS")
            if b.display_lag_intent!="UNKNOWN":
                # V3-57 hosts synthetic speech; native word alignment UNMEASURED.
                raise ValueError("V358_UNMEASURED_NARRATION_LEAD_LAG")
        return self

def synthetic_candidate(case_id:str)->dict:
    """Deterministic test fixture, no model authorship."""
    p=plan(case_id)
    validate(p)
    rationale={
      "QUESTION_HOLD":"Hold the unresolved question so the learner predicts the next operation",
      "SCORE_SELECTION":"Expose the host-approved query to key score relation with motion",
      "SOFTMAX_NORMALIZATION":"Tie the weight-change animation to the host verified normalization invariant",
      "CONTENT_TRANSPORT":"Show how the weighted values contribute to the context token",
      "AREA_PARTITION":"Hold the exact starting whole as the stable area reference",
      "SUBDIVIDE":"Split the SAME source whole without altering its shaded fraction",
      "EQUIVALENCE_LINK":"Emphasize equal shaded area while transforming the partition count",
      "STATE_SETUP":"Hold the existing directed process graph, with no invented edge",
      "STATE_TRANSITION":"Move the state focus along an existing validated transition",
      "CONDITION_PROBE":"Show the unknown check as unknown, never make it pass",
      "CLOSURE":"Hold the certified conclusion for learner inspection",
    }
    return {"version":VERSION,"origin":ORIGIN,"case_id":case_id,
        "ledger_sha256":p.evidence_sha256,
        "learner_problem":"Which visible change would establish the approved claim without inventing a fact?",
        "closure_question":"What observation would distinguish the demonstrated case from an unsupported one?",
        "observable_beats":[{"beat_index":i,"operation":b.operation,
            "claim_id":b.claim_id,"referent_id":b.referent_id,
            "visual_justification":rationale[b.operation],
            "witness_mode":"SEMANTIC_MOTION" if b.operation in MOVEMENT else "OBSERVE_HOLD",
            "display_lag_intent":"UNKNOWN"} for i,b in enumerate(p.beats)],
        "allow_publish":False}

def certify_candidate(raw:dict)->dict:
    candidate=ProposedStory.model_validate(raw)
    return {"case_id":candidate.case_id,"origin":candidate.origin,
        "ledger_sha256":candidate.ledger_sha256,
        "approval":"DATA_SCHEMA_AND_HOST_PROVENANCE_ONLY",
        "pedagogical_quality":"UNRATED",
        "real_model_authoring":"NOT_TESTED",
        "runtime_creativity":"NOT_TESTED",
        "output_runnable_source_code":False,
        "production":"BLOCKED"}
