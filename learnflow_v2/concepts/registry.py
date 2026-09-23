"""In-memory ConceptRegistry service with strict uniqueness and resolution invariants."""

import json
from typing import Any
from learnflow_v2 import V2_SCHEMA_VERSION
from learnflow_v2.core.errors import (
    ConceptRegistryCollisionError,
    ConceptRegistryUnknownRefError,
)
from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.concepts.normalize import (
    normalize_canonical_key,
    normalize_concept_alias,
)
from learnflow_v2.concepts.schema import (
    ConceptEntry,
    ConceptRegistrySchema,
)


class ConceptRegistry:
    """Lesson-scoped registry for canonical semantic concepts."""

    def __init__(self, schema_version: str = V2_SCHEMA_VERSION) -> None:
        if schema_version != V2_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported schema version '{schema_version}', only '{V2_SCHEMA_VERSION}' is supported."
            )
        self.schema_version = schema_version
        self._entries: dict[str, ConceptEntry] = {}  # concept_id -> ConceptEntry
        # token -> (concept_id, token_kind)
        # Guarantees every resolvable token maps to exactly one concept across all namespaces.
        self._resolution_index: dict[str, tuple[str, str]] = {}

    def _collect_entry_tokens(self, entry: ConceptEntry) -> list[tuple[str, str]]:
        """Collect all resolvable tokens claimed by a ConceptEntry."""
        tokens: list[tuple[str, str]] = []

        # 1. concept_id
        tokens.append((entry.concept_id, "concept_id"))
        norm_cid = normalize_concept_alias(entry.concept_id)
        if norm_cid and norm_cid != entry.concept_id:
            tokens.append((norm_cid, "concept_id"))

        # 2. canonical_key
        norm_key = normalize_canonical_key(entry.canonical_key)
        tokens.append((norm_key, "canonical_key"))
        norm_key_alias = normalize_concept_alias(entry.canonical_key)
        if norm_key_alias and norm_key_alias != norm_key:
            tokens.append((norm_key_alias, "canonical_key"))

        # Key body (e.g. "loss" for "concept:loss")
        if norm_key.startswith("concept:"):
            body = norm_key.removeprefix("concept:").strip()
            body_norm = normalize_concept_alias(body)
            if body_norm:
                tokens.append((body_norm, "canonical_key_body"))

        # 3. label (functions as canonical display alias)
        norm_label = normalize_concept_alias(entry.label)
        if norm_label:
            tokens.append((norm_label, "label"))

        # 4. explicit aliases
        for alias in entry.aliases:
            norm_alias = normalize_concept_alias(alias)
            if norm_alias:
                tokens.append((norm_alias, "alias"))

        return tokens

    def register(self, entry: ConceptEntry) -> ConceptEntry:
        """Register a concept entry enforcing cross-namespace uniqueness and resolution invariants.

        Raises:
            ConceptRegistryCollisionError: if concept_id, canonical_key, label, or an alias
                collides with any token already claimed by another concept.
        """
        # Check concept_id
        if entry.concept_id in self._entries:
            existing = self._entries[entry.concept_id]
            if existing == entry:
                # Idempotent re-registration of exact same entry
                return existing
            raise ConceptRegistryCollisionError(
                f"Concept ID collision: '{entry.concept_id}' already registered with different data."
            )

        candidate_tokens = self._collect_entry_tokens(entry)

        # Detect collisions against existing concepts in resolution index
        for token, kind in candidate_tokens:
            if token in self._resolution_index:
                existing_cid, existing_kind = self._resolution_index[token]
                if existing_cid != entry.concept_id:
                    raise ConceptRegistryCollisionError(
                        f"Concept registration collision: token '{token}' ({kind}) for concept "
                        f"'{entry.concept_id}' collides with existing concept '{existing_cid}' ({existing_kind})."
                    )

        # Commit entry and register all tokens
        self._entries[entry.concept_id] = entry
        for token, kind in candidate_tokens:
            self._resolution_index[token] = (entry.concept_id, kind)

        return entry

    def get(self, concept_id: str) -> ConceptEntry:
        """Retrieve a concept strictly by its concept_id."""
        if concept_id not in self._entries:
            raise ConceptRegistryUnknownRefError(
                f"Unknown concept_id: '{concept_id}' not found in registry."
            )
        return self._entries[concept_id]

    def resolve(self, identifier_or_alias: str) -> ConceptEntry:
        """Resolve a concept by concept_id, canonical_key, or normalized alias.

        Resolution is strictly deterministic: every registered token maps
        to exactly one concept without ambiguity or priority-based shadowing.

        Raises:
            ConceptRegistryUnknownRefError if not found.
        """
        # 1. Exact match in index
        if identifier_or_alias in self._resolution_index:
            cid, _ = self._resolution_index[identifier_or_alias]
            return self._entries[cid]

        # 2. Normalized alias
        norm_alias = normalize_concept_alias(identifier_or_alias)
        if norm_alias in self._resolution_index:
            cid, _ = self._resolution_index[norm_alias]
            return self._entries[cid]

        # 3. Normalized canonical key
        norm_key = normalize_canonical_key(identifier_or_alias)
        if norm_key in self._resolution_index:
            cid, _ = self._resolution_index[norm_key]
            return self._entries[cid]

        # 4. Normalized key body
        if norm_key.startswith("concept:"):
            body_norm = normalize_concept_alias(norm_key.removeprefix("concept:"))
            if body_norm in self._resolution_index:
                cid, _ = self._resolution_index[body_norm]
                return self._entries[cid]

        raise ConceptRegistryUnknownRefError(
            f"Concept resolution failed: '{identifier_or_alias}' does not match any ID, key, or alias."
        )

    def contains(self, concept_id: str) -> bool:
        """Check if concept_id exists in registry."""
        return concept_id in self._entries

    def all_concepts(self) -> list[ConceptEntry]:
        """Return all concepts sorted deterministically by concept_id."""
        return sorted(self._entries.values(), key=lambda c: c.concept_id)

    def to_schema(self) -> ConceptRegistrySchema:
        """Export to validated Pydantic schema."""
        return ConceptRegistrySchema(
            schema_version=self.schema_version,  # type: ignore[arg-type]
            concepts=self.all_concepts(),
        )

    @classmethod
    def from_schema(cls, schema: ConceptRegistrySchema) -> "ConceptRegistry":
        """Instantiate registry from schema with full invariant verification."""
        registry = cls(schema_version=schema.schema_version)
        for entry in schema.concepts:
            registry.register(entry)
        return registry

    def to_canonical_json(self) -> str:
        """Deterministic canonical JSON serialization."""
        return canonical_json(self.to_schema())

    @classmethod
    def from_canonical_json(cls, json_str: str) -> "ConceptRegistry":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        schema = ConceptRegistrySchema.model_validate(data)
        return cls.from_schema(schema)
