"""V3-86 compile six host-verified speech phases into exact-frame Manim actions.

No imagined ASR word starts. The alignment unit is one independently
synthesized WAV utterance; its exact frames own one visual decision. A plot
marker always traces a graph state and never physical object displacement.
"""
from __future__ import annotations
from learnflow_v3.v385_affine_visual_semantics import (
    COLOR,X_ZERO,X_FINAL,Y_ZERO,Y_FULL,FPS,_text,need
)
from learnflow_v3.v386_pedagogical_speech_contract import PHASES


def _segment_lines(i,phase,seconds,role):
    need(phase["phase_kind"]==PHASES[phase["phase_index"]] and
         phase["claim_id"]==role["claim_ids"][i],
         "V386_UNGROUNDED_SCRIPT_SEGMENT")
    v=role["verified_values"];p=role["points"]
    start=p["origin"] if i==0 else p["initial"]
    end=p["rate_end"] if i==0 else p["final"]
    ax,ay=start;bx,by=end
    phase_kind=phase["phase_kind"]
    count=round(seconds*FPS)
    need(type(seconds) is float and count>=60,
         "V386_INSUFFICIENT_VOICED_SEMANTIC_PHASE_FRAMES")
    prefix=f"v386_{i}_"
    if i==0:
        tag="WHY THE SLOPE MATTERS"
        formula=f"{v['rate']} × {v['independent']} = {v['change']}"
        label=f"change = {v['change']}"
    else:
        tag="WHAT THE INITIAL VALUE CHANGES"
        formula=f"{v['initial']} + {v['change']} = {v['final']}"
        label=f"final value = {v['final']}"
    if phase_kind=="ORIENT":
        # 4 * 8 = 32 exact frames.
        fixed=32
        lines=[
            f"        # V386_GROUNDED_AUDIO_PHASE_{i}_ORIENT claim={phase['claim_id']}",
            _text(prefix+"step",f"STEP {i+1} OF 2 · {tag}",[0,2.27],26,COLOR["blue"],11.5),
            _text(prefix+"context",role["horizontal_label"]+" → "+role["vertical_label"],[0,1.52],27,COLOR["ink"],10.7),
            f"        {prefix}axis_x=Arrow([{X_ZERO},{Y_ZERO},0],[{X_FINAL+.75:.5f},{Y_ZERO},0],buff=0,stroke_width=3.2,color={COLOR['axis']!r})",
            f"        {prefix}axis_y=Arrow([{X_ZERO},{Y_ZERO},0],[{X_ZERO},{Y_FULL+.38:.5f},0],buff=0,stroke_width=3.2,color={COLOR['axis']!r})",
            _text(prefix+"x_label",role["horizontal_label"],[X_FINAL+.32,Y_ZERO-.48],22,COLOR["muted"],3.1),
            _text(prefix+"y_label",role["vertical_label"],[X_ZERO+.50,Y_FULL+.41],22,COLOR["muted"],3.5),
            f"        {prefix}marker=Dot([{ax},{ay},0],radius=.10,color={COLOR['start']!r})",
            f"        self.play(FadeIn({prefix}step),run_time=8/15)",
            f"        self.play(FadeIn({prefix}context),run_time=8/15)",
            f"        self.play(Create({prefix}axis_x),Create({prefix}axis_y),run_time=8/15)",
            f"        self.play(FadeIn({prefix}x_label),FadeIn({prefix}y_label),run_time=8/15)",
            f"        self.add({prefix}marker)",
        ]
    elif phase_kind=="TRANSFORM":
        # Draw graph, let marker move with semantic source; rise follows the
        # completed curve. 26+7+8 = 41 physical video frames.
        fixed=41
        lines=[
            f"        # V386_GROUNDED_AUDIO_PHASE_{i}_TRANSFORM claim={phase['claim_id']}",
            f"        {prefix}curve=Line([{ax},{ay},0],[{bx},{by},0],color={COLOR['line']!r},stroke_width=7)",
            f"        {prefix}base=DashedLine([{ax},{ay},0],[{bx},{ay},0],dash_length=.12,color={COLOR['muted']!r},stroke_width=2.2)",
            f"        {prefix}rise=DashedLine([{bx},{ay},0],[{bx},{by},0],dash_length=.12,color={COLOR['rise']!r},stroke_width=3)",
            _text(prefix+"rise_text",label,[3.70,.45],24,COLOR["rise"],3.0),
            f"        self.play(Create({prefix}curve),MoveAlongPath({prefix}marker,{prefix}curve),run_time=26/15)",
            f"        self.play(Create({prefix}base),Create({prefix}rise),run_time=7/15)",
            f"        self.play(FadeIn({prefix}rise_text),run_time=8/15)",
        ]
    else:
        # Interpret only after graph and slope have been physically shown;
        # keep result visible throughout narration, clear at segment end.
        fixed=24
        lines=[
            f"        # V386_GROUNDED_AUDIO_PHASE_{i}_INTERPRET claim={phase['claim_id']}",
            _text(prefix+"formula",formula,[0,-2.52],38,COLOR["ink"],9.5),
            f"        self.play(Write({prefix}formula),run_time=10/15)",
            f"        self.play(Indicate({prefix}marker,color={COLOR['rise']!r},scale_factor=1.35),run_time=5/15)",
        ]
    need(count>=fixed+12,"V386_SPEECH_SEGMENT_TOO_SHORT_FOR_MEANINGFUL_HOLD")
    lines.append(f"        self.wait({count-fixed}/15)")
    if phase_kind=="INTERPRET":
        lines.append(
            f"        self.play(FadeOut({prefix}step),FadeOut({prefix}context),"
            f"FadeOut({prefix}axis_x),FadeOut({prefix}axis_y),"
            f"FadeOut({prefix}x_label),FadeOut({prefix}y_label),"
            f"FadeOut({prefix}marker),FadeOut({prefix}curve),"
            f"FadeOut({prefix}base),FadeOut({prefix}rise),"
            f"FadeOut({prefix}rise_text),FadeOut({prefix}formula),run_time=9/15)"
        )
    return lines


def finite_source(trace,durations,role,phases):
    need(len(trace["events"])==2 and len(durations)==len(phases)==6,
         "V386_SIX_PHASE_TIMELINE_REQUIRED")
    need([phase["phase_index"] for phase in phases]==[0,1,2,0,1,2],
         "V386_PHASE_ORDER_INCORRECT")
    lines=[
        "# V3-86 finite host-owned semantic narration/visual event compiler",
        "from manim import *",
        "class GeneratedLesson(Scene):",
        "    def construct(self):",
        "        self.camera.background_color='#080b11'",
        _text("v386_title",trace["title"],[0,3.43],27,COLOR["ink"],12.0),
        "        self.add(v386_title)",
    ]
    for j,(segment,duration) in enumerate(zip(phases,durations,strict=True)):
        i=j//3
        need(segment["semantic_beat_index"]==i and
             segment["claim_id"]==trace["events"][i]["claim_id"],
             "V386_CROSS_CLAIM_AUDIO_IN_VISUAL_PHASE")
        lines.extend(_segment_lines(i,segment,duration,role))
    lines.append("        self.wait(2/15)")
    code="\n".join(lines)+"\n"
    for disallowed in ("__import__(", "eval(", "exec(", "subprocess", "os.system"):
        need(disallowed not in code,"V386_GENERATED_UNSAFE_CODE")
    compile(code,"<host-v386-exact-native>",'exec')
    return code
