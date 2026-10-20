"""Planning service coordinating generation, validation, and single repair."""

import logging
from app.domain.enums import JobStage
from app.domain.errors import PipelineExecutionError
from app.domain.lesson import LearningRequest, LessonPlan
from app.planning.repair import PlanRepairer
from app.planning.validator import validate_lesson_plan
from app.providers.llm.base import LessonPlanner, PlannerOutputValidationError, PlannerProviderError

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
        # At most one additional paid POST: either repair invalid structured
        # JSON, OR repair a semantically invalid but Pydantic-valid plan.
        schema_repaired = False
        try:
            plan = await self.planner.create_plan(request)
        except PlannerOutputValidationError as initial_error:
            repair = getattr(self.planner, "repair_invalid_output", None)
            if not callable(repair):
                raise
            logger.warning(
                "Lesson output failed local Pydantic validation; one targeted repair: %s",
                initial_error.issues,
            )
            try:
                plan = await repair(request, initial_error.invalid_json, initial_error.issues)
            except PlannerOutputValidationError as repaired_error:
                # Never expose raw model content to job records, API or logs.
                raise PlannerProviderError(
                    code="paid_planner_invalid_plan",
                    message="OpenRouter repair failed local validation: "
                            + ", ".join(
                                f"{x['path']} ({x['type']})"
                                for x in repaired_error.issues[:3]
                            ),
                    retryable=False,
                ) from None
            schema_repaired = True

        issues = validate_lesson_plan(request, plan)
        errors = [x for x in issues if x.severity == "error"]

        if not errors:
            return plan

        if schema_repaired:
            # One repair has already consumed the entire paid repair budget.
            # Never fire an unexpected third paid POST.
            raise PipelineExecutionError(
                code="plan_validation_failed",
                message="Repaired lesson plan still failed semantic validation.",
                stage=JobStage.VALIDATING_PLAN,
                retryable=False,
            )

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
