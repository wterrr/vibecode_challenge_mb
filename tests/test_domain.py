"""Unit tests for domain models, validation, and contracts."""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError, TypeAdapter

from app.domain.enums import JobStage, JobStatus, RUNNING_STAGE_ORDER, VisualIntent
from app.domain.errors import JobError
from app.domain.jobs import Job
from app.domain.lesson import (
    ComparisonColumn,
    ComparisonSpec,
    ConceptCardSpec,
    IllustrationSpec,
    LearningRequest,
    LessonPlan,
    ProcessActor,
    ProcessDiagramSpec,
    ProcessStep,
    ScenePlan,
    VisualSpec,
)
from app.domain.timeline import ResolvedSceneTiming, ResolvedTimeline


# ============================================================================
# Enums
# ============================================================================

def test_enums_and_stage_order():
    assert JobStatus.QUEUED.value == "queued"
    assert JobStatus.RUNNING.value == "running"
    assert JobStatus.SUCCEEDED.value == "succeeded"
    assert JobStatus.FAILED.value == "failed"

    assert len(RUNNING_STAGE_ORDER) == 6
    assert RUNNING_STAGE_ORDER[0] == JobStage.PLANNING
    assert RUNNING_STAGE_ORDER[-1] == JobStage.VALIDATING_OUTPUT

    assert len(VisualIntent) == 4
    assert {v.value for v in VisualIntent} == {
        "concept_card",
        "process_diagram",
        "comparison",
        "illustration",
    }


# ============================================================================
# LearningRequest
# ============================================================================

def test_learning_request_valid():
    req = LearningRequest(
        topic="How does TCP work?",
        audience="Software Engineers",
        language="en",
        target_duration_seconds=90,
    )
    assert req.topic == "How does TCP work?"
    assert req.audience == "Software Engineers"
    assert req.language == "en"
    assert req.target_duration_seconds == 90
    assert req.visual_style == "clean"


def test_learning_request_whitespace_normalization():
    req = LearningRequest(
        topic="   How   does  TCP   work?   ",
        audience="   Beginner   Students  ",
    )
    assert req.topic == "How does TCP work?"
    assert req.audience == "Beginner Students"


def test_learning_request_normalized_minimum_lengths():
    # Whitespace padding that reduces below min_length after normalization
    with pytest.raises(ValidationError):
        LearningRequest(topic="  a  ")

    with pytest.raises(ValidationError):
        LearningRequest(
            topic="valid topic",
            audience=" a ",
        )

    # Prove valid normalization still works and meets bounds
    req = LearningRequest(topic="   How   does TCP work?   ")
    assert req.topic == "How does TCP work?"


def test_learning_request_invalid_empty_or_short_topic():
    with pytest.raises(ValidationError):
        LearningRequest(topic="   ")

    with pytest.raises(ValidationError):
        LearningRequest(topic="ab")


def test_learning_request_invalid_language():
    with pytest.raises(ValidationError):
        LearningRequest(topic="Valid Topic", language="fr")  # type: ignore


def test_learning_request_invalid_duration():
    with pytest.raises(ValidationError):
        LearningRequest(topic="Valid Topic", target_duration_seconds=45)  # type: ignore


# ============================================================================
# Visual Specs
# ============================================================================

def test_concept_card_spec_valid_and_bounds():
    spec = ConceptCardSpec(
        heading="TCP Basics",
        points=["Reliable", "Ordered", "Connection-oriented"],
        emphasis=["Reliable"],
    )
    assert spec.type == "concept_card"
    assert len(spec.points) == 3

    # Zero points invalid
    with pytest.raises(ValidationError):
        ConceptCardSpec(heading="Title", points=[])

    # > 5 points invalid
    with pytest.raises(ValidationError):
        ConceptCardSpec(heading="Title", points=["1", "2", "3", "4", "5", "6"])


def test_process_diagram_spec_valid():
    spec = ProcessDiagramSpec(
        title="TCP 3-Way Handshake",
        actors=[
            ProcessActor(id="client", label="Client"),
            ProcessActor(id="server", label="Server"),
        ],
        steps=[
            ProcessStep(order=1, from_actor="client", to_actor="server", label="SYN"),
            ProcessStep(order=2, from_actor="server", to_actor="client", label="SYN-ACK"),
            ProcessStep(order=3, from_actor="client", to_actor="server", label="ACK"),
        ],
    )
    assert spec.type == "process_diagram"
    assert len(spec.actors) == 2
    assert len(spec.steps) == 3


def test_process_diagram_duplicate_actor_ids():
    with pytest.raises(ValidationError, match="Duplicate actor id"):
        ProcessDiagramSpec(
            title="Invalid",
            actors=[
                ProcessActor(id="node", label="Node 1"),
                ProcessActor(id="node", label="Node 2"),
            ],
            steps=[ProcessStep(order=1, label="Step 1")],
        )


def test_process_diagram_unknown_actor_reference():
    with pytest.raises(ValidationError, match="undefined from_actor"):
        ProcessDiagramSpec(
            title="Invalid",
            actors=[ProcessActor(id="client", label="Client")],
            steps=[
                ProcessStep(
                    order=1,
                    from_actor="server",  # undefined
                    label="Test",
                )
            ],
        )


def test_process_diagram_step_order_non_contiguous_or_duplicate():
    # Duplicate order
    with pytest.raises(ValidationError, match="unique"):
        ProcessDiagramSpec(
            title="Invalid",
            actors=[ProcessActor(id="a", label="A")],
            steps=[
                ProcessStep(order=1, label="One"),
                ProcessStep(order=1, label="Duplicate"),
            ],
        )

    # Non-contiguous order (1, 3)
    with pytest.raises(ValidationError, match="contiguous"):
        ProcessDiagramSpec(
            title="Invalid",
            actors=[ProcessActor(id="a", label="A")],
            steps=[
                ProcessStep(order=1, label="One"),
                ProcessStep(order=3, label="Three"),
            ],
        )


def test_process_diagram_too_many_steps():
    steps = [ProcessStep(order=i, label=f"Step {i}") for i in range(1, 10)]  # 9 steps
    with pytest.raises(ValidationError):
        ProcessDiagramSpec(
            title="Too Many Steps",
            actors=[ProcessActor(id="a", label="A")],
            steps=steps,
        )


def test_comparison_spec_columns_valid_and_bounds():
    # 2 columns valid
    spec2 = ComparisonSpec(
        title="TCP vs UDP",
        columns=[
            ComparisonColumn(title="TCP", points=["Reliable"]),
            ComparisonColumn(title="UDP", points=["Fast"]),
        ],
    )
    assert len(spec2.columns) == 2

    # 3 columns valid
    spec3 = ComparisonSpec(
        title="Three-way Comparison",
        columns=[
            ComparisonColumn(title="A", points=["p1"]),
            ComparisonColumn(title="B", points=["p2"]),
            ComparisonColumn(title="C", points=["p3"]),
        ],
    )
    assert len(spec3.columns) == 3

    # 1 column invalid
    with pytest.raises(ValidationError):
        ComparisonSpec(
            title="1 col",
            columns=[ComparisonColumn(title="TCP", points=["Reliable"])],
        )

    # 4 columns invalid
    with pytest.raises(ValidationError):
        ComparisonSpec(
            title="4 col",
            columns=[
                ComparisonColumn(title="A", points=["p1"]),
                ComparisonColumn(title="B", points=["p2"]),
                ComparisonColumn(title="C", points=["p3"]),
                ComparisonColumn(title="D", points=["p4"]),
            ],
        )


def test_illustration_spec():
    spec = IllustrationSpec(
        prompt="A diagram showing light photons interacting with chlorophyll",
        fallback_heading="Photosynthesis Core",
        fallback_points=["Light absorption", "Chemical energy"],
    )
    assert spec.type == "illustration"

    # Empty or short after normalization invalid
    with pytest.raises(ValidationError):
        IllustrationSpec(
            prompt="  ",
            fallback_heading="Heading",
            fallback_points=["Point"],
        )

    with pytest.raises(ValidationError):
        IllustrationSpec(
            prompt=" a ",
            fallback_heading="Heading",
            fallback_points=["Point"],
        )


def test_visual_spec_discriminated_union():
    adapter = TypeAdapter(VisualSpec)

    raw_card = {
        "type": "concept_card",
        "heading": "Title",
        "points": ["Point 1"],
    }
    parsed_card = adapter.validate_python(raw_card)
    assert isinstance(parsed_card, ConceptCardSpec)

    raw_diagram = {
        "type": "process_diagram",
        "title": "Process",
        "actors": [{"id": "client", "label": "Client"}],
        "steps": [{"order": 1, "label": "Start"}],
    }
    parsed_diagram = adapter.validate_python(raw_diagram)
    assert isinstance(parsed_diagram, ProcessDiagramSpec)

    raw_comparison = {
        "type": "comparison",
        "title": "Comparison",
        "columns": [
            {"title": "Col A", "points": ["p1"]},
            {"title": "Col B", "points": ["p2"]},
        ],
    }
    parsed_comparison = adapter.validate_python(raw_comparison)
    assert isinstance(parsed_comparison, ComparisonSpec)

    raw_illustration = {
        "type": "illustration",
        "prompt": "Solar cell layers",
        "fallback_heading": "Solar Cell",
        "fallback_points": ["p-n junction"],
    }
    parsed_illustration = adapter.validate_python(raw_illustration)
    assert isinstance(parsed_illustration, IllustrationSpec)


# ============================================================================
# ScenePlan
# ============================================================================

def test_scene_plan_valid():
    scene = ScenePlan(
        scene_id="s01_intro",
        title="Introduction to TCP",
        concept="Reliability",
        narration="TCP provides guaranteed delivery of packets.",
        key_points=["Guaranteed delivery", "Flow control"],
        visual_intent=VisualIntent.CONCEPT_CARD,
        visual_spec=ConceptCardSpec(
            heading="TCP Intro",
            points=["Reliable", "Ordered"],
        ),
    )
    assert scene.scene_id == "s01_intro"


def test_scene_plan_invalid_scene_id():
    with pytest.raises(ValidationError, match="format"):
        ScenePlan(
            scene_id="scene1",  # Invalid format
            title="Title",
            concept="Concept",
            narration="Narration text",
            key_points=["Point"],
            visual_intent=VisualIntent.CONCEPT_CARD,
            visual_spec=ConceptCardSpec(heading="H", points=["P"]),
        )


def test_scene_plan_visual_intent_mismatch():
    with pytest.raises(ValidationError, match="does not match"):
        ScenePlan(
            scene_id="s01_intro",
            title="Title",
            concept="Concept",
            narration="Narration text",
            key_points=["Point"],
            visual_intent=VisualIntent.COMPARISON,  # Mismatch with concept_card
            visual_spec=ConceptCardSpec(heading="H", points=["P"]),
        )


def test_scene_plan_blank_narration():
    with pytest.raises(ValidationError):
        ScenePlan(
            scene_id="s01_intro",
            title="Title",
            concept="Concept",
            narration="    ",
            key_points=["Point"],
            visual_intent=VisualIntent.CONCEPT_CARD,
            visual_spec=ConceptCardSpec(heading="H", points=["P"]),
        )


# ============================================================================
# LessonPlan
# ============================================================================

def _make_dummy_scene(scene_id: str) -> ScenePlan:
    return ScenePlan(
        scene_id=scene_id,
        title="Scene Title",
        concept="Concept",
        narration="Explanation of the concept.",
        key_points=["Point 1"],
        visual_intent=VisualIntent.CONCEPT_CARD,
        visual_spec=ConceptCardSpec(heading="Heading", points=["Key fact"]),
    )


def test_lesson_plan_valid_scenes_count():
    # 3 scenes valid
    lp3 = LessonPlan(
        title="TCP Guide",
        topic="Computer Networks",
        audience="Students",
        language="en",
        learning_objective="Understand TCP handshake",
        summary="Complete walkthrough of TCP",
        scenes=[_make_dummy_scene(f"s0{i}_step") for i in range(1, 4)],
    )
    assert len(lp3.scenes) == 3

    # 6 scenes valid
    lp6 = LessonPlan(
        title="TCP Guide",
        topic="Computer Networks",
        audience="Students",
        language="en",
        learning_objective="Understand TCP handshake",
        summary="Complete walkthrough of TCP",
        scenes=[_make_dummy_scene(f"s0{i}_step") for i in range(1, 7)],
    )
    assert len(lp6.scenes) == 6


def test_lesson_plan_invalid_scene_counts():
    # 2 scenes invalid (min 3)
    with pytest.raises(ValidationError):
        LessonPlan(
            title="Short",
            topic="Topic",
            audience="Audience",
            language="en",
            learning_objective="Objective",
            summary="Summary",
            scenes=[_make_dummy_scene("s01_a"), _make_dummy_scene("s02_b")],
        )

    # 7 scenes invalid (max 6)
    with pytest.raises(ValidationError):
        LessonPlan(
            title="Long",
            topic="Topic",
            audience="Audience",
            language="en",
            learning_objective="Objective",
            summary="Summary",
            scenes=[_make_dummy_scene(f"s0{i}_step") for i in range(1, 8)],
        )


def test_lesson_plan_duplicate_scene_ids():
    with pytest.raises(ValidationError, match="Duplicate scene id"):
        LessonPlan(
            title="Dup",
            topic="Topic",
            audience="Audience",
            language="en",
            learning_objective="Objective",
            summary="Summary",
            scenes=[
                _make_dummy_scene("s01_intro"),
                _make_dummy_scene("s01_intro"),  # duplicate
                _make_dummy_scene("s02_end"),
            ],
        )


# ============================================================================
# Job Model
# ============================================================================

def test_job_timezone_awareness():
    now_utc = datetime.now(timezone.utc)
    job = Job(
        id="job_123",
        topic="Operating Systems",
        audience="Undergraduates",
        language="vi",
        target_duration_seconds=60,
        created_at=now_utc,
        updated_at=now_utc,
    )
    assert job.id == "job_123"
    assert job.status == JobStatus.QUEUED

    # Naive datetime rejected
    naive_dt = datetime.now()  # no tz
    with pytest.raises(ValidationError, match="timezone-aware"):
        Job(
            id="job_124",
            topic="Topic",
            audience="Audience",
            language="vi",
            target_duration_seconds=60,
            created_at=naive_dt,
            updated_at=now_utc,
        )


def test_job_bounds_validation():
    now_utc = datetime.now(timezone.utc)

    # progress < 0 invalid
    with pytest.raises(ValidationError):
        Job(
            id="job_1",
            topic="T",
            audience="A",
            language="vi",
            target_duration_seconds=60,
            progress_percent=-1,
            created_at=now_utc,
            updated_at=now_utc,
        )

    # progress > 100 invalid
    with pytest.raises(ValidationError):
        Job(
            id="job_1",
            topic="T",
            audience="A",
            language="vi",
            target_duration_seconds=60,
            progress_percent=101,
            created_at=now_utc,
            updated_at=now_utc,
        )

    # attempt < 0 invalid
    with pytest.raises(ValidationError):
        Job(
            id="job_1",
            topic="T",
            audience="A",
            language="vi",
            target_duration_seconds=60,
            attempt_count=-1,
            created_at=now_utc,
            updated_at=now_utc,
        )


# ============================================================================
# Timeline Models
# ============================================================================

def test_resolved_timeline_valid():
    t1 = ResolvedSceneTiming(
        scene_id="s01_intro",
        raw_audio_path="/tmp/s01.wav",
        padded_audio_path="/tmp/s01_padded.wav",
        audio_duration_seconds=5.0,
        render_duration_seconds=5.3,
        start_seconds=0.0,
        end_seconds=5.3,
    )
    t2 = ResolvedSceneTiming(
        scene_id="s02_main",
        raw_audio_path="/tmp/s02.wav",
        padded_audio_path="/tmp/s02_padded.wav",
        audio_duration_seconds=10.0,
        render_duration_seconds=10.3,
        start_seconds=5.3,
        end_seconds=15.6,
    )

    timeline = ResolvedTimeline(
        scenes=[t1, t2],
        total_duration_seconds=15.6,
    )
    assert len(timeline.scenes) == 2
    assert timeline.total_duration_seconds == 15.6


def test_resolved_timeline_gap_or_overlap_invalid():
    t1 = ResolvedSceneTiming(
        scene_id="s01_intro",
        raw_audio_path="/tmp/s01.wav",
        padded_audio_path="/tmp/s01_padded.wav",
        audio_duration_seconds=5.0,
        render_duration_seconds=5.0,
        start_seconds=0.0,
        end_seconds=5.0,
    )
    # Gap: starts at 6.0 instead of 5.0
    t2_gap = ResolvedSceneTiming(
        scene_id="s02_main",
        raw_audio_path="/tmp/s02.wav",
        padded_audio_path="/tmp/s02_padded.wav",
        audio_duration_seconds=5.0,
        render_duration_seconds=5.0,
        start_seconds=6.0,
        end_seconds=11.0,
    )
    with pytest.raises(ValidationError, match="does not match previous end"):
        ResolvedTimeline(scenes=[t1, t2_gap], total_duration_seconds=11.0)


def test_resolved_timeline_duplicate_scene_id():
    t1 = ResolvedSceneTiming(
        scene_id="s01_intro",
        raw_audio_path="/tmp/s01.wav",
        padded_audio_path="/tmp/s01_padded.wav",
        audio_duration_seconds=5.0,
        render_duration_seconds=5.0,
        start_seconds=0.0,
        end_seconds=5.0,
    )
    t2_dup = ResolvedSceneTiming(
        scene_id="s01_intro",  # duplicate ID
        raw_audio_path="/tmp/s02.wav",
        padded_audio_path="/tmp/s02_padded.wav",
        audio_duration_seconds=5.0,
        render_duration_seconds=5.0,
        start_seconds=5.0,
        end_seconds=10.0,
    )
    with pytest.raises(ValidationError, match="Duplicate scene id"):
        ResolvedTimeline(scenes=[t1, t2_dup], total_duration_seconds=10.0)


def test_resolved_timeline_incorrect_total_duration():
    t1 = ResolvedSceneTiming(
        scene_id="s01_intro",
        raw_audio_path="/tmp/s01.wav",
        padded_audio_path="/tmp/s01_padded.wav",
        audio_duration_seconds=5.0,
        render_duration_seconds=5.0,
        start_seconds=0.0,
        end_seconds=5.0,
    )
    with pytest.raises(ValidationError, match="Total duration"):
        ResolvedTimeline(scenes=[t1], total_duration_seconds=10.0)  # should be 5.0
