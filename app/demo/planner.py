"""Offline demo planner serving pre-validated LessonPlans for specific demonstration topics."""

import logging
import re
import unicodedata
from typing import Any

from app.demo.lesson_plans import (
    DEMO_PHOTOSYNTHESIS_PLAN,
    DEMO_RAM_SSD_PLAN,
    DEMO_TCP_PLAN,
)
from app.domain.lesson import LearningRequest, LessonPlan
from app.providers.llm.base import LessonPlanner, PlannerProviderError

logger = logging.getLogger(__name__)


def _normalize_topic(text: str) -> tuple[str, str]:
    """Normalize topic string returning (unicode_cleaned, ascii_stripped)."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    s1 = " ".join(cleaned.split())
    s2 = "".join(
        c for c in unicodedata.normalize("NFD", s1)
        if unicodedata.category(c) != "Mn"
    )
    return s1, s2


_TOPIC_MAP: dict[str, LessonPlan] = {
    # TCP Handshake aliases
    "how does the tcp three way handshake work": DEMO_TCP_PLAN,
    "tcp three way handshake": DEMO_TCP_PLAN,
    "tcp handshake": DEMO_TCP_PLAN,
    "bat tay 3 buoc tcp": DEMO_TCP_PLAN,
    "co che bat tay 3 buoc tcp": DEMO_TCP_PLAN,
    # Photosynthesis aliases
    "explain photosynthesis to a middle school student": DEMO_PHOTOSYNTHESIS_PLAN,
    "photosynthesis": DEMO_PHOTOSYNTHESIS_PLAN,
    "quang hop": DEMO_PHOTOSYNTHESIS_PLAN,
    "qua trinh quang hop": DEMO_PHOTOSYNTHESIS_PLAN,
    # RAM vs SSD aliases
    "ram vs ssd for a beginner": DEMO_RAM_SSD_PLAN,
    "ram vs ssd": DEMO_RAM_SSD_PLAN,
    "so sanh ram va ssd": DEMO_RAM_SSD_PLAN,
    "ram va ssd": DEMO_RAM_SSD_PLAN,
}


class DemoPlanner(LessonPlanner):
    """Offline planner providing deterministic validated plans for documented demo topics."""

    def __init__(self, strict: bool = True) -> None:
        self.strict = strict
        self._topic_map = _TOPIC_MAP

    async def create_plan(self, request: LearningRequest) -> LessonPlan:
        """Return the pre-validated plan matching the requested demo topic, or raise error."""
        s1, s2 = _normalize_topic(request.topic)
        plan = self._topic_map.get(s1) or self._topic_map.get(s2)

        if plan is None:
            logger.warning("Unsupported topic in demo mode: %s", request.topic[:40])
            raise PlannerProviderError(
                code="demo_topic_not_available",
                message="This topic is not available in offline demo mode.",
                retryable=False,
            )

        # Clone and customize language / audience if requested
        plan_dict = plan.model_dump()
        plan_dict["audience"] = request.audience
        plan_dict["language"] = request.language
        return LessonPlan.model_validate(plan_dict)

    async def repair_plan(
        self,
        request: LearningRequest,
        invalid_plan: LessonPlan,
        errors: list[Any],
    ) -> LessonPlan:
        """Demo plans are already validated; return valid plan directly."""
        return await self.create_plan(request)
