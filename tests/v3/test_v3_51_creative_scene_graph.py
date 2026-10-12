"""V3-51 semantic freedom, scope truth and real-V2 SceneGraph adapter contract."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_scene_graph import (
    VERSION,ORIGIN,ledger,digest,validate,manim,positions,Storyboard)
from learnflow_v3.creative_scene_fixtures import fixtures
from learnflow_v3.creative_validation_diagnostics import classify_v350,classify_v351
from learnflow_v3.model_authored_attention import synthetic_fixture as frozen_v350
from learnflow_v2.scenegraph.schema import SceneGraph

ROOT=Path(__file__).resolve().parents[2]
PRE="benchmarks/learnflowbench/v3/v3_51_creative_scene_preregister.json"


def example():
    return deepcopy(fixtures()["tokens_as_network"])


def test_preregistered_evidence_frozen_first():
    reg=json.loads((ROOT/PRE).read_text())
    assert reg["checkpoint"]=="V3-51" and reg["preregistered_before_implementation"]
    assert reg["parent_sha"]=="1ef31e132659b2a7d07e351f0810824c91bc28ee"
    assert [r["id"] for r in reg["frozen_offline_variants"]]==list(fixtures())
    assert reg["quality_gates"]["required_native_count"]==3
    assert "OFFLINE_ONLY" in reg["scope"]


@pytest.mark.parametrize("name",list(fixtures()))
def test_valid_scenes_reuse_actual_v2_scenegraph(name):
    raw=fixtures()[name]
    story,facts,graphs,layout=validate(raw)
    assert story.version==VERSION and story.origin==ORIGIN
    assert raw["evidence_sha256"]==digest(facts)
    assert len(graphs)==len(story.scenes)
    assert all(isinstance(x,SceneGraph) for x in graphs)
    assert len({s.layout for s in story.scenes})>=2
    assert {c for b in story.beats for c in b.claims}=={"A1","A2","A3","A4"}
    assert all(len(layout[g.scene_id])==len(g.nodes) for g in graphs)
    assert all(n.kind.value in {"TEXT","SHAPE","MATH","EQUATION","CHART"}
               for g in graphs for n in g.nodes)
    assert all(n.semantic_role for g in graphs for n in g.nodes)
    # Real generic generator: no dispatch on case, topic keyword or scene IDs.
    code=manim(story,facts,graphs,layout,[10.5]*len(story.beats))
    compile(code,"<host_only_manim>","exec")
    assert "self.play" in code and "GeneratedLesson" in code
    assert "from manim import *" in code
    assert "FadeIn" in code and "Create(" in code
    assert "subprocess" not in code and "__import__" not in code
    assert "exec(" not in code and "eval(" not in code
    assert "V3-51 GENERIC HOST COMPILED" in code


def test_graph_compositions_and_compiled_code_are_meaningfully_distinct():
    raws=fixtures()
    graphs=[];programs=[]
    for case in raws:
        story,truth,v2,coords=validate(raws[case])
        graphs.append((len(story.scenes),len(story.beats),
                       tuple(s.layout for s in story.scenes),
                       tuple(tuple(n.kind for n in s.nodes) for s in story.scenes)))
        programs.append(hashlib.sha256(manim(story,truth,v2,coords,
                [10]*len(story.beats)).encode()).hexdigest())
    assert len(set(programs))==3
    assert len(set(graphs))==3
    assert len({p for g in graphs for p in g[2]})>=4


def test_no_keyword_policing_of_correct_paraphrase_in_flexible_graph():
    x=example()
    x["beats"][1]["narration"]=(
       "To measure compatibility, the query interacts with the two keys. "
       "Their similarity is normalized by the dimension factor before a "
       "distribution over the available information is formed.")
    st,_,_,_=validate(x)
    assert st.beats[1].claims==["A2"]
    assert "dot product" not in st.beats[1].narration


@pytest.mark.parametrize("case",[
  "alter_sha","different_origin","invent_fact","faked_number_label",
  "invalid_analytic_chart","fake_edge","unknown_endpoint",
  "wrong_relation_kind","duplicate_scene","duplicate_node","bad_title",
  "new_claim","unbacked_claim","unknown_action_node","relation_not_revealed",
  "visible_before_reveal","cross_scene_action","new_number","action_python",
  "no_transitions","nonmonotone_scene","wrong_action_kind","unknown_layout",
  "missing_fact_ref","missing_action","missing_scene"])
def test_factual_or_structural_mutations_fail_closed(case):
    x=example()
    s=x["scenes"][0];b=x["beats"][0]
    if case=="alter_sha":x["evidence_sha256"]="0"*64
    elif case=="different_origin":x["origin"]="REAL_MODEL_LIVE"
    elif case=="invent_fact":s["nodes"][0]["fact_ref"]="very_fake_fact"
    elif case=="faked_number_label":s["nodes"][0]["fact_ref"]=None;s["nodes"][0]["label"]="attention score 999"
    elif case=="invalid_analytic_chart":s["nodes"][0]["kind"]="CHART"
    elif case=="fake_edge":s["relations"][0]["target"]="scoreleft"
    elif case=="unknown_endpoint":s["relations"][0]["target"]="lost_node"
    elif case=="wrong_relation_kind":s["relations"][0]["kind"]="EQUIVALENT_TO"
    elif case=="duplicate_scene":x["scenes"][1]["id"]=x["scenes"][0]["id"]
    elif case=="duplicate_node":s["nodes"][1]["id"]=s["nodes"][0]["id"]
    elif case=="bad_title":s["title"]="Attention always predicts 99"
    elif case=="new_claim":b["claims"]=["A5"]
    elif case=="unbacked_claim":b["claims"]=["A4"]
    elif case=="unknown_action_node":b["actions"][0]["target"]="missing_object"
    elif case=="relation_not_revealed":b["actions"][0]={"kind":"connect","target":"leftmatch","source":None,"destination":None}
    elif case=="visible_before_reveal":b["actions"][0]={"kind":"emphasize","target":"ask","source":None,"destination":None}
    elif case=="cross_scene_action":b["actions"][0]["target"]="weightleft"
    elif case=="new_number":b["narration"]+=" Confidence is 123456."
    elif case=="action_python":b["actions"][0]["python"]="import os"
    elif case=="no_transitions":
        for beat in x["beats"]:
            beat["actions"]=[{"kind":"emphasize","target":"ask","source":None,"destination":None}]
    elif case=="nonmonotone_scene":x["beats"][3]["scene_id"]="network"
    elif case=="wrong_action_kind":b["actions"][0]["kind"]="execute_code"
    elif case=="unknown_layout":s["layout"]="HACKED_FREEFORM"
    elif case=="missing_fact_ref":s["nodes"][0]["fact_ref"]=None
    elif case=="missing_action":b["actions"]=[]
    elif case=="missing_scene":x["scenes"]=[]
    assert classify_v351(x)["status"]=="BLOCKED"
    with pytest.raises((Blocked,ValueError)):
        validate(x)


def test_invalid_equivalence_morph_can_never_assert_false_identity():
    x=example()
    # A "replace" between different facts would be a false visual identity.
    x["beats"][0]["actions"][-1]={
       "kind":"replace","target":"rightkey","source":"ask","destination":None}
    with pytest.raises(Blocked):
        validate(x)


def test_generic_move_accepts_only_unoccupied_semantic_regions():
    x=deepcopy(fixtures()["scores_as_comparison"])
    x["beats"][0]["actions"].append({
       "kind":"move","target":"query","source":None,"destination":"BOTTOM_RIGHT"})
    st,truth,graphs,coords=validate(x)
    code=manim(st,truth,graphs,coords,[10]*len(st.beats))
    assert ".animate.move_to([4.150,-1.600,0])" in code
    assert coords["pairing"]["query"]!= (4.15,-1.6)


def test_v350_diagnostics_separate_schema_from_semantic_rejection():
    x=frozen_v350()
    assert classify_v350(x)["stage"]=="accepted"
    malformed=deepcopy(x);del malformed["beats"]["beat_3"]
    result=classify_v350(malformed)
    assert result["stage"]=="json_schema"
    assert any(q["keyword"]=="required" for q in result["error_shapes"])
    assert result["raw_content_stored"] is False
    paraphrase=deepcopy(x)
    paraphrase["beats"]["beat_2"]["narration"]=(
      "We compare the input representation against the other token "
      "representations and normalize the resulting similarities using "
      "the key feature dimension for a stable set of scores.")
    semantic=classify_v350(paraphrase)
    assert semantic["stage"]=="host_semantic"
    assert semantic["code"]=="V350_A2_NOT_GROUNDED"
    assert semantic["raw_content_stored"] is False


def test_v351_sanitized_diagnostics_not_model_attribution():
    good=classify_v351(example())
    assert good["stage"]=="accepted" and good["raw_content_stored"] is False
    bad=example();bad["evidence_sha256"]="0"*64
    r=classify_v351(bad)
    assert r["code"]=="V351_FACT_LEDGER_SHA_MISMATCH"
    assert r["stage"]=="evidence" and r["raw_content_stored"] is False


def test_no_paid_workflow_no_retry_and_old_tests_preserved():
    script=(ROOT/"scripts/run_v3_51_creative_scene_graphs.py").read_text()
    flow=(ROOT/".github/workflows/v3-51-creative-scenegraph.yml").read_text()
    for marker in ("_docker_manim","deterministic_mux","_codec_and_pixel_gates",
                   "max_decoded_sample_delta","V351_VISUAL_STORYBOARDS_NOT_DISTINCT"):
        assert marker in script
    assert "V3-50" in script
    assert "secrets.OPENROUTER_API_KEY" not in flow
    assert "MODEL" not in flow.split("jobs:",1)[1].split("run:",1)[0]
    assert "test_v3_50_one_query_attention.py" in flow
    assert "verify_v2_core_freeze.py" in flow
    assert "verify_learnflow_bench.py" in flow
    assert "v3-51-HOST-THREE-CREATIVE-NATIVE-MP4-NO-AI" in flow
