"""Centralized prompt templates for lesson planning and plan repair."""

from app.domain.lesson import LearningRequest, LessonPlan
from app.planning.validator import PlanIssue
from app.planning.visual_director import required_capability


def build_lesson_plan_prompt(request: LearningRequest) -> str:
    """Build the structured generation prompt for the LLM lesson planner."""
    lang_name = "Vietnamese (Tiếng Việt)" if request.language == "vi" else "English"
    duration = request.target_duration_seconds
    capability = required_capability(request.topic)
    motion_requirement = (
        f"REQUIRED VERIFIED MOTION: For this topic the supported capability is {capability.name}. "
        f"At least half the scenes (minimum two) MUST use {capability.intent.value}. "
        "Other scenes may provide concise context, not replace the actual demonstration. "
        "Treat this as an acceptance requirement, not a styling suggestion."
        if capability else
        "No verified renderer has been certified for this particular mechanism. "
        "Do not invent unsupported motion or substitute decorative animation."
    )

    if duration == 60:
        duration_guidance = (
            "- Scene Count: 3 to 4 scenes\n"
            "- Target Spoken Words: ~100 to 140 words across all scene narrations"
        )
    elif duration == 90:
        duration_guidance = (
            "- Scene Count: 4 to 5 scenes\n"
            "- Target Spoken Words: ~160 to 220 words across all scene narrations"
        )
    else:  # 120s
        duration_guidance = (
            "- Scene Count: 4 to 6 scenes\n"
            "- Target Spoken Words: ~220 to 300 words across all scene narrations"
        )

    return f"""ROLE:
You are an expert educational curriculum designer. You design concise, structured, and engaging lesson plans for short narrated educational videos. You are NOT writing animation code, video editing instructions, marketing copywriting, or conversational chat.

TASK:
Generate a complete, coherent educational LessonPlan for the requested topic, audience, language, and duration.

TOPIC:
{request.topic}

AUDIENCE:
{request.audience}

LANGUAGE:
{request.language} ({lang_name})
CRITICAL: All narration, titles, concepts, bullet points, diagram labels, and summaries MUST be written strictly in {lang_name}.

TARGET DURATION:
{duration} seconds

DURATION & SCENE GUIDELINES:
{duration_guidance}

PEDAGOGICAL SEQUENCE:
Organize the scenes following a natural learning progression:
1. Hook & Context: Introduce the problem, importance, or curiosity.
2. Core Concept / Model: Define the central idea clearly.
3. Process / Practical Example: Step-by-step mechanism or application.
4. Contrast / Trade-offs: Distinctions, comparisons, or boundary conditions.
5. Summary / Takeaway: Key synthesis reinforcing learning outcomes.
(You may use 3 to 6 scenes total as appropriate for the topic and duration).

SUPPORTED VISUAL TYPES:
You must select exactly ONE supported visual type for each scene:
1. concept_card: For core definitions, single principles, key lists, or summary takeaways.
2. process_diagram: For step-by-step sequences, protocols, workflows, cycles, or state transitions. (Requires actors with valid IDs matching ^[a-z][a-z0-9_]{{0,30}}$ and contiguous order 1..N).
3. comparison: For side-by-side trade-offs, A vs B comparisons, or category contrasts (2 to 3 columns).
4. illustration: Only when a concrete physical scene or object materially aids conceptual understanding. MUST include fallback_heading and fallback_points.
5. function_graph: For continuous mathematical change, slopes, rates of change, derivatives, motion along function graphs, and related *function-based* explanations. This is a REAL host-verified animated graph, NOT a slide.
   - function must be one of polynomial / sine / cosine / exponential (no arbitrary expressions or code).
   - polynomial coefficients are ordered [constant, x, x^2, ...], e.g. x^2 is [0, 0, 1]. Values and powers are computed and verified by the host, never put answers in the JSON.
   - focus_x must be in [-2, 2].
   - motion_kind = secant_to_tangent for a moving second point approaching a fixed first point; slope_scan for a point moving along the graph with its instantaneous tangent.
   - Select this family for a mathematics concept whose understanding requires observing continuous graphical transformation. At least one visually explanatory, non-card scene should be chosen whenever an available typed representation is appropriate. Do NOT fabricate a function if none is relevant.


6. array_trace: For algorithmic search over a sorted numeric sequence, especially binary search.
   - algorithm must be "binary_search". The JSON supplies ONLY the example input: values (5-12 sorted integers in -999..999) and target (-999..999).
   - NEVER give mid/low/high, claimed result, search action, executable code, or frame positions: the host replays every comparison using its independently verified V3 algorithm oracle.
   - Two trace scenes should use different valid input examples, ideally one found and one missing.
   - Each trace scene shows stable numbered array cells with movable LOW, MID, HIGH markers, eliminated regions, state transitions, and a verified result. This is not the static process_diagram renderer.

7. central_force_motion: For gravity-driven trajectories, orbital motion,
   bound orbits, planetary motion, artificial satellites and comets.
   - motion_kind = inertia_only / gravity_deflection / bound_orbit.
   - eccentricity = 0..0.45. The host independently integrates Newtonian
     inverse-square central attraction and verifies energy and angular momentum.
   - The renderer shows a moving body, a persistent trail, tangential velocity
     and the radial inward gravity force. It is not a static diagram.
   - DO NOT supply calculations, animation code, arbitrary pixel coordinates
     or ephemerides. It is an idealized two-body teaching illustration.
   - For orbital mechanism lessons, demonstrate ALL THREE modes in separate
     scenes so viewers can observe the causal difference, NOT three text cards.
   - Explain that inertia_only is a counterfactual without gravity, not the
     actual behavior of planets.

PRODUCTION VISUAL DIRECTOR:
{motion_requirement}
For continuous math, demonstrate BOTH moving secant_to_tangent AND moving slope_scan across the lesson.
For binary search, show at least two different valid sorted input arrays and target values.
Write narration that explains what viewers observe happening on the canvas. Avoid transitions
that merely rephrase the same slide. A visual family must not claim a capability it cannot draw.

VISUAL TEACHING REQUIREMENT:
The goal is a visually demonstrated lesson, not narrated slides. Each scene must contain an observable mechanism, state transition, graph, comparison or material illustration relevant to the narration. Prefer a moving mathematical construction for math; avoid using concept_card for consecutive core explanatory scenes. Never claim that a card/diagram moves when it does not. A topic without a verified suitable motion family may remain non-animated rather than falsely depicting mathematical or physical facts.

FACTUAL & QUALITY CAUTION:
- Provide accurate, factual explanations.
- Do NOT fabricate citations or sources.
- Do NOT include URLs or web links in narration.
- Do NOT include markdown code blocks, animation scripts, or HTML.
- Narration in each scene must be fluent, natural spoken speech.

OUTPUT FORMAT:
Return data conforming exactly to the structured JSON schema for LessonPlan.
"""


def build_repair_prompt(
    request: LearningRequest,
    plan: LessonPlan,
    issues: list[PlanIssue],
) -> str:
    """Build a focused repair prompt containing only validation errors."""
    error_issues = [i for i in issues if i.severity == "error"]
    error_bullets = "\n".join(
        f"- [Code: {e.code}] Scene: {e.scene_id or 'global'} -> {e.message}"
        for e in error_issues
    )

    return f"""ROLE:
You are an expert educational curriculum designer repairing a lesson plan.

TASK:
Fix ONLY the listed validation errors in the lesson plan while preserving all valid educational content, wording, and structure.

ORIGINAL REQUEST:
Topic: {request.topic}
Audience: {request.audience}
Language: {request.language}
Target Duration: {request.target_duration_seconds}s

VALIDATION ERRORS TO FIX:
{error_bullets}

CURRENT INVALID LESSON PLAN:
{plan.model_dump_json(indent=2)}

INSTRUCTIONS:
1. Fix all listed errors explicitly.
2. Ensure scene_ids match ^s[0-9]{{2}}_[a-z0-9_]+$ and are unique.
3. If visual_intent is process_diagram, ensure every step references existing actor IDs and orders are contiguous 1..N.
4. Ensure language remains strictly {request.language}.
5. Return the complete corrected LessonPlan matching the structured JSON schema.
"""
