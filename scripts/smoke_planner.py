#!/usr/bin/env python3
"""Manual developer smoke test for Gemini lesson planner (CP3).

Runs against the configured GEMINI_API_KEY environment without leaking secrets.
"""

import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.config import get_settings
from app.domain.lesson import LearningRequest
from app.planning.service import PlanningService
from app.planning.validator import validate_lesson_plan
from app.providers.llm.gemini import GeminiLessonPlanner


async def main() -> None:
    print("=" * 60)
    print("  LearnFlow AI — Gemini Planner Manual Smoke Test")
    print("=" * 60)

    settings = get_settings()
    if not settings.gemini_api_key or not settings.gemini_api_key.strip():
        print("[FAIL] GEMINI_API_KEY is not configured in settings or environment.")
        sys.exit(1)

    print(f"Model configured: {settings.gemini_planner_model}")
    print("Initializing GeminiLessonPlanner...")

    planner = GeminiLessonPlanner(
        api_key=settings.gemini_api_key,
        model=settings.gemini_planner_model,
    )
    service = PlanningService(planner=planner)

    request = LearningRequest(
        topic="How does the TCP three-way handshake work?",
        audience="Developer",
        language="vi",
        target_duration_seconds=60,
    )

    print(f"Sending planning request for topic: '{request.topic}'...")
    try:
        plan = await service.build_valid_plan(request)
        print("\n[SUCCESS] LessonPlan generated and validated successfully!")
        print(f"  Title      : {plan.title}")
        print(f"  Language   : {plan.language}")
        print(f"  Scene Count: {len(plan.scenes)}")
        for idx, scene in enumerate(plan.scenes, start=1):
            print(f"    - Scene {idx}: [{scene.scene_id}] {scene.title} (visual: {scene.visual_intent.value})")

        issues = validate_lesson_plan(request, plan)
        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]
        print(f"  Semantic Validation Errors  : {len(errors)}")
        print(f"  Semantic Validation Warnings: {len(warnings)}")
        for w in warnings:
            print(f"    * Warning [{w.code}]: {w.message}")

    except Exception as e:
        err_code = getattr(e, "code", type(e).__name__)
        print(f"\n[FAIL] Planner smoke test failed with code: {err_code}")
        print(f"  Reason: {getattr(e, 'message', str(e))[:120]}")


if __name__ == "__main__":
    asyncio.run(main())
