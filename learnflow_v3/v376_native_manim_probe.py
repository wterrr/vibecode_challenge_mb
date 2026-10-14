"""V3-76 host-only Manim runtime instrumentation for ACTUAL compiled creative scenes.

Manim (in Docker) reports bounding boxes of actual CMU glyph mobjects after
animations update. The recorder does not trust source Pillow proxies.
No provider-authored Python, no network/secret mount, no visual overlay.

A sample is a Manim update tick and uses construct-time Manim glyph bounds with a conservative Indicate envelope. It is NOT exact frame-varying geometry or automatically an encoded frame.
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
        "        _v376_fp=_v376_out.open('w',encoding='utf-8')",
        "        _V376Path('/output/v376_probe_initialized.marker').write_text('READY')",
        "        _v376_objects = [",
    ]
    for identity,role,var,parent in names:
        entry.append(f"            ({identity!r},{role!r},{var},{parent!r}),")
    entry += [
        "        ]",
        "        _v376_serial=[0]",
        "        def _v376_stage(label):",
        "            if _v376_serial[0]==0:",
        "                _V376Path('/output/v376_stage_'+label+'.marker').write_text('REACHED')",
        "        # R1: actual CMU geometry is measured ONCE at construct time.",
        "        # The bounded compiler allows FadeIn/Connect/Indicate only.",
        "        # This does NOT certify time-varying Manim glyph geometry.",
        "        _v376_bbox_cache={}",
        "        _v376_glyph_color_cache={}",
        "        for _cache_name,_cache_role,_cache_obj,_cache_parent in _v376_objects:",
        "            if _cache_name=='chrome_brand':",
        "                _V376Path('/output/v376_stage_before_precache_bbox.marker').write_text('REACHED')",
        "            # Manim Community 0.19.0 supports get_left/right/top/bottom;",
        "            # get_bounding_box() belongs to a DIFFERENT Manim API.",
        "            _cache_x0=float(_cache_obj.get_left()[0])",
        "            _cache_x1=float(_cache_obj.get_right()[0])",
        "            _cache_y0=float(_cache_obj.get_bottom()[1])",
        "            _cache_y1=float(_cache_obj.get_top()[1])",
        "            if not all(_v376math.isfinite(v) for v in",
        "                       (_cache_x0,_cache_x1,_cache_y0,_cache_y1)):",
        "                raise RuntimeError('V376_NONFINITE_MANIM_EXTENTS')",
        "            if _cache_x1<=_cache_x0 or _cache_y1<=_cache_y0:",
        "                raise RuntimeError('V376_DEGENERATE_MANIM_EXTENTS')",
        "            # Reserve Indicate(scale_factor=1.07) intermediate extent.",
        "            _cache_cx=(_cache_x0+_cache_x1)/2",
        "            _cache_cy=(_cache_y0+_cache_y1)/2",
        "            _cache_w=(_cache_x1-_cache_x0)*1.07/2",
        "            _cache_h=(_cache_y1-_cache_y0)*1.07/2",
        "            _v376_bbox_cache[_cache_name]=(",
        "                _cache_cx-_cache_w,_cache_cy-_cache_h,",
        "                _cache_cx+_cache_w,_cache_cy+_cache_h)",
        "            if _cache_role=='text':",
        "                _cache_candidates=set()",
        "                for _glyph in _cache_obj.get_family():",
        "                    if _glyph is _cache_obj or _glyph.submobjects:continue",
        "                    if not hasattr(_glyph,'get_fill_color'):continue",
        "                    if not hasattr(_glyph,'get_points') or len(_glyph.get_points())==0:continue",
        "                    if float(_glyph.get_fill_opacity())<=.01:continue",
        "                    _glyph_rgb=tuple(round(float(v),6) for v in",
        "                                     _glyph.get_fill_color().to_rgb())",
        "                    if len(_glyph_rgb)!=3 or not all(_v376math.isfinite(v)",
        "                             and 0<=v<=1 for v in _glyph_rgb):",
        "                        raise RuntimeError('V376_INVALID_GLYPH_FILL_RGB')",
        "                    _cache_candidates.add(_glyph_rgb)",
        "                if not _cache_candidates:",
        "                    raise RuntimeError('V376_NO_EFFECTIVE_SVG_GLYPH_COLOR')",
        "                _v376_glyph_color_cache[_cache_name]=sorted(_cache_candidates)",
        "            else:",
        "                _v376_glyph_color_cache[_cache_name]=[tuple(float(v) for v",
        "                    in _cache_obj.get_color().to_rgb())]",
        "            if _cache_name=='chrome_brand':",
        "                _V376Path('/output/v376_stage_after_precache_bbox.marker').write_text('REACHED')",
        "        def _v376_capture(dt):",
        "            _v376_stage('entered')",
        "            if _v376_serial[0]==0:",
        "                _V376Path('/output/v376_probe_first_tick.marker').write_text('ENTERED')",
        "            # Manim Text has thousands of leaf glyph points; never",
        "            # recursively enumerate full Scene family inside a per-frame",
        "            # observer. Named compiler groups own registered labels as",
        "            # DIRECT children, so a one-level set is complete in scope.",
        "            _v376_stage('before_membership')",
        "            _v376_roots=tuple(self.mobjects)",
        "            _v376_family={id(o) for o in _v376_roots}",
        "            for _root in _v376_roots:",
        "                _v376_family.update(id(o) for o in _root.submobjects)",
        "            _v376_stage('after_membership')",
        "            _v376_rows=[]",
        "            _v376_first_record=[False]",
        "            for name,role,obj,parent in _v376_objects:",
        "                if id(obj) not in _v376_family: continue",
        "                if not _v376_first_record[0]:_v376_stage('before_bbox')",
        "                # No get_bounding_box() within a live Manim updater:",
        "                # measured precache coordinates, explicit non-dynamic scope.",
        "                _v376_bounds=_v376_bbox_cache.get(name)",
        "                if _v376_bounds is None:raise RuntimeError('V376_UNCACHED_OBJECT')",
        "                if not _v376_first_record[0]:_v376_stage('after_bbox')",
        "                x0,y0,x1,y1=_v376_bounds",
        "                # Actual Manim camera coordinates -> 1280x720 pixels.",
        "                box=[(x0+config.frame_width/2)*1280/config.frame_width,",
        "                     (config.frame_height/2-y1)*720/config.frame_height,",
        "                     (x1+config.frame_width/2)*1280/config.frame_width,",
        "                     (config.frame_height/2-y0)*720/config.frame_height]",
        "                if not _v376_first_record[0]:_v376_stage('before_color')",
        "                # Root Text.get_color() may be BLACK despite visible",
        "                # CMU SVG children having bright fill. Take actual",
        "                # constructed leaf SVG fill colors, never parent RGB.",
        "                glyph_rgbs=_v376_glyph_color_cache.get(name)",
        "                if not glyph_rgbs:raise RuntimeError('V376_MISSING_GLYPH_COLOR_CACHE')",
        "                color=list(glyph_rgbs[0])",
        "                if not _v376_first_record[0]:_v376_stage('after_color')",
        "                if not _v376_first_record[0]:_v376_stage('before_opacity')",
        "                opacity=float(obj.get_fill_opacity())",
        "                if not _v376_first_record[0]:_v376_stage('after_opacity')",
        "                _v376_first_record[0]=True",
        "                _v376_rows.append({'id':name,'role':role,'bbox_px':box,",
        "                                   'rgb':color,'glyph_rgbs':glyph_rgbs,",
        "                                   'color_source':'CONSTRUCT_TIME_SVG_LEAF_FILL',",
        "                                   'opacity':opacity,'parent':parent})",
        "            row={'seq':_v376_serial[0],",
        "                 'scene_time_s':float(getattr(self,'time',0.)),",
        "                 'dt':float(dt),'objects':_v376_rows}",
        "            _v376_stage('before_serialize')",
        "            _v376_line=_v376json.dumps(row,separators=(',',':'))+'\\n'",
        "            _v376_stage('after_serialize')",
        "            _v376_fp.write(_v376_line)",
        "            _v376_stage('after_write')",
        "            if _v376_serial[0]%15==0:_v376_fp.flush()",
        "            _v376_stage('after_flush')",
        "            _v376_serial[0]+=1",
        "        _v376_monitor=VMobject()",
        "        _v376_monitor.add_updater(lambda mob,dt:_v376_capture(dt),call_updater=False)",
        "        self.add(_v376_monitor)",
    ]
    inject="\n".join(entry)+"\n"
    # do not rely on imported pathlib inside trusted core compiler.
    compiled=source.replace("from manim import *\n",
        "from manim import *\nimport json as _v376json\nimport math as _v376math\nfrom pathlib import Path as _V376Path\n",1)
    compiled=compiled.replace(MARKER,inject+MARKER,1)
    if compiled==source or compiled.count("V3-76 HOST INJECTED")!=1:
        raise Blocked("V376_RUNTIME_INSTRUMENTATION_NOT_APPLIED")
    compile(compiled,"<v376-trusted-host-instrumented-manim>","exec")
    return compiled
