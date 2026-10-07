from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_contracts import (
    AgentContractError,
    AssessmentProbe,
    EvidenceEdge,
    EvidenceGraph,
    EvidenceNodeKind,
    EvidenceRelation,
    LearningBrief,
    LearningObjective,
    LessonScript,
    PedagogyExample,
    PedagogyMisconception,
    PedagogyPlan,
    ResearchClaim,
    ResearchPack,
    ScriptSegment,
    SourceRecord,
    TeachingFunction,
)
from fact_verification import verify_facts
from script_agent import (
    ScriptIssue,
    assemble_lesson_script_wire,
    build_script_agent_task,
    require_visual_director_ready,
    validate_lesson_script,
)


def fixture():
    brief = LearningBrief(
        brief_id="brief.demo",
        user_query="Explain demo.",
        learner_level="beginner",
        target_duration_minutes=3,
        language="en",
    )
    s1 = SourceRecord(source_id="S1", title="One", locator="https://example.test/1")
    s2 = SourceRecord(source_id="S2", title="Two", locator="https://example.test/2")
    pack = ResearchPack(
        pack_id="research.demo",
        topic="demo",
        concepts=("first", "second"),
        sources=(s1, s2),
        claims=(
            ResearchClaim(
                claim_id="C1",
                statement="Supported.",
                source_ids=("S1",),
                confidence=0.9,
            ),
            ResearchClaim(
                claim_id="C2",
                statement="Contradicted.",
                source_ids=("S1", "S2"),
                confidence=0.5,
            ),
        ),
    )
    graph = EvidenceGraph(
        graph_id="evidence.demo",
        research_pack_id=pack.pack_id,
        source_ids=("S1", "S2"),
        claim_ids=("C1", "C2"),
        edges=(
            EvidenceEdge(
                edge_id="E1",
                from_kind=EvidenceNodeKind.SOURCE,
                from_id="S1",
                to_claim_id="C1",
                relation=EvidenceRelation.SUPPORTS,
            ),
            EvidenceEdge(
                edge_id="E2",
                from_kind=EvidenceNodeKind.SOURCE,
                from_id="S1",
                to_claim_id="C2",
                relation=EvidenceRelation.SUPPORTS,
            ),
            EvidenceEdge(
                edge_id="E3",
                from_kind=EvidenceNodeKind.SOURCE,
                from_id="S2",
                to_claim_id="C2",
                relation=EvidenceRelation.CONTRADICTS,
            ),
        ),
    )
    report = verify_facts(pack, graph)
    pedagogy = PedagogyPlan(
        plan_id="pedagogy.demo",
        brief_id=brief.brief_id,
        research_pack_id=pack.pack_id,
        evidence_graph_id=graph.graph_id,
        learning_objectives=(
            LearningObjective(
                objective_id="O1",
                description="Understand first.",
                assessment_criterion="Explain first.",
            ),
            LearningObjective(
                objective_id="O2",
                description="Connect first and second.",
                assessment_criterion="Describe the connection.",
            ),
        ),
        prerequisites=("basic vocabulary",),
        concept_order=("first", "second"),
        worked_examples=(
            PedagogyExample(
                example_id="X1",
                concept="first",
                description="Worked example.",
                claim_ids=("C1",),
            ),
        ),
        misconceptions=(
            PedagogyMisconception(
                misconception_id="M1",
                misconception="Wrong idea.",
                correction="Correct idea.",
                claim_ids=("C1",),
            ),
        ),
        assessment_probes=(
            AssessmentProbe(
                probe_id="P1",
                prompt="Check O1.",
                expected_outcome="O1 response.",
                objective_ids=("O1",),
            ),
            AssessmentProbe(
                probe_id="P2",
                prompt="Check O2.",
                expected_outcome="O2 response.",
                objective_ids=("O2",),
            ),
        ),
    )
    return brief, pack, graph, report, pedagogy


def good_script(pedagogy):
    return LessonScript(
        script_id="script.demo",
        pedagogy_plan_id=pedagogy.plan_id,
        segments=(
            ScriptSegment(
                segment_id="S1",
                spoken_text="We will build the idea step by step.",
                subtitle_text="Build the idea step by step.",
                spoken_language="en",
                subtitle_language="en",
                objective_ids=("O1",),
                teaching_function=TeachingFunction.INTRODUCE,
            ),
            ScriptSegment(
                segment_id="S2",
                spoken_text="This is the supported factual explanation.",
                subtitle_text="Supported factual explanation.",
                spoken_language="en",
                subtitle_language="en",
                claim_ids=("C1",),
                objective_ids=("O1",),
                teaching_function=TeachingFunction.EXPLAIN,
            ),
            ScriptSegment(
                segment_id="S3",
                spoken_text="Now use a concrete example to connect the ideas.",
                subtitle_text="Use a concrete example.",
                spoken_language="en",
                subtitle_language="en",
                claim_ids=("C1",),
                objective_ids=("O1", "O2"),
                teaching_function=TeachingFunction.DEMONSTRATE,
            ),
            ScriptSegment(
                segment_id="S4",
                spoken_text="Can you explain the idea in your own words?",
                subtitle_text="Explain it in your own words.",
                spoken_language="en",
                subtitle_language="en",
                objective_ids=("O2",),
                teaching_function=TeachingFunction.CHECK,
            ),
            ScriptSegment(
                segment_id="S5",
                spoken_text="The supported claim is the anchor for the lesson.",
                subtitle_text="The supported claim anchors the lesson.",
                spoken_language="en",
                subtitle_language="en",
                claim_ids=("C1",),
                objective_ids=("O1", "O2"),
                teaching_function=TeachingFunction.SUMMARIZE,
            ),
        ),
    )


def validate(script, brief, pack, graph, report, pedagogy):
    return validate_lesson_script(
        script,
        brief=brief,
        pack=pack,
        graph=graph,
        fact_report=report,
        pedagogy=pedagogy,
    )


def test_acceptance_verifier_passes():
    proc = subprocess.run(
        [sys.executable, "scripts/verify_script_agent.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "SCRIPT_AGENT=PASS" in proc.stdout
    assert "claim_ids_preserved=PASS" in proc.stdout


def test_good_script_is_visual_director_ready():
    brief, pack, graph, report, pedagogy = fixture()
    result = validate(good_script(pedagogy), brief, pack, graph, report, pedagogy)
    assert result.ready_for_visual_director
    assert result.issues == ()
    require_visual_director_ready(result)


def test_dropping_pedagogy_claim_is_rejected():
    brief, pack, graph, report, pedagogy = fixture()
    script = good_script(pedagogy)
    stripped = script.model_copy(
        update={
            "segments": tuple(
                segment.model_copy(update={"claim_ids": ()})
                for segment in script.segments
            )
        }
    )
    result = validate(stripped, brief, pack, graph, report, pedagogy)
    assert ScriptIssue.CLAIM_SET_MISMATCH in result.issues
    assert result.missing_claim_ids == ("C1",)


def test_adding_claim_not_selected_by_pedagogy_is_rejected():
    brief, pack, graph, report, pedagogy = fixture()
    script = good_script(pedagogy)
    segments = list(script.segments)
    segments[1] = segments[1].model_copy(update={"claim_ids": ("C1", "C2")})
    result = validate(
        script.model_copy(update={"segments": tuple(segments)}),
        brief, pack, graph, report, pedagogy,
    )
    assert ScriptIssue.CLAIM_SET_MISMATCH in result.issues
    assert result.unexpected_claim_ids == ("C2",)


def test_repeating_same_preserved_claim_across_segments_is_allowed():
    brief, pack, graph, report, pedagogy = fixture()
    result = validate(good_script(pedagogy), brief, pack, graph, report, pedagogy)
    assert result.missing_claim_ids == ()
    assert result.unexpected_claim_ids == ()


def test_every_pedagogy_objective_must_be_covered():
    brief, pack, graph, report, pedagogy = fixture()
    script = good_script(pedagogy)
    stripped = script.model_copy(
        update={
            "segments": tuple(
                segment.model_copy(
                    update={
                        "objective_ids": tuple(
                            oid for oid in segment.objective_ids if oid != "O2"
                        )
                    }
                )
                for segment in script.segments
            )
        }
    )
    result = validate(stripped, brief, pack, graph, report, pedagogy)
    assert ScriptIssue.OBJECTIVE_NOT_COVERED in result.issues
    assert result.uncovered_objective_ids == ("O2",)


def test_fact_bearing_teaching_function_requires_claim_binding():
    brief, pack, graph, report, pedagogy = fixture()
    script = good_script(pedagogy)
    segments = list(script.segments)
    segments[1] = segments[1].model_copy(update={"claim_ids": ()})
    result = validate(
        script.model_copy(update={"segments": tuple(segments)}),
        brief, pack, graph, report, pedagogy,
    )
    assert ScriptIssue.FACT_BEARING_SEGMENT_WITHOUT_CLAIM in result.issues
    assert result.ungrounded_segment_ids == ("S2",)


@pytest.mark.parametrize(
    "spoken_text",
    (
        "Put the title at left: 120px.",
        "Use x_px=240 for the object.",
        "Call render_scene_video now.",
        "\x60\x60\x60python\nprint('layout')\n\x60\x60\x60",
        "Send this to FFmpeg.",
    ),
)
def test_visual_or_implementation_directives_are_rejected(spoken_text):
    brief, pack, graph, report, pedagogy = fixture()
    script = good_script(pedagogy)
    segments = list(script.segments)
    segments[0] = segments[0].model_copy(update={"spoken_text": spoken_text})
    result = validate(
        script.model_copy(update={"segments": tuple(segments)}),
        brief, pack, graph, report, pedagogy,
    )
    assert ScriptIssue.VISUAL_OR_IMPLEMENTATION_DIRECTIVE in result.issues
    assert result.boundary_violation_segment_ids == ("S1",)


def test_teaching_function_is_schema_required_for_every_segment():
    with pytest.raises(ValidationError):
        ScriptSegment(
            segment_id="S1",
            spoken_text="Text.",
            subtitle_text="Text.",
            spoken_language="en",
            subtitle_language="en",
        )


def test_script_task_exposes_only_claims_selected_by_pedagogy():
    brief, pack, graph, report, pedagogy = fixture()
    task = build_script_agent_task(brief, pack, graph, report, pedagogy)
    context = json.loads(task["context"])
    assert [item["claim_id"] for item in context["selected_fact_claims"]] == ["C1"]
    assert context["selected_fact_claim_catalog"] == [
        {"index": 0, "claim_id": "C1", "statement": "Supported."}
    ]
    assert [item["objective_id"] for item in context["objective_catalog"]] == ["O1", "O2"]
    assert context["required_ids"]["pedagogy_plan_id"] == pedagogy.plan_id
    assert all(item["claim_id"] != "C2" for item in context["selected_fact_claims"])


def test_script_task_refuses_pedagogy_that_is_not_script_ready():
    brief, pack, graph, report, pedagogy = fixture()
    unsafe = pedagogy.model_copy(
        update={
            "worked_examples": (
                PedagogyExample(
                    example_id="X2",
                    concept="second",
                    description="Blocked factual example.",
                    claim_ids=("C2",),
                ),
            )
        }
    )
    with pytest.raises(AgentContractError, match="not ready"):
        build_script_agent_task(brief, pack, graph, report, unsafe)


def test_script_schema_has_no_visual_or_code_fields():
    schema = LessonScript.model_json_schema()
    segment_properties = set(schema["$defs"]["ScriptSegment"]["properties"])
    assert {
        "x", "y", "width", "height", "pixel_x", "pixel_y",
        "renderer", "code", "scenegraph",
    }.isdisjoint(segment_properties)


def test_script_plan_id_must_match_pedagogy_plan():
    brief, pack, graph, report, pedagogy = fixture()
    script = good_script(pedagogy).model_copy(
        update={"pedagogy_plan_id": "pedagogy.other"}
    )
    with pytest.raises(AgentContractError, match="does not match PedagogyPlan"):
        validate(script, brief, pack, graph, report, pedagogy)


def test_script_surface_does_not_import_renderer_or_visual_director():
    paths = [
        ROOT / "script_agent" / "models.py",
        ROOT / "script_agent" / "gate.py",
        ROOT / "script_agent" / "hermes.py",
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()
    for forbidden in (
        "from learnflow_v2.render",
        "import learnflow_v2.render",
        "from visual_director",
        "import visual_director",
        "deterministicpillowrenderer(",
    ):
        assert forbidden not in source



def _wire_script_payload(pedagogy):
    payload = good_script(pedagogy).model_dump(mode="json")
    for segment in payload["segments"]:
        claim_ids = segment.pop("claim_ids")
        objective_ids = segment.pop("objective_ids")
        segment["claim_indexes"] = [0] if claim_ids else []
        segment["objective_indexes"] = [
            0 if item == "O1" else 1 for item in objective_ids
        ]
    return payload


def test_host_assembles_script_indexes_and_enforces_full_coverage():
    _, _, _, _, pedagogy = fixture()
    script = assemble_lesson_script_wire(
        _wire_script_payload(pedagogy),
        claim_ids=("C1",),
        objective_ids=("O1", "O2"),
    )
    assert {cid for s in script.segments for cid in s.claim_ids} == {"C1"}
    assert {oid for s in script.segments for oid in s.objective_ids} == {"O1", "O2"}


def test_host_rejects_missing_selected_claim_before_visual_gate():
    _, _, _, _, pedagogy = fixture()
    payload = _wire_script_payload(pedagogy)
    for segment in payload["segments"]:
        segment["claim_indexes"] = []
    with pytest.raises(AgentContractError, match="cover every selected factual claim"):
        assemble_lesson_script_wire(
            payload,
            claim_ids=("C1",),
            objective_ids=("O1", "O2"),
        )


def test_script_wire_schema_uses_indexes_not_dynamic_ids():
    brief, pack, graph, report, pedagogy = fixture()
    task = build_script_agent_task(brief, pack, graph, report, pedagogy)
    segment = task["output_schema"]["$defs"]["ScriptSegment"]["properties"]
    assert "claim_indexes" in segment and "objective_indexes" in segment
    assert "claim_ids" not in segment and "objective_ids" not in segment
