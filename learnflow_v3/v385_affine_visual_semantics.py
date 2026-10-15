"""V3-85: typed, source-scoped affine visualization for different semantic roles.

A single verified affine operator graph can express y=m*x+b or v=v0+a*t,
yet these are DIFFERENT teaching meanings. Role registry lives at the
source-contract boundary; renderer knows axes and values, not topic IDs.
The moving point is always a GRAPH POINT, never a moving physical object.
"""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
import json

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.v381_generic_semantic_operators import parse_value, calculate, encode
from learnflow_v3.v383_semantic_unit_storytelling import certify_event

# Frozen metadata from the source-grounded V3-28/V3-82 lineage, not free text
# heuristics or model-generated code. Supporting a new source family requires
# a separately validated semantic law, not an ad-hoc case-specific branch in Manim.
AFFINE_ROLE_REGISTRY={
    "LINEAR_SLOPE":{
        "rate":"m","independent":"x","intercept":"b",
        "horizontal":"x (input)","vertical":"y (output)",
        "horizontal_short":"x","vertical_short":"y",
        "role":"input_output_line","interpretation":"SLOPE_TIMES_INPUT_PLUS_INTERCEPT",
    },
    "CONSTANT_ACCELERATION_VELOCITY":{
        "rate":"acceleration","independent":"elapsed",
        "intercept":"initial_velocity",
        "horizontal":"t (elapsed time)","vertical":"v (velocity)",
        "horizontal_short":"t","vertical_short":"v",
        "role":"velocity_vs_elapsed_time",
        "interpretation":"SLOPE_IS_ACCELERATION_NOT_OBJECT_DISPLACEMENT",
    },
}
FPS=15
COLOR={"axis":"#AEB9C8","line":"#42D9CD",
       "start":"#FFAC71","rise":"#F0D969","ink":"#F4F1E8",
       "muted":"#9CA6B8","blue":"#82B5FF"}
X_ZERO=-3.65
X_FINAL=3.20
Y_ZERO=-1.25
Y_FULL=.65


def need(ok,reason):
    if not ok:
        raise Blocked("V385_"+reason)


def _value(v):
    t=parse_value(v)
    need(t[0]=="scalar" and 0<=t[1]<=40 and t[1].denominator<=100,
         "OUT_OF_BOUNDS_AFFINE_SCALAR")
    return t[1]


def _fmt(v):
    v=Fraction(v)
    return str(v.numerator) if v.denominator==1 else f"{v.numerator}/{v.denominator}"


def role_contract(row,bundle):
    need(bundle.get("status")=="READY_FOR_NATIVE_RESEARCH_ONLY",
         "NO_VERIFIED_QUERY_AND_SOURCE")
    role=AFFINE_ROLE_REGISTRY.get(row.get("source_model"))
    need(role is not None,"UNKNOWN_VERIFIED_SOURCE_SEMANTICS")
    need(bundle["source_reference_kind"]=="PREVIOUSLY_CURATED_V3_28_NOT_LIVE_VERIFIED",
         "SOURCE_SCOPE_SPOOFED")
    need(bundle["source_url"]==bundle["contracts"]["research"]["sources"][0]["locator"],
         "SOURCE_URL_BROKEN")
    need(all(key in row["facts"] for key in
             (role["rate"],role["independent"],role["intercept"])),
         "MISSING_AFFINE_ROLE_BINDINGS")
    rate=_value(row["facts"][role["rate"]])
    x=_value(row["facts"][role["independent"]])
    initial=_value(row["facts"][role["intercept"]])
    need(0<rate<=15 and 0<x<=15 and 0<=initial<=15,
         "AFFINE_RATE_INPUT_OUTSIDE_PROOF_SCOPE")
    delta=rate*x
    final=initial+delta
    need(0<delta<=40 and final<=40,"AFFINE_OUTPUT_OUTSIDE_GRAPH_RANGE")
    trace=bundle["trace"]
    events=trace["events"]
    need(len(events)==2 and [e["kind"] for e in events]==["SCALE","ADD"],
         "UNSUPPORTED_AFFINE_OPERATION_TRACE")
    for event in events:
        actual=calculate(event["kind"],[parse_value(v) for v in event["operands"]])
        need(encode(actual)==event["actual"],"V381_ARITHMETIC_PROVENANCE_MISMATCH")
    scale_inputs=[_value(v) for v in events[0]["operands"]]
    add_inputs=[_value(v) for v in events[1]["operands"]]
    need(sorted(scale_inputs)==sorted([rate,x]) and
         _value(events[0]["actual"])==delta,
         "RATE_TIMES_INPUT_EVIDENCE_MISMATCH")
    need(sorted(add_inputs)==sorted([initial,delta]) and
         _value(events[1]["actual"])==final,
         "INITIAL_PLUS_CHANGE_EVIDENCE_MISMATCH")
    need(set(x["claim_id"] for x in events)=={"C1","C2"},
         "AFFINE_CLAIM_IDS_DRIFT")
    need(bundle["contracts"]["pedagogy_gate"]=="V3_09_VALIDATED" and
         bundle["contracts"]["visual_director_gate"]=="CORE_READY",
         "HERMES_PEDAGOGY_OR_DIRECTOR_NOT_VERIFIED")
    # Use a shared unit-less normalized position transform to prevent visual
    # overflow and show scale-proportion correctly within a single chart.
    def y_pos(v):
        return round(Y_ZERO+(Y_FULL-Y_ZERO)*float(v/final),5)
    points={
        "origin":[X_ZERO,Y_ZERO],
        "input_max":[X_FINAL,Y_ZERO],
        "rate_end":[X_FINAL,y_pos(delta)],
        "initial":[X_ZERO,y_pos(initial)],
        "final":[X_FINAL,y_pos(final)],
    }
    need(points["final"][1]==round(Y_FULL,5),"FINAL_VALUE_NOT_TOP_ENDPOINT")
    need(points["rate_end"][1]>=Y_ZERO and
         points["initial"][1]>=Y_ZERO,"NEGATIVE_GRAPH_Y_POSITION")
    need(points["rate_end"][1]<=Y_FULL and
         points["final"][1]<=Y_FULL,"GRAPH_OVERRUN")
    need(len({tuple(v) for v in points.values()})>=4,"DEGENERATE_GRAPH_POINTS")
    claims={
        "rate":_fmt(rate),"independent":_fmt(x),"initial":_fmt(initial),
        "change":_fmt(delta),"final":_fmt(final),
    }
    result={
        "version":"V3_85_VERIFIED_AFFINE_GRAPH_ROLE_V1",
        "source_kind":row["source_model"],
        "role":role["role"],"interpretation":role["interpretation"],
        "horizontal_label":role["horizontal"],
        "vertical_label":role["vertical"],
        "x_short":role["horizontal_short"],"y_short":role["vertical_short"],
        "verified_values":claims,"points":points,
        "host_source_provenance":"HISTORICALLY_CURATED_V3_28_OPENSTAX_NOT_FRESH_CHECKED",
        "actual_object_motion":"NONE_GRAPH_POINT_ONLY",
        "source_sha256":bundle["source_sha256"],
        "original_generated_query_plan_sha256":bundle["generated_case_sha256"],
        "claim_ids":["C1","C2"],
        "geometry_limits":"HOST_VERIFIED_AXES_1280x720",
        "source_truth_independently_reviewed":False,
        "model_authored":False,
    }
    result["receipt_sha256"]=sha256(
        json.dumps(result,sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()
    return result


def _text(var,content,pos,size=26,color="#F4F1E8",max_width=None):
    # Content interpolated via repr; it is never executed as code.
    expr=(f"        {var}=Text({content!r},font='CMU Serif',"
          f"font_size={size},color={color!r}).move_to("
          f"[{pos[0]:.5f},{pos[1]:.5f},0])")
    if max_width:
        expr+="\n"+f"        if {var}.width > {max_width}: {var}.scale_to_fit_width({max_width})"
    return expr


def emit_step(i,event,seconds,role):
    """Every fixed play is a 15fps integer-frame duration, plus exact hold."""
    need(type(seconds) is float and 8<=seconds<=30,
         "AUDIO_BEAT_TOO_SHORT_FOR_AFFINE_PLOT")
    need(event["claim_id"]==role["claim_ids"][i] and
         event["kind"]==("SCALE" if i==0 else "ADD"),
         "WRONG_NARRATION_CLAIM_TO_GRAPH")
    v=role["verified_values"]
    p=role["points"]
    x0,y0=p["origin"]
    xe,_=p["input_max"]
    if i==0:
        from_point=[x0,y0]
        end_point=p["rate_end"]
        tag="RATE × INPUT = CHANGE"
        formula=f"{v['rate']} × {v['independent']} = {v['change']}"
        intro=f"Rate {v['rate']} applied over input {v['independent']}"
        rise=f"change = {v['change']}"
    else:
        from_point=p["initial"]
        end_point=p["final"]
        tag="INITIAL VALUE + CHANGE = FINAL"
        formula=f"{v['initial']} + {v['change']} = {v['final']}"
        intro=f"Start {v['initial']}; add change {v['change']}"
        rise=f"final = {v['final']}"
    a0,b0=from_point
    a1,b1=end_point
    # Plot axis lines y-axis x=X_ZERO, x-axis y=Y_ZERO.
    # Stage title sits above graph; exact equation sits below graph.
    lines=[
        f"        # V385_VERIFIED_SEMANTIC_GRAPH_BEAT_{i} {role['role']} {event['claim_id']}",
        _text(f"v385_step_{i}",f"STEP {i+1} OF 2 — {tag}",[0,2.27],26,COLOR["blue"],11.5),
        _text(f"v385_source_{i}",intro,[0,1.52],27,COLOR["ink"],10.7),
        f"        v385_x_axis_{i}=Arrow([{X_ZERO}, {Y_ZERO},0],[{X_FINAL+.75:.5f},{Y_ZERO},0],"
        f"buff=0,stroke_width=3.2,color={COLOR['axis']!r})",
        f"        v385_y_axis_{i}=Arrow([{X_ZERO},{Y_ZERO},0],[{X_ZERO},{Y_FULL+.38:.5f},0],"
        f"buff=0,stroke_width=3.2,color={COLOR['axis']!r})",
        _text(f"v385_x_label_{i}",role["horizontal_label"],[X_FINAL+.32,Y_ZERO-.48],22,COLOR["muted"],3.1),
        _text(f"v385_y_label_{i}",role["vertical_label"],[X_ZERO+.50,Y_FULL+.41],22,COLOR["muted"],3.5),
        f"        v385_baseline_{i}=DashedLine([{a0},{b0},0],[{a1},{b0},0],"
        f"dash_length=.12,color={COLOR['muted']!r},stroke_width=2.2)",
        f"        v385_vertical_{i}=DashedLine([{a1},{b0},0],[{a1},{b1},0],"
        f"dash_length=.12,color={COLOR['rise']!r},stroke_width=3)",
        f"        v385_curve_{i}=Line([{a0},{b0},0],[{a1},{b1},0],"
        f"color={COLOR['line']!r},stroke_width=7)",
        f"        v385_marker_{i}=Dot([{a0},{b0},0],radius=.10,color={COLOR['start']!r})",
        _text(f"v385_rise_{i}",rise,[3.70,.45],24,COLOR["rise"],3.0),
        _text(f"v385_formula_{i}",formula,[0,-2.52],38,COLOR["ink"],9.5),
        f"        self.play(FadeIn(v385_step_{i}),run_time=8/15)",
        f"        self.play(FadeIn(v385_source_{i}),run_time=8/15)",
        f"        self.play(Create(v385_x_axis_{i}),Create(v385_y_axis_{i}),run_time=8/15)",
        f"        self.play(FadeIn(v385_x_label_{i}),FadeIn(v385_y_label_{i}),run_time=8/15)",
        f"        self.add(v385_marker_{i})",
        f"        self.play(Create(v385_curve_{i}),MoveAlongPath(v385_marker_{i},v385_curve_{i}),run_time=26/15)",
        f"        self.play(Create(v385_baseline_{i}),Create(v385_vertical_{i}),run_time=7/15)",
        f"        self.play(FadeIn(v385_rise_{i}),Write(v385_formula_{i}),run_time=10/15)",
        f"        self.play(Indicate(v385_marker_{i},color={COLOR['rise']!r},scale_factor=1.35),run_time=5/15)",
    ]
    # 8+8+8+8+26+7+10+5+9 = 89 frames.
    fixed=89
    budget=int(round(seconds*FPS))
    need(budget>=fixed+15,"AFFINE_VIDEO_NO_EXACT_HOLD_TIME")
    lines.extend([
        f"        self.wait({budget-fixed}/15)",
        f"        self.play(FadeOut(v385_step_{i}),FadeOut(v385_source_{i}),"
        f"FadeOut(v385_x_axis_{i}),FadeOut(v385_y_axis_{i}),"
        f"FadeOut(v385_x_label_{i}),FadeOut(v385_y_label_{i}),"
        f"FadeOut(v385_baseline_{i}),FadeOut(v385_vertical_{i}),"
        f"FadeOut(v385_curve_{i}),FadeOut(v385_marker_{i}),"
        f"FadeOut(v385_rise_{i}),FadeOut(v385_formula_{i}),run_time=9/15)",
    ])
    return lines


def finite_manim_source(trace,durations,role):
    need(len(trace["events"])==len(durations)==2,"UNSUPPORTED_GRAPH_BEAT_COUNT")
    # Independent SHA/claims already checked in role_contract.
    lines=[
        "# V3-85 host-owned finite affine graph compiled from V3-82 source evidence",
        "from manim import *",
        "class GeneratedLesson(Scene):",
        "    def construct(self):",
        "        self.camera.background_color='#080b11'",
        _text("v385_title",trace["title"],[0,3.43],27,COLOR["ink"],12.0),
        "        self.add(v385_title)",
    ]
    for i,(e,t) in enumerate(zip(trace["events"],durations,strict=True)):
        lines.extend(emit_step(i,e,t,role))
    lines.append("        self.wait(2/15)")  # global mux tolerance, not per-beat drift
    src="\n".join(lines)+"\n"
    for forbidden in ("__import__(", "eval(", "exec(", "subprocess", "os.system"):
        need(forbidden not in src,"UNSAFE_GENERATED_SOURCE")
    compile(src,"<trusted-v385>",'exec')
    return src
