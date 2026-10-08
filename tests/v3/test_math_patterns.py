"""V3-08 mathematical source replay, identity, negative and actual MP4 QA."""
from __future__ import annotations

from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from learnflow_v2.repair import compute_content_hash
from learnflow_v2.scenegraph import SceneGraph
from learnflow_v3.blackboard_style import BLACK, cmu_font
from learnflow_v3.math_renderer import (
    EquationDerivation, FunctionGraph, parse_polynomial, graph_source,
    pretty_polynomial, pretty_expression,
    verify_function_graph, verify_equation_derivation,
    draw_function_frame, draw_equation_frame,
    render_function_graph, render_equation_derivation,
    _ffmpeg_anchor, _mean_absolute_error,
)
from learnflow_v3.models import SemanticContractError
from learnflow_v3.sequence_renderer import SequenceRenderProfile
from scripts.verify_v3_math_patterns import function_demo, equation_demo


@pytest.fixture
def profile():
    return SequenceRenderProfile(width=640,height=360,fps=12,seconds_per_step=.75)


def test_exact_quadratic_trace_and_chart_binding():
    graph,spec=function_demo()
    verify_function_graph(spec,graph)
    assert [s.y for s in spec.steps]==[0,-3,-4,-3,0]
    assert graph.nodes[0].content==graph_source((-4,0,1),(-2,2))


def test_graph_wrong_y_rejected_even_if_model_rehashed():
    graph,spec=function_demo()
    data=spec.model_dump(mode="json")
    data["steps"][2]["y"]=-3
    forged=FunctionGraph.model_validate(data)
    assert compute_content_hash(forged)!=compute_content_hash(spec)
    with pytest.raises(SemanticContractError,match="GRAPH_POINT_REPLAY_MISMATCH"):
        verify_function_graph(forged,graph)


def test_graph_changed_formula_fails_source_binding_even_when_sha_rebound():
    graph,spec=function_demo()
    data=graph.model_dump(mode="json")
    data["nodes"][0]["content"]="f(x) = 0*x**2; domain=[-2,2]"
    changed=SceneGraph.model_validate(data)
    with pytest.raises(SemanticContractError,match="GRAPH_SOURCE_HASH_MISMATCH"):
        verify_function_graph(spec,changed)
    raw=spec.model_dump(mode="json")
    raw["scenegraph_sha256"]=compute_content_hash(changed)
    with pytest.raises(SemanticContractError,match="GRAPH_SOURCE_DRIFT"):
        verify_function_graph(FunctionGraph.model_validate(raw),changed)


def test_graph_bad_point_order_and_swept_extremum_rejected():
    graph,spec=function_demo()
    raw=spec.model_dump(mode="json")
    raw["steps"][1]["x"]=raw["steps"][0]["x"]
    with pytest.raises(SemanticContractError,match="GRAPH_POINT_ORDER_OR_COVERAGE"):
        verify_function_graph(FunctionGraph.model_validate(raw),graph)
    raw=spec.model_dump(mode="json")
    raw["coefficients"]=[4,0,1]
    # Build a fully rebound valid source so the domain/geometry guard is reached.
    changed=graph.model_dump(mode="json")
    changed["nodes"][0]["content"]=graph_source((4,0,1),(-2,2))
    rebound=SceneGraph.model_validate(changed)
    raw["scenegraph_sha256"]=compute_content_hash(rebound)
    with pytest.raises(SemanticContractError,match="GRAPH_POINT_REPLAY_MISMATCH|CURVE_OUTSIDE_SAFE_AXIS"):
        verify_function_graph(FunctionGraph.model_validate(raw),rebound)


@pytest.mark.parametrize("expression",[
    "__import__('os').system('echo bad')",
    "x / 2", "x**3", "z+1", "x*x*x", "x[0]",
    "(x+1) if True else 0", "x**(-1)", "x.__class__",
])
def test_algebra_untrusted_expression_rejected(expression):
    with pytest.raises(SemanticContractError):
        parse_polynomial(expression)


def test_algebra_symbolic_equivalence_not_sampled_heuristic():
    assert parse_polynomial("(x+2)*(x+2)")==parse_polynomial("x**2+4*x+4")==(4,4,1)
    assert parse_polynomial("x*x+2*x+2*x+4")==(4,4,1)
    assert parse_polynomial("x**2+4*x+5")!=(4,4,1)



def test_math_display_uses_conventional_not_programming_notation():
    assert pretty_polynomial((-4,0,1))=="f(x) = x² − 4"
    assert pretty_polynomial((0,0,0))=="f(x) = 0"
    assert pretty_expression("(x+2)*(x+2)")=="(x + 2)(x + 2)"
    assert pretty_expression("x*x+2*x+2*x+4")=="x² + 2x + 2x + 4"
    assert pretty_expression("x**2+4*x+4")=="x² + 4x + 4"

def test_equation_source_typed_chain_verified():
    graph,spec=equation_demo()
    assert verify_equation_derivation(spec,graph)==(4,4,1)


def test_equation_rehashed_but_false_identity_is_rejected():
    graph,spec=equation_demo()
    data=graph.model_dump(mode="json")
    data["nodes"][-1]["content"]="x**2+4*x+5"
    changed_graph=SceneGraph.model_validate(data)
    raw=spec.model_dump(mode="json")
    raw["steps"][-1]["expression"]="x**2+4*x+5"
    raw["scenegraph_sha256"]=compute_content_hash(changed_graph)
    with pytest.raises(SemanticContractError,match="NOT_SYMBOLICALLY_EQUIVALENT"):
        verify_equation_derivation(EquationDerivation.model_validate(raw),changed_graph)


def test_equation_wrong_edge_identity_fails_even_if_rehashed():
    graph,spec=equation_demo()
    data=graph.model_dump(mode="json")
    data["relations"][0]["source"]="distributed"
    changed=SceneGraph.model_validate(data)
    raw=spec.model_dump(mode="json")
    raw["scenegraph_sha256"]=compute_content_hash(changed)
    with pytest.raises(SemanticContractError,match="TRANSFORMATION_IDENTITY_MISMATCH"):
        verify_equation_derivation(EquationDerivation.model_validate(raw),changed)


def test_equation_source_changes_cannot_silently_reuse_spec():
    graph,spec=equation_demo()
    data=graph.model_dump(mode="json")
    data["nodes"][1]["content"]="x+2"
    changed=SceneGraph.model_validate(data)
    with pytest.raises(SemanticContractError,match="EQUATION_SOURCE_HASH_MISMATCH"):
        verify_equation_derivation(spec,changed)


def test_real_black_background_and_live_intra_beat_math_motion(profile):
    for builder,drawer in ((function_demo,draw_function_frame),(equation_demo,draw_equation_frame)):
        graph,spec=builder()
        a=drawer(spec,graph,1,profile,.12)
        b=drawer(spec,graph,1,profile,.83)
        assert a.getpixel((0,0))==b.getpixel((0,0))==BLACK
        assert _mean_absolute_error(a,b)>0.035
    assert "cmu" in " ".join(cmu_font(20).getname()).lower()


@pytest.mark.parametrize("family",["function","equation"])
def test_mp4_is_decoded_against_semantic_frames_and_intra_beat_motion(tmp_path,profile,family):
    graph,spec=(function_demo() if family=="function" else equation_demo())
    drawer=draw_function_frame if family=="function" else draw_equation_frame
    render=render_function_graph if family=="function" else render_equation_derivation
    path=tmp_path/f"{family}.mp4"
    evidence=render(spec=spec,graph=graph,output_path=path,profile=profile)
    assert path.read_bytes()[4:8]==b"ftyp"
    assert evidence.decoded_qa_pass is True
    assert evidence.frame_count==len(spec.steps)*profile.frames_per_step()
    assert len(evidence.decoded_frame_mae)==len(spec.steps)
    assert max(evidence.decoded_frame_mae)<8
    assert min(evidence.semantic_roi_deltas)>.18
    assert min(evidence.within_beat_motion_deltas)>.035
    assert len(evidence.semantic_object_centers)==len(spec.steps)
    for i in range(len(spec.steps)):
        frame=i*profile.frames_per_step()+profile.frames_per_step()//2
        image=_ffmpeg_anchor(path,at=(frame+.4)/profile.fps,profile=profile)
        ideal=drawer(spec,graph,i,profile,
                     (frame%profile.frames_per_step()+.5)/profile.frames_per_step())
        assert _mean_absolute_error(image,ideal)<8


@pytest.mark.parametrize("family",["function","equation"])
def test_math_video_must_not_overwrite_user_output(tmp_path,profile,family):
    graph,spec=(function_demo() if family=="function" else equation_demo())
    render=render_function_graph if family=="function" else render_equation_derivation
    destination=tmp_path/"owned.mp4"
    destination.write_bytes(b"keep-me")
    with pytest.raises(SemanticContractError,match="UNSAFE_OUTPUT_PATH"):
        render(spec=spec,graph=graph,output_path=destination,profile=profile)
    symlink=tmp_path/"alias.mp4"
    symlink.symlink_to(destination)
    with pytest.raises(SemanticContractError,match="UNSAFE_OUTPUT_PATH"):
        render(spec=spec,graph=graph,output_path=symlink,profile=profile)
    assert destination.read_bytes()==b"keep-me"
