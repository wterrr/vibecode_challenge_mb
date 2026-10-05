from __future__ import annotations

from learnflow_v2.layout.schema import LayoutBox, LayoutGraph, LayoutStrategy, Rect
from learnflow_v2.qa import (
    AssetProbe, AudioProbe, DeterministicQAReport, FrameProbe, QAIssueCode,
    RenderedSceneProbe, TextElementProbe, VisualElementProbe,
)


def _box(node_id: str, x: float, y: float, width: float, height: float, *, role: str = "content", zone: str = "CONTENT") -> LayoutBox:
    return LayoutBox(
        node_id=node_id,
        rect=Rect(x=x, y=y, width=width, height=height),
        zone=zone,
        strategy_role=role,
    )


def _layout(*boxes: LayoutBox, scene_id: str = "scene_qa", strategy: LayoutStrategy = LayoutStrategy.CONCEPT_CARD, routed_edges=()) -> LayoutGraph:
    return LayoutGraph(
        scene_id=scene_id,
        frame_profile_id="16:9_1280x720",
        frame_width=1280.0,
        frame_height=720.0,
        boxes=list(boxes),
        routed_edges=list(routed_edges),
        strategy=strategy,
        feasible=True,
        metadata={},
    )


def _good_layout(scene_id: str = "scene_qa") -> LayoutGraph:
    return _layout(
        _box("n1", 180.0, 220.0, 260.0, 120.0),
        _box("n2", 620.0, 220.0, 260.0, 120.0),
        scene_id=scene_id,
    )


def _good_probe(scene_id: str = "scene_qa", **updates) -> RenderedSceneProbe:
    data = dict(
        scene_id=scene_id,
        expected_duration=5.0,
        rendered_duration=5.0,
        text_elements=(TextElementProbe(element_id="label", font_size_px=24.0, alpha=1.0),),
        visual_elements=(VisualElementProbe(element_id="diagram", alpha=1.0),),
        assets=(AssetProbe(asset_id="asset:diagram", required=True, exists=True),),
        frames=(FrameProbe(timestamp=1.0, mean_luma=18.0, non_black_fraction=0.08),),
        audio=AudioProbe(duration=5.0, rms_windows=(0.03, 0.05, 0.02), expected_audio=True),
        subtitles=(),
    )
    data.update(updates)
    return RenderedSceneProbe(**data)


def _codes(report: DeterministicQAReport) -> set[QAIssueCode]:
    return {issue.code for issue in report.issues}
