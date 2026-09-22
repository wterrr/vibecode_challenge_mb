"""Domain models for learning requests, visual specs, scenes, and lesson plans."""

import re
from typing import Annotated, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from app.domain.enums import VisualIntent

ACTOR_ID_REGEX = re.compile(r"^[a-z][a-z0-9_]{0,30}$")
SCENE_ID_REGEX = re.compile(r"^s[0-9]{2}_[a-z0-9_]+$")


def _collapse_whitespace(text: str) -> str:
    """Strip and collapse internal whitespace sequences."""
    return re.sub(r"\s+", " ", text.strip())


class LearningRequest(BaseModel):
    """User input for generating a learning video."""

    topic: str = Field(min_length=3, max_length=500)
    audience: str = Field(default="Beginner", min_length=2, max_length=80)
    language: Literal["vi", "en"] = "vi"
    target_duration_seconds: Literal[60, 90, 120] = 90
    visual_style: Literal["clean"] = "clean"

    @field_validator("topic", "audience", mode="before")
    @classmethod
    def normalize_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return _collapse_whitespace(value)
        return value


class ConceptCardSpec(BaseModel):
    """Specification for concept card visuals."""

    type: Literal["concept_card"] = "concept_card"
    heading: str = Field(min_length=1, max_length=200)
    points: list[str] = Field(min_length=1, max_length=5)
    emphasis: list[str] = Field(default_factory=list, max_length=4)

    @field_validator("heading", mode="before")
    @classmethod
    def validate_heading(cls, value: object) -> object:
        if isinstance(value, str):
            return _collapse_whitespace(value)
        return value

    @field_validator("points", "emphasis", mode="before")
    @classmethod
    def validate_items(cls, value: object) -> object:
        if isinstance(value, list):
            cleaned = []
            for item in value:
                if isinstance(item, str):
                    normalized = _collapse_whitespace(item)
                    if not normalized:
                        raise ValueError("Item cannot be blank")
                    cleaned.append(normalized)
                else:
                    cleaned.append(item)
            return cleaned
        return value


class ProcessActor(BaseModel):
    """An actor or entity in a process diagram."""

    id: str
    label: str = Field(min_length=1, max_length=80)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not ACTOR_ID_REGEX.match(value):
            raise ValueError(
                f"Actor id '{value}' must match regex ^[a-z][a-z0-9_]{{0,30}}$"
            )
        return value

    @field_validator("label", mode="before")
    @classmethod
    def validate_label(cls, value: object) -> object:
        if isinstance(value, str):
            return _collapse_whitespace(value)
        return value


class ProcessStep(BaseModel):
    """A step or message in a process diagram."""

    order: int = Field(ge=1)
    from_actor: str | None = None
    to_actor: str | None = None
    label: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=300)

    @field_validator("label", mode="before")
    @classmethod
    def validate_label(cls, value: object) -> object:
        if isinstance(value, str):
            return _collapse_whitespace(value)
        return value

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, value: object) -> object:
        if isinstance(value, str):
            norm = _collapse_whitespace(value)
            return norm if norm else None
        return value


class ProcessDiagramSpec(BaseModel):
    """Specification for sequence or process diagrams."""

    type: Literal["process_diagram"] = "process_diagram"
    title: str = Field(min_length=1, max_length=200)
    actors: list[ProcessActor] = Field(min_length=1, max_length=6)
    steps: list[ProcessStep] = Field(min_length=1, max_length=8)

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, value: object) -> object:
        if isinstance(value, str):
            return _collapse_whitespace(value)
        return value

    @model_validator(mode="after")
    def validate_process_semantics(self) -> "ProcessDiagramSpec":
        actor_ids = set()
        for actor in self.actors:
            if actor.id in actor_ids:
                raise ValueError(f"Duplicate actor id '{actor.id}'")
            actor_ids.add(actor.id)

        orders = [step.order for step in self.steps]
        if len(orders) != len(set(orders)):
            raise ValueError("Process step orders must be unique")

        expected_orders = list(range(1, len(self.steps) + 1))
        if sorted(orders) != expected_orders:
            raise ValueError(
                f"Process step orders must be contiguous from 1 to {len(self.steps)}"
            )

        for step in self.steps:
            if step.from_actor is not None and step.from_actor not in actor_ids:
                raise ValueError(
                    f"Step {step.order} references undefined from_actor '{step.from_actor}'"
                )
            if step.to_actor is not None and step.to_actor not in actor_ids:
                raise ValueError(
                    f"Step {step.order} references undefined to_actor '{step.to_actor}'"
                )

        return self


class ComparisonColumn(BaseModel):
    """A single column in a comparison visual."""

    title: str = Field(min_length=1, max_length=100)
    subtitle: str | None = Field(default=None, max_length=160)
    points: list[str] = Field(min_length=1, max_length=5)

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, value: object) -> object:
        if isinstance(value, str):
            return _collapse_whitespace(value)
        return value

    @field_validator("subtitle", mode="before")
    @classmethod
    def validate_subtitle(cls, value: object) -> object:
        if isinstance(value, str):
            norm = _collapse_whitespace(value)
            return norm if norm else None
        return value

    @field_validator("points", mode="before")
    @classmethod
    def validate_points(cls, value: object) -> object:
        if isinstance(value, list):
            cleaned = []
            for pt in value:
                if isinstance(pt, str):
                    normalized = _collapse_whitespace(pt)
                    if not normalized:
                        raise ValueError("Comparison point cannot be blank")
                    cleaned.append(normalized)
                else:
                    cleaned.append(pt)
            return cleaned
        return value


class ComparisonSpec(BaseModel):
    """Specification for side-by-side comparisons."""

    type: Literal["comparison"] = "comparison"
    title: str = Field(min_length=1, max_length=200)
    columns: list[ComparisonColumn] = Field(min_length=2, max_length=3)

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, value: object) -> object:
        if isinstance(value, str):
            return _collapse_whitespace(value)
        return value


class IllustrationSpec(BaseModel):
    """Specification for an educational illustration with fallback content."""

    type: Literal["illustration"] = "illustration"
    prompt: str = Field(min_length=3, max_length=1000)
    fallback_heading: str = Field(min_length=1, max_length=160)
    fallback_points: list[str] = Field(min_length=1, max_length=4)

    @field_validator("prompt", "fallback_heading", mode="before")
    @classmethod
    def validate_non_blank(cls, value: object) -> object:
        if isinstance(value, str):
            return _collapse_whitespace(value)
        return value

    @field_validator("fallback_points", mode="before")
    @classmethod
    def validate_fallback_points(cls, value: object) -> object:
        if isinstance(value, list):
            cleaned = []
            for pt in value:
                if isinstance(pt, str):
                    normalized = _collapse_whitespace(pt)
                    if not normalized:
                        raise ValueError("Fallback point cannot be blank")
                    cleaned.append(normalized)
                else:
                    cleaned.append(pt)
            return cleaned
        return value


VisualSpec = Annotated[
    ConceptCardSpec
    | ProcessDiagramSpec
    | ComparisonSpec
    | IllustrationSpec,
    Field(discriminator="type"),
]


class ScenePlan(BaseModel):
    """Plan for an individual educational scene."""

    scene_id: str
    title: str = Field(min_length=1, max_length=200)
    concept: str = Field(min_length=1, max_length=300)
    narration: str = Field(min_length=1)
    key_points: list[str] = Field(min_length=1, max_length=5)
    visual_intent: VisualIntent
    visual_spec: VisualSpec

    @field_validator("scene_id")
    @classmethod
    def validate_scene_id(cls, value: str) -> str:
        if not SCENE_ID_REGEX.match(value):
            raise ValueError(
                f"Scene id '{value}' must match format ^s[0-9]{{2}}_[a-z0-9_]+$"
            )
        return value

    @field_validator("title", "concept", "narration", mode="before")
    @classmethod
    def validate_text_fields(cls, value: object) -> object:
        if isinstance(value, str):
            return _collapse_whitespace(value)
        return value

    @field_validator("key_points", mode="before")
    @classmethod
    def validate_key_points(cls, value: object) -> object:
        if isinstance(value, list):
            cleaned = []
            for pt in value:
                if isinstance(pt, str):
                    normalized = _collapse_whitespace(pt)
                    if not normalized:
                        raise ValueError("Key point cannot be blank")
                    cleaned.append(normalized)
                else:
                    cleaned.append(pt)
            return cleaned
        return value

    @model_validator(mode="after")
    def validate_visual_intent_match(self) -> "ScenePlan":
        if self.visual_intent.value != self.visual_spec.type:
            raise ValueError(
                f"visual_intent '{self.visual_intent.value}' does not match "
                f"visual_spec type '{self.visual_spec.type}'"
            )
        return self


class LessonPlan(BaseModel):
    """Complete lesson plan generated for a video."""

    schema_version: Literal["1.0"] = "1.0"
    title: str = Field(min_length=1, max_length=200)
    topic: str = Field(min_length=1, max_length=500)
    audience: str = Field(min_length=1, max_length=80)
    language: Literal["vi", "en"]
    learning_objective: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1, max_length=1000)
    scenes: list[ScenePlan] = Field(min_length=3, max_length=6)

    @field_validator("title", "topic", "audience", "learning_objective", "summary", mode="before")
    @classmethod
    def validate_non_blank_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return _collapse_whitespace(value)
        return value

    @model_validator(mode="after")
    def validate_unique_scenes(self) -> "LessonPlan":
        seen_ids = set()
        for scene in self.scenes:
            if scene.scene_id in seen_ids:
                raise ValueError(f"Duplicate scene id '{scene.scene_id}' in LessonPlan")
            seen_ids.add(scene.scene_id)
        return self
