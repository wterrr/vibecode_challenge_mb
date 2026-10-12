"""V3-53: finite compositional semantic director; host truth, author-chosen visuals.

No provider inference, arbitrary Manim source, unbounded symbols or model-authored
mathematical assertions. This *prospective* model-facing JSON protocol has not
been tested with a genuine LLM and is not a general-domain teaching grammar.
"""
from __future__ import annotations

from collections import Counter
from types import SimpleNamespace
from typing import Literal
import math

from pydantic import BaseModel,ConfigDict,Field,model_validator
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_scene_graph import digest
from learnflow_v3.semantic_attention_motion import Case,ground,check,facts
from learnflow_v3.visual_quality_system import BG,BODY,ACCENT,PROCESS_COLOR,MUTED,HAIRLINE

VERSION="v3-53-composable-grounded-creative-director-v1"
ORIGIN="HOST_SYNTHETIC_DIRECTOR_NOT_MODEL"
CAUSAL=("compare","normalize","transport","compose")
OPTIONAL=("intro","inspect")
ALL_STAGES=CAUSAL+OPTIONAL
CLAIMS={"intro":"A1","compare":"A2","normalize":"A3",
        "inspect":"A3","transport":"A4","compose":"A4"}
FOCUS={
 "intro":("query","key_a","key_b"),
 "compare":("query","score_a","score_b"),
 "normalize":("score_a","score_b","weight_a","weight_b"),
 "inspect":("weight_a","weight_b","context"),
 "transport":("value_a","value_b","weight_a","weight_b"),
 "compose":("value_a","value_b","context")
}
VISUALS=("trace","compare","spotlight")
STYLE={
 "network":{"qx":-4.8,"ka":-.9,"kb":3.55,"header":"Information flow"},
 "weighted_bars":{"qx":-4.5,"ka":-.55,"kb":3.60,"header":"Compare, then combine"},
 "value_mixture":{"qx":-4.65,"ka":-1.10,"kb":3.40,"header":"Where the context comes from"}
}


class DirectedBeat(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True,frozen=True)
    op:Literal["intro","compare","normalize","inspect","transport","compose"]
    claim_id:Literal["A1","A2","A3","A4"]
    evidence_sha256:str=Field(pattern=r"^[a-f0-9]{64}$")
    focus_ref:Literal["query","key_a","key_b","score_a","score_b",
                      "weight_a","weight_b","value_a","value_b","context"]
    visual_mode:Literal["trace","compare","spotlight"]


class DirectorPlan(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True,frozen=True)
    version:Literal["v3-53-composable-grounded-creative-director-v1"]
    origin:Literal["HOST_SYNTHETIC_DIRECTOR_NOT_MODEL"]
    case:Case
    story_style:Literal["network","weighted_bars","value_mixture"]
    evidence_sha256:str=Field(pattern=r"^[a-f0-9]{64}$")
    beats:tuple[DirectedBeat,...]=Field(min_length=4,max_length=6)

    @model_validator(mode="after")
    def syntax_order(self):
        ops=[b.op for b in self.beats]
        if any(ops.count(k)!=1 for k in CAUSAL):
            raise ValueError("V353_REQUIRED_CAUSAL_STAGES_MISSING_OR_DUPLICATE")
        if any(ops.count(k)>1 for k in OPTIONAL):
            raise ValueError("V353_DUPLICATE_OPTIONAL_STAGE")
        indices={name:ops.index(name) for name in CAUSAL}
        if not all(indices[k]<indices[CAUSAL[i+1]] for i,k in enumerate(CAUSAL[:-1])):
            raise ValueError("V353_CAUSAL_STAGE_DEPENDENCY_ORDER")
        if "intro" in ops and ops.index("intro")>indices["compare"]:
            raise ValueError("V353_INTRO_MUST_PRECEDE_COMPARE")
        if "inspect" in ops and ops.index("inspect")<indices["normalize"]:
            raise ValueError("V353_INSPECTION_REQUIRES_WEIGHT_FACTS")
        return self


def validated(plan:DirectorPlan):
    if not isinstance(plan,DirectorPlan):
        raise Blocked("V353_DIRECTOR_TYPED_INPUT_REQUIRED")
    try:
        # model_copy bypasses Pydantic, so recheck all nested fields.
        p=DirectorPlan.model_validate(plan.model_dump())
    except Exception:
        raise Blocked("V353_DIRECTOR_SCHEMA_OR_CAUSAL_ORDER_REJECTED") from None
    original=ground(p.case)
    ev,graph=check(original)
    h=digest(ev)
    if h!=p.evidence_sha256:
        raise Blocked("V353_UNBOUND_QKV_LEDGER")
    ops=[b.op for b in p.beats]
    for i,b in enumerate(p.beats):
        if b.evidence_sha256!=h or b.claim_id!=CLAIMS[b.op]:
            raise Blocked("V353_CLAIM_OR_STAGE_EVIDENCE_FORGED")
        if b.focus_ref not in FOCUS[b.op]:
            raise Blocked("V353_UNGROUNDED_FOCUS_REFERENCE")
        if b.op=="inspect" and b.focus_ref=="context" and ops.index("compose")>i:
            raise Blocked("V353_CONTEXT_NOT_YET_COMPOSED")
    return p,ev,graph


def plan_for(case:Case,style:str,stages:list[str]):
    if style not in STYLE:raise Blocked("V353_UNKNOWN_STORY_STYLE")
    ev=facts(case);h=digest(ev)
    preferred={
      "intro":("query","trace"),
      "compare":("score_a","compare"),
      "normalize":("weight_a","spotlight"),
      "inspect":("weight_b","compare"),
      "transport":("value_a","trace"),
      "compose":("context","spotlight")}
    beats=tuple(DirectedBeat(op=op,claim_id=CLAIMS[op],
              evidence_sha256=h,focus_ref=preferred[op][0],
              visual_mode=preferred[op][1]) for op in stages)
    result=DirectorPlan(version=VERSION,origin=ORIGIN,case=case,
                        story_style=style,evidence_sha256=h,beats=beats)
    validated(result)
    return result


def narration(plan:DirectorPlan):
    p,ev,_=validated(plan)
    favored="first" if ev["weights"][0]>ev["weights"][1] else "second"
    words={
      "intro":"A query asks where useful information lives. Two key and value tokens are available, and every comparison here uses a small illustrative vector rather than a trained model prediction.",
      "compare":"First the query meets each key. Their dot products are divided by the square root of the key dimension to yield scaled compatibility scores. We will now use those scores to select proportions.",
      "normalize":"Softmax turns those scores into nonnegative weights that sum to one. Notice how the lengths of the colored bars express a stronger and a weaker match without changing the underlying values.",
      "inspect":"Compare the two normalized weights and their color identities. The longer segment points toward a greater contribution, but the other value remains part of the mixture rather than being discarded.",
      "transport":"Now follow both value vectors into the calculation. Each keeps its identity and color as its contribution flows into the context strip, with a length determined by its verified softmax weight.",
      "compose":"Finally the two weighted contributions form one context vector. With these illustrative basis vectors the result coordinates are exactly the normalized weights, and the "+favored+" token makes the larger contribution."}
    return SimpleNamespace(beats=[SimpleNamespace(
          narration=words[b.op],claim_ids=[b.claim_id]) for b in p.beats])


def compile_manim(plan:DirectorPlan,seconds:list[float]):
    p,ev,graph=validated(plan)
    if len(seconds)!=len(p.beats) or any(not 4.5<=x<=23 for x in seconds):
        raise Blocked("V353_PHYSICAL_NARRATION_DURATION_OUT_OF_SUPPORT")
    s=STYLE[p.story_style];w0,w1=ev["weights"];q=ev["q"]
    sa,sb=ev["scaled_scores"];ca,cb=ev["context"]
    def T(name,string,x,y,font=25,color=BODY):
        return (f"        {name}=Text({string!r},font='CMU Serif',font_size={font},color={color!r})"
                f".move_to([{x:.3f},{y:.3f},0])")
    lines=[
      "# V353 TRUSTED COMPOSABLE DIRECTOR NO MODEL PYTHON",
      "from manim import *",
      "class GeneratedLesson(Scene):",
      "    def construct(self):",
      f"        self.camera.background_color={BG!r}",
      T("brand","LEARNFLOW    /    SEMANTIC MOTION",-4.4,3.53,16,MUTED),
      T("main_title",s["header"],0,3.00,36,BODY),
      f"        divider=Line([-6.1,2.59,0],[6.1,2.59,0],color={HAIRLINE!r},stroke_width=1.3)",
      "        self.add(brand,main_title,divider)",
      T("query_text",f"Q = [{q[0]}, {q[1]}]",s["qx"],1.14,28,ACCENT),
      T("key_a_text","KEY A  [1, 0]",s["ka"],1.52,26,PROCESS_COLOR),
      T("key_b_text","KEY B  [0, 1]",s["kb"],1.52,26,ACCENT),
      f"        query_box=RoundedRectangle(width=2.55,height=1.15,corner_radius=.16,stroke_color={ACCENT!r}).move_to([{s['qx']},1.14,0])",
      f"        key_a_box=RoundedRectangle(width=3.15,height=1.15,corner_radius=.16,stroke_color={PROCESS_COLOR!r}).move_to([{s['ka']},1.52,0])",
      f"        key_b_box=RoundedRectangle(width=3.15,height=1.15,corner_radius=.16,stroke_color={ACCENT!r}).move_to([{s['kb']},1.52,0])",
      "        query_node=VGroup(query_box,query_text)",
      "        key_a_node=VGroup(key_a_box,key_a_text)",
      "        key_b_node=VGroup(key_b_box,key_b_text)",
      T("scaled_a",f"score A = {sa:.3f}",-2.7,-.36,27,PROCESS_COLOR),
      T("scaled_b",f"score B = {sb:.3f}",2.7,-.36,27,ACCENT),
      T("rule","dot product   /   sqrt(d_k)",0,-1.50,25,BODY),
      f"        bar_a=Rectangle(width={4*w0:.5f},height=.54,fill_color={PROCESS_COLOR!r},fill_opacity=.94,stroke_width=0).move_to([-2.2,.10,0])",
      f"        bar_b=Rectangle(width={4*w1:.5f},height=.54,fill_color={ACCENT!r},fill_opacity=.94,stroke_width=0).move_to([2.2,.10,0])",
      T("wa",f"weight A  {w0:.3f}",-2.2,-.79,27,PROCESS_COLOR),
      T("wb",f"weight B  {w1:.3f}",2.2,-.79,27,ACCENT),
      T("softmax_title","softmax makes comparable proportions",0,1.75,27,BODY),
      T("value_a","VALUE A   [1, 0]",-3.3,1.48,27,PROCESS_COLOR),
      T("value_b","VALUE B   [0, 1]",3.3,1.48,27,ACCENT),
      T("share_a",f"{w0:.3f} × [1, 0]",-3.0,-1.05,24,PROCESS_COLOR),
      T("share_b",f"{w1:.3f} × [0, 1]",3.0,-1.05,24,ACCENT),
      f"        segment_a=Rectangle(width={5*w0:.6f},height=.57,fill_color={PROCESS_COLOR!r},fill_opacity=.95,stroke_width=0).move_to([{(-2.5+2.5*w0):.6f},-2.16,0])",
      f"        segment_b=Rectangle(width={5*w1:.6f},height=.57,fill_color={ACCENT!r},fill_opacity=.95,stroke_width=0).move_to([{(2.5-2.5*w1):.6f},-2.16,0])",
      f"        context_rail=RoundedRectangle(width=5.2,height=.78,corner_radius=.12,stroke_color={HAIRLINE!r},stroke_width=1.3).move_to([0,-2.16,0])",
      T("context",f"context = [{ca:.3f}, {cb:.3f}]",0,-2.95,31,BODY),
      T("result_line","The weights determine both value contributions",0,1.82,24,MUTED),
      f"        arrow_a=Arrow([{s['qx']+1.35:.3f},1.20,0],[{s['ka']-1.7:.3f},1.50,0],buff=0,stroke_width=3,color={PROCESS_COLOR!r})",
      f"        arrow_b=Arrow([{s['qx']+1.2:.3f},.68,0],[{s['kb']-1.7:.3f},.82,0],buff=0,stroke_width=3,color={ACCENT!r})",
    ]
    # This dispatch is by typed semantic opcode, NEVER by fixture ID, and
    # determines actual rendering operations, not only text emphasis.
    def actions(op):
        if op=="intro":
            return [("FadeIn(query_node),FadeIn(key_a_node),FadeIn(key_b_node)",1.4),
                    ("Indicate(query_node,color=YELLOW)",.8)]
        if op=="compare":
            return [("FadeIn(query_node),FadeIn(key_a_node),FadeIn(key_b_node)",.45)] if "intro" not in [x.op for x in p.beats] else []
        return []
    visible_q=False
    for index,beat in enumerate(p.beats):
        op=beat.op
        events=[]
        if op=="intro":
            events=actions("intro");visible_q=True
        elif op=="compare":
            if not visible_q:
                events.append(("FadeIn(query_node),FadeIn(key_a_node),FadeIn(key_b_node)",.85));visible_q=True
            events += [
              ("Create(arrow_a),Create(arrow_b)",1.2),
              ("FadeIn(scaled_a),FadeIn(scaled_b),FadeIn(rule)",1.15),
              ("Indicate(scaled_a,color=YELLOW),Indicate(scaled_b,color=YELLOW)",.6)]
        elif op=="normalize":
            events=[
              ("FadeOut(query_node),FadeOut(key_a_node),FadeOut(key_b_node),FadeOut(arrow_a),FadeOut(arrow_b),FadeOut(rule)",.60),
              ("TransformFromCopy(scaled_a,bar_a),TransformFromCopy(scaled_b,bar_b),FadeIn(softmax_title)",1.6),
              ("FadeOut(scaled_a),FadeOut(scaled_b)",.4),
              ("FadeIn(wa),FadeIn(wb)",.65)]
        elif op=="inspect":
            if [x.op for x in p.beats].index("compose")<index:
                events=[("Indicate(segment_a,color=TEAL),Indicate(segment_b,color=YELLOW)",.85)]
            else:
                events=[("Indicate(bar_a,color=TEAL),Indicate(bar_b,color=YELLOW)",.85)]
        elif op=="transport":
            events=[
              ("FadeOut(wa),FadeOut(wb),FadeOut(softmax_title)",.55),
              ("FadeIn(value_a),FadeIn(value_b),FadeIn(context_rail)",.85),
              ("TransformFromCopy(value_a,share_a),TransformFromCopy(value_b,share_b)",1.05),
              ("TransformFromCopy(bar_a,segment_a),TransformFromCopy(bar_b,segment_b)",1.55)]
        elif op=="compose":
            events=[
              ("FadeOut(value_a),FadeOut(value_b),FadeOut(bar_a),FadeOut(bar_b),FadeOut(share_a),FadeOut(share_b)",.65),
              ("FadeIn(context),FadeIn(result_line)",.90),
              ("Indicate(segment_a,color=TEAL),Indicate(segment_b,color=YELLOW)",.70)]
        # Model-chosen focus/mode also affects real target visual emphasis.
        target={
          "query":"query_node","key_a":"key_a_node","key_b":"key_b_node",
          "score_a":"scaled_a","score_b":"scaled_b","weight_a":"bar_a",
          "weight_b":"bar_b","value_a":"value_a","value_b":"value_b",
          "context":"context"}[beat.focus_ref]
        # Stage focus is only allowed when the referenced host object is visible.
        if (op=="inspect" and target=="context" and
           [x.op for x in p.beats].index("compose")<index):
            raise Blocked("V353_INSPECT_VISIBILITY_BROKEN")
        if beat.visual_mode=="trace":
            # path trace is grounded in the same object; no model-provided SVG.
            events.append((f"Flash({target},color=YELLOW)",.5))
        elif beat.visual_mode=="compare":
            events.append((f"Circumscribe({target},color=YELLOW)",.65))
        else:
            events.append((f"Indicate({target},color=YELLOW,scale_factor=1.05)",.55))
        t=sum(duration for _,duration in events)
        if seconds[index]-t<.35:
            raise Blocked("V353_MOTION_EXCEEDS_NARRATION")
        lines.append(f"        # V353_BEAT_{index}_{op} claim={beat.claim_id} evidence_sha={p.evidence_sha256}")
        for cmd,d in events:
            lines.append(f"        self.play({cmd},run_time={d:.3f})")
        lines.append(f"        self.wait({seconds[index]-t:.5f})")
    lines.append("        self.wait(.4)")
    code="\n".join(lines)+"\n"
    if any(b in code for b in ("__import__","subprocess","eval(","exec(","import os")):
        raise Blocked("V353_UNSAFE_HOST_CODE")
    compile(code,"<v353-host-composition>","exec")
    return code
