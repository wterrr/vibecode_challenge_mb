import pytest
import numpy as np
from pydantic import ValidationError
from pathlib import Path
from learnflow_v2.scenegraph.schema import SceneGraph
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.semantic_attention_motion import Case,MotionPlan,ground,check,facts,compile_manim,OP_SEQUENCE
from scripts.run_v3_52_semantic_motion import prereg,classify_colors,pixel_gate

ROOT=Path(__file__).resolve().parents[2]

def sample(row):
    return Case(topic_id=row["id"],query=tuple(row["query"]),keys=tuple(tuple(x) for x in row["keys"]),values=tuple(tuple(x) for x in row["values"]),dim=row["dim"])

def test_preregister_first_and_no_model():
    reg=prereg()
    assert reg["parent_sha"]=="7da60601998529208cbc19f8189c373f0244cec2"
    assert reg["safety"]["provider_requests"]==0
    assert reg["video_requirements"]["native_count"]==2

@pytest.mark.parametrize("row",prereg()["cases"])
def test_facts_generic_compiler_real_v2_contract(row):
    plan=ground(sample(row));ev,g=check(plan)
    assert isinstance(g,SceneGraph)
    assert len(g.nodes)==10 and len(g.relations)==6
    assert sum(ev["weights"])==pytest.approx(1)
    assert ev["context"]==pytest.approx(ev["weights"])
    assert [step.kind for step in plan.steps]==list(OP_SEQUENCE)
    code=compile_manim(plan,[11.,12.,12.,10.])
    compile(code,"<host_only>","exec")
    assert "TransformFromCopy(bar_a,seg_a)" in code
    assert "TransformFromCopy(bar_b,seg_b)" in code
    assert f"width={5*ev['weights'][0]:.6f}" in code
    assert f"width={5*ev['weights'][1]:.6f}" in code
    assert "V352_SEMANTIC_BEAT_3" in code
    assert "__import__" not in code and "subprocess" not in code

def test_counterfactual_changes_context_and_rendered_area():
    a,b=[facts(sample(row)) for row in prereg()["cases"]]
    assert a["weights"][0]>a["weights"][1]
    assert b["weights"][0]<b["weights"][1]
    assert a["weights"][0]==pytest.approx(b["weights"][1])
    assert b["context"]==pytest.approx(b["weights"])
    assert abs(a["weights"][0]-b["weights"][0])>.30

@pytest.mark.parametrize("field,value",[
    ("query",(1,1)),("query",(-1,0)),("dim",4),
    ("keys",((0,1),(1,0))),("values",((0,0),(0,1))),
    ("topic_id","unsupported")])
def test_no_new_fact_values_or_wrong_query(field,value):
    d=sample(prereg()["cases"][0]).model_dump();d[field]=value
    with pytest.raises((ValidationError,ValueError,Blocked)):
        ground(Case.model_validate(d))

@pytest.mark.parametrize("mutation",[
    "wrong_evidence","wrong_origin","wrong_op","wrong_claim",
    "wrong_source","wrong_beat","wrong_fact_sha","wrong_context"])
def test_invalid_motion_fails_closed(mutation):
    p=ground(sample(prereg()["cases"][0]));d=p.model_dump()
    d["steps"]=list(d["steps"])
    if mutation=="wrong_evidence":d["evidence_sha256"]="0"*64
    if mutation=="wrong_origin":d["origin"]="REAL_MODEL"
    if mutation=="wrong_op":d["steps"].reverse()
    if mutation=="wrong_claim":d["steps"][1]["claim_id"]="A4"
    if mutation=="wrong_source":d["steps"][2]["subject_id"]="query"
    if mutation=="wrong_beat":d["steps"][0]["beat"]=3
    if mutation=="wrong_fact_sha":d["steps"][0]["fact_sha256"]="f"*64
    if mutation=="wrong_context":d["case"]["query"]=(1,1)
    with pytest.raises((ValidationError,ValueError,Blocked)):
        check(MotionPlan.model_validate(d))

def test_model_copy_bypass_not_trusted():
    p=ground(sample(prereg()["cases"][0]))
    with pytest.raises(Blocked):
        check(p.model_copy(update={"evidence_sha256":"0"*64}))
    with pytest.raises(Blocked):
        ground(p.case.model_copy(update={"query":(1,1)}))

def test_h264_pixel_gate_calibration_and_negative_controls(monkeypatch,tmp_path):
    import scripts.run_v3_52_semantic_motion as r
    plan=ground(sample(prereg()["cases"][0]))
    def img(a,b):
        f=np.zeros((720,1280,3),dtype=np.uint8)
        f[542:565,430:430+a]=[115,202,210]
        f[542:565,430+a:430+a+b]=[233,183,102]
        return f
    baseline=img(0,0)
    assert classify_colors(img(270,130))["teal_pixels"]>5000
    beats=[{"frames":150}]*4
    monkeypatch.setattr(r,"_frame",lambda p,i:baseline)
    with pytest.raises(Blocked,match="V352_WEIGHTED_TRANSPORT"):
        pixel_gate(tmp_path/"s.mp4",beats,plan)
    monkeypatch.setattr(r,"_frame",lambda p,i:baseline if i==297 else img(130,270))
    with pytest.raises(Blocked,match="V352_RENDERED_CONTEXT_RATIO"):
        pixel_gate(tmp_path/"s.mp4",beats,plan)
    monkeypatch.setattr(r,"_frame",lambda p,i:baseline if i==297 else img(270,130))
    proof=pixel_gate(tmp_path/"s.mp4",beats,plan)
    assert proof["negative"]["total_causal_pixels"]==0
    assert abs(proof["actual_teal_area_fraction"]-.675)<.02

@pytest.mark.parametrize("durations",[[1,1,1,1],[10,10,10],[10,10,10,25]])
def test_bad_beat_lengths(durations):
    with pytest.raises(Blocked,match="V352_SPEECH_DURATION"):
        compile_manim(ground(sample(prereg()["cases"][0])),durations)

def test_native_ci_artifact_and_old_gates_not_optional():
    w=(ROOT/".github/workflows/v3-52-semantic-motion.yml").read_text()
    assert "test_v3_51_creative_scene_graph.py" in w
    assert "test_v3_50_one_query_attention.py" in w
    assert "verify_v2_core_freeze.py" in w
    assert "verify_learnflow_bench.py" in w
    assert "if-no-files-found: error" in w
    assert "runner.temp" in w
    assert "secrets.OPENROUTER_API_KEY" not in w
