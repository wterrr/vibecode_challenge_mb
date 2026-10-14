"""V3-76 host-only Manim runtime instrumentation for ACTUAL compiled creative scenes.

Manim (in Docker) reports bounding boxes of actual CMU glyph mobjects after
animations update. The recorder does not trust source Pillow proxies.
No provider-authored Python, no network/secret mount, no visual overlay.

A sample represents a Manim update tick, not automatically an encoded frame.
Downstream MUST independently verify timestamps/count against decoded H264.
"""
from __future__ import annotations

import json
import re

from learnflow_v3.creative_manim_ablation import Blocked

OUTFILE="/output/v376_runtime_geometry.jsonl"
MARKER="        self.play("

def instrument(source:str,story)->str:
    if not isinstance(source,str) or not source.startswith(
            "# V3-51 GENERIC HOST COMPILED SOURCE NEVER MODEL PYTHON\n"):
        raise Blocked("V376_UNTRUSTED_COMPILER_SOURCE")
    if source.count("class GeneratedLesson(Scene):")!=1 or MARKER not in source:
        raise Blocked("V376_MISSING_COMPILER_ACTION_BOUNDARY")
    names=[
        ("chrome_brand","text","brand",""),
        ("chrome_top","text","top",""),
    ]
    for si,scene in enumerate(story.scenes):
        names.append((f"scene_{si}_title","text",f"v351_section_{si}",""))
        for ni,node in enumerate(scene.nodes):
            stem=f"v351_n{si}_{ni}"
            if node.kind=="CHART":
                names.append((f"{scene.id}:{node.id}:bar","shape",stem+"_shape",""))
                names.append((f"{scene.id}:{node.id}:caption","text",stem+"_caption",""))
            elif node.kind=="SHAPE":
                names.append((f"{scene.id}:{node.id}:shape","shape",stem+"_shape",""))
                names.append((f"{scene.id}:{node.id}:label","text",stem+"_label",
                              f"{scene.id}:{node.id}:shape"))
            else:
                names.append((f"{scene.id}:{node.id}:text","text",stem+"_label",""))
    # Each variable is derived from an accepted, bounded Storyboard, and only
    # allows recognized generated internal identifiers (never model Python).
    for _,_,symbol,_ in names:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]{0,80}",symbol):
            raise Blocked("V376_UNSAFE_INSTRUMENTATION_SYMBOL")
        if f"{symbol}=" not in source:
            raise Blocked("V376_UNEXPORTED_RUNTIME_OBJECT:"+symbol)
    entry=[
        "        # V3-76 HOST INJECTED ACTUAL MANIM MOBJECT BBOX PROBE",
        "        _v376_out = _V376Path("+repr(OUTFILE)+")",
        "        _v376_out.write_text('',encoding='utf-8')",
        "        _v376_objects = [",
    ]
    for identity,role,var,parent in names:
        entry.append(f"            ({identity!r},{role!r},{var},{parent!r}),")
    entry += [
        "        ]",
        "        _v376_serial=[0]",
        "        def _v376_capture(dt):",
        "            _v376_family={id(o) for o in self.get_mobject_family_members()}",
        "            _v376_rows=[]",
        "            for name,role,obj,parent in _v376_objects:",
        "                if id(obj) not in _v376_family: continue",
        "                bb=obj.get_bounding_box()",
        "                x0=min(float(v[0]) for v in bb); x1=max(float(v[0]) for v in bb)",
        "                y0=min(float(v[1]) for v in bb); y1=max(float(v[1]) for v in bb)",
        "                # Actual Manim camera coordinates -> 1280x720 pixels.",
        "                box=[(x0+config.frame_width/2)*1280/config.frame_width,",
        "                     (config.frame_height/2-y1)*720/config.frame_height,",
        "                     (x1+config.frame_width/2)*1280/config.frame_width,",
        "                     (config.frame_height/2-y0)*720/config.frame_height]",
        "                color=[float(v) for v in obj.get_color().to_rgb()]",
        "                opacity=float(obj.get_fill_opacity())",
        "                _v376_rows.append({'id':name,'role':role,'bbox_px':box,",
        "                                   'rgb':color,'opacity':opacity,'parent':parent})",
        "            row={'seq':_v376_serial[0],",
        "                 'scene_time_s':float(getattr(self,'time',0.)),",
        "                 'dt':float(dt),'objects':_v376_rows}",
        "            with _v376_out.open('a',encoding='utf-8') as f:",
        "                f.write(_v376json.dumps(row,separators=(',',':'))+'\\n')",
        "            _v376_serial[0]+=1",
        "        _v376_monitor=VMobject()",
        "        _v376_monitor.add_updater(lambda mob,dt:_v376_capture(dt))",
        "        self.add(_v376_monitor)",
    ]
    inject="\n".join(entry)+"\n"
    # do not rely on imported pathlib inside trusted core compiler.
    compiled=source.replace("from manim import *\n",
        "from manim import *\nimport json as _v376json\nfrom pathlib import Path as _V376Path\n",1)
    compiled=compiled.replace(MARKER,inject+MARKER,1)
    if compiled==source or compiled.count("V3-76 HOST INJECTED")!=1:
        raise Blocked("V376_RUNTIME_INSTRUMENTATION_NOT_APPLIED")
    compile(compiled,"<v376-trusted-host-instrumented-manim>","exec")
    return compiled
