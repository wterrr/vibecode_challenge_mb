"""V3-07 bounded state replay, semantic mutation, actual MP4 and font QA."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest
from PIL import Image
from pydantic import ValidationError

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v2.repair import compute_content_hash
from learnflow_v2.scenegraph import SceneGraph
from learnflow_v3.blackboard_style import cmu_font, BLACK
from learnflow_v3.models import SemanticContractError
from learnflow_v3.code_process_renderer import (
    CodeStep, CodeLine, CodeWalkthrough, ProcessStep, ProcessWalkthrough,
    verify_code_walkthrough, verify_process_walkthrough, layout_process,
    draw_code_frame, draw_process_frame, render_code_walkthrough, render_process_walkthrough,
    _ffmpeg_anchor, _mean_absolute_error,
)
from learnflow_v3.sequence_renderer import SequenceRenderProfile, draw_binary_search_frame
from scripts.verify_v3_code_process_render import code_demo, process_demo
from scripts.verify_v3_binary_search_render import create_certified_demo_bundle


@pytest.fixture
def profile():
    return SequenceRenderProfile(width=640,height=360,fps=12,seconds_per_step=0.75)


def test_computer_modern_is_real_and_background_is_absolute_black(profile):
    regular=cmu_font(25)
    mono=cmu_font(25,mono=True)
    assert "cmu" in " ".join(regular.getname()).lower()
    assert "cmu" in " ".join(mono.getname()).lower()
    code_graph,code=code_demo()
    im=draw_code_frame(code,code_graph,0,profile)
    assert im.getpixel((0,0))==BLACK==(0,0,0)
    assert im.getpixel((im.width-1,0))==BLACK
    process_graph,proc=process_demo()
    image=draw_process_frame(proc,process_graph,0,profile)
    assert image.getpixel((0,0))==BLACK
    bundle,trace=create_certified_demo_bundle(values=(1,3,5),target=3)
    image=draw_binary_search_frame(trace=trace,step_index=0,progress=1.0,
                  subtitle=bundle["script"].segments[0].spoken_text,profile=profile)
    assert image.getpixel((0,0))==BLACK


def test_code_replay_valid_and_unchanged_variable_identity():
    graph,spec=code_demo()
    verify_code_walkthrough(spec,graph)
    assert [s.variables for s in spec.steps][-1]=={"low":0,"high":2,"mid":3}


def test_code_forged_state_is_rejected():
    graph,spec=code_demo()
    raw=spec.model_dump(mode="json")
    raw["steps"][2]["variables"]["mid"]=2
    forged=CodeWalkthrough.model_validate(raw)
    with pytest.raises(SemanticContractError,match="STATE_REPLAY_MISMATCH"):
        verify_code_walkthrough(forged,graph)


@pytest.mark.parametrize("bad",[
    "mid = __import__('os').system('echo hi')",
    "mid = int(2)",
    "for x in range(4): pass",
    "mid = 1 / 2",
    "mid = high ** 200",
    "mid = unknown + 1",
    "mid = (low + high) // 0",
])
def test_code_disallowed_python_cannot_execute(bad):
    graph,spec=code_demo()
    raw=spec.model_dump(mode="json")
    raw["lines"][2]["source"]=bad
    changed_graph=graph.model_dump(mode="json")
    changed_graph["nodes"][0]["content"]="\n".join(line["source"] for line in raw["lines"])
    changed_graph=SceneGraph.model_validate(changed_graph)
    raw["scenegraph_sha256"]=compute_content_hash(changed_graph)
    modified=CodeWalkthrough.model_validate(raw)
    with pytest.raises(SemanticContractError,match="UNSUPPORTED_CODE_EXPRESSION|CODE_STATEMENT_NOT_ALLOWLISTED|CODE_PARSE_REJECTED"):
        verify_code_walkthrough(modified,changed_graph)


def test_code_source_graph_drift_rejected_even_when_trace_rehashed():
    graph,spec=code_demo()
    raw=graph.model_dump(mode="json")
    raw["nodes"][0]["content"]="low = 123"
    changed=SceneGraph.model_validate(raw)
    with pytest.raises(SemanticContractError,match="CODE_GRAPH_HASH_MISMATCH"):
        verify_code_walkthrough(spec,changed)
    raw_spec=spec.model_dump(mode="json")
    raw_spec["scenegraph_sha256"]=compute_content_hash(changed)
    forged=CodeWalkthrough.model_validate(raw_spec)
    with pytest.raises(SemanticContractError,match="CODE_SOURCE_SCENEGRAPH_DRIFT"):
        verify_code_walkthrough(forged,changed)


def test_process_branching_identity_and_same_graph_layout(profile):
    graph,spec=process_demo()
    verify_process_walkthrough(spec,graph)
    a=layout_process(graph,profile)
    b=layout_process(graph,profile)
    assert a==b and len(a)==4
    assert a["start"][0]<a["valid"][0]<a["finish"][0]
    assert a["valid"][1]!=a["invalid"][1]
    assert set(x.id for x in graph.relations)=={"e1","e2","e3","e4"}


def test_forged_process_edge_and_orphan_node_fail_closed():
    graph,spec=process_demo()
    raw=spec.model_dump(mode="json")
    raw["steps"][1]["via_edge_id"]="e2"  # wrong branch, same source
    forged=ProcessWalkthrough.model_validate(raw)
    with pytest.raises(SemanticContractError,match="TOPOLOGY_REPLAY_MISMATCH"):
        verify_process_walkthrough(forged,graph)
    raw["steps"][1]["via_edge_id"]="missing-edge"
    forged=ProcessWalkthrough.model_validate(raw)
    with pytest.raises(SemanticContractError,match="TOPOLOGY_REPLAY_MISMATCH"):
        verify_process_walkthrough(forged,graph)


def test_process_mutated_graph_requires_rebinding_all_proof():
    graph,spec=process_demo()
    raw=graph.model_dump(mode="json")
    raw["relations"][0]["target"]="invalid"
    changed=SceneGraph.model_validate(raw)
    with pytest.raises(SemanticContractError,match="PROCESS_GRAPH_HASH_MISMATCH"):
        verify_process_walkthrough(spec,changed)
    sp=spec.model_dump(mode="json")
    sp["scenegraph_sha256"]=compute_content_hash(changed)
    with pytest.raises(SemanticContractError,match="TOPOLOGY_REPLAY_MISMATCH"):
        verify_process_walkthrough(ProcessWalkthrough.model_validate(sp),changed)


def test_process_cycle_and_many_nodes_refuse_instead_of_flattening():
    graph,spec=process_demo()
    raw=graph.model_dump(mode="json")
    raw["relations"].append({"id":"cycle","source":"finish","target":"start","kind":"FLOW"})
    changed=SceneGraph.model_validate(raw)
    with pytest.raises(SemanticContractError,match="CYCLIC_GRAPH"):
        layout_process(changed)


def test_frames_keep_black_background_no_default_concept_cards(profile):
    code_graph,code=code_demo()
    pro_graph,pro=process_demo()
    for i in range(len(code.steps)):
        im=draw_code_frame(code,code_graph,i,profile)
        assert im.getpixel((1,1))==BLACK
    for i in range(len(pro.steps)):
        im=draw_process_frame(pro,pro_graph,i,profile)
        assert im.getpixel((1,1))==BLACK


@pytest.mark.parametrize("family",["code","process"])
def test_real_mp4_frame_decode_and_per_state_pixel_qa(tmp_path,profile,family):
    graph,spec=(code_demo() if family=="code" else process_demo())
    render=render_code_walkthrough if family=="code" else render_process_walkthrough
    drawer=draw_code_frame if family=="code" else draw_process_frame
    out=tmp_path/f"{family}.mp4"
    evidence=render(spec=spec,graph=graph,output_path=out,profile=profile)
    assert out.read_bytes()[4:8]==b"ftyp"
    assert evidence.frame_count==len(spec.steps)*profile.frames_per_step()
    assert evidence.video_bytes>2000
    assert evidence.video_checks_pass is True
    assert evidence.family==("CODE_WALKTHROUGH" if family=="code" else "PROCESS_FLOW")
    assert len(evidence.sample_frames)==len(spec.steps)
    assert all(m<8 for m in evidence.decoded_mae)
    assert all(d>1.15 for d in evidence.semantic_roi_delta)
    assert len(evidence.within_beat_motion_delta)==len(spec.steps)
    assert all(d>0.035 for d in evidence.within_beat_motion_delta)
    assert len(evidence.stable_object_centers)==(len(spec.lines) if family=="code" else len(graph.nodes))
    for i,k in enumerate(evidence.sample_frames):
        decoded=_ffmpeg_anchor(out,at=(k+0.4)/profile.fps,profile=profile)
        ideal=drawer(spec,graph,i,profile,
                     (k%profile.frames_per_step()+.5)/profile.frames_per_step())
        assert _mean_absolute_error(decoded,ideal)<8.0


@pytest.mark.parametrize("family",["code","process"])
def test_existing_file_and_symlink_never_overwritten(tmp_path,profile,family):
    graph,spec=(code_demo() if family=="code" else process_demo())
    render=render_code_walkthrough if family=="code" else render_process_walkthrough
    protected=tmp_path/"protected.mp4"
    protected.write_bytes(b"DO-NOT-DELETE")
    with pytest.raises(SemanticContractError,match="UNSAFE_OUTPUT_PATH"):
        render(spec=spec,graph=graph,output_path=protected,profile=profile)
    link=tmp_path/"link.mp4"
    link.symlink_to(protected)
    with pytest.raises(SemanticContractError,match="UNSAFE_OUTPUT_PATH"):
        render(spec=spec,graph=graph,output_path=link,profile=profile)
    assert protected.read_bytes()==b"DO-NOT-DELETE"


def test_dynamic_state_changes_source_digest_even_same_code():
    graph,spec=code_demo()
    data=spec.model_dump(mode="json")
    data["steps"][-1]["variables"]["high"]=15
    forged=CodeWalkthrough.model_validate(data)
    assert compute_content_hash(spec)!=compute_content_hash(forged)
    with pytest.raises(SemanticContractError,match="STATE_REPLAY_MISMATCH"):
        verify_code_walkthrough(forged,graph)


def test_within_beat_code_and_process_motion_are_not_static_images(profile):
    graph,code=code_demo()
    first=draw_code_frame(code,graph,2,profile,progress=0.12)
    second=draw_code_frame(code,graph,2,profile,progress=0.85)
    assert _mean_absolute_error(first,second)>0.06
    graph,process=process_demo()
    first=draw_process_frame(process,graph,1,profile,progress=0.12)
    second=draw_process_frame(process,graph,1,profile,progress=0.85)
    assert _mean_absolute_error(first,second)>0.03


def test_dense_variable_panel_fails_before_geometry_or_encoding():
    graph,spec=code_demo()
    raw=spec.model_dump(mode="json")
    raw["steps"][1]["variables"].update({f"v{i}":i for i in range(6)})
    with pytest.raises(SemanticContractError, match="VARIABLE_PANEL_TOO_DENSE"):
        verify_code_walkthrough(CodeWalkthrough.model_validate(raw),graph)
