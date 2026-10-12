"""V3-47 finite, evidence-grounded *data* grammar for pedagogical visual events.

This grammar is intentionally HOST-AUTHORED for this OFFLINE checkpoint. The
V3-45 provider-facing schema is unchanged; no inference or provider schema
compatibility is claimed. The Manim compiler consumes ONLY validated records,
never author-supplied code. Unsupported truth conditions FAIL CLOSED.
"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from learnflow_v3.creative_manim_ablation import Blocked

OPS = ("subdivide","equivalence_link","condition_probe",
       "state_transition","causal_emphasis")
GRAMMAR_VERSION="v3-47-host-semantic-grammar-v1"
SYNTHETIC_GRAMMAR_ORIGIN="HOST_SYNTHETIC_PEDAGOGICAL_GRAMMAR_NOT_MODEL_AUTHORED"

class Transformation(BaseModel):
    model_config=ConfigDict(extra="forbid",frozen=True)
    kind:Literal["subdivide","equivalence_link","condition_probe",
                 "state_transition","causal_emphasis"]
    beat_index:int=Field(ge=0,le=3)
    event_target:str=Field(min_length=1,max_length=32)
    claim_id:Literal["F1","F2","F3","P1","P2","P3"]
    subject_id:str=Field(min_length=1,max_length=32)
    source_id:str=Field(max_length=32)
    factor:int=Field(ge=1,le=8)
    outcome:Literal["not_applicable","unknown"]

class TransformationPlan(BaseModel):
    model_config=ConfigDict(extra="forbid")
    grammar_version:Literal["v3-47-host-semantic-grammar-v1"]
    origin:Literal["HOST_SYNTHETIC_PEDAGOGICAL_GRAMMAR_NOT_MODEL_AUTHORED"]
    actions:list[Transformation]=Field(min_length=2,max_length=10)

    @model_validator(mode="after")
    def unique(self):
        keys=[(x.beat_index,x.event_target,x.kind) for x in self.actions]
        if len(keys)!=len(set(keys)):
            raise ValueError("V347_DUPLICATE_GRAMMAR_ACTION")
        return self


def validate_transformations(scene, plan:TransformationPlan)->list[dict]:
    """Bind graph actions against every fact, beat and existing event ID.

    An outcome of PASS or FAIL is UNSUPPORTED; the process source contains
    neither a predicate nor measured truth. This is not a causal proof.
    """
    if not isinstance(plan,TransformationPlan):
        raise Blocked("V347_GRAMMAR_TYPED_PLAN_REQUIRED")
    nodes={g.id:g for g in scene.graphics if g.kind=="node"}
    edges={g.id:g for g in scene.graphics if g.kind=="edge"}
    labels={g.id:g for g in scene.graphics if g.kind=="label"}
    partitions={x.id:x for x in scene.partitions}
    relations={(r.source,r.target):r for r in scene.relations}
    matched=[]
    for a in plan.actions:
        beat=scene.beats[a.beat_index]
        if a.claim_id not in beat.claim_ids:
            raise Blocked("V347_GRAMMAR_CLAIM_UNBOUND")
        expected_kind={
            "subdivide":"morph_partition",
            "equivalence_link":"show_label",
            "condition_probe":"traverse_edge",
            "state_transition":"traverse_edge",
            "causal_emphasis":"traverse_edge",
        }[a.kind]
        # One object may legitimately have distinct events in the same
        # narrated beat (e.g. reveal_edge then traverse_edge). Identity is
        # (beat, event KIND, object) not just (beat, object).
        events=[e for e in beat.events if e.target==a.event_target
                and e.kind==expected_kind]
        if len(events)!=1:
            raise Blocked("V347_GRAMMAR_EVENT_UNBOUND")
        event=events[0]
        if scene.family=="fraction_equivalence":
            if a.kind=="subdivide":
                if (event.kind!="morph_partition" or a.source_id!=event.source
                    or a.subject_id!=event.target or a.claim_id!="F3"):
                    raise Blocked("V347_SUBDIVISION_UNGROUNDED")
                r=relations.get((a.source_id,a.subject_id))
                if not r or r.multiply_by!=a.factor or a.factor<2:
                    raise Blocked("V347_SUBDIVISION_FACTOR_UNGROUNDED")
                left,right=partitions[a.source_id],partitions[a.subject_id]
                if len(right.part_ids)!=a.factor*len(left.part_ids):
                    raise Blocked("V347_SUBDIVISION_CELL_INVARIANT")
                if a.outcome!="not_applicable":
                    raise Blocked("V347_FRACTION_OUTCOME_INVALID")
            elif a.kind=="equivalence_link":
                r=next((r for r in scene.relations if r.proof_label_id==a.subject_id),None)
                if not (r and event.kind=="show_label" and
                        event.target==r.proof_label_id and
                        a.source_id==r.source and a.claim_id=="F2" and
                        a.factor==r.multiply_by and a.outcome=="not_applicable"):
                    raise Blocked("V347_EQUIVALENCE_PROOF_UNGROUNDED")
            else:
                raise Blocked("V347_WRONG_FAMILY_FRACTION_ACTION")
        elif scene.family=="ordered_process":
            if a.factor!=1:
                raise Blocked("V347_PROCESS_FACTOR_INVALID")
            if (event.kind!="traverse_edge" or event.target not in edges or
                a.event_target!=a.subject_id or
                a.source_id!=edges[a.subject_id].src):
                raise Blocked("V347_GRAPH_TRANSITION_UNBOUND")
            edge=edges[a.subject_id]
            if a.kind=="condition_probe":
                if (a.claim_id!="P2" or a.outcome!="unknown" or
                    "verify" not in nodes[edge.dst].text.lower()):
                    # This source refers to Verify as a particular fact
                    # label; it cannot generalize to arbitrary predicates.
                    raise Blocked("V347_CONDITION_FACT_NOT_PROVIDED")
            elif a.kind in ("state_transition","causal_emphasis"):
                if (a.outcome!="not_applicable" or
                    a.claim_id not in ("P2","P3")):
                    raise Blocked("V347_PROCESS_CLAIM_OR_OUTCOME_INVALID")
                if a.kind=="causal_emphasis" and a.claim_id!="P3":
                    raise Blocked("V347_CAUSAL_EMPHASIS_NOT_GROUNDED")
            else:
                raise Blocked("V347_WRONG_FAMILY_PROCESS_ACTION")
        else:
            raise Blocked("V347_UNKNOWN_SEMANTIC_FAMILY")
        matched.append({"beat_index":a.beat_index,"event_target":event.target,
                        "event_kind":event.kind,"claim_id":a.claim_id,
                        "kind":a.kind,"relative_at":event.at,
                        "relative_span":event.span,"truth_status":a.outcome})
    if scene.family=="fraction_equivalence":
        if {a.kind for a in plan.actions}!={"subdivide","equivalence_link"}:
            raise Blocked("V347_FRACTION_GRAMMAR_COVERAGE_INCOMPLETE")
    else:
        kinds={a.kind for a in plan.actions}
        if kinds!={"condition_probe","state_transition","causal_emphasis"}:
            raise Blocked("V347_PROCESS_GRAMMAR_COVERAGE_INCOMPLETE")
    return matched


def offline_host_plan(scene)->TransformationPlan:
    """Create registered synthetic grammar DATA, never an LLM response.

    Pull events/objects from the validated scene graph instead of using
    fixture IDs. A held-out graph can rename all IDs without rewriting code.
    """
    actions=[]
    if scene.family=="fraction_equivalence":
        r=scene.relations[0]
        for i,beat in enumerate(scene.beats):
            for e in beat.events:
                if e.kind=="morph_partition" and e.source==r.source and e.target==r.target:
                    actions.append(Transformation(kind="subdivide",beat_index=i,
                        event_target=e.target,claim_id="F3",subject_id=r.target,
                        source_id=r.source,factor=r.multiply_by,outcome="not_applicable"))
                if e.kind=="show_label" and e.target==r.proof_label_id:
                    actions.append(Transformation(kind="equivalence_link",beat_index=i,
                        event_target=e.target,claim_id="F2",subject_id=r.proof_label_id,
                        source_id=r.source,factor=r.multiply_by,outcome="not_applicable"))
    elif scene.family=="ordered_process":
        traversal=[(i,beat,e) for i,beat in enumerate(scene.beats)
                   for e in beat.events if e.kind=="traverse_edge"]
        if len(traversal)!=2:
            raise Blocked("V347_PROCESS_EXPECTS_TWO_CERTIFIED_TRANSITIONS")
        for k,(i,beat,e) in enumerate(traversal):
            edge=next(g for g in scene.graphics if g.id==e.target and g.kind=="edge")
            claim="P2" if k==0 else "P3"
            actions.append(Transformation(kind="state_transition",beat_index=i,
                event_target=e.target,claim_id=claim,subject_id=e.target,
                source_id=edge.src,factor=1,outcome="not_applicable"))
            if k==0:
                actions.append(Transformation(kind="condition_probe",beat_index=i,
                    event_target=e.target,claim_id="P2",subject_id=e.target,
                    source_id=edge.src,factor=1,outcome="unknown"))
            else:
                actions.append(Transformation(kind="causal_emphasis",beat_index=i,
                    event_target=e.target,claim_id="P3",subject_id=e.target,
                    source_id=edge.src,factor=1,outcome="not_applicable"))
    else:
        raise Blocked("V347_UNSUPPORTED_FAMILY")
    plan=TransformationPlan(grammar_version=GRAMMAR_VERSION,
                            origin=SYNTHETIC_GRAMMAR_ORIGIN,actions=actions)
    validate_transformations(scene,plan)
    return plan


def actions_for(plan,beat_index:int,event_target:str):
    return [a for a in plan.actions
            if a.beat_index==beat_index and a.event_target==event_target]
