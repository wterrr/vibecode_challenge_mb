"""Tests for ConceptRegistry, normalization, and canonical serialization."""

import pytest
from pydantic import ValidationError

from learnflow_v2.concepts.normalize import (
    deterministic_concept_id,
    normalize_canonical_key,
    normalize_concept_alias,
)
from learnflow_v2.concepts.registry import ConceptRegistry
from learnflow_v2.concepts.schema import (
    V2_SCHEMA_VERSION,
    ConceptEntry,
    ConceptRegistrySchema,
    SemanticType,
)
from learnflow_v2.core.errors import (
    ConceptRegistryCollisionError,
    ConceptRegistryUnknownRefError,
)
from learnflow_v2.core.serialization import canonical_json


def test_normalization_rules():
    # 1. NFKC + collapse whitespace + casefold
    assert normalize_concept_alias("  Loss   Function ") == "loss function"
    assert normalize_concept_alias("Cross-Entropy\tLoss\n") == "cross-entropy loss"

    # 2. Vietnamese diacritics must NOT be stripped
    vi_norm = normalize_concept_alias("  Học   Sâu  ")
    assert vi_norm == "học sâu"
    assert vi_norm != "hoc sau"  # Diacritics preserved

    # 3. Canonical key derivation
    assert normalize_canonical_key("Loss Function") == "concept:loss_function"
    assert normalize_canonical_key("concept:backprop") == "concept:backprop"

    # 4. Deterministic concept ID
    cid1 = deterministic_concept_id("concept:loss_function")
    cid2 = deterministic_concept_id("concept:loss_function")
    cid_diff = deterministic_concept_id("concept:accuracy")
    assert cid1 == cid2
    assert cid1 != cid_diff
    assert cid1.startswith("c_")


def test_valid_registry_creation_and_lookup():
    registry = ConceptRegistry()
    assert registry.schema_version == V2_SCHEMA_VERSION

    entry = ConceptEntry(
        concept_id="c_loss_1",
        canonical_key="concept:loss",
        label="Loss",
        aliases=["loss function", "cost function"],
        semantic_type=SemanticType.CONCEPT,
    )
    registry.register(entry)

    assert registry.contains("c_loss_1")
    assert registry.get("c_loss_1") == entry
    assert registry.resolve("c_loss_1") == entry
    assert registry.resolve("concept:loss") == entry
    assert registry.resolve("loss function") == entry
    assert registry.resolve("cost function") == entry
    assert registry.resolve("Loss") == entry  # Label as alias


def test_stable_canonical_serialization_and_roundtrip():
    registry = ConceptRegistry()
    entry1 = ConceptEntry(
        concept_id="c_alpha",
        canonical_key="concept:alpha",
        label="Alpha",
        aliases=["a1"],
    )
    entry2 = ConceptEntry(
        concept_id="c_beta",
        canonical_key="concept:beta",
        label="Beta",
        aliases=["b1"],
    )
    # Register in arbitrary order
    registry.register(entry2)
    registry.register(entry1)

    json_str_1 = registry.to_canonical_json()
    json_str_2 = registry.to_canonical_json()
    assert json_str_1 == json_str_2

    # Round-trip parse
    restored = ConceptRegistry.from_canonical_json(json_str_1)
    assert restored.to_canonical_json() == json_str_1
    assert restored.get("c_alpha") == entry1
    assert restored.get("c_beta") == entry2


def test_duplicate_concept_id_rejected():
    registry = ConceptRegistry()
    entry1 = ConceptEntry(
        concept_id="c_loss",
        canonical_key="concept:loss",
        label="Loss",
    )
    registry.register(entry1)

    # Different entry with duplicate ID
    entry2 = ConceptEntry(
        concept_id="c_loss",
        canonical_key="concept:different",
        label="Different Label",
    )
    with pytest.raises(ConceptRegistryCollisionError) as exc_info:
        registry.register(entry2)
    assert exc_info.value.code == "CONCEPT_REGISTRY_COLLISION"


def test_canonical_key_collision_rejected():
    registry = ConceptRegistry()
    entry1 = ConceptEntry(
        concept_id="c_loss_a",
        canonical_key="concept:loss",
        label="Loss A",
    )
    registry.register(entry1)

    entry2 = ConceptEntry(
        concept_id="c_loss_b",
        canonical_key="concept:loss",
        label="Loss B",
    )
    with pytest.raises(ConceptRegistryCollisionError) as exc_info:
        registry.register(entry2)
    assert exc_info.value.code == "CONCEPT_REGISTRY_COLLISION"


def test_collision_after_normalization_rejected():
    registry = ConceptRegistry()
    entry1 = ConceptEntry(
        concept_id="c_loss_1",
        canonical_key="concept:loss_func",
        label="Loss Function",
    )
    registry.register(entry1)

    # Normalized canonical key will collide
    entry2 = ConceptEntry(
        concept_id="c_loss_2",
        canonical_key="  concept:loss_func  ",
        label="Loss Function Variant",
    )
    with pytest.raises(ConceptRegistryCollisionError) as exc_info:
        registry.register(entry2)
    assert exc_info.value.code == "CONCEPT_REGISTRY_COLLISION"


def test_ambiguous_normalized_alias_rejected():
    registry = ConceptRegistry()
    entry1 = ConceptEntry(
        concept_id="c_loss",
        canonical_key="concept:loss",
        label="Loss",
        aliases=["error function"],
    )
    registry.register(entry1)

    # Concept 2 tries to claim the same alias
    entry2 = ConceptEntry(
        concept_id="c_metric",
        canonical_key="concept:metric",
        label="Metric",
        aliases=["  Error   Function  "],
    )
    with pytest.raises(ConceptRegistryCollisionError) as exc_info:
        registry.register(entry2)
    assert exc_info.value.code == "CONCEPT_REGISTRY_COLLISION"


def test_unknown_resolve_rejected():
    registry = ConceptRegistry()
    with pytest.raises(ConceptRegistryUnknownRefError) as exc_info:
        registry.get("c_nonexistent")
    assert exc_info.value.code == "CONCEPT_REGISTRY_UNKNOWN_REF"

    with pytest.raises(ConceptRegistryUnknownRefError) as exc_info:
        registry.resolve("nonexistent_alias")
    assert exc_info.value.code == "CONCEPT_REGISTRY_UNKNOWN_REF"


def test_same_normalized_alias_resolves_deterministically():
    registry = ConceptRegistry()
    entry = ConceptEntry(
        concept_id="c_gradient",
        canonical_key="concept:gradient_descent",
        label="Gradient Descent",
        aliases=["gradient descent", "steepest descent"],
    )
    registry.register(entry)

    # Various whitespace and case variants resolve to exact same entry
    assert registry.resolve("  Gradient   Descent  ") == entry
    assert registry.resolve("STEEPEST DESCENT") == entry
    assert registry.resolve("gradient descent") == entry


def test_strict_pydantic_forbids_extra_fields():
    with pytest.raises(ValidationError):
        ConceptEntry(
            concept_id="c_test",
            canonical_key="concept:test",
            label="Test",
            extra_field="forbidden",  # type: ignore[call-arg]
        )


def test_alias_shadows_canonical_key_collision():
    registry = ConceptRegistry()
    registry.register(
        ConceptEntry(
            concept_id="c_foo",
            canonical_key="concept:foo",
            label="Foo Label",
        )
    )
    with pytest.raises(ConceptRegistryCollisionError) as exc_info:
        registry.register(
            ConceptEntry(
                concept_id="c_bar",
                canonical_key="concept:bar",
                label="Bar Label",
                aliases=["foo"],
            )
        )
    assert exc_info.value.code == "CONCEPT_REGISTRY_COLLISION"


def test_canonical_key_shadows_existing_alias_collision():
    registry = ConceptRegistry()
    registry.register(
        ConceptEntry(
            concept_id="c_bar",
            canonical_key="concept:bar",
            label="Bar Label",
            aliases=["foo"],
        )
    )
    with pytest.raises(ConceptRegistryCollisionError) as exc_info:
        registry.register(
            ConceptEntry(
                concept_id="c_foo",
                canonical_key="concept:foo",
                label="Foo Label",
            )
        )
    assert exc_info.value.code == "CONCEPT_REGISTRY_COLLISION"


def test_alias_shadows_concept_id_collision():
    registry = ConceptRegistry()
    registry.register(
        ConceptEntry(
            concept_id="c_loss_target",
            canonical_key="concept:loss",
            label="Loss",
        )
    )
    with pytest.raises(ConceptRegistryCollisionError) as exc_info:
        registry.register(
            ConceptEntry(
                concept_id="c_other",
                canonical_key="concept:other",
                label="Other",
                aliases=["c_loss_target"],
            )
        )
    assert exc_info.value.code == "CONCEPT_REGISTRY_COLLISION"


def test_concept_id_shadows_alias_collision():
    registry = ConceptRegistry()
    registry.register(
        ConceptEntry(
            concept_id="c_first",
            canonical_key="concept:first",
            label="First",
            aliases=["target_id"],
        )
    )
    with pytest.raises(ConceptRegistryCollisionError) as exc_info:
        registry.register(
            ConceptEntry(
                concept_id="target_id",
                canonical_key="concept:second",
                label="Second",
            )
        )
    assert exc_info.value.code == "CONCEPT_REGISTRY_COLLISION"


def test_label_alias_shadows_another_canonical_key_collision():
    registry = ConceptRegistry()
    registry.register(
        ConceptEntry(
            concept_id="c_foo",
            canonical_key="concept:foo",
            label="Foo Concept",
        )
    )
    with pytest.raises(ConceptRegistryCollisionError) as exc_info:
        registry.register(
            ConceptEntry(
                concept_id="c_bar",
                canonical_key="concept:bar",
                label="foo",
            )
        )
    assert exc_info.value.code == "CONCEPT_REGISTRY_COLLISION"


def test_unsupported_registry_schema_version_rejected():
    with pytest.raises(ValidationError):
        ConceptRegistrySchema(schema_version="999", concepts=[])  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        ConceptRegistrySchema(schema_version="2.0", concepts=[])  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        ConceptRegistrySchema(schema_version="", concepts=[])  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Unsupported schema version"):
        ConceptRegistry(schema_version="999")


def test_domain_metadata_json_safety():
    from pathlib import Path

    # Allowed JSON safe
    entry = ConceptEntry(
        concept_id="c_valid_meta",
        canonical_key="concept:valid_meta",
        label="Valid Meta",
        domain_metadata={
            "str": "text",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "null": None,
            "list": [1, "two", False, None, {"nested": "value"}],
            "dict": {"inner": [1, 2, 3]},
        },
    )
    assert entry.domain_metadata["int"] == 42

    # Forbidden: Path
    with pytest.raises(ValidationError):
        ConceptEntry(
            concept_id="c_bad_meta_1",
            canonical_key="concept:bad_meta_1",
            label="Bad Meta",
            domain_metadata={"path": Path("/tmp")},
        )

    # Forbidden: bytes
    with pytest.raises(ValidationError):
        ConceptEntry(
            concept_id="c_bad_meta_2",
            canonical_key="concept:bad_meta_2",
            label="Bad Meta",
            domain_metadata={"raw": b"bytes"},
        )

    # Forbidden: callable
    with pytest.raises(ValidationError):
        ConceptEntry(
            concept_id="c_bad_meta_3",
            canonical_key="concept:bad_meta_3",
            label="Bad Meta",
            domain_metadata={"fn": lambda x: x},
        )

    # Forbidden: custom object
    with pytest.raises(ValidationError):
        ConceptEntry(
            concept_id="c_bad_meta_4",
            canonical_key="concept:bad_meta_4",
            label="Bad Meta",
            domain_metadata={"obj": object()},
        )

    # Forbidden: tuple
    with pytest.raises(ValidationError):
        ConceptEntry(
            concept_id="c_bad_meta_tuple",
            canonical_key="concept:bad_meta_tuple",
            label="Bad Meta Tuple",
            domain_metadata={"tup": (1, 2)},
        )

    # Forbidden: nested tuple inside list
    with pytest.raises(ValidationError):
        ConceptEntry(
            concept_id="c_bad_meta_nest_tuple",
            canonical_key="concept:bad_meta_nest_tuple",
            label="Bad Meta Nested Tuple",
            domain_metadata={"items": [(1, 2)]},
        )

    # Forbidden: set
    with pytest.raises(ValidationError):
        ConceptEntry(
            concept_id="c_bad_meta_set",
            canonical_key="concept:bad_meta_set",
            label="Bad Meta Set",
            domain_metadata={"tags": {"a", "b"}},
        )

    # Forbidden: float NaN
    with pytest.raises(ValidationError):
        ConceptEntry(
            concept_id="c_bad_meta_nan",
            canonical_key="concept:bad_meta_nan",
            label="Bad Meta NaN",
            domain_metadata={"val": float("nan")},
        )

    # Forbidden: float +Infinity
    with pytest.raises(ValidationError):
        ConceptEntry(
            concept_id="c_bad_meta_pos_inf",
            canonical_key="concept:bad_meta_pos_inf",
            label="Bad Meta Pos Inf",
            domain_metadata={"val": float("inf")},
        )

    # Forbidden: float -Infinity
    with pytest.raises(ValidationError):
        ConceptEntry(
            concept_id="c_bad_meta_neg_inf",
            canonical_key="concept:bad_meta_neg_inf",
            label="Bad Meta Neg Inf",
            domain_metadata={"val": float("-inf")},
        )
