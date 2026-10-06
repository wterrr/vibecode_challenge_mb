from __future__ import annotations

import math
from pathlib import Path
from types import SimpleNamespace
import wave

import pytest

from learnflow_v2.layout.schema import LayoutBox, LayoutGraph, LayoutStrategy, Rect
from learnflow_v2.motion import MotionEvent, MotionPlan, MotionStyle, MotionVerb, schedule_motion_plan
from learnflow_v2.motion.compiler import compile_motion_schedule
from learnflow_v2.render import PillowFFmpegRenderer, RenderInvalidInputError, assemble_rendered_scenes
from learnflow_v2.scenegraph import LayoutIntentSpec, SceneGraph, SceneNode
from learnflow_v2.scenegraph.enums import LayoutIntent, NodeKind, ScenePurpose


def make_scene(scene_id: str = "scene_a", *, long_text: bool = False):
    body = "A deterministic renderer turns semantic artifacts into pixels."
    if long_text:
        body = " ".join([body] * 80)
    graph = SceneGraph(
        scene_id=scene_id,
        purpose=ScenePurpose.EXPLAIN,
        concept="Rendering",
        nodes=[
            SceneNode(id="title", kind=NodeKind.CONCEPT, label="LearnFlow Renderer", semantic_role="PRIMARY_CONCEPT"),
            SceneNode(id="body", kind=NodeKind.TEXT, label=body, semantic_role="SUPPORTING_POINT"),
        ],
        relations=[],
        groups=[],
        layout_intent=LayoutIntentSpec(type=LayoutIntent.CONCEPT_CARD),
    )
    layout = LayoutGraph(
        scene_id=scene_id,
        frame_profile_id="16:9_640x360",
        frame_width=640.0,
        frame_height=360.0,
        boxes=[
            LayoutBox(node_id="title", rect=Rect(x=32, y=24, width=576, height=72), zone="TITLE", strategy_role="title"),
            LayoutBox(node_id="body", rect=Rect(x=80, y=125, width=480, height=160), zone="CONTENT", strategy_role="content"),
        ],
        routed_edges=[],
        strategy=LayoutStrategy.CONCEPT_CARD,
        feasible=True,
        metadata={},
    )
    plan = MotionPlan(
        scene_id=scene_id,
        events=(
            MotionEvent(id="enter_title", target="title", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
            MotionEvent(id="enter_body", target="body", verb=MotionVerb.ENTER, style=MotionStyle.SLIDE),
            MotionEvent(id="focus_body", target="body", verb=MotionVerb.EMPHASIZE, style=MotionStyle.HIGHLIGHT),
        ),
    )
    schedule = schedule_motion_plan(plan, scene_duration=3.0, graph=graph)
    return graph, layout, compile_motion_schedule(schedule)


def tone(path: Path, duration: float, rate: int = 48000) -> Path:
    frames = int(round(duration * rate))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(rate)
        for i in range(frames):
            sample = int(2400 * math.sin(2.0 * math.pi * 220.0 * i / rate))
            wav.writeframesraw(sample.to_bytes(2, byteorder="little", signed=True))
    return path


def test_renderer_outputs_real_mp4_and_audio(tmp_path):
    graph, layout, motion = make_scene()
    result = PillowFFmpegRenderer(fps=12).render(
        scene_graph=graph, layout_graph=layout, motion=motion,
        output_path=tmp_path / "scene.mp4", audio_path=tone(tmp_path / "tone.wav", 3.0),
    )
    assert Path(result.output_path).is_file()
    assert result.file_size_bytes > 10_000
    assert result.width == 640 and result.height == 360 and result.fps == 12
    assert result.has_audio is True
    assert abs(result.rendered_duration - 3.0) <= 0.12
    assert len(result.sampled_frames) == 3
    assert result.sampled_frames[0].sha256 != result.sampled_frames[-1].sha256


def test_renderer_visual_digest_is_reproducible(tmp_path):
    graph, layout, motion = make_scene()
    renderer = PillowFFmpegRenderer(fps=12)
    one = renderer.render(scene_graph=graph, layout_graph=layout, motion=motion, output_path=tmp_path / "one.mp4")
    two = renderer.render(scene_graph=graph, layout_graph=layout, motion=motion, output_path=tmp_path / "two.mp4")
    assert one.visual_digest == two.visual_digest
    assert tuple(x.sha256 for x in one.sampled_frames) == tuple(x.sha256 for x in two.sampled_frames)


def test_renderer_detects_text_truncation_evidence(tmp_path):
    graph, layout, motion = make_scene(long_text=True)
    result = PillowFFmpegRenderer(fps=12).render(scene_graph=graph, layout_graph=layout, motion=motion, output_path=tmp_path / "long.mp4")
    body = next(item for item in result.text_evidence if item.element_id == "body")
    assert body.truncated is True
    assert body.rendered_chars < body.source_chars


def test_renderer_rejects_scene_id_mismatch(tmp_path):
    graph, layout, motion = make_scene()
    with pytest.raises(RenderInvalidInputError):
        PillowFFmpegRenderer().render(scene_graph=graph, layout_graph=layout.model_copy(update={"scene_id": "other"}), motion=motion, output_path=tmp_path / "x.mp4")


def test_renderer_rejects_missing_layout_node(tmp_path):
    graph, layout, motion = make_scene()
    with pytest.raises(RenderInvalidInputError):
        PillowFFmpegRenderer().render(scene_graph=graph, layout_graph=layout.model_copy(update={"boxes": layout.boxes[:1]}), motion=motion, output_path=tmp_path / "x.mp4")


def test_renderer_revalidates_model_construct_bypass(tmp_path):
    graph, layout, motion = make_scene()
    forged = LayoutGraph.model_construct(
        schema_version="2.1", scene_id=graph.scene_id, frame_profile_id="x", frame_width=640.0, frame_height=360.0,
        boxes=[], routed_edges=[], strategy=LayoutStrategy.CONCEPT_CARD, feasible=True, metadata={},
    )
    with pytest.raises(Exception):
        PillowFFmpegRenderer().render(scene_graph=graph, layout_graph=forged, motion=motion, output_path=tmp_path / "x.mp4")


def test_assembly_consumes_adjacent_transition_contract_and_falls_back_to_fade(tmp_path):
    renderer = PillowFFmpegRenderer(fps=12)
    g1, l1, m1 = make_scene("s1"); g2, l2, m2 = make_scene("s2")
    r1 = renderer.render(scene_graph=g1, layout_graph=l1, motion=m1, output_path=tmp_path / "s1.mp4", audio_path=tone(tmp_path / "a1.wav", 3.0))
    r2 = renderer.render(scene_graph=g2, layout_graph=l2, motion=m2, output_path=tmp_path / "s2.mp4", audio_path=tone(tmp_path / "a2.wav", 3.0))
    transition = SimpleNamespace(
        transition_id="t12", from_scene="s1", to_scene="s2", duration=0.4,
        persistent_objects=(SimpleNamespace(effective_operation=SimpleNamespace(value="MOVE")),),
    )
    video = assemble_rendered_scenes(video_id="v", scenes=(r1, r2), transition_plans=(transition,), output_path=tmp_path / "final.mp4")
    assert Path(video.output_path).is_file()
    assert video.file_size_bytes > 10_000
    assert video.transition_ids == ("t12",)
    assert any("FALLBACK" in item for item in video.diagnostics)
    assert 5.4 <= video.duration <= 5.8


def test_assembly_rejects_transition_endpoint_mismatch(tmp_path):
    renderer = PillowFFmpegRenderer(fps=12)
    g1, l1, m1 = make_scene("s1"); g2, l2, m2 = make_scene("s2")
    r1 = renderer.render(scene_graph=g1, layout_graph=l1, motion=m1, output_path=tmp_path / "s1.mp4")
    r2 = renderer.render(scene_graph=g2, layout_graph=l2, motion=m2, output_path=tmp_path / "s2.mp4")
    transition = SimpleNamespace(transition_id="bad", from_scene="s1", to_scene="s3", duration=0.4, persistent_objects=())
    with pytest.raises(RenderInvalidInputError):
        assemble_rendered_scenes(video_id="v", scenes=(r1, r2), transition_plans=(transition,), output_path=tmp_path / "bad.mp4")
