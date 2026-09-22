"""Plan repairer handling single-turn correction of validation errors."""

from app.domain.lesson import LearningRequest, LessonPlan
from app.planning.validator import PlanIssue
from app.providers.llm.base import LessonPlanner


class PlanRepairer:
    """Invokes the planner to repair a lesson plan with specific validation errors."""

    def __init__(self, planner: LessonPlanner):
        self.planner = planner

    async def repair(
        self,
        request: LearningRequest,
        invalid_plan: LessonPlan,
        errors: list[PlanIssue],
    ) -> LessonPlan:
        """Request a single targeted repair for an invalid LessonPlan."""
        return await self.planner.repair_plan(request, invalid_plan, errors)
