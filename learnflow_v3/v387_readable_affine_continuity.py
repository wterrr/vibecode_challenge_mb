"""V3-87 source-scoped affine visual hierarchy and geometric line continuity.

No model-authored Python. Both (x,y) and (t,v) share this source-typed finite
layout, not topic-specific fixtures. Phase timing belongs to original WAV.
This generator is opt-in and does not alter any V3-80..V3-86 renderer.
"""
from __future__ import annotations
from fractions import Fraction
from hashlib import sha256
import json

from learnflow_v3.v385_affine_visual_semantics import need, COLOR, FPS, role_contract
from learnflow_v3.v386_pedagogical_speech_contract import PHASES

# Safe 1280x720 Manim world coordinates; all layout boxes are disjoint
# by CONSTRUCTION and checked independently prior to rendering.
X0=-3.95
X1=2.55
Y0=-1.25
Y1=.85
AXIS_RIGHT=3.25
AXIS_TOP=1.11
RESULT_Y=-2.67

# Audit-friendly zones (left, right, bottom, top); units are Manim world.
RECTS={
    "heading":(-6.25,6.25,1.50,3.46),
    "plot":(-4.25,3.30,-1.59,1.23),
    "callout":(3.70,6.45,-.75,1.10),
    "conclusion":(-5.10,5.10,-3.18,-2.23),
}
FONT_SIZES={"title":34,"step":32,"context":33,"axis":28,
            "callout_tag":28,"callout_value":36,"answer":46}


def _f(s):
    return Fraction(s)


def _rect_disjoint(a,b):
    l1,r1,b1,t1=a;l2,r2,b2,t2=b
    return r1<=l2 or r2<=l1 or t1<=b2 or t2<=b1


def layout(role):
    need(role["version"]=="V3_85_VERIFIED_AFFINE_GRAPH_ROLE_V1",
         "UNVERIFIED_SOURCE_ROLE_VERSION")
    v=role["verified_values"]
    rate=_f(v["rate"]);x=_f(v["independent"]);init=_f(v["initial"])
    delta=_f(v["change"]);total=_f(v["final"])
    need(x>0 and rate>0 and init>=0 and delta==rate*x and total==delta+init,
         "SOURCE_AFFINE_NUMBERS_NOT_CONSERVED")
    need(total>0,"DEGENERATE_GRAPH_SCALE")
    h=Y1-Y0
    frac=init/total
    y_delta=round(Y0+h*float(delta/total),5)
    y_intercept=round(Y0+h*float(frac),5)
    # The transformed and reference line must have exactly identical slope.
    need(abs((y_intercept-Y0)-(Y1-y_delta))<=.000025,
         "C2_DOES_NOT_TRANSLATE_THE_SAME_SLOPE")
    need(all(_rect_disjoint(RECTS[k],RECTS[j])
             for i,k in enumerate(RECTS)
             for j in list(RECTS)[i+1:]),
         "VISUAL_LABEL_OR_PLOT_ZONES_OVERLAP")
    need(all(size>=28 for size in FONT_SIZES.values()),
         "LEGIBILITY_MIN_TYPE_SIZE")
    need(X1+0.5 < RECTS["callout"][0] and
         AXIS_RIGHT < RECTS["callout"][0] and
         RECTS["plot"][2]<=Y0 and
         Y1<RECTS["plot"][3] and
         RESULT_Y>RECTS["conclusion"][2],
         "ENDPOINT_ANNOTATION_OR_EQUATION_COLLISION")
    points={
        "origin":[X0,Y0],"reference_final":[X1,y_delta],
        "intercept":[X0,y_intercept],"translated_final":[X1,Y1],
    }
    token={
        "semantic_role":role["role"],
        "source_sha256":role["source_sha256"],
        "role_receipt_sha256":role["receipt_sha256"],
        "claims":role["claim_ids"],
        "geometry":points,"reference_slope_delta_y":round(y_delta-Y0,5),
        "translated_slope_delta_y":round(Y1-y_intercept,5),
        "vertical_intercept_shift":round(y_intercept-Y0,5),
        "type_sizes":FONT_SIZES,"safe_regions":RECTS,
        "visual_decision":"REUSE_C1_REFERENCE_THEN_TRANSLATE_UP_BY_VERIFIED_INTERCEPT",
        "labels_in_distinct_gutter":True,
        "historical_openstax_source_not_newly_reviewed":True,
        "graph_dot_is_not_a_physical_object":True,
    }
    token["sha256"]=sha256(json.dumps(token,sort_keys=True).encode()).hexdigest()
    return token


def _txt(name,string,x,y,size,color,maxwidth):
    # Truncation never substitutes numbers; long labels only shrink to a cap,
    # never enlarge short ones. All labels are source contract constants.
    return [
        f"        {name}=Text({string!r},font='CMU Serif',font_size={size},color={color!r}).move_to([{x:.5f},{y:.5f},0])",
        f"        if {name}.width > {maxwidth}: {name}.scale_to_fit_width({maxwidth})",
    ]


def emit_phase(i,phase,seconds,role,plan):
    need(phase["semantic_beat_index"]==i and
         phase["phase_kind"]==PHASES[phase["phase_index"]] and
         phase["claim_id"]==plan["claims"][i],
         "VOICE_PHASE_CLAIM_OR_STAGE_NOT_BOUND")
    count=round(seconds*FPS)
    need(type(seconds) is float and count>=95,"AUDIO_PHASE_TOO_SHORT")
    prefix=f"v387_{i}_"
    v=role["verified_values"];p=plan["geometry"]
    x0,y0=p["origin"]; xf,ychange=p["reference_final"]
    _,yintercept=p["intercept"];_,yfinal=p["translated_final"]
    kind=phase["phase_kind"]
    if role["role"]=="velocity_vs_elapsed_time":
        gradient_label="ACCELERATION = SLOPE"
        result_key="Δv" if i==0 else "v final"
    else:
        gradient_label="OUTPUT CHANGE = SLOPE × INPUT"
        result_key="Δy" if i==0 else "y final"
    formula=(f"{v['rate']} × {v['independent']} = {v['change']}" if i==0
             else f"{v['initial']} + {v['change']} = {v['final']}")
    if i==1:
        tag="SHIFT THE SAME SLOPE BY THE STARTING VALUE"
        value=v["final"]
    else:
        tag="READ THE RATE AND ITS EFFECT"
        value=v["change"]
    lines=[]
    if kind=="ORIENT":
        fixed=32
        lines=[f"        # V387_SPEECH_SCENE_{i}_ORIENT claim={phase['claim_id']}"]
        lines+=_txt(prefix+"step",f"STEP {i+1} / 2 · {tag}",0,2.46,32,COLOR["blue"],12.1)
        lines+=_txt(prefix+"title",role["horizontal_label"]+" → "+role["vertical_label"],0,1.75,33,COLOR["ink"],11.0)
        lines.extend([
            f"        {prefix}axis_x=Arrow([{X0},{Y0},0],[{AXIS_RIGHT},{Y0},0],buff=0,stroke_width=4,color={COLOR['axis']!r})",
            f"        {prefix}axis_y=Arrow([{X0},{Y0},0],[{X0},{AXIS_TOP},0],buff=0,stroke_width=4,color={COLOR['axis']!r})",
        ])
        lines+=_txt(prefix+"xname",role["horizontal_label"],2.36,-1.84,28,COLOR["muted"],4.0)
        lines+=_txt(prefix+"yname",role["vertical_label"],-5.12,.95,28,COLOR["muted"],3.65)
        lines.extend([
            f"        {prefix}marker=Dot([{xf if i else x0},{ychange if i else y0},0],radius=.12,color={COLOR['start']!r})",
            f"        self.play(FadeIn({prefix}step),run_time=8/15)",
            f"        self.play(FadeIn({prefix}title),run_time=8/15)",
            f"        self.play(Create({prefix}axis_x),Create({prefix}axis_y),run_time=8/15)",
            f"        self.play(FadeIn({prefix}xname),FadeIn({prefix}yname),run_time=8/15)",
        ])
        if i==1:
            lines.extend([
                f"        {prefix}reference=DashedLine([{x0},{y0},0],[{xf},{ychange},0],dash_length=.15,color={COLOR['muted']!r},stroke_width=3)",
                f"        {prefix}intercept_dot=Dot([{x0},{yintercept},0],radius=.09,color={COLOR['rise']!r})",
                f"        self.add({prefix}reference,{prefix}intercept_dot)",
            ])
        lines.append(f"        self.add({prefix}marker)")
    elif kind=="TRANSFORM":
        fixed=41
        lines=[f"        # V387_SPEECH_SCENE_{i}_TRANSFORM claim={phase['claim_id']}"]
        lines+=_txt(prefix+"callout_tag",gradient_label,4.89,.80,28,COLOR["blue"],2.5)
        lines+=_txt(prefix+"callout_value",f"{result_key} = {value}",4.89,.22,36,COLOR["rise"],2.55)
        if i==0:
            lines.extend([
                f"        {prefix}curve=Line([{x0},{y0},0],[{xf},{ychange},0],color={COLOR['line']!r},stroke_width=9)",
                f"        self.play(Create({prefix}curve),MoveAlongPath({prefix}marker,{prefix}curve),run_time=26/15)",
                f"        {prefix}rise=DashedLine([{xf},{y0},0],[{xf},{ychange},0],dash_length=.13,color={COLOR['rise']!r},stroke_width=3)",
                f"        self.play(Create({prefix}rise),run_time=7/15)",
            ])
        else:
            dy=plan["vertical_intercept_shift"]
            lines.extend([
                f"        {prefix}curve=Line([{x0},{y0},0],[{xf},{ychange},0],color={COLOR['line']!r},stroke_width=9)",
                f"        self.add({prefix}curve)",
                f"        {prefix}shifted=Line([{x0},{yintercept},0],[{xf},{yfinal},0],color={COLOR['line']!r},stroke_width=9)",
                f"        self.play(Transform({prefix}curve,{prefix}shifted),{prefix}marker.animate.shift(UP*{dy:.6f}),run_time=26/15)",
                f"        {prefix}rise=DashedLine([{x0},{y0},0],[{x0},{yintercept},0],dash_length=.13,color={COLOR['rise']!r},stroke_width=3)",
                f"        self.play(Create({prefix}rise),run_time=7/15)",
            ])
        lines.extend([
            f"        self.play(FadeIn({prefix}callout_tag),FadeIn({prefix}callout_value),run_time=8/15)",
        ])
    else:
        fixed=24
        lines=[f"        # V387_SPEECH_SCENE_{i}_INTERPRET claim={phase['claim_id']}"]
        lines+=_txt(prefix+"formula",formula,0,RESULT_Y,46,COLOR["ink"],9.7)
        lines.extend([
            f"        self.play(Write({prefix}formula),run_time=10/15)",
            f"        self.play(Indicate({prefix}marker,color={COLOR['rise']!r},scale_factor=1.25),run_time=5/15)",
        ])
    need(count>=fixed+12,"NO_REAL_PCM_HOLD_FRAMES")
    lines.append(f"        self.wait({count-fixed}/15)")
    if kind=="INTERPRET":
        objs=[prefix+x for x in ("step","title","axis_x","axis_y","xname","yname","marker",
                                  "curve","rise","callout_tag","callout_value","formula")]
        if i==1:
            objs.extend([prefix+"reference",prefix+"intercept_dot"])
        lines.append("        self.play("+",".join("FadeOut("+x+")" for x in objs)+",run_time=9/15)")
    return lines


def finite_source(trace,durations,role,phases):
    need(len(trace["events"])==2 and len(durations)==len(phases)==6,
         "SIX_PCM_PHASES_REQUIRED")
    verified_plan=layout(role)
    need([x["phase_index"] for x in phases]==[0,1,2,0,1,2],
         "INVALID_SPEECH_PHASE_SEQUENCE")
    lines=[
        "# V3-87 host-only grounded chart readability, translation and narration",
        "from manim import *",
        "class GeneratedLesson(Scene):",
        "    def construct(self):",
        "        self.camera.background_color='#080b11'",
    ]
    lines+=_txt("v387_lesson_name",trace["title"],0,3.34,34,COLOR["ink"],12.25)
    lines.append("        self.add(v387_lesson_name)")
    for j,(phase,sec) in enumerate(zip(phases,durations,strict=True)):
        i=j//3
        need(phase["claim_id"]==trace["events"][i]["claim_id"],
             "CLAIM_ID_TO_PLOT_DRIFT")
        lines.extend(emit_phase(i,phase,sec,role,verified_plan))
    lines.append("        self.wait(2/15)")
    source="\n".join(lines)+"\n"
    for bad in ("__import__(", "eval(", "exec(", "os.system", "subprocess"):
        need(bad not in source,"UNTRUSTED_PYTHON_IN_NATIVE_SCENE")
    compile(source,"<verified-v387-story>",'exec')
    return source
