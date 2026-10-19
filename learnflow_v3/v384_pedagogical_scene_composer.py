"""V3-84 opt-in spatial scene composition from exact V3-83 unit certificates.

This is a bounded host storyboard grammar (SCALE, ADD), not a free-form
model agent, general scientific causal proof, or expert pedagogical acceptance.
Every visible count is derived from V3-81 exact arithmetic; no topic ID dispatch.
"""
from __future__ import annotations
import math
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.v383_semantic_unit_storytelling import certify_event

PALETTE = {"cyan":"#42D9CD","orange":"#FFAC71","ink":"#F4F1E8",
           "muted":"#9CA6B8","gold":"#F0D969","blue":"#82B5FF"}
UNIT_SIDE = .355
UNIT_STEP = .455
GROUP_GAP = .24
BOARD_Y = -.43
ADD_LEFT_X = -3.08
ADD_RIGHT_X = 3.08
RESULT_Y = -2.65


def require(ok, reason):
    if not ok:
        raise Blocked("V384_"+reason)


def _bounded_points(n, *, center_x, center_y, columns=8, cell_step=UNIT_STEP):
    require(type(n) is int and 1<=n<=24,"INVALID_UNIT_COUNT")
    cols=min(n,columns)
    return [(round(center_x+(k%cols-(cols-1)/2)*cell_step,5),
             round(center_y-(k//cols)*cell_step,5)) for k in range(n)]


def layout_event(event):
    proof=certify_event(event)
    a,b=proof["inputs"]
    operator=proof["operator"]
    if operator=="SCALE":
        columns=min(b,3)
        rows=math.ceil(b/columns)
        group_w=columns*UNIT_STEP+.21
        group_h=rows*UNIT_STEP+.21
        grid_cols=min(a,6)
        grid_rows=math.ceil(a/grid_cols)
        width=grid_cols*group_w+(grid_cols-1)*GROUP_GAP
        height=grid_rows*group_h+(grid_rows-1)*GROUP_GAP
        require(width<=10.4 and height<=2.65,"STORY_GROUPS_OVERFLOW_BOARD")
        centers=[]
        for idx in range(a):
            cx=(idx%grid_cols-(grid_cols-1)/2)*(group_w+GROUP_GAP)
            cy=BOARD_Y+(grid_rows-1)/2*(group_h+GROUP_GAP)-(idx//grid_cols)*(group_h+GROUP_GAP)
            centers.append((round(cx,5),round(cy,5)))
        unit_offsets=_bounded_points(b,center_x=0,center_y=(rows-1)*UNIT_STEP/2,columns=columns)
        require(len(centers)==a and len(unit_offsets)==b,"GROUP_IDENTITY_COUNT")
        targets=[(round(cx+ux,5),round(cy+uy,5))
                 for cx,cy in centers for ux,uy in unit_offsets]
        name=f"{a} EQUAL GROUPS · {b} EACH"
        geometry={"operator":operator,"count":a*b,"group_centers":centers,
                  "unit_offsets":unit_offsets,"unit_targets":targets,
                  "group_width":round(group_w,5),"group_height":round(group_h,5),
                  "guide":name,"source_counts":[a,b]}
    else:
        left=_bounded_points(a,center_x=ADD_LEFT_X,center_y=-.20,columns=6)
        right=_bounded_points(b,center_x=ADD_RIGHT_X,center_y=-.20,columns=6)
        final=_bounded_points(a+b,center_x=0,center_y=-.35,columns=8,cell_step=.58)
        require(len(left)+len(right)==len(final),"ADDITION_OBJECT_CONTINUITY")
        geometry={"operator":operator,"count":a+b,"source_left":left,
                  "source_right":right,"unit_targets":final,
                  "guide":f"{a} PIECES  +  {b} PIECES","source_counts":[a,b]}
    for x,y in geometry["unit_targets"]:
        require(-5.3 <= x <= 5.3 and -1.91<=y<=.75,
                "VISUAL_UNIT_OUTSIDE_SAFE_BOARD")
    # Header y 2.27 / 1.41; drawing y <= .75; equation y -2.65.
    # At physical radius .18, vertical clearance from nearest other zone:
    # from explanatory caption baseline y 1.41: >= .48 world units;
    # from result text baseline -2.65: >= .56 world units.
    require(max(y for x,y in geometry["unit_targets"])+UNIT_SIDE/2 <= .94,
            "STORYBOARD_COLLIDES_WITH_EXPLANATION")
    require(min(y for x,y in geometry["unit_targets"])-UNIT_SIDE/2 >= -2.12,
            "STORYBOARD_COLLIDES_WITH_ANSWER")
    geometry["host_verification"]=proof
    geometry["layout"]="STAGED_GROUPS_WITH_CAUSAL_CONTINUITY"
    return geometry


def plan(trace):
    events=trace.get("events")
    require(isinstance(events,list) and 2<=len(events)<=8,"INVALID_STORY_EVENT_COUNT")
    result=[layout_event(event) for event in events]
    require(len(result)==len(events),"NARRATION_VISUAL_PLAN_DRIFT")
    return result


def _str(x):
    return repr(x)


def _tile_at(name,pos,color):
    x,y=pos
    return (f"        {name} = Square(side_length={UNIT_SIDE},"
            f"stroke_width=1.2,stroke_color={_str(PALETTE['ink'])},"
            f"fill_color={_str(color)},fill_opacity=.94)"
            f".move_to([{x:.5f},{y:.5f},0])")


def _scale_animation(i,geom):
    a,b=geom["source_counts"]
    offsets=geom["unit_offsets"]
    seedpts=[(-4.80+x,-.43+y) for x,y in offsets]
    lines=[f"        seed_{i}=VGroup()"]
    for k,p in enumerate(seedpts):
        lines.append(_tile_at(f"seed_piece_{i}_{k}",p,PALETTE["cyan"]))
        lines.append(f"        seed_{i}.add(seed_piece_{i}_{k})")
    lines.extend([
        f"        self.play(FadeIn(seed_{i},shift=UP*.12),run_time=8/15)",
        f"        group_frames_{i}=VGroup()",
        f"        target_groups_{i}=VGroup()",
    ])
    for k,(cx,cy) in enumerate(geom["group_centers"]):
        lines.extend([
            f"        group_frame_{i}_{k}=RoundedRectangle("
            f"width={geom['group_width']+.07:.5f},height={geom['group_height']+.07:.5f},"
            f"corner_radius=.12,stroke_color={_str(PALETTE['blue'])},"
            "stroke_width=1.5,fill_opacity=.035)"
            f".move_to([{cx:.5f},{cy:.5f},0])",
            f"        group_frames_{i}.add(group_frame_{i}_{k})",
            f"        target_groups_{i}.add(seed_{i}.copy().move_to([{cx:.5f},{cy:.5f},0]))",
        ])
    # Source unit-relative ordering and count are identical in every clone.
    lines.extend([
        f"        self.play(LaggedStart(*[TransformFromCopy(seed_{i},g) "
        f"for g in target_groups_{i}],lag_ratio=.12),run_time=26/15)",
        f"        self.play(FadeIn(group_frames_{i}),FadeOut(seed_{i}),run_time=7/15)",
    ])
    return lines,[f"target_groups_{i}",f"group_frames_{i}"]


def _add_animation(i,geom):
    a,b=geom["source_counts"]
    left=f"left_collection_{i}"
    right=f"right_collection_{i}"
    lines=[f"        {left}=VGroup()",f"        {right}=VGroup()"]
    for k,p in enumerate(geom["source_left"]):
        lines.append(_tile_at(f"left_piece_{i}_{k}",p,PALETTE["cyan"]))
        lines.append(f"        {left}.add(left_piece_{i}_{k})")
    for k,p in enumerate(geom["source_right"]):
        lines.append(_tile_at(f"right_piece_{i}_{k}",p,PALETTE["orange"]))
        lines.append(f"        {right}.add(right_piece_{i}_{k})")
    lines.extend([
        f"        self.play(FadeIn({left},shift=UP*.1),"
        f"FadeIn({right},shift=UP*.1),run_time=8/15)",
        f"        moving_{i}=list({left})+list({right})",
        f"        merged_target_{i}={geom['unit_targets']!r}",
        f"        self.play(*[piece.animate.move_to([loc[0],loc[1],0]) "
        f"for piece,loc in zip(moving_{i},merged_target_{i},strict=True)],run_time=26/15)",
        f"        self.play(Circumscribe(VGroup({left},{right}),"
        f"color={_str(PALETTE['gold'])},run_time=7/15))",
    ])
    return lines,[left,right]


def emit_step(i,event,duration,total):
    """Finite native code, one visually continuous stage with fixed timing."""
    geom=layout_event(event)
    require(type(duration) is float and 7<=duration<=30,"INSUFFICIENT_SPEECH_WINDOW")
    a,b=geom["source_counts"]
    label="BUILD EQUAL GROUPS" if geom["operator"]=="SCALE" else "COMBINE WITHOUT LOSING PIECES"
    lines=[
        f"        # V384_COMPOSITION_STAGE_{i}:{geom['operator']} unit_count={geom['count']}",
        f"        step_badge_{i}=Text({f'STEP {i+1} OF {total}'!r},font='CMU Serif',"
        f"font_size=23,color={_str(PALETTE['gold'])}).move_to([-5.12,2.22,0])",
        f"        step_label_{i}=Text({_str(label)},font='CMU Serif',"
        f"font_size=28,color={_str(PALETTE['blue'])}).move_to([.75,2.22,0])",
        f"        operands_{i}=Text({_str(geom['guide'])},font='CMU Serif',"
        f"font_size=30,color={_str(PALETTE['ink'])}).move_to([0,1.42,0])",
        f"        if operands_{i}.width > 10.0: operands_{i}.scale_to_fit_width(10.0)",
        f"        rule_{i}=Line([-5.35,1.00,0],[5.35,1.00,0],"
        f"stroke_width=1.5,color={_str(PALETTE['muted'])})",
        f"        answer_{i}=Text({_str(event['result_text'])},font='CMU Serif',"
        f"font_size=40,color={_str(PALETTE['ink'])}).move_to([0,{RESULT_Y:.5f},0])",
        f"        if answer_{i}.width > 8.6: answer_{i}.scale_to_fit_width(8.6)",
        f"        self.play(FadeIn(step_badge_{i}),FadeIn(step_label_{i}),run_time=8/15)",
        f"        self.play(FadeIn(operands_{i}),run_time=8/15)",
        f"        self.play(Create(rule_{i}),run_time=5/15)",
    ]
    if geom["operator"]=="SCALE":
        middle,objects=_scale_animation(i,geom)
    else:
        middle,objects=_add_animation(i,geom)
    # All 9 animation phases use integer-frame durations at 15 fps.
    # Previously Manim ceil-rounded each fractional .50/.55/.35/... play
    # independently: observed native 479 frames vs 468 exact WAV frames.
    # Fixed visual phases: 8+8+5+8+26+7+10+5+9 = 86 frames per beat.
    # Allocate every remaining speech frame to a single exact-frame hold.
    exact_frames=int(round(duration*15))
    fixed_frames=86
    require(exact_frames>=fixed_frames+12,"NO_EXACT_FRAME_HOLD_BUDGET")
    hold_frames=exact_frames-fixed_frames
    lines.extend(middle)
    lines.extend([
        f"        self.play(Write(answer_{i}),run_time=10/15)",
        f"        self.play(Indicate(answer_{i},color={_str(PALETTE['gold'])},"
        f"scale_factor=1.04),run_time=5/15)",
        f"        self.wait({hold_frames}/15)",
        f"        self.play(FadeOut(step_badge_{i}),FadeOut(step_label_{i}),"
        f"FadeOut(operands_{i}),FadeOut(rule_{i}),FadeOut(answer_{i}),"
        +",".join(f"FadeOut({item})" for item in objects)+
        ",run_time=9/15)",
    ])
    return lines
