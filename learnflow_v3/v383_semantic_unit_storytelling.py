"""V3-83 bounded, topic-neutral physical-unit storytelling for native Manim.

Opt-in, finite host-emitted geometry. It cannot certify visual beauty,
scientific facts, learner comprehension or arbitrary semantic operator families.
Each physical unit is counted from independently verified V3-81 arithmetic.
"""
from __future__ import annotations
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.v381_generic_semantic_operators import calculate, parse_value, encode

MAX_UNITS = 24
SAFE_OPERATORS = frozenset({"SCALE", "ADD"})
# Approximate Manim world geometry, intentionally independent of topic.
TILE = .29
PITCH = .38
LEFT_CENTER = -2.75
RIGHT_CENTER = 2.75


def check(ok, msg):
    if not ok:
        raise Blocked("V383_" + msg)


def _integer(raw):
    parsed = parse_value(raw)
    check(parsed[0] == "scalar" and parsed[1].denominator == 1 and
          1 <= parsed[1].numerator <= MAX_UNITS,
          "UNIT_PICTOGRAM_REQUIRES_POSITIVE_INTEGER")
    return parsed[1].numerator


def certify_event(e):
    check(isinstance(e, dict) and e.get("kind") in SAFE_OPERATORS,
          "UNSUPPORTED_VISUAL_OPERATOR")
    operands = e.get("operands")
    check(isinstance(operands, list) and len(operands) == 2,
          "INVALID_NATIVE_OPERANDS")
    left, right = (_integer(x) for x in operands)
    expected = left * right if e["kind"] == "SCALE" else left + right
    result = _integer(e.get("actual"))
    check(1 <= expected == result <= MAX_UNITS,
          "MATH_RESULT_OR_UNIT_COUNT_MISMATCH")
    replay = calculate(e["kind"],[parse_value(x) for x in operands])
    check(encode(replay) == e["actual"],"UNCERTIFIED_HOST_ARITHMETIC")
    if e["kind"] == "SCALE":
        check(left <= 12 and right <= 12,"UNSAFE_GROUP_GEOMETRY")
    return {
        "operator":e["kind"],"inputs":[left,right],"result_units":result,
        "initial_unit_count":right if e["kind"]=="SCALE" else left+right,
        "final_unit_count":result,
        "physical_rule":("REPLICATE_EQUAL_GROUP_WITH_SOURCE_CONTINUITY"
                         if e["kind"]=="SCALE" else
                         "REPOSITION_ORIGINAL_DISJOINT_UNITS_NO_CLONING"),
        "host_verified":True, "claim_id":e["claim_id"],"output_id":e["id"],
        "unit_type":"equal_area_geometric_tiles",
    }


def receipts(trace):
    events=trace.get("events")
    check(isinstance(events,list) and len(events)>=2,"MISSING_NATIVE_BEATS")
    result=[certify_event(e) for e in events]
    check(all(x["host_verified"] for x in result),"UNIT_PROOF_FAILURE")
    return result


def _source_tile(group, index, center_x, count):
    """Generate source unit tokens positioned in a bounded left/right well."""
    col=index%8
    row=index//8
    x=center_x+(col-(min(count,8)-1)/2)*PITCH
    y=-.60-row*.43
    return (f"        {group}.add(Square(side_length={TILE},"
            f"stroke_color='#E7E4DC',stroke_width=1.1,"
            f"fill_color={'#42D9CD' if 'left' in group else '#FFAC71'!r},"
            f"fill_opacity=.89).move_to([{x:.5f},{y:.5f},0]))")


def _unit_group_source(i,a,b):
    """Show exact b-unit source, then visually COPY it a times."""
    name=f"seed_{i}"
    lines=[f"        {name} = VGroup()"]
    spacing=min(.38,1.28/b)
    # Source lives in left well; final groups live between -3 and 3.
    for y in range(b):
        pos=-.75+(y-(b-1)/2)*spacing
        lines.append(
            f"        {name}.add(Square(side_length={min(.30,spacing*.77):.6f},"
            "stroke_color='#E7E4DC',stroke_width=1.0,"
            "fill_color='#42D9CD',fill_opacity=.9)"
            f".move_to([-4.15,{pos:.6f},0]))")
    lines.extend([
        f"        repeated_{i} = VGroup()",
        f"        for j in range({a}):",
        f"            repeated_{i}.add({name}.copy().move_to("
        f"[((j-({a}-1)/2)*{spacing:.7f}),-.75,0]))",
        f"        self.play(FadeIn({name}),run_time=.4)",
        f"        self.play(LaggedStart(*[TransformFromCopy({name},g) for g in repeated_{i}],"
        f"lag_ratio=.09),run_time=1.2)",
        f"        self.play(FadeOut({name}),run_time=.4)",
    ])
    return lines, f"repeated_{i}"


def _unit_add_source(i,a,b):
    """Persist all a+b colored tokens while each token moves once."""
    l,r=f"units_left_{i}",f"units_right_{i}"
    lines=[f"        {l}=VGroup()",f"        {r}=VGroup()"]
    for k in range(a):
        lines.append(_source_tile(l,k,LEFT_CENTER,a))
    for k in range(b):
        lines.append(_source_tile(r,k,RIGHT_CENTER,b))
    lines.extend([
        f"        self.play(FadeIn({l}),FadeIn({r}),run_time=.4)",
        f"        merged_{i} = list({l}) + list({r})",
        f"        self.play(*[unit.animate.move_to("
        f"[(idx%12-({a+b}-1 if {a+b}<12 else 11)/2)*.43,"
        f"-.65-(idx//12)*.48,0]) for idx,unit in enumerate(merged_{i})],run_time=1.2)",
        "        self.wait(.4)",
    ])
    return lines, f"{l},{r}"


def emit_beat(i,e,duration):
    """Called after heading and arrow reveal. Exact total = duration."""
    evidence=certify_event(e)
    a,b=evidence["inputs"]
    check(type(duration) is float and duration>=6.5,"INSUFFICIENT_SPEECH_BUDGET")
    if evidence["operator"] == "SCALE":
        middle,objects=_unit_group_source(i,a,b)
    else:
        middle,objects=_unit_add_source(i,a,b)
    # Intro already takes .8+.6; tile work .4+1.2+.4 =2.0;
    # result reveal .6, emphasis .6, fadeout .6 -> total 5.2 sec.
    remaining=duration-5.2
    lines=[
        f"        # V383_UNIT_WITNESS_STEP_{i}:{evidence['operator']} "
        f"inputs={a},{b} output={evidence['result_units']}",
        *middle,
        f"        self.play(Write(answer_{i}),run_time=.6)",
        f"        self.play(Indicate(answer_{i},color='#F0D969',scale_factor=1.025),run_time=.6)",
        f"        self.wait({remaining:.8f})",
        f"        self.play(FadeOut(heading_{i}),FadeOut(left_{i}),"
        f"FadeOut(right_{i}),FadeOut(arrow_{i}),"
        f"FadeOut(answer_{i}),"
        + ",".join(f"FadeOut({name})" for name in objects.split(",")) +
        ",run_time=.6)",
    ]
    return lines
