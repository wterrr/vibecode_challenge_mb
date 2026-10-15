"""Finite, trusted Manim emission from V3-81 host-attested operator events.

Reuses the pinned V3-34/V3-52 Docker+audio/native pipeline. Never compiles
model-supplied Python; exact rational proofs are recomputed in the interpreter.
Educational quality and full visual collision coverage are not established.
"""
from __future__ import annotations

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.v381_generic_semantic_operators import need, parse_value, fmt


def source(trace: dict, durations: list[float]) -> str:
    events = trace["events"]
    need(len(events) == len(durations) and len(events) >= 2,
         "NARRATION_TIMELINE_DRIFT")
    need(all(type(t) is float and 5 <= t <= 30 for t in durations),
         "AUDIO_BUDGET_OUT_OF_BOUNDS")
    lines = [
        "# V3-81 trusted host-only compiled source, no provider Python",
        "from manim import *",
        "class GeneratedLesson(Scene):",
        "    def construct(self):",
        "        self.camera.background_color = '#080b11'",
        f"        title = Text({trace['title']!r},font='CMU Serif',font_size=30,color='#F4F1E8').scale_to_fit_width(10).to_edge(UP,buff=.38)",
        "        self.add(title)",
    ]
    for i, (event, duration) in enumerate(zip(events, durations, strict=True)):
        op = event["kind"]
        # Both operands and the result are independently host-derived.
        x, y = event["operand_text"]
        result = event["result_text"]
        operator = {"SCALE": "multiply", "ADD": "add",
                    "EQUIVALENT_PARTITION": "subdivide"}[op]
        lines.extend([
            f"        # GROUND_TRUTH_STEP_{i}: {op}",
            f"        heading_{i} = Text({f'Step {i+1} | {operator}'!r},font='CMU Serif',font_size=30,color='#82B5FF').move_to([0,2.00,0])",
            f"        left_{i} = Text({x!r},font='CMU Serif',font_size=25,color='#42D9CD').scale_to_fit_width(5.0).move_to([-3.0,1.06,0])",
            f"        right_{i} = Text({y!r},font='CMU Serif',font_size=25,color='#FFAC71').scale_to_fit_width(5.0).move_to([3.0,1.06,0])",
            f"        arrow_{i} = Arrow([-1.7,.45,0],[1.7,.45,0],buff=0,stroke_width=5,color='#F0D969')",
            f"        answer_{i} = Text({result!r},font='CMU Serif',font_size=34,color='#F4F1E8').scale_to_fit_width(9.0).move_to([0,-1.68,0])",
            f"        self.play(FadeIn(heading_{i}),FadeIn(left_{i}),FadeIn(right_{i}),run_time=.8)",
            f"        self.play(Create(arrow_{i}),run_time=.6)",
        ])
        if op == "EQUIVALENT_PARTITION":
            first = parse_value(event["operands"][0])
            last = parse_value(event["actual"])
            need(first[0] == last[0] == "fraction", "PARTITION_TRACE_WRONG")
            a, b = first[1]
            c, d = last[1]
            for ident, numerator, denominator in (("before", a, b), ("after", c, d)):
                # Uniform cell widths and host-verified shaded proportions;
                # no topic-specific coordinates or image overlay.
                lines.extend([
                    f"        {ident}_{i} = VGroup()",
                    f"        for j in range({denominator}):",
                    f"            cell = Rectangle(width={6.6/denominator:.8f},height=.84,stroke_color='#F4F1E8',stroke_width=1.6,fill_color='#42D9CD',fill_opacity=(.82 if j < {numerator} else .06))",
                    f"            cell.move_to([{(-3.3+3.3/denominator):.8f} + j*{6.6/denominator:.8f},-.13,0])",
                    f"            {ident}_{i}.add(cell)",
                ])
            lines.extend([
                f"        self.play(FadeIn(before_{i}),run_time=.6)",
                f"        self.play(Transform(before_{i},after_{i}),run_time=1.2)",
                f"        self.play(Write(answer_{i}),run_time=.8)",
                f"        self.wait({duration-4.6:.8f})",
                f"        self.play(FadeOut(heading_{i}),FadeOut(left_{i}),FadeOut(right_{i}),FadeOut(arrow_{i}),FadeOut(before_{i}),FadeOut(answer_{i}),run_time=.6)",
            ])
            # Total: .8+.6+.6+1.2+.8+(duration-4.6)+.6 = duration
        else:
            lines.extend([
                f"        self.play(TransformFromCopy(VGroup(left_{i},right_{i}),answer_{i}),run_time=1.2)",
                f"        self.play(Indicate(answer_{i},color='#F0D969',scale_factor=1.05),run_time=.8)",
                f"        self.wait({duration-4.0:.8f})",
                f"        self.play(FadeOut(heading_{i}),FadeOut(left_{i}),FadeOut(right_{i}),FadeOut(arrow_{i}),FadeOut(answer_{i}),run_time=.6)",
            ])
            # Total: .8+.6+1.2+.8+(duration-4.0)+.6 = duration.
    # One physically explicit two-frame end-only pad absorbs Manim's verified
    # <=1-frame action rounding, then exact audio-frame mux trims it.
    # Do not pad every beat: that would shift the narration/event timeline.
    lines.append("        self.wait(2/15)")
    result = "\n".join(lines) + "\n"
    for forbidden in ("__import__(", "eval(", "exec(", "subprocess", "os.system"):
        need(forbidden not in result, "UNSAFE_EMITTED_SOURCE")
    compile(result, "<trusted-host-v381>", "exec")
    return result
