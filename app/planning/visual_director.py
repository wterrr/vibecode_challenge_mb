"""Capability-based visual teaching requirements for production real AI plans.

This registry maps *supported pedagogical mechanisms* to trusted renderer
families. It does not fabricate animation for unimplemented subject areas
and never substitutes a static card when a supported mechanism was requested.

Adding a future capability means registering an intent + mechanism policy,
not authoring a video template for each user topic or example value.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil
import re
import unicodedata

from app.domain.lesson import ArrayTraceSpec, FunctionGraphSpec, CentralForceMotionSpec, LessonPlan
from app.domain.enums import VisualIntent


@dataclass(frozen=True)
class MotionCapability:
    token_patterns: tuple[str, ...]
    intent: VisualIntent
    name: str


CAPABILITIES = (
    MotionCapability(
        token_patterns=(r"\bbinary search\b",r"\btim kiem nhi phan\b"),
        intent=VisualIntent.ARRAY_TRACE,
        name="verified_array_search",
    ),
    MotionCapability(
        token_patterns=(
            r"\bquy dao\b", r"\borbit(s|al|ing)?\b",
            r"\bchuyen dong quanh\b", r"\bgravitational trajectory\b",
        ),
        intent=VisualIntent.CENTRAL_FORCE_MOTION,
        name="verified_inverse_square_motion",
    ),
    MotionCapability(
        token_patterns=(r"\bderivatives?\b",r"\bdao ham\b",r"\bdifferentiation\b"),
        intent=VisualIntent.FUNCTION_GRAPH,
        name="function_slope_motion",
    ),
)


def normalize_search_text(value: str) -> str:
    s = unicodedata.normalize("NFKD", value.casefold().replace("đ","d"))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s)


def required_capability(topic: str) -> MotionCapability | None:
    """Only route unambiguous mechanisms that already have audited renderers."""
    normalized = normalize_search_text(topic)
    matches = [c for c in CAPABILITIES
               if any(re.search(p, normalized) for p in c.token_patterns)]
    return matches[0] if len(matches) == 1 else None


def visual_teaching_errors(topic: str, plan: LessonPlan) -> list[tuple[str,str]]:
    """Reject slide-dominated lesson plans for supported teaching mechanisms."""
    cap = required_capability(topic)
    if cap is None:
        return []  # No false claim of generic 3B1B-level capability.
    motion_scenes = [s for s in plan.scenes if s.visual_intent == cap.intent]
    minimum = max(2, ceil(len(plan.scenes)/2))
    failures: list[tuple[str,str]] = []
    if len(motion_scenes) < minimum:
        failures.append((
            "insufficient_semantic_motion",
            f"{cap.name} requires at least {minimum} of {len(plan.scenes)} "
            f"scenes using visual_intent='{cap.intent.value}', not narrated cards.",
        ))
    if cap.intent == VisualIntent.CENTRAL_FORCE_MOTION:
        modes = {
            scene.visual_spec.motion_kind for scene in motion_scenes
            if isinstance(scene.visual_spec, CentralForceMotionSpec)
        }
        missing = {"inertia_only", "gravity_deflection", "bound_orbit"} - modes
        if missing:
            failures.append((
                "missing_physical_causal_sequence",
                "Use inertia_only, gravity_deflection and bound_orbit scenes to "
                "show the causal transition from a straight tangent to a bound orbit; "
                "no static diagram substitutes for a demonstrated trajectory.",
            ))
    if cap.intent == VisualIntent.ARRAY_TRACE and len(motion_scenes) >= 2:
        sources = {
            (tuple(s.visual_spec.values), s.visual_spec.target)
            for s in motion_scenes if isinstance(s.visual_spec, ArrayTraceSpec)
        }
        if len(sources) < 2:
            failures.append(("repeated_visual_example",
                             "Show two different sorted arrays/targets; host replays each trace."))
    if cap.intent == VisualIntent.FUNCTION_GRAPH and len(motion_scenes) >= 2:
        modes = {
            s.visual_spec.motion_kind for s in motion_scenes
            if isinstance(s.visual_spec, FunctionGraphSpec)
        }
        if not {"secant_to_tangent", "slope_scan"}.issubset(modes):
            failures.append(("missing_visual_transformation",
                             "Include both secant_to_tangent and slope_scan to explain the mechanism."))
    return failures
