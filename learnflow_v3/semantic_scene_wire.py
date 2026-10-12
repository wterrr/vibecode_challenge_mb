"""V3-45: model-facing, strict provider-portable semantic scene DATA contract.

One discriminated family in host semantic validation: fraction_equivalence or
ordered_process. No model API. Provider schema is limited to the *previously*
audited V3-41 strict subset; conditional invariants remain host-authoritative.

Do not confuse local synthetic JSON or a compiled host Python file with a
model-authored scene. The only supported evidence is offline feasibility.
"""
from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from fractions import Fraction
import json
import keyword
import math
import re
from typing import Literal

from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from learnflow_v3.compatible_scene_protocol import _forbid_unsupported
from learnflow_v3.creative_manim_ablation import Blocked, PALETTE
from learnflow_v3.semantic_visual_events import SemanticLesson, HOST_ORIGIN, compile_manim as fraction_manim

VERSION = "v3-45-model-facing-two-family-semantic-wire-v1"
SYNTHETIC_ORIGIN = "SYNTHETIC_OFFLINE_JSON_MODEL_FACING_NOT_LIVE_MODEL"
FAMILIES = ("fraction_equivalence", "ordered_process")
COLORS = ("WHITE","TEAL","YELLOW","BLUE","ORANGE","GREEN","GREY")
KINDS = ("tile","label","node","edge")
KINDS_EVENTS = ("reveal_partition","morph_partition","show_label","emphasize","hold",
                "reveal_node","reveal_edge","traverse_edge")
ALLOWED_CLAIMS = {"fraction_equivalence":frozenset(("F1","F2","F3")),
                  "ordered_process":frozenset(("P1","P2","P3"))}
# These meaning anchors are a host-supplied, per-topic claim bank; they are
# NOT arbitrary factual discoveries obtained from the LLM.
CLAIM_BANK = {
    "F1":"One half equals two quarters.",
    "F2":"Multiplying numerator and denominator by two preserves this fraction.",
    "F3":"Two out of four equal shaded parts represent one half.",
    "P1":"Begin the ordered process at the Start step.",
    "P2":"After Start, the verification step checks a condition.",
    "P3":"After verification, the process reaches Finish.",
}

def _strict():
    return ConfigDict(extra="forbid")

class Visual(BaseModel):
    model_config=_strict()
    id:str=Field(pattern=r"^[a-z][a-z0-9_]{0,22}$")
    kind:Literal["tile","label","node","edge"]
    x:float=Field(ge=-5.6,le=5.6)
    y:float=Field(ge=-2.4,le=2.4)
    width:float=Field(ge=.2,le=4.0)
    height:float=Field(ge=.2,le=2.4)
    color:Literal["WHITE","TEAL","YELLOW","BLUE","ORANGE","GREEN","GREY"]
    text:str=Field(max_length=65)
    src:str
    dst:str

    @model_validator(mode="after")
    def correct(self):
        if keyword.iskeyword(self.id) or self.id in ("self","Text","Scene","Dot"):
            raise ValueError("V345_UNSAFE_IDENTIFIER")
        if self.kind in ("tile","edge") and self.text:
            raise ValueError("V345_VISUAL_TEXT_UNUSED_MUST_EMPTY")
        if self.kind in ("tile","label","node") and (self.src or self.dst):
            raise ValueError("V345_VISUAL_EDGE_FIELDS_UNUSED")
        if self.kind=="edge" and (not self.src or not self.dst or self.src==self.dst):
            raise ValueError("V345_EDGE_ENDPOINTS_INVALID")
        if self.kind in ("label","node") and not self.text.strip():
            raise ValueError("V345_EMPTY_VISIBLE_TEXT")
        if self.kind=="edge" and (self.x or self.y):
            raise ValueError("V345_EDGE_POSITION_MUST_ZERO")
        if any(ord(c)<32 for c in self.text):
            raise ValueError("V345_CONTROL_CHAR")
        return self

class PartitionWire(BaseModel):
    model_config=_strict()
    id:str=Field(pattern=r"^[a-z][a-z0-9_]{0,22}$")
    part_ids:list[str]=Field(min_length=2,max_length=12)
    shaded_ids:list[str]=Field(min_length=1,max_length=11)
    numerator:int=Field(ge=1,le=12)
    denominator:int=Field(ge=2,le=12)

class RelationWire(BaseModel):
    model_config=_strict()
    source:str
    target:str
    multiply_by:int=Field(ge=2,le=8)
    proof_label_id:str

class EventWire(BaseModel):
    model_config=_strict()
    kind:Literal["reveal_partition","morph_partition","show_label","emphasize","hold",
                 "reveal_node","reveal_edge","traverse_edge"]
    target:str
    source:str
    at:float=Field(ge=0,lt=1)
    span:float=Field(gt=0,le=.6)

class BeatWire(BaseModel):
    model_config=_strict()
    claim_ids:list[Literal["F1","F2","F3","P1","P2","P3"]]=Field(min_length=1,max_length=3)
    narration:str=Field(min_length=65,max_length=270)
    events:list[EventWire]=Field(min_length=1,max_length=10)

class SceneWire(BaseModel):
    model_config=_strict()
    family:Literal["fraction_equivalence","ordered_process"]
    title:str=Field(min_length=8,max_length=65)
    objective:str=Field(min_length=12,max_length=140)
    graphics:list[Visual]=Field(min_length=4,max_length=32)
    partitions:list[PartitionWire]=Field(max_length=5)
    relations:list[RelationWire]=Field(max_length=4)
    beats:list[BeatWire]=Field(min_length=4,max_length=4)

    @model_validator(mode="after")
    def semantic(self):
        ids=[v.id for v in self.graphics]+[p.id for p in self.partitions]
        if len(set(ids))!=len(ids):
            raise ValueError("V345_DUPLICATE_GRAPHIC_ID")
        objs={x.id:x for x in self.graphics}
        if any(set(b.claim_ids)-ALLOWED_CLAIMS[self.family] for b in self.beats):
            raise ValueError("V345_UNTRUSTED_CLAIM_ID")
        if {cid for b in self.beats for cid in b.claim_ids}!=ALLOWED_CLAIMS[self.family]:
            raise ValueError("V345_FACT_COVERAGE_INCOMPLETE")
        if self.family=="fraction_equivalence":
            if (not self.partitions or not self.relations or
                any(x.kind in ("node","edge") for x in self.graphics)):
                raise ValueError("V345_FRACTION_FAMILY_FIELD_MISMATCH")
            # The V3-44 validator is the authoritative existing engine: it
            # handles partition overlaps, proof, exact ratio and event state.
            fraction_lesson(self)
        else:
            if self.partitions or self.relations or any(
                x.kind=="tile" for x in self.graphics
            ):
                raise ValueError("V345_FLOW_FAMILY_FIELD_MISMATCH")
            # Numbers in process screen labels must not escape the trusted
            # process claim bank through the separate graphics channel.
            if any(re.search(r"\\d",x.text) for x in self.graphics
                   if x.kind in ("node","label")):
                raise ValueError("V345_PROCESS_UNSUPPORTED_VISIBLE_NUMBER")
            # Compiler manufactures one caption variable per process node.
            # Forbid a user-declared identifier colliding with generated names.
            derived={x.id+"_caption" for x in self.graphics if x.kind=="node"}
            if derived & set(ids):
                raise ValueError("V345_GENERATED_CAPTION_ID_COLLISION")
            self._validate_process(objs)
        # Unknown number tokens fail before speech is synthesized. This is a
        # syntactic screen; semantic prose truth still needs fact-checking.
        for beat in self.beats:
            nums=re.findall(r"(?<![A-Za-z_])\d+(?:\.\d+)?(?![A-Za-z_])",beat.narration)
            if self.family=="ordered_process" and nums:
                raise ValueError("V345_PROCESS_UNSUPPORTED_NUMERIC_CLAIM")
            if self.family=="fraction_equivalence" and any(n not in ("1","2","4") for n in nums):
                raise ValueError("V345_FRACTION_UNSUPPORTED_NUMERIC_CLAIM")
        return self

    def _validate_process(self,objs):
        nodes={x.id:x for x in self.graphics if x.kind=="node"}
        edges={x.id:x for x in self.graphics if x.kind=="edge"}
        labels={x.id:x for x in self.graphics if x.kind=="label"}
        if len(nodes)<3 or len(edges)<2:
            raise ValueError("V345_PROCESS_REQUIRES_MINIMUM_GRAPH")
        if len(set(x.text for x in nodes.values()))!=len(nodes):
            raise ValueError("V345_NODE_NAMES_DUPLICATED")
        forward=defaultdict(list)
        indeg={nid:0 for nid in nodes}
        for e in edges.values():
            if e.src not in nodes or e.dst not in nodes:
                raise ValueError("V345_EDGE_DANGLING_NODE")
            forward[e.src].append(e.dst);indeg[e.dst]+=1
        if sum(v==0 for v in indeg.values())!=1:
            raise ValueError("V345_PROCESS_NEEDS_SINGLE_START")
        start=next(k for k,d in indeg.items() if d==0)
        if sum(not forward[n] for n in nodes)!=1:
            raise ValueError("V345_PROCESS_NEEDS_SINGLE_END")
        visited=[];q=deque((start,))
        while q:
            n=q.popleft()
            if n in visited:raise ValueError("V345_PROCESS_CYCLE_OR_JOIN")
            visited.append(n)
            q.extend(forward[n])
        if set(visited)!=set(nodes) or len(edges)!=len(nodes)-1:
            raise ValueError("V345_PROCESS_UNREACHABLE_OR_BRANCH_UNSUPPORTED")
        # Minimum safety: node centres and bounded sizes may not overlap.
        for ix,x in enumerate(nodes.values()):
            for y in list(nodes.values())[ix+1:]:
                if (abs(x.x-y.x)<(x.width+y.width)/2+.15 and
                    abs(x.y-y.y)<(x.height+y.height)/2+.15):
                    raise ValueError("V345_PROCESS_NODE_OVERLAP")
        visible=set()
        seen_traversal=[]
        visit_nodes=[]
        for beat in self.beats:
            last=0.
            for e in beat.events:
                if e.at<last-1e-6 or e.at+e.span>1+1e-6:
                    raise ValueError("V345_PROCESS_EVENT_OVERLAP_OR_OUTSIDE_BEAT")
                last=e.at+e.span
                if e.kind=="hold":
                    if e.target or e.source:raise ValueError("V345_HOLD_NOT_EMPTY")
                elif e.kind=="reveal_node":
                    if e.target not in nodes or e.target in visible or e.source:
                        raise ValueError("V345_INVALID_NODE_REVEAL")
                    visible.add(e.target);visit_nodes.append(e.target)
                elif e.kind=="reveal_edge":
                    x=edges.get(e.target)
                    if x is None or e.target in visible or e.source or x.src not in visible or x.dst not in visible:
                        raise ValueError("V345_INVALID_EDGE_REVEAL")
                    visible.add(e.target)
                elif e.kind=="traverse_edge":
                    x=edges.get(e.target)
                    if x is None or e.target not in visible or e.source or "P2" not in beat.claim_ids and "P3" not in beat.claim_ids:
                        raise ValueError("V345_INVALID_EDGE_TRAVERSAL")
                    seen_traversal.append(e.target)
                elif e.kind=="show_label":
                    if e.target not in labels or e.target in visible or e.source:
                        raise ValueError("V345_INVALID_LABEL_REVEAL")
                    visible.add(e.target)
                elif e.kind=="emphasize":
                    if e.target not in visible or e.source:
                        raise ValueError("V345_HIGHLIGHT_BEFORE_SHOW")
                else:
                    raise ValueError("V345_FRACTION_EVENT_IN_PROCESS")
        if visit_nodes!=visited:
            raise ValueError("V345_NODE_REVEAL_ORDER_WRONG")
        correct=[e.id for a,b in zip(visited,visited[1:]) for e in edges.values()
                 if e.src==a and e.dst==b]
        if seen_traversal!=correct:
            raise ValueError("V345_PROCESS_TRAVERSAL_NOT_TOPOLOGY")

def fraction_lesson(w:SceneWire)->SemanticLesson:
    """Lossless host wrapper around existing V3-44 certified semantic graph."""
    tiles=[];labels=[]
    for x in w.graphics:
        if x.kind=="tile":
            tiles.append({k:getattr(x,k) for k in ("id","x","y","width","height","color")})
        elif x.kind=="label":
            labels.append({k:getattr(x,k) for k in ("id","x","y","text","color")})
    for b in w.beats:
        if any(e.kind in ("reveal_node","reveal_edge","traverse_edge") for e in b.events):
            raise ValueError("V345_WRONG_FAMILY_EVENT")
    return SemanticLesson.model_validate({
        "title":w.title,
        "tiles":tiles,"labels":labels,
        "partitions":[p.model_dump() for p in w.partitions],
        "relations":[r.model_dump() for r in w.relations],
        "beats":[{"claim_ids":b.claim_ids,"narration":b.narration,
                  "events":[e.model_dump() for e in b.events]} for b in w.beats],
        "provenance":HOST_ORIGIN,
    })

def _s(typ,**kwargs):
    return {"type":typ,**kwargs}
def _obj(properties):
    return {"type":"object","properties":properties,"required":list(properties),
            "additionalProperties":False}
def _enum_values(low,high,step=1):
    n=round((high-low)/step)
    return [round(low+i*step,4) for i in range(n+1)]

def portable_semantic_schema():
    """V3-41 provider-portable subset, total enum budget verified.

    Model sees ONE schema with typed family tag; host rejects impossible
    combinations. Does not claim a provider endpoint has accepted the schema.
    """
    grid=lambda lo,hi,step:_s("number",enum=_enum_values(lo,hi,step))
    graphic=_obj({
        "id":_s("string"),"kind":_s("string",enum=list(KINDS)),
        "x":grid(-5.6,5.6,.1),"y":grid(-2.4,2.4,.1),
        "width":grid(.2,4,.1),"height":grid(.2,2.4,.1),
        "color":_s("string",enum=list(COLORS)),"text":_s("string"),
        "src":_s("string"),"dst":_s("string"),
    })
    part=_obj({"id":_s("string"),"part_ids":_s("array",items=_s("string")),
               "shaded_ids":_s("array",items=_s("string")),
               "numerator":_s("integer",enum=list(range(1,13))),
               "denominator":_s("integer",enum=list(range(2,13)))})
    relation=_obj({"source":_s("string"),"target":_s("string"),
                   "multiply_by":_s("integer",enum=list(range(2,9))),
                   "proof_label_id":_s("string")})
    event=_obj({"kind":_s("string",enum=list(KINDS_EVENTS)),
                "target":_s("string"),"source":_s("string"),
                "at":grid(0,.95,.05),"span":grid(.05,.6,.05)})
    beat=_obj({"claim_ids":_s("array",items=_s("string",enum=list(CLAIM_BANK))),
               "narration":_s("string"),
               "events":_s("array",items=event)})
    schema=_obj({"family":_s("string",enum=list(FAMILIES)),
                 "title":_s("string"),"objective":_s("string"),
                 "graphics":_s("array",items=graphic),
                 "partitions":_s("array",items=part),
                 "relations":_s("array",items=relation),
                 "beats":_s("array",items=beat)})
    _forbid_unsupported(schema)
    Draft202012Validator.check_schema(schema)
    return schema

def decode_model_facing_scene(raw)->SceneWire:
    """Reject; no model prose executed, no repair, normalization or inference."""
    if not isinstance(raw,dict):
        raise Blocked("V345_MODEL_JSON_NOT_OBJECT")
    try:
        Draft202012Validator(portable_semantic_schema()).validate(raw)
    except Exception:
        raise Blocked("V345_PROVIDER_PORTABLE_SCHEMA_REJECTED") from None
    try:
        return SceneWire.model_validate(raw)
    except ValidationError:
        raise Blocked("V345_HOST_SEMANTIC_SCENE_REJECTED") from None

def compile_scene(scene:SceneWire,durations:list[float])->str:
    if len(durations)!=4 or any(not 2<=d<=20 for d in durations):
        raise Blocked("V345_MEASURED_BEAT_DURATION_INVALID")
    if scene.family=="fraction_equivalence":
        code=fraction_manim(fraction_lesson(scene),durations)
    else:
        code=_compile_process(scene,durations)
    if any(x in code for x in ("__import__","eval(","exec(","subprocess","import os","os.system")):
        raise Blocked("V345_HOST_CODE_SAFETY_FAILURE")
    compile(code,"<v345 trusted host manim>","exec")
    return code

def _compile_process(scene:SceneWire,durations:list[float])->str:
    # This is the SECOND semantic family, independent of any fraction fixture.
    nodes={o.id:o for o in scene.graphics if o.kind=="node"}
    edges={o.id:o for o in scene.graphics if o.kind=="edge"}
    labels={o.id:o for o in scene.graphics if o.kind=="label"}
    lines=["# V3-45 SYNTHETIC_OFFLINE_JSON_MODEL_FACING_NOT_LIVE_MODEL",
           "from manim import *","class GeneratedLesson(Scene):",
           "    def construct(self):","        self.camera.background_color = '#000000'"]
    for n in nodes.values():
        lines.append(f"        {n.id} = RoundedRectangle(width={n.width:.2f},height={n.height:.2f},"
                     f"corner_radius=.14,color={PALETTE[n.color]!r},fill_opacity=.22)"
                     f".move_to([{n.x:.2f},{n.y:.2f},0])")
        lines.append(f"        {n.id}_caption = Text({n.text!r},font='CMU Serif',font_size=30,"
                     f"color={PALETTE['WHITE']!r}).scale_to_fit_width({min(n.width*.85,2.0):.2f})"
                     f".move_to({n.id}.get_center())")
    for e in edges.values():
        lines.append(f"        {e.id} = Arrow({e.src}.get_center(),{e.dst}.get_center(),"
                     f"buff=.75,stroke_width=4,color={PALETTE[e.color]!r})")
    for l in labels.values():
        lines.append(f"        {l.id} = Text({l.text!r},font='CMU Serif',font_size=31,"
                     f"color={PALETTE[l.color]!r}).scale_to_fit_width({min(7.,max(.7,len(l.text)*.22)):.2f})"
                     f".move_to([{l.x:.2f},{l.y:.2f},0])")
    lines.append("        cursor = Dot(color=YELLOW,radius=.09)")
    for i,(beat,full) in enumerate(zip(scene.beats,durations)):
        lines.append(f"        # V345 AUDIO BEAT {i+1}, actual seconds {full:.5f}")
        elapsed=0.
        for e in beat.events:
            ahead=full*e.at-elapsed
            if ahead>1e-6:lines.append(f"        self.wait({ahead:.5f})")
            dur=full*e.span
            if e.kind=="reveal_node":
                lines.append(f"        self.play(FadeIn({e.target}),FadeIn({e.target}_caption),run_time={dur:.5f})")
            elif e.kind=="reveal_edge":
                lines.append(f"        self.play(Create({e.target}),run_time={dur:.5f})")
            elif e.kind=="traverse_edge":
                edge=edges[e.target]
                lines.append(f"        cursor.move_to({edge.src}.get_center())")
                lines.append(f"        self.add(cursor)")
                lines.append(f"        self.play(MoveAlongPath(cursor,Line({edge.src}.get_center(),"
                             f"{edge.dst}.get_center())),run_time={dur:.5f})")
            elif e.kind=="show_label":
                lines.append(f"        self.play(FadeIn({e.target}),run_time={dur:.5f})")
            elif e.kind=="emphasize":
                lines.append(f"        self.play(Indicate({e.target},color=YELLOW),run_time={dur:.5f})")
            else:
                lines.append(f"        self.wait({dur:.5f})")
            elapsed=full*(e.at+e.span)
        if full-elapsed>1e-5:
            lines.append(f"        self.wait({full-elapsed:.5f})")
    lines.append("        # V345 video-only padding; exact-frame deterministic mux trims here.")
    lines.append("        self.wait(.8)")
    return "\n".join(lines)+"\n"
