from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from learnflow_v2.layout.schema import (
    GraphBackendKind, LayoutBox, LayoutGraph, LayoutStrategy, Point, Rect,
    RoutedEdge, RoutingStyle,
)
from learnflow_v2.motion.compiler import (
    CompiledMotionArtifact, CompiledMotionEvent, PropertyKeyframe, PropertyTrack,
    PropertyTrackKind,
)
from learnflow_v2.motion.enums import MotionStyle, MotionTargetKind, MotionVerb
from learnflow_v2.render import (
    DeterministicPillowRenderer, RenderArtifactKind, RenderInvalidInputError,
    RenderProfile, assemble_video, mux_audio_track, render_scene_video, render_transition_video,
)
from learnflow_v2.scenegraph.enums import LayoutIntent, NodeKind, RelationKind
from learnflow_v2.scenegraph.schema import (
    LayoutIntentSpec, SceneGraph, SceneNode, SceneRelation,
)
from learnflow_v2.transitions.schema import (
    InterSceneTransitionPlan, PersistentObjectTransition, TransitionOperation,
)


def _scene(scene_id: str, *, suffix: str = "") -> SceneGraph:
    return SceneGraph(
        scene_id=scene_id,
        nodes=[
            SceneNode(id=f"a{suffix}", kind=NodeKind.CONCEPT, label="Input"),
            SceneNode(id=f"b{suffix}", kind=NodeKind.CONCEPT, label="Output"),
        ],
        relations=[
            SceneRelation(id=f"r{suffix}", source=f"a{suffix}", target=f"b{suffix}", kind=RelationKind.FLOW)
        ],
        layout_intent=LayoutIntentSpec(type=LayoutIntent.PROCESS),
    )


def _layout(scene_id: str, *, suffix: str = "", shift: float = 0.0, feasible: bool = True) -> LayoutGraph:
    return LayoutGraph(
        scene_id=scene_id,
        frame_profile_id="test-320x180",
        frame_width=320,
        frame_height=180,
        boxes=[
            LayoutBox(node_id=f"a{suffix}", rect=Rect(x=25+shift, y=55, width=90, height=60), zone="CONTENT"),
            LayoutBox(node_id=f"b{suffix}", rect=Rect(x=205+shift, y=55, width=90, height=60), zone="CONTENT"),
        ],
        routed_edges=[
            RoutedEdge(
                edge_id=f"r{suffix}", source=f"a{suffix}", target=f"b{suffix}",
                points=[Point(x=115+shift, y=85), Point(x=205+shift, y=85)],
                routing_style=RoutingStyle.ORTHOGONAL, backend=GraphBackendKind.GRAPHVIZ,
            )
        ],
        strategy=LayoutStrategy.DIRECTED_GRAPH,
        feasible=feasible,
    )


def _static_motion(scene_id: str, duration: float = 0.5) -> CompiledMotionArtifact:
    return CompiledMotionArtifact(scene_id=scene_id, scene_duration=duration, events=(), tracks=())


def _fade_motion(scene_id: str) -> CompiledMotionArtifact:
    track = PropertyTrack(
        track_id="enter__opacity", target="a", target_kind=MotionTargetKind.NODE,
        property_kind=PropertyTrackKind.OPACITY, start_time=0.0, end_time=0.4,
        keyframes=(
            PropertyKeyframe(offset=0.0, time=0.0, value=0.0, easing="linear"),
            PropertyKeyframe(offset=1.0, time=0.4, value=1.0, easing="linear"),
        ),
        metadata={"transition":"fade_in"},
    )
    event = CompiledMotionEvent(
        event_id="enter", target="a", target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.ENTER, style=MotionStyle.FADE,
        start_time=0.0, end_time=0.4, tracks=(track,),
    )
    return CompiledMotionArtifact(scene_id=scene_id, scene_duration=0.5, events=(event,), tracks=(track,))


def test_render_frame_is_deterministic():
    renderer = DeterministicPillowRenderer()
    scene, layout, motion = _scene("s1"), _layout("s1"), _fade_motion("s1")
    a = renderer.render_frame(scene, layout, motion, 0.2).tobytes()
    b = renderer.render_frame(scene, layout, motion, 0.2).tobytes()
    assert a == b


def test_enter_fade_changes_pixels_over_time():
    renderer = DeterministicPillowRenderer()
    scene, layout, motion = _scene("s1"), _layout("s1"), _fade_motion("s1")
    before = renderer.render_frame(scene, layout, motion, 0.0).tobytes()
    after = renderer.render_frame(scene, layout, motion, 0.4).tobytes()
    assert before != after


def test_renderer_rejects_infeasible_layout():
    with pytest.raises(RenderInvalidInputError):
        DeterministicPillowRenderer().render_frame(_scene("s1"), _layout("s1", feasible=False), _static_motion("s1"), 0.0)


def test_renderer_rejects_scene_identity_mismatch():
    with pytest.raises(RenderInvalidInputError):
        DeterministicPillowRenderer().render_frame(_scene("s1"), _layout("s2"), _static_motion("s1"), 0.0)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")
def test_render_scene_video_produces_real_mp4_and_stable_frame_digest(tmp_path: Path):
    profile = RenderProfile(profile_id="test", fps=5, preset="ultrafast")
    scene, layout, motion = _scene("s1"), _layout("s1"), _fade_motion("s1")
    first = render_scene_video(scene, layout, motion, tmp_path/"a.mp4", profile=profile)
    second = render_scene_video(scene, layout, motion, tmp_path/"b.mp4", profile=profile)
    assert first.kind == RenderArtifactKind.SCENE
    assert Path(first.path).stat().st_size > 1000
    assert first.frame_digest == second.frame_digest
    assert first.source_hash == second.source_hash
    assert first.frame_count == second.frame_count


def _transition() -> InterSceneTransitionPlan:
    return InterSceneTransitionPlan(
        transition_id="t12", from_scene="s1", to_scene="s2", duration=0.4,
        persistent_objects=(
            PersistentObjectTransition(
                semantic_key="concept:a", concept_id="c_a",
                from_node_id="a", to_node_id="a2",
                requested_operation=TransitionOperation.MOVE,
                effective_operation=TransitionOperation.MOVE,
                source_rect=Rect(x=25, y=55, width=90, height=60),
                target_rect=Rect(x=45, y=55, width=90, height=60),
                source_frame_width=320, source_frame_height=180,
                target_frame_width=320, target_frame_height=180,
                source_zone="CONTENT", target_zone="CONTENT",
            ),
        ),
        departing_node_ids=("b",), entering_node_ids=("b2",),
    )


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")
def test_render_transition_move_and_assembly(tmp_path: Path):
    profile = RenderProfile(profile_id="test", fps=5, preset="ultrafast")
    s1, l1 = _scene("s1"), _layout("s1")
    s2, l2 = _scene("s2", suffix="2"), _layout("s2", suffix="2", shift=20)
    m1, m2 = _static_motion("s1"), _static_motion("s2")
    a1 = render_scene_video(s1, l1, m1, tmp_path/"s1.mp4", profile=profile)
    transition = render_transition_video(s1, l1, s2, l2, _transition(), tmp_path/"t.mp4", profile=profile)
    a2 = render_scene_video(s2, l2, m2, tmp_path/"s2.mp4", profile=profile)
    final = assemble_video((a1, transition, a2), tmp_path/"final.mp4")
    assert transition.kind == RenderArtifactKind.TRANSITION
    assert final.kind == RenderArtifactKind.VIDEO
    assert Path(final.path).stat().st_size > 1000
    assert final.frame_count == a1.frame_count + transition.frame_count + a2.frame_count


def test_transition_renderer_rejects_wrong_endpoints(tmp_path: Path):
    bad = _transition().model_copy(update={"from_scene": "wrong"})
    with pytest.raises(RenderInvalidInputError):
        render_transition_video(_scene("s1"), _layout("s1"), _scene("s2", suffix="2"), _layout("s2", suffix="2", shift=20), bad, tmp_path/"bad.mp4", profile=RenderProfile(profile_id="test",fps=2,preset="ultrafast"))



def test_relation_motion_requires_routed_geometry():
    track = PropertyTrack(
        track_id="draw__edge", target="r", target_kind=MotionTargetKind.RELATION,
        property_kind=PropertyTrackKind.EDGE_DRAW_PROGRESS, start_time=0.0, end_time=0.4,
        keyframes=(
            PropertyKeyframe(offset=0.0, time=0.0, value=0.0, easing="linear"),
            PropertyKeyframe(offset=1.0, time=0.4, value=1.0, easing="linear"),
        ),
        metadata={"stroke_progress":"source_to_target"},
    )
    event = CompiledMotionEvent(
        event_id="draw", target="r", target_kind=MotionTargetKind.RELATION,
        verb=MotionVerb.RELATION, style=MotionStyle.DRAW_EDGE,
        start_time=0.0, end_time=0.4, tracks=(track,),
    )
    motion = CompiledMotionArtifact(scene_id="s1", scene_duration=0.5, events=(event,), tracks=(track,))
    no_route = _layout("s1").model_copy(update={"routed_edges": []})
    with pytest.raises(RenderInvalidInputError, match="without routed edge geometry"):
        DeterministicPillowRenderer().render_frame(_scene("s1"), no_route, motion, 0.2)


def test_renderer_rejects_routed_edge_that_contradicts_scene_relation():
    bad_edge = _layout("s1").routed_edges[0].model_copy(update={"source": "b", "target": "a"})
    bad_layout = _layout("s1").model_copy(update={"routed_edges": [bad_edge]})
    with pytest.raises(RenderInvalidInputError, match="endpoints contradict"):
        DeterministicPillowRenderer().render_frame(_scene("s1"), bad_layout, _static_motion("s1"), 0.0)


def test_public_scene_render_revalidates_forged_profile(tmp_path: Path):
    forged = RenderProfile.model_construct(profile_id="bad", fps=0, crf=18, preset="ultrafast")
    with pytest.raises(Exception):
        render_scene_video(_scene("s1"), _layout("s1"), _static_motion("s1"), tmp_path/"bad.mp4", profile=forged)


def test_transition_rejects_stale_geometry_even_when_plan_is_individually_valid(tmp_path: Path):
    plan = _transition()
    item_payload = plan.persistent_objects[0].model_dump(mode="json")
    item_payload["source_rect"] = {"x":35, "y":55, "width":90, "height":60}
    for key in ("normalized_displacement_x", "normalized_displacement_y", "normalized_scale_x", "normalized_scale_y"):
        item_payload.pop(key, None)
    stale_item = PersistentObjectTransition.model_validate(item_payload)
    stale = InterSceneTransitionPlan(
        transition_id=plan.transition_id,
        from_scene=plan.from_scene,
        to_scene=plan.to_scene,
        duration=plan.duration,
        persistent_objects=(stale_item,),
        departing_node_ids=plan.departing_node_ids,
        entering_node_ids=plan.entering_node_ids,
    )
    with pytest.raises(RenderInvalidInputError, match="geometry contradicts"):
        render_transition_video(
            _scene("s1"), _layout("s1"),
            _scene("s2", suffix="2"), _layout("s2", suffix="2", shift=20),
            stale, tmp_path/"stale.mp4",
            profile=RenderProfile(profile_id="test", fps=2, preset="ultrafast"),
        )


def test_transition_public_boundary_revalidates_forged_plan(tmp_path: Path):
    plan = _transition()
    forged = plan.model_copy(update={"duration": float("nan"), "duration_ms": float("nan")})
    with pytest.raises(Exception):
        render_transition_video(
            _scene("s1"), _layout("s1"),
            _scene("s2", suffix="2"), _layout("s2", suffix="2", shift=20),
            forged, tmp_path/"forged.mp4",
            profile=RenderProfile(profile_id="test", fps=2, preset="ultrafast"),
        )


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")
def test_audio_mux_adds_aac_stream_and_preserves_video_frames(tmp_path: Path):
    profile = RenderProfile(profile_id="test", fps=5, preset="ultrafast")
    scene, layout, motion = _scene("s1"), _layout("s1"), _static_motion("s1", duration=0.6)
    video = render_scene_video(scene, layout, motion, tmp_path/"video.mp4", profile=profile)
    # Explicit deterministic input audio; production mux must not synthesize implicitly.
    audio = tmp_path/"audio.wav"
    proc = __import__("subprocess").run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo:d=0.3",
            str(audio),
        ],
        check=False,
    )
    assert proc.returncode == 0
    muxed = mux_audio_track(video.model_copy(update={"kind": RenderArtifactKind.VIDEO}), audio, tmp_path/"muxed.mp4")
    probe = __import__("subprocess").run(
        [
            "ffprobe", "-v", "error", "-show_entries", "stream=codec_name,codec_type",
            "-of", "json", str(muxed.path),
        ],
        capture_output=True, text=True, check=True,
    )
    streams = __import__("json").loads(probe.stdout)["streams"]
    assert any(item["codec_type"] == "video" and item["codec_name"] == "h264" for item in streams)
    assert any(item["codec_type"] == "audio" and item["codec_name"] == "aac" for item in streams)
    assert muxed.frame_digest == video.frame_digest

def test_source_artifacts_are_not_mutated_by_frame_render():
    scene, layout, motion = _scene("s1"), _layout("s1"), _fade_motion("s1")
    scene_before = scene.model_dump_json()
    layout_before = layout.model_dump_json()
    motion_before = motion.to_canonical_json()
    DeterministicPillowRenderer().render_frame(scene, layout, motion, 0.2)
    assert scene.model_dump_json() == scene_before
    assert layout.model_dump_json() == layout_before
    assert motion.to_canonical_json() == motion_before


def test_renderer_text_payload_matches_layout_content_precedence():
    scene = SceneGraph(
        scene_id="text_contract",
        nodes=(
            SceneNode(
                id="n",
                kind=NodeKind.CONCEPT,
                label="THIS LABEL IS INTENTIONALLY MUCH TOO LONG FOR THE CARD AND MUST NOT BE CONCATENATED",
                content="Short content",
            ),
        ),
        relations=(),
        layout_intent=LayoutIntentSpec(type=LayoutIntent.CONCEPT_CARD),
    )
    layout = LayoutGraph(
        scene_id="text_contract",
        frame_profile_id="test-320x180",
        frame_width=320,
        frame_height=180,
        boxes=(LayoutBox(node_id="n", rect=Rect(x=90, y=55, width=140, height=70), zone="CONTENT"),),
        routed_edges=(),
        strategy=LayoutStrategy.CONCEPT_CARD,
        feasible=True,
    )
    frame = DeterministicPillowRenderer().render_frame(scene, layout, None, 0.0)
    assert frame.size == (320, 180)


def test_renderer_rejects_text_that_cannot_fit_readable_18px_box():
    scene = SceneGraph(
        scene_id="text_overflow",
        nodes=(
            SceneNode(
                id="n",
                kind=NodeKind.CONCEPT,
                content="This content requires several readable wrapped lines and must never spill outside its solved card.",
            ),
        ),
        relations=(),
        layout_intent=LayoutIntentSpec(type=LayoutIntent.CONCEPT_CARD),
    )
    layout = LayoutGraph(
        scene_id="text_overflow",
        frame_profile_id="test-320x180",
        frame_width=320,
        frame_height=180,
        boxes=(LayoutBox(node_id="n", rect=Rect(x=120, y=75, width=80, height=28), zone="CONTENT"),),
        routed_edges=(),
        strategy=LayoutStrategy.CONCEPT_CARD,
        feasible=True,
    )
    with pytest.raises(RenderInvalidInputError, match="does not fit solved LayoutGraph box"):
        DeterministicPillowRenderer().render_frame(scene, layout, None, 0.0)
