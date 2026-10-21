"""Host-owned, bounded visual tool registry for the paid planning agent.

The model can *request* these functions, but only the host executes them.
None accepts Python, shell, arbitrary functions, pixel commands, filesystem
paths, URLs, or external network destinations. Every probe uses the same
typed specs and mathematical oracles as the production renderers.
"""
from __future__ import annotations

import json
import math
from typing import Any

from pydantic import ValidationError

from app.domain.enums import VisualIntent
from app.domain.lesson import ArrayTraceSpec, FunctionGraphSpec, CentralForceMotionSpec
from app.rendering.array_trace import verified_array_trace
from app.rendering.function_graph import value_and_slope
from app.rendering.central_force_motion import orbital_states, energy, angular_momentum

MAX_TOOL_CALLS = 3
MAX_ARGUMENT_BYTES = 4096

# OpenRouter's function-calling schema is for model guidance, NOT trusted
# validation. Pydantic and the V3 oracle always validate executed arguments.
VISUAL_TOOLS: tuple[dict[str, Any], ...] = (
    {
        "type": "function",
        "function": {
            "name": "describe_visual_tools",
            "description": "Discover every host-registered visual family and its limits. No arguments.",
            "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "probe_array_trace",
            "description": (
                "Verify a proposed sorted-array binary-search example using the host's "
                "independent V3 oracle. Returns each comparison and the leftmost answer; "
                "no executable code, frame coordinates or model-generated result accepted."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "values": {"type": "array", "items": {"type": "integer"}, "minItems": 5, "maxItems": 12},
                    "target": {"type": "integer", "minimum": -999, "maximum": 999},
                },
                "required": ["values", "target"], "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "probe_function_graph",
            "description": (
                "Verify a polynomial, sine, cosine, or exponential graph. Compute the "
                "function value and derivative at focus_x using host-owned mathematics."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "function": {"type": "string", "enum": ["polynomial", "sine", "cosine", "exponential"]},
                    "coefficients": {"type": "array", "items": {"type": "number"}, "maxItems": 5},
                    "focus_x": {"type": "number", "minimum": -2, "maximum": 2},
                    "motion_kind": {"type": "string", "enum": ["secant_to_tangent", "slope_scan"]},
                },
                "required": ["function", "coefficients", "focus_x", "motion_kind"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "probe_central_force_motion",
            "description": (
                "Verify an inverse-square gravitational trajectory using a bounded "
                "eccentricity and teaching mode. Returns host-computed conserved "
                "energy, angular momentum and orbit-closure proof."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "motion_kind": {
                        "type": "string", "enum": ["inertia_only","gravity_deflection","bound_orbit"],
                    },
                    "eccentricity": {"type": "number", "minimum": 0, "maximum": .45},
                },
                "required": ["motion_kind","eccentricity"],"additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "probe_code2video_scene",
            "description": (
                "Validate a semantic request for one Code2Video scene. Does NOT "
                "run generated Python; an isolated worker renders after the "
                "full LessonPlan is accepted. Use only for concepts that "
                "existing verified renderer families cannot visualize."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type":"string","minLength":3,"maxLength":110},
                    "visual_goal": {"type":"string","minLength":12,"maxLength":500},
                },
                "required":["title","visual_goal"],"additionalProperties":False,
            },
        },
    },
)


def tool_catalog(*, code2video_enabled: bool = False) -> dict[str, Any]:
    """Source of truth for available motion and static renderers.

    The static families have scene-spec contracts but no mathematical probe;
    do not misrepresent them as continuous visual animation.
    """
    return {
        "version": "production-visual-tools-v1",
        "scene_tools": [
            {"intent": VisualIntent.CONCEPT_CARD.value, "motion": "static_card"},
            {"intent": VisualIntent.PROCESS_DIAGRAM.value, "motion": "discrete_highlight"},
            {"intent": VisualIntent.COMPARISON.value, "motion": "static_comparison"},
            {"intent": VisualIntent.ILLUSTRATION.value, "motion": "static_or_image"},
            {"intent": VisualIntent.FUNCTION_GRAPH.value, "motion": "continuous_verified",
             "probe": "probe_function_graph", "families": ["polynomial", "sine", "cosine", "exponential"]},
            {"intent": VisualIntent.ARRAY_TRACE.value, "motion": "stateful_verified",
             "probe": "probe_array_trace", "algorithms": ["binary_search"]},
            {"intent": VisualIntent.CODE2VIDEO_SCENE.value,
             "motion": "generated_manim_worker",
             "available": code2video_enabled,
             "probe": "probe_code2video_scene" if code2video_enabled else None,
             "security": "separate_secretless_renderer"},
            {"intent": VisualIntent.CENTRAL_FORCE_MOTION.value, "motion": "continuous_verified",
             "probe": "probe_central_force_motion",
             "physics": "idealized_newtonian_inverse_square_two_body"},
        ],
        "safety": "No model-provided code, math results, pixel coordinates or shell commands.",
    }


def visual_tool_definitions(*, code2video_enabled: bool = False) -> list[dict[str, Any]]:
    """Return independent JSON-compatible tool definitions for OpenRouter."""
    allowed = VISUAL_TOOLS if code2video_enabled else VISUAL_TOOLS[:-1]
    return json.loads(json.dumps(allowed))


def execute_visual_tool(name: str, raw_arguments: str, *,
                        code2video_enabled: bool = False) -> dict[str, Any]:
    """Fail closed on every unsupported or unverified request.

    Results are deterministic and safe to feed back to the model as evidence,
    but the resulting LessonPlan must still pass the full rendering contracts.
    """
    if name not in {t["function"]["name"] for t in visual_tool_definitions(code2video_enabled=code2video_enabled)}:
        raise ValueError("visual_tool_not_registered")
    if not isinstance(raw_arguments, str) or len(raw_arguments.encode("utf-8")) > MAX_ARGUMENT_BYTES:
        raise ValueError("visual_tool_arguments_too_large")
    try:
        args = json.loads(raw_arguments)
    except (ValueError, TypeError) as exc:
        raise ValueError("visual_tool_invalid_json") from exc
    if not isinstance(args, dict):
        raise ValueError("visual_tool_arguments_not_object")

    if name == "describe_visual_tools":
        if args:
            raise ValueError("visual_tool_unexpected_arguments")
        return tool_catalog(code2video_enabled=code2video_enabled)

    if name == "probe_code2video_scene":
        from app.domain.lesson import Code2VideoSceneSpec
        if not code2video_enabled:
            raise ValueError("code2video_worker_disabled")
        if set(args) != {"title","visual_goal"}:
            raise ValueError("visual_tool_unexpected_arguments")
        try:
            spec=Code2VideoSceneSpec.model_validate({"type":"code2video_scene",**args})
        except ValidationError as exc:
            raise ValueError("code2video_scene_invalid") from exc
        return {
            "intent":"code2video_scene", "accepted":True,
            "title":spec.title, "visual_goal":spec.visual_goal,
            "execution":"deferred_to_secretless_manim_worker",
            "guarantees":"typed_request_only_not_yet_rendered",
        }

    if name == "probe_array_trace":
        if set(args) != {"values", "target"}:
            raise ValueError("visual_tool_unexpected_arguments")
        try:
            spec = ArrayTraceSpec.model_validate({"type": "array_trace", "algorithm": "binary_search", **args})
            trace = verified_array_trace(spec)
        except (ValidationError, ValueError) as exc:
            raise ValueError("visual_tool_array_not_verified") from exc
        return {
            "intent": "array_trace", "verified": True,
            "values": list(trace.query.values), "target": trace.query.target,
            "result_index": trace.result_index, "trace_sha256": trace.trace_sha256,
            "steps": [
                {"low": s.low, "mid": s.mid, "high": s.high,
                 "observed": s.observed, "action": s.action}
                for s in trace.steps
            ],
        }

    if name == "probe_central_force_motion":
        if set(args) != {"motion_kind","eccentricity"}:
            raise ValueError("visual_tool_unexpected_arguments")
        try:
            spec = CentralForceMotionSpec.model_validate({
                "type": "central_force_motion", **args,
            })
            states = orbital_states(spec)
        except (ValidationError, ValueError, OverflowError) as exc:
            raise ValueError("visual_tool_physics_not_verified") from exc
        return {
            "intent": "central_force_motion", "verified": True,
            "motion_kind": spec.motion_kind, "eccentricity": spec.eccentricity,
            "host_energy": round(energy(states[0]),6),
            "host_angular_momentum": round(angular_momentum(states[0]),6),
            "host_orbit_closed": True,
            "model": "idealized_inverse_square_mu_1",
        }

    if set(args) != {"function", "coefficients", "focus_x", "motion_kind"}:
        raise ValueError("visual_tool_unexpected_arguments")
    try:
        spec = FunctionGraphSpec.model_validate({"type": "function_graph", **args})
        # A bounded spec can still produce overflowing values at selected
        # x with exponential-like operations: reject nonfinite values.
        value, slope = value_and_slope(spec, spec.focus_x)
        if not (math.isfinite(value) and math.isfinite(slope)):
            raise ValueError("nonfinite graph probe")
    except (ValidationError, ValueError, OverflowError) as exc:
        raise ValueError("visual_tool_graph_not_verified") from exc
    return {
        "intent": "function_graph", "verified": True,
        "function": spec.function, "coefficients": spec.coefficients,
        "focus_x": spec.focus_x, "motion_kind": spec.motion_kind,
        "host_value_at_focus": round(value, 6), "host_slope_at_focus": round(slope, 6),
    }


def render_tool_receipts(receipts: list[dict[str, Any]]) -> str:
    """Serialize only validated host outputs, bounded for paid prompt budget."""
    if not receipts or len(receipts) > MAX_TOOL_CALLS:
        raise ValueError("visual_tool_receipts_count_invalid")
    return json.dumps(receipts, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
