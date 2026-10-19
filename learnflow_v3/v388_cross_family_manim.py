"""V3-88 finite trusted native pedagogy for two non-affine transformation families.

No model-written Python, no topic ID switches, no arbitrary storyboard JSON.
The family selector is a typed, verified action grammar; exact facts and state
originate in independent prior verifiers. Physical objects persist across beats.
"""
from __future__ import annotations
from learnflow_v3.v388_cross_family_planner import compile_case,check

FPS=15
CMU="CMU Serif"
CYAN="#42D9CD"
GOLD="#F0D969"
INK="#F4F1E8"
MUTED="#A2B4C5"
DARK="#303D53"
BG="#080b11"


def _t(name,s,x,y,size=30,color=INK,max_width=11):
    lines=[f"        {name}=Text({s!r},font={CMU!r},font_size={size},color={color!r}).move_to([{x:.4f},{y:.4f},0])"]
    if max_width:
        lines.append(f"        if {name}.width>{max_width}: {name}.scale_to_fit_width({max_width})")
    return lines


def _hold(frames,fixed):
    check(type(frames) is int and frames>=fixed+20,"PCM_SEMANTIC_BEAT_TOO_SHORT")
    return f"        self.wait({frames-fixed}/15)"


def _fraction(plan,frames):
    n,d,nt,dt=plan["ratio"]
    k=plan["subdivision_factor"]
    check(dt==d*k and nt==n*k,"PARTITION_COUNT_CHANGED_AFTER_ORACLE")
    check(len(frames)==3,"FRACTION_NEEDS_THREE_NARRATION_PHASES")
    lines=[
      f"        bar=Rectangle(width=8,height=1.48,stroke_color={INK!r},stroke_width=3,fill_color={DARK!r},fill_opacity=1).move_to([0,.05,0])",
      f"        shade=Rectangle(width={8*n/d:.8f},height=1.44,stroke_width=0,fill_color={CYAN!r},fill_opacity=.95).move_to([{-4+4*n/d:.7f},.05,0])",
      "        source_guides=VGroup()",
    ]
    for j in range(1,d):
        x=-4+8*j/d
        lines.append(f"        source_guides.add(Line([{x:.6f},-.69,0],[{x:.6f},.79,0],stroke_width=4,color={INK!r}))")
    lines+=_t("original",f"FIRST VIEW: {n}/{d} SHADED",0,1.47,32,GOLD)
    lines+=_t("original_desc","ONE WHOLE / EQUAL ORIGINAL PARTS",0,-1.27,27,MUTED)
    lines.extend([
        "        self.play(FadeIn(bar),FadeIn(shade),run_time=10/15)",
        "        self.play(LaggedStart(*[Create(g) for g in source_guides],lag_ratio=.18),run_time=15/15)",
        "        self.play(FadeIn(original),FadeIn(original_desc),run_time=7/15)",
        _hold(frames[0],32),
        "        refined_guides=VGroup()",
    ])
    for j in range(1,dt):
        if j%k==0:continue
        x=-4+8*j/dt
        lines.append(f"        refined_guides.add(Line([{x:.6f},-.69,0],[{x:.6f},.79,0],stroke_width=3.3,color={GOLD!r}))")
    lines+=_t("refined",f"REFINED VIEW: {nt}/{dt} SHADED",0,-1.86,33,GOLD)
    lines.extend([
        "        self.play(LaggedStart(*[Create(g) for g in refined_guides],lag_ratio=.11),run_time=26/15)",
        "        self.play(FadeIn(refined),run_time=10/15)",
        _hold(frames[1],36),
    ])
    lines+=_t("equation",f"{n}/{d} = {nt}/{dt}",0,-2.64,46,INK)
    lines.extend([
        "        self.play(Write(equation),run_time=15/15)",
        "        self.play(Indicate(shade,color='#FFAC71',scale_factor=1.02),run_time=10/15)",
        _hold(frames[2],25),
    ])
    return lines


def _search(plan,frames):
    values=plan["values"]
    events=plan["scripted_semantic_events"]
    check(len(events)==len(frames) and len(values)<=12,
          "SEARCH_VISUAL_STATE_NOT_BOUND_TO_PCM")
    n=len(values)
    pitch=min(1.11,11.4/n)
    lines=["        array=VGroup()"]
    for j,v in enumerate(values):
        x=(j-(n-1)/2)*pitch
        lines.append(f"        square_{j}=RoundedRectangle(width={pitch*.85:.6f},height=.91,corner_radius=.12,stroke_width=2,stroke_color={INK!r},fill_color={DARK!r},fill_opacity=.90).move_to([{x:.6f},-.15,0])")
        lines+=_t(f"label_{j}",str(v),x,-.15,30,INK,max_width=pitch*.68)
        lines.append(f"        cell_{j}=VGroup(square_{j},label_{j})")
        lines.append(f"        array.add(cell_{j})")
    lines.append("        self.add(array)")
    # Preserve exactly ONE active best candidate across the entire trace.
    # A later match at a smaller index supersedes the previously highlighted
    # match, so the final frame cannot suggest two equally valid answers.
    prior_candidate=None
    for i,(e,frames_i) in enumerate(zip(events,frames,strict=True)):
        if e["phase"]=="COMPARE":
            low,mid,high=e["low"],e["mid"],e["high"]
            check(0<=low<=mid<=high<n,"INVALID_PREVALIDATED_SEARCH_BOUNDS")
            check(len(set(e["discard"]))==len(e["discard"]) and
                  all(0<=j<n for j in e["discard"]),
                  "UNSAFE_ELIMINATION_TARGET")
            heading=f"LOW {low}   MID {mid}   HIGH {high}     TARGET {plan['target']}"
            explanation={
                "DISCARD_LEFT":"DISCARD LEFT SIDE; INCREASE LOW",
                "KEEP_LEFT":"DISCARD RIGHT SIDE; DECREASE HIGH",
                "RECORD_CANDIDATE":"SAVE MATCH; SEARCH LEFT FOR AN EARLIER INDEX"
            }[e["action"]]
            lines+=_t(f"bounds_{i}",heading,0,1.57,31,GOLD,11.8)
            lines+=_t(f"reason_{i}",explanation,0,-1.65,27,CYAN,11.5)
            lines.extend([
                f"        self.play(FadeIn(bounds_{i}),run_time=7/15)",
                f"        self.play(Indicate(cell_{mid},color={GOLD!r},scale_factor=1.10),run_time=9/15)",
            ])
            anim=[f"square_{j}.animate.set_fill({DARK!r},opacity=.14).set_stroke({MUTED!r},width=.7)" for j in e["discard"]]
            if e["action"]=="RECORD_CANDIDATE":
                if prior_candidate is not None and prior_candidate!=mid:
                    check(mid<prior_candidate,
                          "LEFTMOST_CANDIDATE_DID_NOT_MOVE_TO_EARLIER_INDEX")
                    anim.append(f"square_{prior_candidate}.animate.set_stroke({MUTED!r},width=1.5)")
                anim.append(f"square_{mid}.animate.set_stroke({GOLD!r},width=5)")
                prior_candidate=mid
            else:
                anim.append(f"square_{mid}.animate.set_stroke({MUTED!r},width=1.5)")
            lines.append("        self.play("+",".join(anim)+",run_time=16/15)")
            lines.extend([
                f"        self.play(FadeIn(reason_{i}),run_time=9/15)",
                _hold(frames_i,48),
                f"        self.play(FadeOut(bounds_{i}),FadeOut(reason_{i}),run_time=7/15)",
            ])
        else:
            check(e["phase"]=="COMPLETE","UNKNOWN_PREVALIDATED_SEARCH_PHASE")
            answer=(f"LEFTMOST INDEX = {e['candidate']}" if e["candidate"] is not None
                    else "TARGET NOT FOUND")
            lines+=_t("search_answer",answer,0,-2.18,43,GOLD,11.5)
            lines.extend([
                "        self.play(Write(search_answer),run_time=15/15)",
                _hold(frames_i,15),
            ])
    return lines


def finite_source(row,plan,durations):
    # A complete revalidation of original prompt and exact evidence happens
    # at the trust boundary, not only once in the orchestration layer.
    fresh=compile_case(row)
    check(fresh["status"]=="SUPPORTED_HOST_ONLY" and fresh["plan"]==plan,
          "TAMPERED_VISUAL_SOURCE_OR_REPLAYED_STORYBOARD")
    beats=plan["scripted_semantic_events"]
    check(len(durations)==len(beats) and
          all(type(t) is float and 5.0<=t<=30 for t in durations),
          "ACTUAL_PCM_BEAT_DURATION_UNSUPPORTED")
    frames=[round(t*FPS) for t in durations]
    lines=[
        "# V3-88 exact host-semantic native renderer, no model-authored source",
        "from manim import *",
        "class GeneratedLesson(Scene):",
        "    def construct(self):",
        f"        self.camera.background_color={BG!r}",
    ]
    if plan["family"]=="FRACTION_EQUIVALENCE":
        headline="WHY SUBDIVISION PRESERVES THE SAME WHOLE"
    elif plan["family"]=="ORDERED_SEARCH":
        headline="BINARY SEARCH: ONLY KEEP POSSIBLE INDICES"
    else:raise ValueError("V388_NO_NATIVE_COMPILER_FOR_FAMILY")
    lines+=_t("title",headline,0,2.63,34,INK,12.0)
    lines.append("        self.add(title)")
    if plan["visual_operator"]=="PARTITION_REFINEMENT":
        lines.extend(_fraction(plan,frames))
    elif plan["visual_operator"]=="ORDERED_ELIMINATION_WITH_CANDIDATE":
        lines.extend(_search(plan,frames))
    else:raise ValueError("V388_UNSUPPORTED_SEMANTIC_OPERATOR")
    lines.append("        self.wait(2/15)")
    source="\n".join(lines)+"\n"
    check(all(q not in source for q in ("__import__(", "eval(", "exec(", "os.system", "subprocess")),
          "UNTRUSTED_PYTHON_IN_TYPED_COMPILER")
    compile(source,"<finite-v388>",'exec')
    return source
