"""Corpus acceptance tests: 100 valid fixtures, negative invalid cases, and geometry boundary."""

import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from learnflow_v2.concepts.registry import ConceptRegistry
from learnflow_v2.concepts.schema import ConceptEntry, ConceptRegistrySchema
from learnflow_v2.core.errors import (
    ConceptRegistryCollisionError,
    ConceptRegistryUnknownRefError,
    LearnFlowV2Error,
)
from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.scenegraph.enums import (
    LayoutIntent,
    NodeKind,
    PortHint,
    PreferredRegion,
    ReadingDirection,
    RelationKind,
    ScenePurpose,
)
from learnflow_v2.scenegraph.schema import SceneGraph
from learnflow_v2.scenegraph.validation import validate_scenegraph_with_registry

FIXTURES_DIR = Path("benchmarks/fixtures/v2")


def test_100_valid_scenegraph_corpus():
    corpus_file = FIXTURES_DIR / "scenegraph_valid_corpus.json"
    assert corpus_file.exists(), "Committed valid fixture corpus must exist"

    with open(corpus_file, encoding="utf-8") as f:
        data = json.load(f)

    # 1. Exact count check
    graphs_data = data["graphs"]
    assert len(graphs_data) == 100, f"Expected exactly 100 valid fixture graphs, got {len(graphs_data)}"

    # 2. Registry verification
    registry_schema = ConceptRegistrySchema.model_validate(data["registry"])
    registry = ConceptRegistry.from_schema(registry_schema)
    assert len(registry.all_concepts()) > 0

    # 3. Enum coverage trackers
    observed_node_kinds: set[NodeKind] = set()
    observed_relation_kinds: set[RelationKind] = set()
    observed_purposes: set[ScenePurpose] = set()
    observed_intents: set[LayoutIntent] = set()
    observed_directions: set[ReadingDirection] = set()
    observed_regions: set[PreferredRegion] = set()
    observed_ports: set[PortHint] = set()

    for idx, g_dict in enumerate(graphs_data):
        # A. Pydantic-valid
        graph = SceneGraph.model_validate(g_dict)

        # B. Registry-aware valid
        validate_scenegraph_with_registry(graph, registry)

        # C. Canonical serialization round-trip valid
        json_1 = canonical_json(graph)
        graph_restored = SceneGraph.model_validate_json(json_1)
        json_2 = canonical_json(graph_restored)
        assert json_1 == json_2

        # Track enums
        observed_purposes.add(graph.purpose)
        observed_intents.add(graph.layout_intent.type)
        observed_directions.add(graph.layout_intent.reading_direction)

        for node in graph.nodes:
            observed_node_kinds.add(node.kind)
            if node.layout_hint and node.layout_hint.preferred_region:
                observed_regions.add(node.layout_hint.preferred_region)

        for rel in graph.relations:
            observed_relation_kinds.add(rel.kind)
            observed_ports.add(rel.source_port)
            observed_ports.add(rel.target_port)

    # 4. Assert full enum coverage across the corpus
    assert observed_node_kinds == set(NodeKind), f"Missing NodeKinds: {set(NodeKind) - observed_node_kinds}"
    assert observed_relation_kinds == set(RelationKind), f"Missing RelationKinds: {set(RelationKind) - observed_relation_kinds}"
    assert observed_purposes == set(ScenePurpose), f"Missing ScenePurposes: {set(ScenePurpose) - observed_purposes}"
    assert observed_intents == set(LayoutIntent), f"Missing LayoutIntents: {set(LayoutIntent) - observed_intents}"
    assert observed_directions == set(ReadingDirection), f"Missing ReadingDirections: {set(ReadingDirection) - observed_directions}"
    assert observed_regions == set(PreferredRegion), f"Missing PreferredRegions: {set(PreferredRegion) - observed_regions}"
    assert observed_ports == set(PortHint), f"Missing PortHints: {set(PortHint) - observed_ports}"


def test_invalid_cases_corpus():
    invalid_file = FIXTURES_DIR / "scenegraph_invalid_cases.json"
    assert invalid_file.exists(), "Committed invalid fixture cases must exist"

    with open(invalid_file, encoding="utf-8") as f:
        cases = json.load(f)

    assert len(cases) >= 10

    # Minimal registry for registry-validation test cases
    test_registry = ConceptRegistry()
    test_registry.register(
        ConceptEntry(
            concept_id="c_loss_test",
            canonical_key="concept:loss_canonical",
            label="Loss",
        )
    )

    for case in cases:
        case_id = case["case_id"]
        expected_code = case["expected_error_code"]
        target_type = case["target_type"]
        payload = case["payload"]

        if target_type == "scenegraph":
            if expected_code == "VALIDATION_ERROR":
                with pytest.raises(ValidationError):
                    SceneGraph.model_validate(payload)
            else:
                with pytest.raises(LearnFlowV2Error) as exc_info:
                    SceneGraph.model_validate(payload)
                assert exc_info.value.code == expected_code, (
                    f"Case {case_id}: expected code {expected_code}, got {exc_info.value.code}"
                )

        elif target_type == "registry_validation":
            graph = SceneGraph.model_validate(payload)
            with pytest.raises(LearnFlowV2Error) as exc_info:
                validate_scenegraph_with_registry(graph, test_registry)
            assert exc_info.value.code == expected_code, (
                f"Case {case_id}: expected code {expected_code}, got {exc_info.value.code}"
            )

        elif target_type == "registry":
            reg = ConceptRegistry()
            c1 = ConceptEntry.model_validate(payload["concept_1"])
            c2 = ConceptEntry.model_validate(payload["concept_2"])
            reg.register(c1)
            with pytest.raises(ConceptRegistryCollisionError) as exc_info:
                reg.register(c2)
            assert exc_info.value.code == expected_code

        elif target_type == "registry_schema":
            if expected_code == "VALIDATION_ERROR":
                with pytest.raises(ValidationError):
                    ConceptRegistrySchema.model_validate(payload)
            else:
                with pytest.raises(LearnFlowV2Error) as exc_info:
                    ConceptRegistrySchema.model_validate(payload)
                assert exc_info.value.code == expected_code


def test_no_v2_geometry_or_future_dependencies():
    """Negative search test proving SceneGraph semantic IR has no layout solver, and V2 has no future deps."""
    forbidden_terms_everywhere = [
        "graphviz",
        "elk",
        "motion_canvas",
        "manim",
        "ffmpeg",
        "gemini",
        "hermes",
    ]

    v2_source_dir = Path("learnflow_v2")
    for py_file in v2_source_dir.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8").lower()
        for term in forbidden_terms_everywhere:
            assert f"import {term}" not in text, f"Forbidden import of '{term}' in {py_file}"
            assert f"from {term}" not in text, f"Forbidden import from '{term}' in {py_file}"

        # kiwisolver is only allowed in layout backend (V2-03)
        if "layout/backends" not in str(py_file):
            assert "import kiwisolver" not in text, f"Forbidden import of 'kiwisolver' outside layout backends in {py_file}"
            assert "from kiwisolver" not in text, f"Forbidden import from 'kiwisolver' outside layout backends in {py_file}"

