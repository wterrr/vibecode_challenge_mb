"""Planning service coordinating generation, validation, and single repair."""

import logging
from app.domain.enums import JobStage
from app.domain.errors import PipelineExecutionError
from app.domain.lesson import LearningRequest, LessonPlan
from app.planning.repair import PlanRepairer
from app.planning.validator import validate_lesson_plan
from app.providers.llm.base import LessonPlanner

logger = logging.getLogger(__name__)


class PlanningService:
    """Orchestrates structured lesson planning, semantic validation, and maximum one repair."""

    def __init__(
        self,
        planner: LessonPlanner,
        repairer: PlanRepairer | None = None,
    ):
        self.planner = planner
        self.repairer = repairer or PlanRepairer(planner)

    async def build_valid_plan(
        self,
        request: LearningRequest,
    ) -> LessonPlan:
        """Create and semantically validate a LessonPlan, attempting at most one repair if invalid."""
        plan = await self.planner.create_plan(request)

        issues = validate_lesson_plan(request, plan)
        errors = [x for x in issues if x.severity == "error"]

        if not errors:
            return plan

        logger.info(
            "Initial lesson plan had %d validation errors; invoking single repair attempt",
            len(errors),
        )

        repaired = await self.repairer.repair(
            request,
            plan,
            errors,
        )

        issues2 = validate_lesson_plan(request, repaired)
        errors2 = [x for x in issues2 if x.severity == "error"]

        if errors2:
            logger.error(
                "Lesson plan repair failed validation with %d errors",
                len(errors2),
            )
            raise PipelineExecutionError(
                code="plan_validation_failed",
                message="The generated lesson plan could not be validated.",
                stage=JobStage.VALIDATING_PLAN,
                retryable=False,
            )

        return repaired
