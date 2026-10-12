"""V3-46 shared, host-owned visual quality tokens and bounded layout rules.

This module intentionally contains no topic-ID lookups or LLM execution.
It is opt-in; older V3-44/V3-45 compilers keep their exact frozen output by
default. It produces Manim-source statements only from vetted enum families
and host-validated bounded strings. Nothing here claims student learning gain.
"""
from __future__ import annotations
from dataclasses import dataclass

from learnflow_v3.creative_manim_ablation import Blocked

BG="#080B11"
HAIRLINE="#364351"
MUTED="#92A8B6"
ACCENT="#E9B766"
PANEL="#101B26"
BODY="#E8ECF0"
PROCESS_COLOR="#73CAD2"
SAFE_HORIZONTAL=6.35
SAFE_VERTICAL=3.45
FOOTER_Y=-3.42
EYEBROW_Y=3.39
HEADER_LINE_Y=3.16
CARD_HEIGHT=3.0
CARD_WIDTH=3.25

FAMILY_TEXT={
 "fraction_equivalence":("MATHEMATICS","EQUIVALENCE"),
 "ordered_process":("COMPUTER SCIENCE","PROCEDURE")
}
BEAT_NAMES={
 "fraction_equivalence":("WHOLE","PARTS","PROOF","RECAP"),
 "ordered_process":("START","CHECK","ARRIVE","RECAP")
}

def frame_lines(family:str)->list[str]:
    """Create consistent visual chrome that stays out of content rectangles.

    Computer Modern caption typography and ultra-subtle academic accent
    marks define a shared hierarchy rather than two bespoke scenes.
    """
    if family not in FAMILY_TEXT:
        raise Blocked("V346_UNSUPPORTED_VISUAL_FAMILY")
    subject,topic=FAMILY_TEXT[family]
    return [
      "        # V346 SHARED_VISUAL_SYSTEM: screen-safe consistent chrome",
      f"        self.camera.background_color = {BG!r}",
      f"        v346_eyebrow = Text({('LEARNFLOW  /  '+subject)!r},font='CMU Serif',"
      f"font_size=15,color={MUTED!r}).move_to([-4.65,{EYEBROW_Y:.3f},0])",
      f"        v346_section = Text({topic!r},font='CMU Serif',font_size=15,"
      f"color={ACCENT!r}).move_to([5.13,{EYEBROW_Y:.3f},0])",
      f"        v346_rule = Line([-{SAFE_HORIZONTAL:.2f},{HEADER_LINE_Y:.3f},0],"
      f"[{SAFE_HORIZONTAL:.2f},{HEADER_LINE_Y:.3f},0],"
      f"stroke_width=.85,color={HAIRLINE!r})",
      f"        v346_footrule = Line([-{SAFE_HORIZONTAL:.2f},-3.22,0],"
      f"[{SAFE_HORIZONTAL:.2f},-3.22,0],"
      f"stroke_width=.7,color={HAIRLINE!r})",
      "        self.add(v346_eyebrow,v346_section,v346_rule,v346_footrule)",
      "        v346_beats = VGroup()",
      "        v346_labels = VGroup()",
      *[
        f"        v346_beats.add(Circle(radius=.045,color={ACCENT!r} if {i}==0 "
        f"else {HAIRLINE!r},fill_opacity=1).move_to([{-1.55+i*1.03:.2f},{FOOTER_Y:.2f},0]))"
        for i in range(4)
      ],
      # In particular, only the dots are visible: small labels lower than
      # -3.45 would violate the registered safe-area contract.
      "        self.add(v346_beats)",
    ]

def beat_focus_lines(index:int)->list[str]:
    if index not in range(4):
        raise Blocked("V346_INVALID_BEAT_INDEX")
    return [
       f"        v346_beats[{index}].set_fill({ACCENT!r},opacity=1)",
       f"        v346_beats[{index}].set_stroke({ACCENT!r},width=1.2)",
    ]

def panel_lines(centres:list[float])->list[str]:
    """Three-dimensional style depth stays behind source semantics."""
    if len(centres)!=2 or any(abs(v)>4.45 for v in centres):
        raise Blocked("V346_FRACTION_PANEL_OUT_OF_SAFE_AREA")
    lines=[]
    for i,x in enumerate(centres):
        lines.append(
          f"        v346_panel_{i} = RoundedRectangle(width={CARD_WIDTH:.2f},"
          f"height={CARD_HEIGHT:.2f},corner_radius=.15,"
          f"stroke_width=1,stroke_color={HAIRLINE!r},"
          f"fill_color={PANEL!r},fill_opacity=.45)"
          f".move_to([{x:.3f},.08,0]).set_z_index(-10)"
        )
    lines.append("        self.add(v346_panel_0,v346_panel_1)")
    return lines

def text_style_lines(ident:str,kind:str,text:str,x:float,y:float,
                     rgb:str,width:float)->str:
    if kind not in ("title","label","node_caption") or not (.5<=width<=7):
        raise Blocked("V346_TEXT_STYLE_NOT_SUPPORTED")
    font_size={"title":39,"label":29,"node_caption":26}[kind]
    # Never force text width larger than its natural width; strict max bound
    # shrinks long terms with size & height guard instead of overflowing.
    return (
      f"        {ident} = Text({text!r},font='CMU Serif',"
      f"font_size={font_size},color={rgb!r})"
      f".scale_to_fit_width(min({width:.2f},"
      f"max(.48,len({text!r})*.225)))"
      f".move_to([{x:.3f},{y:.3f},0]).set_z_index(2)"
    )

def caption_max_width(node_width:float)->float:
    # 0.24 units from each boundary; fails closed on impossible width.
    result=node_width-.48
    if result<.52:
        raise Blocked("V346_CAPTION_WIDTH_INSUFFICIENT")
    return round(result,3)

def safe_rectangles(family:str,graphics:list)->dict:
    """Finite pre-render text bounds from authored centres and font budget.

    This is NOT a pixel OCR/text-measurement gate; frame-based diagnostics
    independently measure actual occupied visual region after rendering.
    """
    if family not in FAMILY_TEXT:
        raise Blocked("V346_UNKNOWN_FAMILY")
    issues=[]
    bounds=[]
    for o in graphics:
        if o.kind not in ("label","node"):
            continue
        caption=(o.kind=="node")
        w=caption_max_width(o.width) if caption else min(6.5,max(.8,len(o.text)*.215))
        height=.50 if caption else .65
        bounds.append({"id":o.id,"x":o.x,"y":o.y,"width_budget":w,"height_budget":height})
        if abs(o.x)+w/2 > SAFE_HORIZONTAL or abs(o.y)+height/2>2.95:
            issues.append(o.id)
    if issues:
        raise Blocked("V346_TEXT_OUTSIDE_SAFE_CONTENT_RECT:" + ",".join(issues))
    return {"bounds":bounds,"safe_area_pass":True}

def style_receipt()->dict:
    return {
     "version":"v3-46-shared-opt-in-v1",
     "font":"CMU Serif",
     "background":BG,
     "header_rule":HEADER_LINE_Y,
     "eyebrow_y":EYEBROW_Y,
     "footer_y":FOOTER_Y,
     "content_safe_x":SAFE_HORIZONTAL,
     "content_safe_y":2.95,
     "node_caption_inside_inset":.24,
     "families":list(FAMILY_TEXT),
     "provenance":"HOST_OWNED_VISUAL_SYSTEM_NO_PROVIDER_AUTHORED_CODE"
    }
