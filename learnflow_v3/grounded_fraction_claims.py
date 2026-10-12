"""V3-49 versioned, *host-verified* topic-specific fraction claims.

Scope is intentionally one semantic family. This file never changes the
V3-45 global F1/F2/F3 claim bank or accepts freeform provider-generated code.
F1/F2/F3 here are local *roles*, rebound to a unique verified evidence SHA.
"""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
import json
from types import SimpleNamespace
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.semantic_visual_events import SemanticLesson, HOST_ORIGIN
from learnflow_v3.pedagogical_visual_grammar import offline_host_plan, validate_transformations

VERSION = "v3-49-host-grounded-fractions-v1"
ORIGIN = "V349_HOST_VERIFIED_TOPIC_EVIDENCE_NOT_MODEL"
WHOLE = 2.4
HEIGHT = 1.8
NUMBER_WORDS = ("zero","one","two","three","four","five","six","seven",
                "eight","nine","ten","eleven","twelve")


def digest(data: dict) -> str:
    return sha256(json.dumps(data,sort_keys=True,
        ensure_ascii=True,separators=(",",":")).encode()).hexdigest()


class FractionTopic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    topic_id: str = Field(pattern=r"^[a-z][a-z0-9_]{2,30}$")
    numerator: int = Field(ge=1,le=5)
    denominator: int = Field(ge=2,le=6)
    factor: int = Field(ge=2,le=3)
    target_numerator: int = Field(ge=1,le=12)
    target_denominator: int = Field(ge=2,le=12)

    @model_validator(mode="after")
    def exact_relation(self):
        if (self.numerator>=self.denominator or
            self.target_numerator!=self.numerator*self.factor or
            self.target_denominator!=self.denominator*self.factor or
            self.target_numerator>=self.target_denominator or
            Fraction(self.numerator,self.denominator)!=
            Fraction(self.target_numerator,self.target_denominator)):
            raise ValueError("V349_UNGROUNDED_FRACTION_TOPIC")
        return self


class ClaimRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    claim_id: Literal["F1","F2","F3"]
    predicate: Literal["same_fraction","multiply_both","same_shaded_share"]
    source_topic_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    facts_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class EvidenceBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["v3-49-host-grounded-fractions-v1"]
    origin: Literal["V349_HOST_VERIFIED_TOPIC_EVIDENCE_NOT_MODEL"]
    topic: FractionTopic
    proof: str
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    claims: tuple[ClaimRecord,ClaimRecord,ClaimRecord]


def proof(topic: FractionTopic) -> str:
    return (f"({topic.numerator}×{topic.factor})/"
            f"({topic.denominator}×{topic.factor}) = "
            f"{topic.target_numerator}/{topic.target_denominator}")


def fact_payload(topic: FractionTopic, role: str) -> dict:
    n,d,k=topic.numerator,topic.denominator,topic.factor
    facts={
      "F1":{"fraction":[n,d],"equivalent":[n*k,d*k],
            "identity":Fraction(n,d)==Fraction(n*k,d*k)},
      "F2":{"numerator_factor":[n,k,n*k],
            "denominator_factor":[d,k,d*k],"proof":proof(topic)},
      "F3":{"source_shaded":[n,d],"target_shaded":[n*k,d*k],
            "same_shaded_share":Fraction(n,d)==Fraction(n*k,d*k)}
    }
    return facts[role]


def ground(topic: FractionTopic) -> EvidenceBundle:
    if not isinstance(topic,FractionTopic):
        raise Blocked("V349_TYPED_TOPIC_REQUIRED")
    source_sha=digest({"version":VERSION, "topic":topic.model_dump()})
    predicates={"F1":"same_fraction","F2":"multiply_both",
                "F3":"same_shaded_share"}
    claims=tuple(ClaimRecord(claim_id=role,predicate=predicates[role],
        source_topic_sha256=source_sha,
        facts_sha256=digest(fact_payload(topic,role)))
        for role in ("F1","F2","F3"))
    return EvidenceBundle(version=VERSION,origin=ORIGIN,topic=topic,
                          proof=proof(topic),source_sha256=source_sha,
                          claims=claims)


def verify(bundle: EvidenceBundle) -> None:
    if not isinstance(bundle,EvidenceBundle):
        raise Blocked("V349_EVIDENCE_BUNDLE_REQUIRED")
    expected=ground(bundle.topic)
    if bundle.model_dump()!=expected.model_dump():
        raise Blocked("V349_UNBOUND_OR_TAMPERED_TOPIC_CLAIM")
    for record in bundle.claims:
        facts=fact_payload(bundle.topic,record.claim_id)
        if facts.get("identity",True) is False or facts.get("same_shaded_share",True) is False:
            raise Blocked("V349_UNPROVEN_RATIO")
    if bundle.origin!=ORIGIN:
        raise Blocked("V349_SYNTHETIC_ORIGIN_SPOOF")


def _tile(identifier:str,index:int,denom:int,shaded:int,offset:float)->dict:
    width=WHOLE/denom
    return {"id":identifier,"x":round(offset+(index+.5)*width,6),
            "y":.5,"width":round(width,6),"height":HEIGHT,
            "color":"TEAL" if index<shaded else "GREY"}


def _beat(narration,claim_ids,events):
    return {"narration":narration,"claim_ids":claim_ids,"events":events}


def _event(kind,target="",source="",at=0.,span=.1):
    return {"kind":kind,"target":target,"source":source,"at":at,"span":span}


def build(bundle: EvidenceBundle):
    """Compile untrusted ratio values only AFTER exact verification.

    Reuses V3-44 semantic graph validator, V3-47 finite grammar and Manim
    code generator. No bypass of V3-48's frozen SceneWire global bank.
    """
    verify(bundle)
    t=bundle.topic
    n,d,k=t.numerator,t.denominator,t.factor
    nd=t.target_denominator
    left=[_tile(f"src_{i}",i,d,n,-4.55) for i in range(d)]
    right=[_tile(f"dst_{i}",i,nd,n*k,1.6) for i in range(nd)]
    src_ids=[x["id"] for x in left]
    dst_ids=[x["id"] for x in right]
    s=NUMBER_WORDS
    labels=[
      {"id":"lesson_title","x":0.0,"y":2.25,"text":"Equivalent parts of a whole","color":"WHITE"},
      {"id":"source_ratio","x":-3.35,"y":-1.05,"text":f"{n}/{d}","color":"WHITE"},
      {"id":"target_ratio","x":2.8,"y":-1.05,"text":f"{n*k}/{nd}","color":"WHITE"},
      {"id":"equality_proof","x":0.0,"y":-2.1,"text":bundle.proof,"color":"YELLOW"},
      {"id":"equal_whole","x":0.0,"y":.45,"text":"Same shaded amount","color":"WHITE"}
    ]
    beat0=f"This whole has {s[d]} equal parts, with {s[n]} shaded. The first diagram shows {s[n]} out of {s[d]} equal parts."
    beat1=(f"Watch each original part split into {s[k]} smaller equal pieces. "
           f"The shaded area remains unchanged while there are now {s[nd]} parts.")
    beat2=(f"Multiply the numerator and denominator by {s[k]}. "
           f"This converts {s[n]} over {s[d]} to {s[n*k]} over {s[nd]} without changing its value.")
    beat3=(f"These two pictures show the same shaded share of the same whole. "
           f"Subdividing equal pieces changes how we count parts, not their ratio.")
    beats=[
      _beat(beat0,["F1"],[_event("show_label","lesson_title",at=0,span=.1),
          _event("reveal_partition","source_parts",at=.15,span=.1),
          _event("show_label","source_ratio",at=.32,span=.1),
          _event("hold",at=.55,span=.35)]),
      _beat(beat1,["F1","F3"],[_event("morph_partition","target_parts",
             source="source_parts",at=.0,span=.25),
          _event("show_label","target_ratio",at=.32,span=.1),
          _event("hold",at=.6,span=.3)]),
      _beat(beat2,["F2"],[_event("show_label","equality_proof",at=.05,span=.2),
          _event("emphasize","equality_proof",at=.32,span=.16),
          _event("hold",at=.65,span=.25)]),
      _beat(beat3,["F1","F3"],[_event("show_label","equal_whole",at=.05,span=.16),
          _event("emphasize","source_parts",at=.3,span=.12),
          _event("emphasize","target_parts",at=.5,span=.12),
          _event("hold",at=.72,span=.2)])
    ]
    raw={
      "title":f"{n}/{d} and {n*k}/{nd} show the same amount",
      "tiles":left+right,"labels":labels,
      "partitions":[
        {"id":"source_parts","part_ids":src_ids,"shaded_ids":src_ids[:n],
         "numerator":n,"denominator":d},
        {"id":"target_parts","part_ids":dst_ids,"shaded_ids":dst_ids[:n*k],
         "numerator":n*k,"denominator":nd}],
      "relations":[{"source":"source_parts","target":"target_parts",
                    "multiply_by":k,"proof_label_id":"equality_proof"}],
      "beats":beats,"provenance":HOST_ORIGIN
    }
    lesson=SemanticLesson.model_validate(raw)
    # Build a strictly validated adapter for the previously audited V3-47
    # grammar; do NOT construct or relax the legacy V3-45 SceneWire.
    graphics=[SimpleNamespace(kind="tile",**x) for x in left+right]+[
        SimpleNamespace(kind="label",**x) for x in labels]
    adapter=SimpleNamespace(
        family="fraction_equivalence",partitions=lesson.partitions,
        relations=lesson.relations,graphics=graphics,beats=lesson.beats)
    plan=offline_host_plan(adapter)
    validate_transformations(adapter,plan)
    return lesson,adapter,plan
