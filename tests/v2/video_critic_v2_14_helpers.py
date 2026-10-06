from __future__ import annotations

from learnflow_v2.videoqa import (
    VideoCriticDimension,
    VideoCriticIssue,
    VideoDimensionAssessment,
    VideoCriticRecommendation,
    VideoCriticRequest,
    VideoCriticResponse,
    VideoCriticStatus,
    VideoIssueSeverity,
    VideoIssueType,
    VideoRecommendationOp,
    VideoSceneSummary,
    VideoTransitionSummary,
    VisualModality,
)


def assessments(*failed: VideoCriticDimension) -> tuple[VideoDimensionAssessment, ...]:
    failed_set = set(failed)
    return tuple(
        VideoDimensionAssessment(
            dimension=dimension,
            passed=dimension not in failed_set,
            summary=("Needs review" if dimension in failed_set else "No issue detected"),
        )
        for dimension in VideoCriticDimension
    )


def make_request() -> VideoCriticRequest:
    scenes = (
        VideoSceneSummary(
            scene_id="s1", ordinal=0, duration=3.0,
            narration="First explain the prediction.", visual_modality=VisualModality.DIAGRAM,
            style_signature=("dark", "blue-accent"), concept_keys=("concept:prediction",),
            learning_objective_ids=("obj:1",), representative_frame_ref="frame://s1",
            scene_quality_approved=True, quality_artifact_id="qa:s1", quality_artifact_hash="1"*64,
        ),
        VideoSceneSummary(
            scene_id="s2", ordinal=1, duration=4.0,
            narration="Then connect prediction to loss.", visual_modality=VisualModality.DIAGRAM,
            style_signature=("dark", "blue-accent"), concept_keys=("concept:prediction", "concept:loss"),
            learning_objective_ids=("obj:1", "obj:2"), representative_frame_ref="frame://s2",
            scene_quality_approved=True, quality_artifact_id="qa:s2", quality_artifact_hash="2"*64,
        ),
        VideoSceneSummary(
            scene_id="s3", ordinal=2, duration=3.0,
            narration="Finally compare prediction and target.", visual_modality=VisualModality.COMPARISON,
            style_signature=("dark", "blue-accent"), concept_keys=("concept:prediction", "concept:target"),
            learning_objective_ids=("obj:2",), representative_frame_ref="frame://s3",
            scene_quality_approved=True, quality_artifact_id="qa:s3", quality_artifact_hash="3"*64,
        ),
    )
    transitions = (
        VideoTransitionSummary(
            transition_id="t12", from_scene_id="s1", to_scene_id="s2", duration=0.5,
            effective_operation="MOVE", persistent_semantic_keys=("concept:prediction",),
        ),
        VideoTransitionSummary(
            transition_id="t23", from_scene_id="s2", to_scene_id="s3", duration=0.5,
            effective_operation="FADE", fallback_reason="backend_unsupported_move",
            persistent_semantic_keys=("concept:prediction",),
        ),
    )
    return VideoCriticRequest(
        video_id="video-1", final_video_ref="video://draft", video_artifact_hash="a"*64, lesson_goal="Explain prediction and loss clearly.",
        lesson_objective_ids=("obj:1", "obj:2"), total_duration=11.0,
        scenes=scenes, transitions=transitions,
    )


def make_review_response() -> VideoCriticResponse:
    return VideoCriticResponse(
        status=VideoCriticStatus.REVIEW_REQUIRED,
        dimension_assessments=assessments(VideoCriticDimension.VISUAL_VARIETY, VideoCriticDimension.CONTINUITY),
        issues=(
            VideoCriticIssue(
                issue_id="repeat", issue_type=VideoIssueType.VISUAL_REPETITION,
                severity=VideoIssueSeverity.MEDIUM, scene_ids=("s1", "s2"),
                reason="Two adjacent scenes use the same diagram modality.",
            ),
            VideoCriticIssue(
                issue_id="continuity", issue_type=VideoIssueType.TRANSITION_CONTINUITY,
                severity=VideoIssueSeverity.HIGH, scene_ids=("s2", "s3"), transition_ids=("t23",),
                reason="Persistent prediction concept loses spatial continuity.",
            ),
        ),
        recommendations=(
            VideoCriticRecommendation(
                recommendation_id="vary", op=VideoRecommendationOp.CHANGE_VISUAL_MODALITY,
                scene_ids=("s2",), rationale="Use an illustration to break repetition.",
                suggested_modality=VisualModality.ILLUSTRATION,
            ),
            VideoCriticRecommendation(
                recommendation_id="fix-continuity", op=VideoRecommendationOp.FIX_CONTINUITY,
                scene_ids=("s2", "s3"), rationale="Preserve the prediction concept through the transition.",
            ),
        ),
    )
