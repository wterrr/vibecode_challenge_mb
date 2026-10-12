"""V3-51 generic evidence-bound V2 SceneGraph -> host-owned finite Manim compiler.

This is NOT a live LLM protocol and cannot attest to free-form narration truth.
No model-supplied code, equations, or arbitrary numerical values are evaluated.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
import math
import re
from types import SimpleNamespace
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from learnflow_v2.scenegraph.enums import LayoutIntent
from learnflow_v2.scenegraph.schema import SceneGraph
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.model_authored_attention import exact_example
from learnflow_v3.visual_quality_system import BG, BODY, MUTED, ACCENT, PROCESS_COLOR

VERSION="v3-51-creative-graph-ir-v1"
ORIGIN="OFFLINE_HOST_STORYBOARD_NOT_MODEL"
CLAIMS=("A1","A2","A3","A4")
SAFE_IDS=re.compile(r"^[a-z][a-z0-9_]{1,29}$")
NUMBER=re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?")
LETTERS=re.compile(r"^[A-Za-z][A-Za-z \-,:?]{1,48}$")
REGION={
 "TOP_LEFT":(-4.15,1.6),"TOP":(0,1.6),"TOP_RIGHT":(4.15,1.6),
 "LEFT":(-4.15,0),"CENTER":(0,0),"RIGHT":(4.15,0),
 "BOTTOM_LEFT":(-4.15,-1.6),"BOTTOM":(0,-1.6),
 "BOTTOM_RIGHT":(4.15,-1.6)}
TONE={"primary":PROCESS_COLOR,"secondary":MUTED,"accent":ACCENT}
RELATIONS=frozenset({"FLOW","COMPARES_WITH","DEPENDS_ON","TRANSFORMS_INTO","EQUIVALENT_TO"})
OPERATIONS=("reveal","emphasize","connect","hide","move","replace")


def digest(value)->str:
    return sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()


def ledger()->dict:
    """The *only* source of numeric labels; independently computed from V3-50."""
    e=exact_example()
    a,b=e["weights"];sa,sb=e["scores"];ca,cb=e["context"]
    facts={
     "q":("Q = [1, 0]","A1",None),
     "key_a":("K_A = [1, 0]","A1",None),
     "key_b":("K_B = [0, 1]","A1",None),
     "value_a":("V_A = [1, 0]","A1",None),
     "value_b":("V_B = [0, 1]","A1",None),
     "score_a":(f"s_A = {sa:.3f}","A2",sa),
     "score_b":(f"s_B = {sb:.3f}","A2",sb),
     "weight_a":(f"w_A = {a:.3f}","A3",a),
     "weight_b":(f"w_B = {b:.3f}","A3",b),
     "context":(f"context = [{ca:.3f}, {cb:.3f}]","A4",None),
     "formula":("softmax(Q K^T / sqrt(d_k)) V","A4",None)}
    allowed={
     ("q","key_a","COMPARES_WITH"),
     ("q","key_b","COMPARES_WITH"),
     ("key_a","score_a","FLOW"),
     ("key_b","score_b","FLOW"),
     ("score_a","weight_a","TRANSFORMS_INTO"),
     ("score_b","weight_b","TRANSFORMS_INTO"),
     ("weight_a","context","FLOW"),
     ("weight_b","context","FLOW"),
     ("value_a","context","FLOW"),
     ("value_b","context","FLOW"),
     ("formula","context","DEPENDS_ON")}
    return {
     "version":"v3-51-host-verified-attention-ledger-v1",
     "facts":{k:{"text":t,"claim":c,"bar_value":v} for k,(t,c,v) in facts.items()},
     "allowed_edges":sorted([list(row) for row in allowed]),
     "source_math":"scaled_dot_product_attention",
     "host_calculated":True,"model_code":False,
     "claims":list(CLAIMS)}


class Node(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    id:str=Field(min_length=2,max_length=30,pattern=r"^[a-z][a-z0-9_]*$")
    kind:Literal["TEXT","SHAPE","MATH","EQUATION","CHART"]
    fact_ref:str|None=None
    label:str|None=None
    region:Literal["TOP_LEFT","TOP","TOP_RIGHT","LEFT","CENTER","RIGHT",
                   "BOTTOM_LEFT","BOTTOM","BOTTOM_RIGHT"]="CENTER"
    tone:Literal["primary","secondary","accent"]="primary"

    @model_validator(mode="after")
    def no_assertion_laundering(self):
        if (self.fact_ref is None)==(self.label is None):
            raise ValueError("V351_NODE_MUST_HAVE_EXACTLY_ONE_LABEL_SOURCE")
        if self.label is not None and not LETTERS.fullmatch(self.label):
            raise ValueError("V351_FREE_LABEL_MAY_NOT_ASSERT_MATH_OR_DIGITS")
        return self


class Relation(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    id:str=Field(pattern=r"^[a-z][a-z0-9_]*$",max_length=30)
    source:str
    target:str
    kind:Literal["FLOW","COMPARES_WITH","DEPENDS_ON","TRANSFORMS_INTO","EQUIVALENT_TO"]


class Scene(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    id:str=Field(min_length=2,max_length=30,pattern=r"^[a-z][a-z0-9_]*$")
    title:str=Field(min_length=4,max_length=48)
    layout:Literal["PROCESS","COMPARISON","FREEFORM","GRID"]
    nodes:list[Node]=Field(min_length=2,max_length=8)
    relations:list[Relation]=Field(default_factory=list,max_length=10)


class Action(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    kind:Literal["reveal","emphasize","connect","hide","move","replace"]
    target:str
    source:str|None=None
    destination:Literal["TOP_LEFT","TOP","TOP_RIGHT","LEFT","CENTER","RIGHT",
                         "BOTTOM_LEFT","BOTTOM","BOTTOM_RIGHT"]|None=None


class Beat(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    scene_id:str
    claims:list[Literal["A1","A2","A3","A4"]]=Field(min_length=1,max_length=4)
    narration:str=Field(min_length=45,max_length=430)
    actions:list[Action]=Field(min_length=1,max_length=5)

    @model_validator(mode="after")
    def bounded_narration(self):
        if len(self.narration.split()) not in range(8,77):
            raise ValueError("V351_NARRATION_BUDGET")
        if any(ord(c)<32 for c in self.narration):
            raise ValueError("V351_CONTROL_CHARACTER")
        return self


class Storyboard(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    version:Literal["v3-51-creative-graph-ir-v1"]
    origin:Literal["OFFLINE_HOST_STORYBOARD_NOT_MODEL"]
    evidence_sha256:str=Field(pattern=r"^[a-f0-9]{64}$")
    title:str=Field(min_length=6,max_length=60)
    scenes:list[Scene]=Field(min_length=2,max_length=5)
    beats:list[Beat]=Field(min_length=3,max_length=7)


def _label(node:Node,evidence:dict)->str:
    return (evidence["facts"][node.fact_ref]["text"]
            if node.fact_ref is not None else node.label)


def positions(s:Scene)->dict[str,tuple[float,float]]:
    """Deterministic host-owned placement. Region preference is an *intent*."""
    if s.layout=="PROCESS" and len(s.nodes)<=4:
        n=len(s.nodes);coords=[
            (-4.4+8.8*(i/max(1,n-1)),0.) for i in range(n)]
        # PROCESS row uses model ordering, not frozen topic positions.
        return {node.id:coords[i] for i,node in enumerate(s.nodes)}
    if s.layout=="COMPARISON":
        n=len(s.nodes)
        rows=math.ceil(n/2)
        coords=[(-3.05 if i%2==0 else 3.05,
                 (rows-1)*.80-1.60*(i//2)) for i in range(n)]
        return {node.id:coords[i] for i,node in enumerate(s.nodes)}
    if s.layout=="GRID":
        cols=3 if len(s.nodes)>4 else 2
        rows=math.ceil(len(s.nodes)/cols)
        coords=[((i%cols-(cols-1)/2)*4.1,
                 (rows-1)/2*1.65-(i//cols)*1.65) for i in range(len(s.nodes))]
        return {node.id:coords[i] for i,node in enumerate(s.nodes)}
    unused=list(REGION.values());placed={}
    for n in s.nodes:
        ideal=REGION[n.region]
        idx=min(range(len(unused)),
           key=lambda k:((unused[k][0]-ideal[0])**2+
                         (unused[k][1]-ideal[1])**2,k))
        placed[n.id]=unused.pop(idx)
    return placed


def validate(raw:dict)->tuple[Storyboard,dict,list[SceneGraph],dict]:
    try:
        story=Storyboard.model_validate(raw)
    except Exception:
        raise Blocked("V351_STRUCTURE_INVALID") from None
    evidence=ledger()
    if story.evidence_sha256!=digest(evidence):
        raise Blocked("V351_FACT_LEDGER_SHA_MISMATCH")
    if len({s.id for s in story.scenes})!=len(story.scenes):
        raise Blocked("V351_DUPLICATE_SCENE")
    graph_by_id={};plan={};v2graphs=[]
    for s in story.scenes:
        if not LETTERS.fullmatch(s.title):
            raise Blocked("V351_TITLE_MUST_NOT_ASSERT_UNVERIFIED_MATH")
        if len({n.id for n in s.nodes})!=len(s.nodes):
            raise Blocked("V351_DUPLICATE_NODE")
        if len({r.id for r in s.relations})!=len(s.relations):
            raise Blocked("V351_DUPLICATE_RELATION")
        node_by_id={n.id:n for n in s.nodes}
        for n in s.nodes:
            if n.fact_ref is not None and n.fact_ref not in evidence["facts"]:
                raise Blocked("V351_UNBOUND_FACT")
            if n.kind=="CHART" and (n.fact_ref is None or
                evidence["facts"][n.fact_ref]["bar_value"] is None or
                not 0<=evidence["facts"][n.fact_ref]["bar_value"]<=1):
                raise Blocked("V351_CHART_REQUIRES_HOST_VALUE_0_TO_1")
        for r in s.relations:
            if r.source not in node_by_id or r.target not in node_by_id:
                raise Blocked("V351_RELATION_REF_MISSING")
            left,right=node_by_id[r.source],node_by_id[r.target]
            if left.fact_ref is None or right.fact_ref is None:
                raise Blocked("V351_UNGROUNDED_RELATION")
            if [left.fact_ref,right.fact_ref,r.kind] not in evidence["allowed_edges"]:
                raise Blocked("V351_RELATION_CLAIM_NOT_SUPPORTED")
        # Delegate reference/topology/type validation to *existing* V2 SceneGraph.
        obj={
          "scene_id":s.id,"concept":"Host verified scaled dot-product attention",
          "purpose":"DEMONSTRATE","layout_intent":{"type":s.layout},
          "nodes":[{"id":n.id,"kind":n.kind,"label":_label(n,evidence),
                    "semantic_role":n.fact_ref or "NONFACTUAL_VISUAL_LABEL",
                    "layout_hint":{"preferred_region":n.region}} for n in s.nodes],
          "relations":[r.model_dump() for r in s.relations]}
        try:
            g=SceneGraph.model_validate(obj)
        except Exception:
            raise Blocked("V351_EXISTING_V2_SCENEGRAPH_REJECTED") from None
        v2graphs.append(g);graph_by_id[s.id]=s
        co=positions(s)
        # Fail closed if placements are too close, not silently overlap.
        for i,(name,p) in enumerate(co.items()):
            for other,q in list(co.items())[i+1:]:
                if abs(p[0]-q[0])<2.9 and abs(p[1]-q[1])<1.50:
                    raise Blocked("V351_LAYOUT_COLLISION")
        plan[s.id]=co
    if len({b.scene_id for b in story.beats})<2:
        raise Blocked("V351_REQUIRES_MORE_THAN_ONE_SCENE")
    order=[s.id for s in story.scenes]
    visited=[];shown={s.id:set() for s in story.scenes};edges={s.id:set() for s in story.scenes}
    seen_claims=set();action_counts=Counter()
    moving_positions={name:dict(positions_) for name,positions_ in plan.items()}
    allowed_numbers={"0","1","2","0.707","0.670","0.330","0.67","0.33"}
    for b in story.beats:
        if b.scene_id not in graph_by_id:
            raise Blocked("V351_BEAT_UNKNOWN_SCENE")
        if b.scene_id not in visited: visited.append(b.scene_id)
        if visited.index(b.scene_id)<len(visited)-1:
            raise Blocked("V351_CANNOT_REVISIT_DISMISSED_SCENE")
        s=graph_by_id[b.scene_id];nodes={n.id:n for n in s.nodes}
        relations={r.id:r for r in s.relations}
        if any(x not in allowed_numbers for x in NUMBER.findall(b.narration)):
            raise Blocked("V351_UNSUPPORTED_NARRATION_NUMERIC_FACT")
        seen_claims.update(b.claims)
        for a in b.actions:
            action_counts[a.kind]+=1
            valid=relations if a.kind=="connect" else nodes
            if a.target not in valid:
                raise Blocked("V351_ACTION_UNKNOWN_TARGET")
            if a.kind=="reveal":
                if a.target in shown[s.id]:
                    raise Blocked("V351_ALREADY_REVEALED")
                shown[s.id].add(a.target)
            elif a.kind=="connect":
                rel=relations[a.target]
                if (rel.source not in shown[s.id] or
                    rel.target not in shown[s.id] or a.target in edges[s.id]):
                    raise Blocked("V351_CONNECT_BEFORE_ENDPOINTS_OR_DUPLICATE")
                edges[s.id].add(a.target)
            elif a.kind=="replace":
                if a.source not in nodes or a.source not in shown[s.id] or a.target in shown[s.id]:
                    raise Blocked("V351_INVALID_REPLACE")
                if nodes[a.source].fact_ref is None or nodes[a.source].fact_ref!=nodes[a.target].fact_ref:
                    raise Blocked("V351_REPLACE_BREAKS_SEMANTIC_IDENTITY")
                shown[s.id].remove(a.source);shown[s.id].add(a.target)
            else:
                if a.target not in shown[s.id]:
                    raise Blocked("V351_ACTION_BEFORE_SHOW")
                if a.kind=="hide":shown[s.id].remove(a.target)
                if a.kind=="move":
                    if not a.destination:
                        raise Blocked("V351_MOVE_MISSING_DESTINATION")
                    dest=REGION[a.destination]
                    for other in shown[s.id]-{a.target}:
                        pt=moving_positions[s.id][other]
                        if abs(pt[0]-dest[0])<2.9 and abs(pt[1]-dest[1])<1.50:
                            raise Blocked("V351_MOVE_COLLIDES")
                    moving_positions[s.id][a.target]=dest
            if a.kind!="move" and a.destination is not None:
                raise Blocked("V351_UNEXPECTED_DESTINATION")
            if a.kind!="replace" and a.source is not None:
                raise Blocked("V351_UNEXPECTED_SOURCE")
        # Each declared claim must actually be present as a visible evidence label
        # rather than merely checked by keyword in model-written narration.
        active_claims={
          evidence["facts"][nodes[n].fact_ref]["claim"]
          for n in shown[s.id] if nodes[n].fact_ref is not None}
        if not set(b.claims).intersection(active_claims):
            raise Blocked("V351_BEAT_WITH_NO_VISUAL_FACT_EVIDENCE")
    if visited!=order or seen_claims!=set(CLAIMS):
        raise Blocked("V351_MISSING_SCENES_OR_CLAIM_COVERAGE")
    if action_counts["reveal"]<6 or (action_counts["connect"]+action_counts["replace"]+
                                    action_counts["move"]<1):
        raise Blocked("V351_DECORATIVE_STATIC_STORYBOARD")
    return story,evidence,v2graphs,plan


def audio_proxy(story:Storyboard):
    return SimpleNamespace(beats=[SimpleNamespace(narration=b.narration,
        claim_ids=b.claims) for b in story.beats])


def manim(story:Storyboard,evidence:dict,graphs:list[SceneGraph],layout:dict,
          seconds:list[float])->str:
    if len(seconds)!=len(story.beats) or any(not 3<=d<=24 for d in seconds):
        raise Blocked("V351_TIMING_INVALID")
    lines=[
      "# V3-51 GENERIC HOST COMPILED SOURCE NEVER MODEL PYTHON",
      "from manim import *","class GeneratedLesson(Scene):",
      "    def construct(self):",
      f"        self.camera.background_color={BG!r}",
      f"        brand=Text('LEARNFLOW  /  VISUAL THINKING',font='CMU Serif',font_size=15,color={MUTED!r}).to_edge(UP,buff=.17)",
      f"        top=Text({story.title!r},font='CMU Serif',font_size=30,color={BODY!r}).move_to([0,2.76,0]).scale_to_fit_width(10.7)",
      "        self.add(brand,top)",
    ]
    objnames={};relname={};node_by_scene={}
    for index,s in enumerate(story.scenes):
        nodes={n.id:n for n in s.nodes};node_by_scene[s.id]=nodes
        for i,n in enumerate(s.nodes):
            name=f"v351_n{index}_{i}";objnames[(s.id,n.id)]=name
            x,y=layout[s.id][n.id]
            text=_label(n,evidence);color=TONE[n.tone]
            if n.kind=="CHART":
                val=evidence["facts"][n.fact_ref]["bar_value"]
                lines.append(
                   f"        {name}_shape=RoundedRectangle(width=.85,height={max(.24,1.75*val):.4f},"
                   f"corner_radius=.08,stroke_color={color!r},fill_color={color!r},"
                   f"fill_opacity=.65).move_to([{x:.3f},{y+.15:.3f},0])")
                lines.append(
                   f"        {name}_caption=Text({text!r},font='CMU Serif',font_size=22,"
                   f"color={BODY!r}).move_to([{x:.3f},{y-.82:.3f},0]).scale_to_fit_width(2.7)")
                lines.append(f"        {name}=VGroup({name}_shape,{name}_caption)")
            else:
                lines.append(
                   f"        {name}_label=Text({text!r},font='CMU Serif',"
                   f"font_size={24 if n.kind in ('MATH','EQUATION') else 26},"
                   f"color={color!r}).scale_to_fit_width(2.75).move_to([{x:.3f},{y:.3f},0])")
                if n.kind=="SHAPE":
                    lines.append(
                      f"        {name}_shape=RoundedRectangle(width=3.0,height=1.12,"
                      f"corner_radius=.16,stroke_color={color!r},stroke_width=1.7,"
                      f"fill_color='#13212D',fill_opacity=.60).move_to([{x:.3f},{y:.3f},0])")
                    lines.append(f"        {name}=VGroup({name}_shape,{name}_label)")
                else:lines.append(f"        {name}=VGroup({name}_label)")
        for i,r in enumerate(s.relations):
            name=f"v351_e{index}_{i}";relname[(s.id,r.id)]=name
            left,right=objnames[(s.id,r.source)],objnames[(s.id,r.target)]
            lines.append(
              f"        {name}=Arrow({left}.get_center(),{right}.get_center(),"
              f"buff=.70,stroke_width=3,tip_length=.12,color={ACCENT!r}).set_z_index(-2)")
    current=None;visible=[];start=0
    for i,b in enumerate(story.beats):
        if b.scene_id!=current:
            if visible:
                lines.append("        self.play(FadeOut("+",".join(visible)+"),run_time=.35)")
            visible=[];current=b.scene_id
        actions=b.actions;period=seconds[i]
        each=min(.80,max(.23,(period-1.0)/len(actions)))
        spent=.35 if i and story.beats[i-1].scene_id!=b.scene_id else 0
        for a in actions:
            name=(relname if a.kind=="connect" else objnames)[(b.scene_id,a.target)]
            if a.kind=="reveal":
                lines.append(f"        self.play(FadeIn({name}),run_time={each:.3f})")
                visible.append(name)
            elif a.kind=="connect":
                lines.append(f"        self.play(Create({name}),run_time={each:.3f})")
                visible.append(name)
            elif a.kind=="emphasize":
                lines.append(f"        self.play(Indicate({name},color={ACCENT!r},scale_factor=1.07),run_time={each:.3f})")
            elif a.kind=="hide":
                lines.append(f"        self.play(FadeOut({name}),run_time={each:.3f})")
                visible.remove(name)
            elif a.kind=="move":
                x,y=REGION[a.destination]
                lines.append(f"        self.play({name}.animate.move_to([{x:.3f},{y:.3f},0]),run_time={each:.3f})")
            elif a.kind=="replace":
                src=objnames[(b.scene_id,a.source)]
                lines.append(f"        self.play(ReplacementTransform({src},{name}),run_time={each:.3f})")
                visible.remove(src);visible.append(name)
            spent+=each
        if period-spent<.05:
            raise Blocked("V351_BEAT_VISUAL_EVENTS_EXCEED_SPEECH")
        lines.append(f"        self.wait({period-spent:.4f}) # BEAT_{i+1} claims={','.join(b.claims)}")
        start+=period
    lines.append("        self.wait(.4)")
    code="\n".join(lines)+"\n"
    if any(q in code for q in ("__import__","exec(","eval(","subprocess","import os")):
        raise Blocked("V351_UNSAFE_GENERATED_SOURCE")
    compile(code,"<v351-host-compiled-scenes>","exec")
    return code
