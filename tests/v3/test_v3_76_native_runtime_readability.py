"""V3-76 runtime telemetry contract and hostile negative mutation cases."""
import json
from pathlib import Path
import pytest

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_scene_fixtures import fixtures
from learnflow_v3.creative_candidate_acceptance import accept,mock_candidate_bytes
from learnflow_v3.creative_scene_graph import manim
from learnflow_v3.v376_native_manim_probe import instrument
from learnflow_v3.v376_native_runtime_readability import (
    contrast_ratio,intersection,validate_telemetry,read_runtime,
    REQUIRED_CONTRAST,RUNTIME_FILENAME
)
from scripts.run_v3_75_creative_native_qa import REG as PRIOR_REG
from scripts.run_v3_76_native_runtime_readability import PREREG

def row(i,*,low=False,overlap=False):
    light=[.92,.94,.96]
    dark=[.12,.12,.12]
    return {"seq":i,"scene_time_s":i/15,"dt":1/15,
            "objects":[
             {"id":"title","role":"text","bbox_px":[70,50,300,92],"opacity":1.,
              "rgb":dark if low else light,"parent":""},
             {"id":"score_b","role":"text","bbox_px":[120,205,260,232],"opacity":1.,
              "rgb":light,"parent":""},
             {"id":"bar_a","role":"shape","bbox_px":[120,216 if overlap else 280,360,316],"opacity":1.,
              "rgb":[.9,.7,.4],"parent":""},
             {"id":"node","role":"shape","bbox_px":[500,250,700,380],"opacity":1.,
              "rgb":[.4,.7,.7],"parent":""},
             {"id":"label","role":"text","bbox_px":[552,295,648,322],"opacity":1.,
              "rgb":light,"parent":"node"},
            ]}

def stream(n=120,**kwargs):
    return [row(i,**kwargs) for i in range(n)]

def test_first_child_preregister_unmodified_old_study_artifacts():
    r=json.loads(PREREG.read_text())
    assert r["parent"]["pr"]==111
    assert r["parent"]["sha"]=="612600ff1558a0e398bb19a96ac857d67a3b04a2"
    assert r["kind"]=="FIRST_CHILD_PREREG_BEFORE_IMPLEMENTATION"
    assert r["restrictions"]["no_model_api_post"] is True
    assert r["hard_acceptance"]["min_text_contrast_ratio"]==4.5

def test_negative_actual_attention_score_label_and_bar_intersect():
    k=validate_telemetry(stream(overlap=True),120)
    assert k["actual_glyph_shape_intersections"]
    assert k["actual_glyph_shape_intersections"][0]["a"]=="score_b"

def test_positive_no_collision_manipulation_passes_geometry():
    k=validate_telemetry(stream(),120)
    assert not k["actual_glyph_shape_intersections"]
    assert not k["contrast_defects"]
    assert k["runtime_samples"]==120

@pytest.mark.parametrize("variant",["low_contrast","miss_seq","missing_samples","duplicate_seq","nan_bbox","unregistered_kind","hidden_all","text_shape_overlap"])
def test_adversarial_runtime_failure_inventory(variant):
    rows=stream(low=variant=="low_contrast",overlap=variant=="text_shape_overlap")
    if variant=="miss_seq":rows[18]["seq"]=90
    if variant=="missing_samples":rows=rows[:60]
    if variant=="duplicate_seq":rows[4]["seq"]=3
    if variant=="nan_bbox":rows[10]["objects"][2]["bbox_px"][0]=float("nan")
    if variant=="unregistered_kind":rows[4]["objects"][0]["role"]="shader"
    if variant=="hidden_all":
        for a in rows:
            for ob in a["objects"]:ob["opacity"]=0
    if variant in ("low_contrast","text_shape_overlap"):
        k=validate_telemetry(rows,120)
        assert (k["contrast_defects"] if variant=="low_contrast"
                else k["actual_glyph_shape_intersections"])
    else:
        with pytest.raises(Blocked,match="V376_"):
            validate_telemetry(rows,120)

def test_containment_exception_only_for_exact_parent_id():
    rows=stream()
    assert not validate_telemetry(rows,120)["actual_glyph_shape_intersections"]
    for a in rows:a["objects"][4]["parent"]="not_its_own_box"
    assert validate_telemetry(rows,120)["actual_glyph_shape_intersections"]

def test_bg_contrast_wcag_ratio_is_not_raw_RGB_delta():
    assert contrast_ratio((.13,.13,.13))<REQUIRED_CONTRAST
    assert contrast_ratio((.92,.94,.96))>REQUIRED_CONTRAST
    assert intersection((50,50,100,100),(98,80,120,120))
    assert not intersection((50,50,100,100),(101,80,120,120))

def test_missing_or_invalid_telemetry_fails_closed(tmp_path):
    with pytest.raises(Blocked,match="RUNTIME_TELEMETRY_MISSING"):
        read_runtime(tmp_path/RUNTIME_FILENAME)
    p=tmp_path/RUNTIME_FILENAME
    p.write_text("{ this is invalid\\n"*180)
    with pytest.raises(Blocked,match="RUNTIME_TELEMETRY_CORRUPT"):
        read_runtime(p)

def test_host_owned_compiler_instrumentation_actually_targets_native_object_variables():
    raw=fixtures()["scores_as_comparison"]
    accepted,meta=accept(mock_candidate_bytes(raw))
    assert accepted
    story=accepted["storyboard"]
    source=manim(story,accepted["facts"],accepted["graphs"],accepted["layout"],
                 [12.0]*len(story.beats))
    out=instrument(source,story)
    assert out.startswith("# V3-51 GENERIC HOST COMPILED SOURCE")
    assert out.count("V3-76 HOST INJECTED ACTUAL MANIM") == 1
    assert "_v376_monitor.add_updater" in out
    assert "_v376_roots=tuple(self.mobjects)" in out
    assert "call_updater=False" in out
    assert "v376_probe_first_tick.marker" in out
    assert out.index("V3-76 HOST INJECTED") < out.index("self.play(")
    assert "_v376_fp=_v376_out.open" in out
    assert "mock_score_comparison" not in out
    assert "from pathlib import Path as _V376Path" in out

def test_reject_instrumentation_if_compiler_was_not_verified():
    with pytest.raises(Blocked,match="V376_UNTRUSTED_COMPILER_SOURCE"):
        instrument("import os;exec('unsafe')",None)

def test_actual_creative_runner_opt_in_order_before_docker_after_mux():
    source=(Path(__file__).resolve().parents[2]/
            "scripts/run_v3_54_model_candidate_quality.py").read_text()
    assert 'runtime_v376:bool=False' in source
    assert source.index("host_code=instrument") < source.index("render,sandbox=_docker_manim")
    assert source.index("v376_runtime=evaluate") > source.index("mux=deterministic_mux")
    assert source.index("v376_runtime=evaluate") < source.index('folder/"native_quality_receipt.json"')

def test_original_qa_scope_kept_and_no_false_human_learner_claim():
    p=json.loads(PRIOR_REG.read_text())
    assert p["checkpoint"]=="V3-75"
    assert json.loads(PREREG.read_text())["restrictions"]["production"]=="BLOCKED"
