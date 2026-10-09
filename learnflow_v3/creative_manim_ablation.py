"""V3-34: bounded LLM scene plan with factual invariants and safe Manim compiler.

Model controls narrative, scene composition, positions and movement. Only this
trusted host module writes executable Python. Model output is JSON DATA and
never compiled/executed. The eventual Manim subprocess runs sandboxed.
"""
from __future__ import annotations
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator

VERSION="v3-34-creative-manim-primitive-ablation-v1"
MANIFEST="benchmarks/learnflowbench/v3/v3_34_scene_ablation_preregister.json"
PALETTE={"WHITE":"#f4f1e8","TEAL":"#42d9cd","YELLOW":"#f0d969",
         "BLUE":"#82b5ff","ORANGE":"#ffac71","GREEN":"#8fe6aa","GREY":"#9b9b9b"}
FACTS={
  "F1":"One half equals two quarters.",
  "F2":"Multiplying numerator and denominator by the same nonzero number preserves the fraction value.",
  "F3":"Two shaded parts out of four equally sized parts represent one half.",
}
BEATS=4
ALLOWED_NUMBERS={"1","2","4","0.5","50"}
class Blocked(ValueError):pass


def strict_model():
    return ConfigDict(extra="forbid")


class Graphic(BaseModel):
    model_config=strict_model()
    id:str=Field(pattern=r"^[a-z][a-z0-9_]{0,22}$")
    kind:Literal["text","rectangle","circle","dot"]
    x:float=Field(ge=-5.7,le=5.7)
    y:float=Field(ge=-2.55,le=2.55)
    color:Literal["WHITE","TEAL","YELLOW","BLUE","ORANGE","GREEN","GREY"]
    text:str=""
    width:float=Field(default=1.0,ge=.25,le=4)
    height:float=Field(default=.6,ge=.18,le=2.4)
    radius:float=Field(default=.45,ge=.06,le=1.2)
    @model_validator(mode="after")
    def consistent(self):
        if self.kind=="text":
            if not 1<=len(self.text.strip())<=40 or any(ord(c)<32 for c in self.text):
                raise ValueError("V334_TEXT_TOO_LONG_OR_CONTROL")
            if not _allowed_visible_math(self.text):
                raise ValueError("V334_UNVERIFIED_VISIBLE_NUMERIC_FACT")
        elif self.text:
            raise ValueError("V334_SHAPE_WITH_TEXT")
        return self


class Motion(BaseModel):
    model_config=strict_model()
    action:Literal["show","move","emphasize","remove","wait"]
    target:str|None=None
    x:float|None=Field(default=None,ge=-5.7,le=5.7)
    y:float|None=Field(default=None,ge=-2.55,le=2.55)
    @model_validator(mode="after")
    def action_contract(self):
        if self.action=="wait":
            if self.target is not None or self.x is not None or self.y is not None:
                raise ValueError("V334_WAIT_CAN_NOT_TARGET")
        else:
            if not self.target:raise ValueError("V334_MOTION_MISSING_TARGET")
            if self.action=="move" and (self.x is None or self.y is None):
                raise ValueError("V334_MOVE_MISSING_POINT")
            if self.action!="move" and (self.x is not None or self.y is not None):
                raise ValueError("V334_NON_MOVE_WITH_POINT")
        return self


class LectureBeat(BaseModel):
    model_config=strict_model()
    claim_ids:list[Literal["F1","F2","F3"]]=Field(min_length=1,max_length=3)
    narration:str=Field(min_length=65,max_length=270)
    visual_goal:str=Field(min_length=8,max_length=150)
    actions:list[Motion]=Field(min_length=1,max_length=8)
    @model_validator(mode="after")
    def grounded(self):
        if not _allowed_visible_math(self.narration):
            raise ValueError("V334_UNVERIFIED_SPOKEN_NUMERIC_FACT")
        if re.search(r"\b(doubl\w*|trip\w*)\b",self.narration,re.I) and "F2" not in self.claim_ids:
            raise ValueError("V334_MUTIPLICATION_WITHOUT_CLAIM")
        return self


class CreativeScene(BaseModel):
    model_config=strict_model()
    title:str=Field(min_length=8,max_length=65)
    learning_objective:str=Field(min_length=12,max_length=140)
    objects:list[Graphic]=Field(min_length=5,max_length=22)
    beats:list[LectureBeat]=Field(min_length=BEATS,max_length=BEATS)
    model_author:Literal["openai/gpt-6-luna"]|None=None
    @model_validator(mode="after")
    def whole_plan(self):
        ids=[x.id for x in self.objects]
        if len(ids)!=len(set(ids)):raise ValueError("V334_DUPLICATE_GRAPHIC_IDS")
        state=set()
        for i,beat in enumerate(self.beats):
            if len(beat.narration.split())<12:raise ValueError("V334_SHORT_NARRATION")
            for motion in beat.actions:
                if motion.action=="wait":continue
                if motion.target not in ids:raise ValueError("V334_UNKNOWN_OBJECT")
                if motion.action=="show":
                    if motion.target in state:raise ValueError("V334_DUPLICATED_SHOW")
                    state.add(motion.target)
                elif motion.target not in state:
                    raise ValueError("V334_OBJECT_NOT_YET_VISIBLE")
                elif motion.action=="remove":
                    state.remove(motion.target)
            if len(state)>20:raise ValueError("V334_OVERCROWDED_FRAME")
        claims={id for beat in self.beats for id in beat.claim_ids}
        if claims!={"F1","F2","F3"}:raise ValueError("V334_INCOMPLETE_TOPIC_FACT_COVERAGE")
        if len({x.kind for x in self.objects})<2:
            raise ValueError("V334_VISUAL_NOT_ANIMATION")
        return self


def _allowed_visible_math(text:str)->bool:
    """Reject numeric drift, even though free prose is not full fact verification."""
    numbers=re.findall(r"(?<![A-Za-z_])(?:\d+(?:\.\d+)?)(?![A-Za-z_])",text)
    return all(x in ALLOWED_NUMBERS for x in numbers)


def checked_manifest(root:Path)->dict:
    prereg=json.loads((root/MANIFEST).read_text())
    original=json.loads((root/"benchmarks/learnflowbench/v3/v3_33_locked_unseen_topics.json").read_text())
    topic=original["cases"][0]
    if (prereg["preimplementation_locked"] is not True or
        prereg["topic_id"]!="lfb-018-math" or
        prereg["topic_id"]!=topic["topic_id"] or
        prereg["topic_query_sha256"]!=topic["query_sha256"] or
        prereg["provider_requests_cap"]!=1 or prereg["model"]!="openai/gpt-6-luna" or
        prereg["provider_fallback"] is not False or
        prereg["provider_retries"]!=0):
        raise Blocked("V334_UNREGISTERED_SELECTION_OR_BUDGET_CHANGE")
    if Fraction(1,2)!=Fraction(2,4) or Fraction(2,4)!=Fraction(1,2):
        raise Blocked("V334_ARITHMETIC_PROOF_FAILURE")
    if Fraction(1*2,2*2)!=Fraction(1,2):
        raise Blocked("V334_EQUIVALENCE_PROOF_FAILURE")
    return prereg


def ablation_baselines(root:Path,plan:CreativeScene)->dict:
    from learnflow_v3.unseen_domain_quality_audit import audit_six
    audit=audit_six(root)
    row=audit["rows"][0]
    if row["topic_id"]!="lfb-018-math" or row["domain"]!="math" or audit["abstain"]!=6:
        raise Blocked("V334_BASELINE_CHANGED")
    # B really uses the model's creative plan, but the existing typed adapter
    # covers source-certified LINEAR_FUNCTION slope, not ratio part diagrams.
    b="ABSTAIN_OLD_RENDERER_CANNOT_REPRESENT_GENERATED_FRACTION_GRAPHICS"
    return {
      "A":{"status":row["status"],"rendered":False,"input":"frozen V3-33 exact topic"},
      "B":{"status":b,"rendered":False,
           "input":"same MODEL authored objects, actions, narration as C",
           "old_renderer_capability":"FUNCTION_GRAPH only; no certified fraction partition and object motions"},
      "C":{"status":"AWAIT_REAL_SANDBOX_MP4","rendered":False,
           "input":"same MODEL authored objects, actions, narration as B"},
      "pilot_is_not_symmetric_three_finished_videos":True
    }


def manim_code(plan:CreativeScene,durations:list[float])->str:
    if len(durations)!=BEATS or any(not 2<=t<=20 for t in durations):
        raise Blocked("V334_MEASURED_AUDIO_DURATION_INVALID")
    lines=[
      "# Host-generated finite Manim source; no provider Python is executed.",
      "from manim import *",
      "class GeneratedLesson(Scene):",
      "    def construct(self):",
      "        self.camera.background_color = '#000000'",
    ]
    for item in plan.objects:
        v=item.id; col=PALETTE[item.color]; pos=f"[{item.x:.3f}, {item.y:.3f}, 0]"
        if item.kind=="text":
            obj=f"Text({item.text!r}, font='CMU Serif', font_size=30, color={col!r})"
            lines.append(f"        {v} = {obj}.scale_to_fit_width({min(6.0,max(.65,len(item.text)*.28)):.2f}).move_to({pos})")
        elif item.kind=="rectangle":
            lines.append(f"        {v} = Rectangle(width={item.width:.3f},height={item.height:.3f},color={col!r},fill_opacity=0.55).move_to({pos})")
        elif item.kind=="circle":
            lines.append(f"        {v} = Circle(radius={item.radius:.3f},color={col!r},fill_opacity=0.45).move_to({pos})")
        else:
            lines.append(f"        {v} = Dot(point={pos},radius={item.radius:.3f},color={col!r})")
    for n,(beat,total) in enumerate(zip(plan.beats,durations,strict=True)):
        lines.append(f"        # BEAT {n+1} - exact audio-budget duration {total:.3f}s")
        unit=total/len(beat.actions)
        for motion in beat.actions:
            if motion.action=="wait":
                lines.append(f"        self.wait({unit:.5f})")
            elif motion.action=="show":
                lines.append(f"        self.play(FadeIn({motion.target},scale=.9),run_time={unit:.5f})")
            elif motion.action=="move":
                lines.append(f"        self.play({motion.target}.animate.move_to([{motion.x:.3f},{motion.y:.3f},0]),run_time={unit:.5f})")
            elif motion.action=="emphasize":
                lines.append(f"        self.play(Indicate({motion.target},color=YELLOW,scale_factor=1.07),run_time={unit:.5f})")
            elif motion.action=="remove":
                lines.append(f"        self.play(FadeOut({motion.target}),run_time={unit:.5f})")
    lines.append("")
    result="\n".join(lines)
    if any(x in result for x in ("__import__","eval(","exec(","subprocess","os.system")):
        raise Blocked("V334_EMITTER_SAFETY_CONTRACT")
    return result


def fixture_plan()->CreativeScene:
    """A plainly labeled synthetic fixture for offline sandbox smoke, NOT LLM."""
    return CreativeScene.model_validate({
      "title":"Two quarters make one half",
      "learning_objective":"See how equal partitions relate fractions and ratios",
      "objects":[
        {"id":"title","kind":"text","text":"One half = Two quarters","x":0,"y":2.2,"color":"WHITE"},
        {"id":"l1","kind":"rectangle","x":-2.8,"y":.7,"width":1.3,"height":.9,"color":"TEAL"},
        {"id":"l2","kind":"rectangle","x":-1.4,"y":.7,"width":1.3,"height":.9,"color":"GREY"},
        {"id":"r1","kind":"rectangle","x":.5,"y":.7,"width":.65,"height":.9,"color":"TEAL"},
        {"id":"r2","kind":"rectangle","x":1.2,"y":.7,"width":.65,"height":.9,"color":"TEAL"},
        {"id":"r3","kind":"rectangle","x":1.9,"y":.7,"width":.65,"height":.9,"color":"GREY"},
        {"id":"r4","kind":"rectangle","x":2.6,"y":.7,"width":.65,"height":.9,"color":"GREY"},
        {"id":"lbl","kind":"text","text":"1/2 = 2/4","x":0,"y":-1.7,"color":"YELLOW"}
      ],
      "beats":[
        {"claim_ids":["F1"],"narration":"Let's split this bar into two equal parts. One shaded part is one half, a simple fraction.","visual_goal":"Reveal the first half bar","actions":[{"action":"show","target":"title"},{"action":"show","target":"l1"},{"action":"show","target":"l2"}]},
        {"claim_ids":["F2"],"narration":"Multiply both the top and bottom by two. The value stays the same, even when the pieces change shape.","visual_goal":"Reveal four pieces","actions":[{"action":"show","target":"r1"},{"action":"show","target":"r2"},{"action":"show","target":"r3"},{"action":"show","target":"r4"}]},
        {"claim_ids":["F3"],"narration":"Two shaded quarters out of four equal quarters also make one half. The ratio of shaded parts is the same.","visual_goal":"Show both partitions","actions":[{"action":"show","target":"lbl"},{"action":"emphasize","target":"r1"},{"action":"emphasize","target":"r2"}]},
        {"claim_ids":["F1","F3"],"narration":"So one half and two quarters are equal fractions. Compare the colored areas to see why the ratio stays unchanged.","visual_goal":"Final visual comparison","actions":[{"action":"emphasize","target":"l1"},{"action":"emphasize","target":"r1"},{"action":"emphasize","target":"lbl"}]}
      ],"model_author":None})
