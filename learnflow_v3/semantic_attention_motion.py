"""V3-52: exact-evidence semantic motion, not decorative static transitions.

Finite HOST compiler creates weighted softmax bars, transports value identities,
and composes the actual arithmetic context. No provider code is ever executed.
Reuses V3-51 data provenance, existing V2 SceneGraph contract and AV pipeline.
"""
from __future__ import annotations
import math
from types import SimpleNamespace
from typing import Literal

from pydantic import BaseModel,ConfigDict,Field,model_validator

from learnflow_v2.scenegraph.schema import SceneGraph
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_scene_graph import digest
from learnflow_v3.visual_quality_system import BG,BODY,ACCENT,PROCESS_COLOR,MUTED,HAIRLINE

VERSION="v3-52-attention-semantic-motion-v1"
ORIGIN="HOST_SYNTHETIC_ATTENTION_MOTION_NOT_MODEL"
OP_SEQUENCE=("dot_score_compare","softmax_weight_morph",
             "value_weight_transport","context_compose")
CLAIM_SEQUENCE=("A2","A3","A4","A4")
QUERIES={"query_matches_token_a":(1,0),
         "heldout_query_matches_token_b":(0,1)}


class Case(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True,frozen=True)
    topic_id:Literal["query_matches_token_a","heldout_query_matches_token_b"]
    query:tuple[int,int]
    keys:tuple[tuple[int,int],tuple[int,int]]
    values:tuple[tuple[int,int],tuple[int,int]]
    dim:int=Field(ge=2,le=2)

    @model_validator(mode="after")
    def bound(self):
        if (self.query!=QUERIES[self.topic_id] or
            self.keys!=((1,0),(0,1)) or self.values!=((1,0),(0,1)) or self.dim!=2):
            raise ValueError("V352_PREREGISTERED_QKV_SUPPORT_ONLY")
        return self


class Step(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True,frozen=True)
    kind:Literal["dot_score_compare","softmax_weight_morph",
                 "value_weight_transport","context_compose"]
    claim_id:Literal["A2","A3","A4"]
    subject_id:Literal["query","scores","values","context"]
    beat:int=Field(ge=0,le=3)
    fact_sha256:str=Field(min_length=64,max_length=64,pattern=r"^[0-9a-f]{64}$")


class MotionPlan(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True,frozen=True)
    version:Literal["v3-52-attention-semantic-motion-v1"]
    origin:Literal["HOST_SYNTHETIC_ATTENTION_MOTION_NOT_MODEL"]
    case:Case
    evidence_sha256:str=Field(min_length=64,max_length=64,pattern=r"^[0-9a-f]{64}$")
    steps:tuple[Step,Step,Step,Step]


def facts(case:Case)->dict:
    q=case.query;k=case.keys;v=case.values
    scores=[sum(float(a*b) for a,b in zip(q,key))/math.sqrt(case.dim) for key in k]
    mx=max(scores);u=[math.exp(x-mx) for x in scores];z=sum(u)
    w=[t/z for t in u]
    ctx=[sum(w[i]*v[i][j] for i in range(2)) for j in range(2)]
    if not (abs(sum(w)-1)<1e-12 and all(0<x<1 for x in w) and
            all(abs(ctx[i]-w[i])<1e-12 for i in range(2))):
        raise Blocked("V352_MATH_IDENTITY_NOT_CERTIFIED")
    return {"q":list(q),"keys":[list(x) for x in k],
       "values":[list(x) for x in v],"dk":case.dim,
       "scaled_scores":scores,"weights":w,"context":ctx,
       "proof_kind":"exact_scaled_dot_product_softmax_weighted_sum",
       "source":"HOST_EXACT_NUMERIC_ARITHMETIC_FROM_PREREG_QKV"}


def ground(case:Case)->MotionPlan:
    if not isinstance(case,Case):raise Blocked("V352_CASE_TYPE_REQUIRED")
    ev=facts(case);h=digest(ev)
    roles=("query","scores","values","context")
    steps=tuple(Step(kind=k,claim_id=CLAIM_SEQUENCE[i],
                     subject_id=roles[i],beat=i,fact_sha256=h)
                for i,k in enumerate(OP_SEQUENCE))
    return MotionPlan(version=VERSION,origin=ORIGIN,case=case,
                      evidence_sha256=h,steps=steps)


def check(plan:MotionPlan)->tuple[dict,SceneGraph]:
    if not isinstance(plan,MotionPlan):raise Blocked("V352_TYPED_PLAN_REQUIRED")
    try:
        verified=Case.model_validate(plan.case.model_dump())
    except Exception:
        raise Blocked("V352_QKV_CHANGED") from None
    expected=ground(verified)
    if plan.model_dump()!=expected.model_dump():
        raise Blocked("V352_TAMPERED_MOTION_OR_WRONG_CLAIM")
    ev=facts(verified)
    # Actual existing V2 semantic identity and edge contract.
    data={
      "scene_id":"attention_causal_motion",
      "purpose":"DEMONSTRATE",
      "concept":"One query, two key-value vectors, verified weighted context",
      "layout_intent":{"type":"PROCESS"},
      "nodes":[{"id":n,"kind":"MATH" if n in
         ("query","score_a","score_b","weight_a","weight_b","context") else "SHAPE",
         "label":n.replace("_"," ").title(),
         "semantic_role":n} for n in (
           "query","key_a","key_b","score_a","score_b",
           "weight_a","weight_b","value_a","value_b","context")],
      "relations":[
         {"id":"compare_a","source":"query","target":"key_a","kind":"COMPARES_WITH"},
         {"id":"compare_b","source":"query","target":"key_b","kind":"COMPARES_WITH"},
         {"id":"scale_a","source":"score_a","target":"weight_a","kind":"TRANSFORMS_INTO"},
         {"id":"scale_b","source":"score_b","target":"weight_b","kind":"TRANSFORMS_INTO"},
         {"id":"mix_a","source":"value_a","target":"context","kind":"FLOW"},
         {"id":"mix_b","source":"value_b","target":"context","kind":"FLOW"}]
    }
    try:
        graph=SceneGraph.model_validate(data)
    except Exception:
        raise Blocked("V352_V2_SCENEGRAPH_REJECTED") from None
    return ev,graph


def narration(plan:MotionPlan):
    ev,_=check(plan)
    q=plan.case.query
    qname="first" if q==(1,0) else "second"
    a,b=ev["weights"];out=ev["context"]
    lines=[
     ("Two key tokens are available. Our one query matches the "+qname+
      " key more strongly. Watch the dot-product compatibility scores form before they are scaled by the square root of the key dimension."),
     ("The scaled scores enter softmax and become two attention weights. "+
      "Each weight is between zero and one, and their sum is exactly one. "+
      "Their relative sizes now appear as different bar lengths."),
     ("Now watch the value vectors remain identifiable as their contributions "+
      "travel toward the output. The weights control how much of each colored "+
      "value contributes. This movement is the causal explanation, not a decorative transition."),
     ("The two weighted contributions combine into a single context vector. "+
      "Because our illustrative values are basis vectors, the context coordinates "+
      "are the attention weights. The larger contribution comes from the "+qname+" token.")
    ]
    if not (all(16<len(t.split())<75 for t in lines) and
            abs(sum((a,b))-1)<1e-12 and sum(out)>0.999):
        raise Blocked("V352_NARRATION_FACT_OR_LENGTH_INVALID")
    return SimpleNamespace(beats=[SimpleNamespace(narration=t,
             claim_ids=[("A1","A2")[i==0] if False else CLAIM_SEQUENCE[i]])
             for i,t in enumerate(lines)])


def compile_manim(plan:MotionPlan,seconds:list[float])->str:
    ev,graph=check(plan)
    if len(seconds)!=4 or any(not 5.0<=t<=22 for t in seconds):
        raise Blocked("V352_SPEECH_DURATION_UNSUPPORTED")
    a,b=ev["weights"]; sa,sb=ev["scaled_scores"];x,y=ev["context"]
    q=ev["q"]
    def text_line(name,value,xpos,ypos,fs=25,color=BODY):
        return (f"        {name}=Text({value!r},font='CMU Serif',font_size={fs},"
                f"color={color!r}).move_to([{xpos:.3f},{ypos:.3f},0])")
    # A single compiler; only arithmetic from a certified plan changes.
    lines=[
      "# V352 HOST_COMPILED_SEMANTIC_MOTION_NO_PROVIDER_PYTHON",
      "from manim import *",
      "class GeneratedLesson(Scene):",
      "    def construct(self):",
      f"        self.camera.background_color={BG!r}",
      text_line("brand","LEARNFLOW   /   ATTENTION, MADE VISIBLE",-4.52,3.57,16,MUTED),
      text_line("heading","How weighted values build a context",0,3.02,35,BODY),
      f"        rule=Line([-6.1,2.62,0],[6.1,2.62,0],color={HAIRLINE!r},stroke_width=1.2)",
      "        self.add(brand,heading,rule)",
      text_line("beat_label","MATCH",5.35,3.55,16,ACCENT),
      "        self.add(beat_label)",
      text_line("q_label",f"Q = [{q[0]}, {q[1]}]",-4.8,1.10,28,ACCENT),
      text_line("key_a","KEY A  [1, 0]",-.9,1.55,27,PROCESS_COLOR),
      text_line("key_b","KEY B  [0, 1]",3.55,1.55,27,ACCENT),
      f"        qbox=RoundedRectangle(width=2.4,height=1.15,corner_radius=.2,stroke_color={ACCENT!r},fill_color='#203039',fill_opacity=.56).move_to([-4.8,1.1,0])",
      f"        ka_box=RoundedRectangle(width=3.2,height=1.15,corner_radius=.2,stroke_color={PROCESS_COLOR!r},fill_color='#142C34',fill_opacity=.56).move_to([-.9,1.55,0])",
      f"        kb_box=RoundedRectangle(width=3.2,height=1.15,corner_radius=.2,stroke_color={ACCENT!r},fill_color='#2B251B',fill_opacity=.52).move_to([3.55,1.55,0])",
      "        q_group=VGroup(qbox,q_label)",
      "        k_a_group=VGroup(ka_box,key_a)",
      "        k_b_group=VGroup(kb_box,key_b)",
      f"        arrow_a=Arrow([-3.5,1.12,0],[-2.65,1.52,0],buff=0,stroke_width=4,color={PROCESS_COLOR!r}).set_z_index(-2)",
      f"        arrow_b=Arrow([-3.6,.67,0],[1.80,.75,0],buff=0,stroke_width=4,color={ACCENT!r}).set_z_index(-2)",
      text_line("score_a",f"scaled score A = {sa:.3f}",-2.75,-.23,26,PROCESS_COLOR),
      text_line("score_b",f"scaled score B = {sb:.3f}",2.60,-.23,26,ACCENT),
      text_line("score_rule","Q  dot  K     /     sqrt(d_k)",0,-1.26,25,BODY),
      f"        bar_a=Rectangle(width={max(.12,4*a):.5f},height=.55,"
        f"stroke_color={PROCESS_COLOR!r},fill_color={PROCESS_COLOR!r},fill_opacity=.88).move_to([-2.20,.03,0])",
      f"        bar_b=Rectangle(width={max(.12,4*b):.5f},height=.55,"
        f"stroke_color={ACCENT!r},fill_color={ACCENT!r},fill_opacity=.88).move_to([2.20,.03,0])",
      text_line("softmax_title","softmax  →  normalized attention weights",0,1.53,29,BODY),
      text_line("weight_a",f"weight A = {a:.3f}",-2.20,-.79,27,PROCESS_COLOR),
      text_line("weight_b",f"weight B = {b:.3f}",2.20,-.79,27,ACCENT),
      text_line("unit_label","The weights sum to one",0,-1.55,23,MUTED),
      text_line("value_a","V_A = [1, 0]",-3.35,1.36,29,PROCESS_COLOR),
      text_line("value_b","V_B = [0, 1]",3.35,1.36,29,ACCENT),
      text_line("mix_title","Each value travels with its own weight",0,2.05,28,BODY),
      # Host-derived context segments, exact arithmetic pixel widths.
      f"        seg_a=Rectangle(width={5*a:.6f},height=.57,"
        f"stroke_color={PROCESS_COLOR!r},fill_color={PROCESS_COLOR!r},fill_opacity=.94)"
        f".move_to([{(-2.5+2.5*a):.6f},-2.16,0])",
      f"        seg_b=Rectangle(width={5*b:.6f},height=.57,"
        f"stroke_color={ACCENT!r},fill_color={ACCENT!r},fill_opacity=.94)"
        f".move_to([{(2.5-2.5*b):.6f},-2.16,0])",
      "        combined=VGroup(seg_a,seg_b)",
      text_line("contribution_a",f"{a:.3f} × [1, 0]",-3.0,-.35,25,PROCESS_COLOR),
      text_line("contribution_b",f"{b:.3f} × [0, 1]",3.0,-.35,25,ACCENT),
      text_line("context",f"context = [{x:.3f}, {y:.3f}]",0,-2.99,33,BODY),
      text_line("conclusion","Normalized weights shape the information we keep",0,-1.18,23,MUTED),
      # Optional effect controls never change numeric truth.
      f"        rail=RoundedRectangle(width=5.22,height=.78,corner_radius=.12,"
       f"stroke_color={HAIRLINE!r},stroke_width=1.5).move_to([0,-2.16,0])",
    ]
    # Every beat consumed for exactly its narrated duration; create at least
    # .2 seconds extra native footage then trim by physical WAV frame budget.
    def phase(n,contents,times):
        spent=sum(t for _,t in times)
        if seconds[n]-spent<.3:
            raise Blocked("V352_SPEECH_BEAT_SHORTER_THAN_CAUSAL_MOTION")
        lines.append(f"        # V352_SEMANTIC_BEAT_{n} {OP_SEQUENCE[n]} from host verified evidence")
        for action,sec in times:
            lines.append(f"        self.play({action},run_time={sec:.3f})")
        lines.append(f"        self.wait({seconds[n]-spent:.5f})")
    phase(0,None,[
      ("FadeIn(q_group),FadeIn(k_a_group),FadeIn(k_b_group)",1.25),
      ("Create(arrow_a),Create(arrow_b)",1.3),
      ("FadeIn(score_a),FadeIn(score_b),FadeIn(score_rule)",1.0),
      ("Indicate(score_a,color=YELLOW),Indicate(score_b,color=YELLOW)",.75)
    ])
    phase(1,None,[
      ("FadeOut(q_group),FadeOut(k_a_group),FadeOut(k_b_group),FadeOut(arrow_a),FadeOut(arrow_b),FadeOut(score_rule)",.85),
      ("Transform(beat_label,Text('NORMALIZE',font='CMU Serif',font_size=16,color="+repr(ACCENT)+").move_to([5.35,3.55,0]))",.40),
      ("TransformFromCopy(score_a,bar_a),TransformFromCopy(score_b,bar_b),FadeIn(softmax_title)",1.8),
      ("FadeIn(weight_a),FadeIn(weight_b),FadeIn(unit_label)",.8)
    ])
    phase(2,None,[
      ("FadeOut(score_a),FadeOut(score_b),FadeOut(softmax_title),FadeOut(unit_label)",.7),
      ("Transform(beat_label,Text('TRANSPORT',font='CMU Serif',font_size=16,color="+repr(ACCENT)+").move_to([5.35,3.55,0]))",.4),
      ("FadeIn(mix_title),FadeIn(value_a),FadeIn(value_b),FadeIn(contribution_a),FadeIn(contribution_b),FadeIn(rail)",1.05),
      ("TransformFromCopy(bar_a,seg_a),TransformFromCopy(bar_b,seg_b)",1.9),
      ("Indicate(value_a,color=TEAL),Indicate(value_b,color=YELLOW)",.65)
    ])
    phase(3,None,[
      ("Transform(beat_label,Text('COMPOSE',font='CMU Serif',font_size=16,color="+repr(ACCENT)+").move_to([5.35,3.55,0]))",.4),
      ("FadeOut(value_a),FadeOut(value_b),FadeOut(bar_a),FadeOut(bar_b),FadeOut(weight_a),FadeOut(weight_b),FadeOut(mix_title),FadeOut(contribution_a),FadeOut(contribution_b)",.75),
      ("Indicate(seg_a,color=TEAL),Indicate(seg_b,color=YELLOW)",1.0),
      ("FadeIn(context),FadeIn(conclusion)",.85)
    ])
    lines.append("        self.wait(.6)")
    src="\n".join(lines)+"\n"
    if any(x in src for x in ("__import__","exec(","eval(","subprocess","import os")):
        raise Blocked("V352_UNSAFE_HOST_COMPILER")
    compile(src,"<v352 trusted semantic motion compiler>","exec")
    return src
