"""Strict, semantic Pydantic models for MotionPlan V2.

MotionPlan represents semantic animation intent independent from layout geometry
and renderer execution. It contains strictly zero pixel coordinates, durations,
easing curves, opacity tracks, transforms, or renderer commands.
"""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from learnflow_v2.core.errors import (
    MotionDuplicateEventIdError,
    MotionGrammarIncompatibleError,
    MotionInvalidInputError,
    MotionInvalidTargetError,
    MotionUnsupportedSchemaVersionError,
    MotionUnsupportedTierError,
)
from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.motion.enums import (
    TIER_1_MOTION_GRAMMAR,
    TIER_2_3_RESERVED_STYLES,
    TIER_2_3_RESERVED_VERBS,
    VERB_TARGET_KIND_MAP,
    MotionStyle,
    MotionTargetKind,
    MotionVerb,
)

V2_MOTION_SCHEMA_VERSION = "2.1"


class MotionTrigger(BaseModel):
    """Semantic trigger binding for motion events (e.g. narration beat reference).

    Contains strictly symbolic references only, with zero timing or scheduling calculation.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    beat: str = Field(..., min_length=1, description="Symbolic narration beat reference")

    @field_validator("beat")
    @classmethod
    def _validate_beat(cls, v: str) -> str:
        if not v or not v.strip():
            raise MotionInvalidInputError("Trigger beat cannot be empty or whitespace-only")
        return v.strip()


class MotionEvent(BaseModel):
    """Semantic motion event expressing animation intent in a single scene.

    Constrained strictly to Tier-1 Motion Grammar. Rejects arbitrary strings,
    unsupported verbs/styles, and invalid category-action combinations.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., min_length=1, description="Unique, stable motion event identifier")
    target: str = Field(..., min_length=1, description="Symbolic ID of target node or relation in SceneGraph")
    verb: MotionVerb = Field(..., description="Semantic motion category/verb")
    style: MotionStyle = Field(..., description="Semantic motion style/action")
    trigger: MotionTrigger | None = Field(default=None, description="Optional semantic trigger reference")
    target_kind: MotionTargetKind | None = Field(
        default=None,
        description="Explicit target entity kind (NODE or RELATION). Inferred if None.",
    )

    @property
    def target_id(self) -> str:
        """Convenience alias for target."""
        return self.target

    @field_validator("id", "target")
    @classmethod
    def _validate_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise MotionInvalidInputError("Identifier cannot be empty or whitespace-only")
        return v.strip()

    @field_validator("trigger", mode="before")
    @classmethod
    def _coerce_trigger(cls, v: Any) -> Any:
        if isinstance(v, str):
            return MotionTrigger(beat=v)
        return v

    @model_validator(mode="after")
    def _validate_event(self) -> "MotionEvent":
        # 1. Tier 1 Grammar check
        if self.verb in TIER_2_3_RESERVED_VERBS:
            raise MotionUnsupportedTierError(
                f"Motion verb '{self.verb.value}' is reserved for Tier 2/3 and unsupported in Tier 1."
            )
        if self.style in TIER_2_3_RESERVED_STYLES:
            raise MotionUnsupportedTierError(
                f"Motion style '{self.style.value}' is reserved for Tier 2/3 and unsupported in Tier 1."
            )

        allowed_styles = TIER_1_MOTION_GRAMMAR.get(self.verb)
        if allowed_styles is None or self.style not in allowed_styles:
            allowed_names = sorted(s.value for s in (allowed_styles or frozenset()))
            raise MotionGrammarIncompatibleError(
                f"Invalid motion grammar combination: verb '{self.verb.value}' with style '{self.style.value}'. "
                f"Allowed styles for {self.verb.value}: {allowed_names}"
            )

        # 2. Target kind check & inference
        expected_kind = VERB_TARGET_KIND_MAP[self.verb]
        if self.target_kind is not None and self.target_kind != expected_kind:
            raise MotionInvalidTargetError(
                f"Motion verb '{self.verb.value}' requires target_kind '{expected_kind.value}', "
                f"got '{self.target_kind.value}' for target '{self.target}'"
            )
        if self.target_kind is None:
            object.__setattr__(self, "target_kind", expected_kind)

        return self


class MotionPlan(BaseModel):
    """Complete semantic motion plan for a scene.

    Contains a versioned, ordered sequence of semantic animation events.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(
        default=V2_MOTION_SCHEMA_VERSION,
        description="Motion plan schema version (must be '2.1')",
    )
    scene_id: str = Field(..., min_length=1, description="Scene identifier matching SceneGraph")
    events: tuple[MotionEvent, ...] = Field(
        default_factory=tuple,
        description="Ordered sequence of semantic motion events preserving narrative order",
    )

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, v: str) -> str:
        if v != V2_MOTION_SCHEMA_VERSION:
            raise MotionUnsupportedSchemaVersionError(
                f"Unsupported schema_version '{v}', expected '{V2_MOTION_SCHEMA_VERSION}'"
            )
        return v

    @field_validator("scene_id")
    @classmethod
    def _validate_scene_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise MotionInvalidInputError("scene_id cannot be empty or whitespace-only")
        return v.strip()

    @model_validator(mode="after")
    def _validate_plan(self) -> "MotionPlan":
        seen_ids: set[str] = set()
        for ev in self.events:
            if ev.id in seen_ids:
                raise MotionDuplicateEventIdError(
                    f"Duplicate motion event ID '{ev.id}' in MotionPlan for scene '{self.scene_id}'"
                )
            seen_ids.add(ev.id)
        return self

    def to_canonical_json(self) -> str:
        """Serialize MotionPlan to canonical deterministic JSON."""
        return canonical_json(self)

    @classmethod
    def from_canonical_json(cls, json_str: str) -> "MotionPlan":
        """Parse MotionPlan from canonical JSON string."""
        return cls.model_validate_json(json_str)

    @classmethod
    def from_json(cls, json_str: str) -> "MotionPlan":
        """Parse MotionPlan from JSON string."""
        return cls.model_validate_json(json_str)

    def validate_with_scenegraph(self, graph: Any) -> None:
        """Validate this plan against a SceneGraph."""
        from learnflow_v2.motion.validation import validate_motion_plan_with_scenegraph

        validate_motion_plan_with_scenegraph(self, graph)
