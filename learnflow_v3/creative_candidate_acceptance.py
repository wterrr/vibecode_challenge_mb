"""V3-54: accept simulated *model-shaped* Creative SceneGraph JSON safely.

OFFLINE ONLY. These messages are locally authored, NOT provider responses.
The host injects provenance, version and verified facts, not the candidate.
Do not claim semantic truth of unrestricted narration or AI creativity.
"""
from __future__ import annotations

from hashlib import sha256
import json

from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Literal

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_scene_graph import (
    Scene,Beat,Storyboard,ORIGIN as HOST_ORIGIN,VERSION as HOST_VERSION,
    ledger,digest,validate
)

VERSION="v3-54-scene-candidate-wire-v1"
MOCK_ORIGIN="HOST_MOCK_CANDIDATE_NOT_MODEL"
MAX_BYTES=65536
TOPIC="frozen_scaled_dot_product_attention"


class Candidate(BaseModel):
    """No provider/model origin or arbitrary executable fields in authoring wire."""
    model_config=ConfigDict(extra="forbid",strict=True)
    protocol_version:Literal["v3-54-scene-candidate-wire-v1"]
    topic_id:Literal["frozen_scaled_dot_product_attention"]
    evidence_sha256:str=Field(pattern=r"^[a-f0-9]{64}$")
    title:str=Field(min_length=6,max_length=60)
    scenes:list[Scene]=Field(min_length=2,max_length=5)
    beats:list[Beat]=Field(min_length=3,max_length=7)


def candidate_schema()->dict:
    schema=Candidate.model_json_schema()
    Draft202012Validator.check_schema(schema)
    return schema


def packet_for_fixture(source:dict)->dict:
    """Host-only mock factory, *never* passed off as a live LLM result."""
    return {
       "protocol_version":VERSION,
       "topic_id":TOPIC,
       "evidence_sha256":source["evidence_sha256"],
       "title":source["title"],
       "scenes":source["scenes"],
       "beats":source["beats"]
    }


def _diag(stage:str,code:str,model_sha:str|None=None,paths:list[dict]|None=None)->dict:
    return {
      "status":"BLOCKED","stage":stage,"code":code,
      "error_shapes":(paths or [])[:8],
      "input_sha256":model_sha,
      "raw_candidate_stored":False,
      "real_provider_calls":0,
      "origin":MOCK_ORIGIN
    }


def accept(candidate_bytes:bytes):
    """Return trusted SceneGraph + sanitized diagnostic. No raw provider text kept."""
    if not isinstance(candidate_bytes,bytes) or len(candidate_bytes)>MAX_BYTES:
        return None,_diag("wire","V354_INVALID_OR_OVERSIZE_WIRE")
    h=sha256(candidate_bytes).hexdigest()
    try:
        def refuse_constant(_):raise ValueError("nonfinite JSON")
        obj=json.loads(candidate_bytes.decode("utf-8"),
                       parse_constant=refuse_constant)
    except (ValueError,UnicodeError,TypeError,OverflowError):
        return None,_diag("wire","V354_MALFORMED_JSON",h)
    schema=candidate_schema()
    errs=sorted(Draft202012Validator(schema).iter_errors(obj),
                key=lambda e:(tuple(map(str,e.absolute_path)),str(e.validator)))
    if errs:
        safe=[{"path":".".join(str(v) for v in e.absolute_path)[:96],
               "keyword":str(e.validator)[:35]} for e in errs[:8]]
        return None,_diag("json_schema","V354_CANDIDATE_SCHEMA_REJECTED",h,safe)
    try:
        typed=Candidate.model_validate(obj)
    except ValidationError:
        return None,_diag("typed_schema","V354_STRICT_TYPED_REJECTED",h)
    if typed.evidence_sha256!=digest(ledger()):
        return None,_diag("evidence","V354_LEDGER_BINDING_FAILED",h)
    trusted={
       "version":HOST_VERSION,"origin":HOST_ORIGIN,
       "evidence_sha256":typed.evidence_sha256,
       "title":typed.title,
       "scenes":[s.model_dump(mode="json") for s in typed.scenes],
       "beats":[b.model_dump(mode="json") for b in typed.beats]
    }
    try:
        storyboard,facts,graphs,layout=validate(trusted)
    except Blocked as e:
        code=str(e)
        if not code.startswith("V351_") or len(code)>90:
            code="V354_UNKNOWN_GRAPH_REJECTION"
        return None,_diag("semantic_graph",code,h)
    accepted={
       "storyboard":storyboard,"facts":facts,"graphs":graphs,"layout":layout,
       "candidate_sha256":h,
       "trusted_scene_sha256":digest(trusted),
       "source_class":MOCK_ORIGIN
    }
    return accepted,{
       "status":"ACCEPTED_OFFLINE_CONTRACT_ONLY",
       "stage":"accepted","code":None,
       "error_shapes":[],"input_sha256":h,
       "raw_candidate_stored":False,
       "real_provider_calls":0,"origin":MOCK_ORIGIN,
       "accepted_claims":list(facts["claims"]),
       "graph_count":len(graphs),
       "node_count":sum(len(g.nodes) for g in graphs),
       "note":"MOCK packet accepted; genuine model compatibility NOT TESTED"
    }


def mock_candidate_bytes(fixture:dict)->bytes:
    return json.dumps(packet_for_fixture(fixture),
       ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
