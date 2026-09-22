"""Centralized prompt templates for lesson planning and plan repair."""

from app.domain.lesson import LearningRequest, LessonPlan
from app.planning.validator import PlanIssue


def build_lesson_plan_prompt(request: LearningRequest) -> str:
    """Build the structured generation prompt for the LLM lesson planner."""
    lang_name = "Vietnamese (Tiếng Việt)" if request.language == "vi" else "English"
    duration = request.target_duration_seconds

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
