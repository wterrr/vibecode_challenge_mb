"""V3-76R1: fail-closed pinned-Manim first-frame bisection invariants."""
import json
from pathlib import Path
import pytest
from learnflow_v3.creative_manim_ablation import Blocked
from scripts.run_v3_76r1_bounded_manim_probe import PREREG, PARENT_SHA, compile_smoke, SOURCE
from learnflow_v3.v376_native_manim_probe import instrument

ROOT=Path(__file__).resolve().parents[2]

def test_first_child_prereg_locks_failed_evidence_and_bounded_condition():
    r=json.loads(PREREG.read_text())
    assert r["checkpoint"]=="V3-76R1"
    assert r["kind"]=="FIRST_CHILD_PREREG_BEFORE_CODE"
    assert r["parent"]["pr"]==112 and r["parent"]["sha"]==PARENT_SHA
    assert len(r["locked_failures"])==2
    assert [x["artifact"] for x in r["locked_failures"]]==[
        11878370723,11878514832]
    assert r["acceptance"]["smoke"].startswith("actual pinned Docker")
    assert r["boundaries"]["no_model_api"]
    assert r["boundaries"]["production"]=="BLOCKED"

def test_smoke_is_host_only_and_same_instrumented_class():
    source=compile_smoke()
    assert source.startswith("# V3-51 GENERIC HOST COMPILED SOURCE")
    assert "class GeneratedLesson(Scene)" in source
    assert source.count("V3-76 HOST INJECTED ACTUAL MANIM")==1
    assert "_cache_obj.get_left()[0]" in source
    assert "_cache_obj.get_right()[0]" in source
    assert "_cache_obj.get_top()[1]" in source
    assert "_cache_obj.get_bottom()[1]" in source
    assert "v376_stage_before_bbox.marker" not in source
    assert "v376_stage_" in source and "_v376_fp.write" in source
    assert "self.play(FadeIn" in source
    assert source.index("V3-76 HOST INJECTED")<source.index("self.play(")
    assert "import requests" not in source and "urlopen" not in source
    compile(source,"<native-smoke-source>","exec")

def test_stage_markers_bisect_first_geometry_and_serialization():
    txt=(ROOT/"learnflow_v3/v376_native_manim_probe.py").read_text()
    steps=["entered","before_membership","after_membership","before_bbox",
           "after_bbox","before_color","after_color",
           "before_opacity","after_opacity",
           "before_serialize","after_serialize","after_write","after_flush"]
    for step in steps:
        assert f"_v376_stage('{step}')" in txt
    assert "if _v376_serial[0]==0:" in txt

def test_smoke_time_budget_fails_closed_and_never_runs_arbitrary_model():
    s=(ROOT/"scripts/run_v3_76r1_bounded_manim_probe.py").read_text()
    assert "subprocess.run(command,capture_output=True,text=True,timeout=45)" in s
    assert '"--network","none"' in s and '"--read-only"' in s
    assert "not result[\"render_timed_out\"]" in s
    assert "MINIMAL_PHYSICAL_PROBE_PASS" in s
    assert "MINIMAL_REAL_MANIM_PROBE_NOT_CERTIFIED" in s
    assert '"runtime_rows"]>=15' in s
    assert "result[\"runtime_first_row_nonempty\"]" in s

def test_full_creative_must_be_after_smoke_gate_not_before():
    yaml=(ROOT/".github/workflows/v3-76-native-manim-runtime-readability.yml").read_text()
    a=yaml.index("run_v3_76r1_bounded_manim_probe.py")
    b=yaml.index("run_v3_76_native_runtime_readability.py")
    assert a<b
    assert "v376r1_smoke/" in yaml
    assert "v376_native_runtime/" in yaml

def test_no_change_to_study_pedagogy_outcomes():
    r=json.loads(PREREG.read_text())
    assert r["boundaries"]["human_quality"]=="UNRATED"
    assert r["boundaries"]["learning_gain"]=="NOT_MEASURED"
    assert r["boundaries"]["no_frozen_clip_replacement"]

def test_r1_actual_cmu_bounds_precached_before_frame_updater_with_conservative_envelope():
    src=compile_smoke()
    before=src.index("_cache_obj.get_left()[0]")
    callback=src.index("def _v376_capture(dt):")
    assert before<callback
    runtime=src[callback:]
    assert "_v376_bounds=_v376_bbox_cache.get(name)" in runtime
    assert "_cache_obj.get_left()[0]" not in runtime
    assert "_v376_bounds=_v376_bbox_cache.get(name)" in runtime
    assert "*1.07/2" in src
    assert "v376_stage_before_precache_bbox.marker" in src
    assert "v376_stage_after_precache_bbox.marker" in src

def test_a3_effective_svg_glyph_fill_not_black_parent_color():
    from learnflow_v3.v376_native_runtime_readability import validate_telemetry
    rows=[]
    for i in range(120):
        rows.append({"seq":i,"scene_time_s":i/15.,"dt":1/15.,
            "objects":[
               {"id":"chrome","role":"text","bbox_px":[70,50,300,92],
                "rgb":[0.,0.,0.],"opacity":1.,"parent":""},
               {"id":"value","role":"text","bbox_px":[120,205,260,232],
                "rgb":[0.,0.,0.],"opacity":1.,"parent":""},
               {"id":"bar","role":"shape","bbox_px":[120,280,360,316],
                "rgb":[.9,.7,.4],"opacity":1.,"parent":""},
               {"id":"node","role":"shape","bbox_px":[500,250,700,380],
                "rgb":[.4,.7,.7],"opacity":1.,"parent":""},
               {"id":"label","role":"text","bbox_px":[552,295,648,322],
                "rgb":[0.,0.,0.],"opacity":1.,"parent":"node"},
            ]})
    for row in rows:
        for o in row["objects"]:
            if o["role"]=="text":
                o["rgb"]=[0.,0.,0.]  # Manim Text container's incorrect BLACK style
                o["glyph_rgbs"]=[[.92,.94,.96]]
                o["color_source"]="CONSTRUCT_TIME_SVG_LEAF_FILL"
    evidence=validate_telemetry(rows,120)
    assert not evidence["contrast_defects"],evidence["contrast_defects"]
    # Worst actual child fill color wins; dark glyph may not be averaged away.
    for row in rows:
        for o in row["objects"]:
            if o["role"]=="text":
                o["glyph_rgbs"].append([.13,.13,.13])
    bad=validate_telemetry(rows,120)
    assert bad["contrast_defects"]


def test_a3_glyph_fill_provenance_required_in_physical_runner():
    from scripts.run_v3_76r1_bounded_manim_probe import compile_smoke
    source=compile_smoke()
    assert "_cache_obj.get_family()" in source
    assert "_glyph.get_fill_color().to_rgb()" in source
    assert "V376_NO_EFFECTIVE_SVG_GLYPH_COLOR" in source
    check=(ROOT/"learnflow_v3/v376_native_runtime_readability.py").read_text()
    assert "NATIVE_TEXT_GLYPH_FILL_PROVENANCE_MISSING" in check
    assert "min(contrast_ratio(color) for color in candidates)" in check


def test_a3_preregister_no_lowering_contrast_before_fix():
    amend=json.loads((ROOT/"benchmarks/learnflowbench/v3/v3_76r1_recovery_amendment_a3.json").read_text())
    assert amend["amendment"]=="A3_SVG_GLYPH_COLOR_PROVENANCE"
    assert amend["evidence"]["run"]==38541169374
    assert amend["evidence"]["artifact"]==11882608398
    assert "merging main" in amend["non_goals"]
