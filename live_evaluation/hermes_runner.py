"""Exact pinned-Hermes structured runner for governed live V2D evaluation."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
import time
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from agent_contracts import BudgetUsage
from runtime_governance import BudgetCharge, HardBudgetController, SpendCategory
from runtime_governance.hermes_plugin import load_state, save_state

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class StageUsage:
    stage: str
    model: str
    attempts: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float | None
    cost_status: str
    api_calls: int
    duration_seconds: float
    schema_retry_used: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LiveHermesStructuredRunner:
    """Use exact Hermes AIAgent with hard usage quotas and uncapped USD telemetry."""

    _STAGE_RESERVATIONS = {
        "research_orchestration": {"usd": 0.0, "provider_attempts": 128},
        "pedagogy_agent": {"usd": 0.0, "provider_attempts": 3},
        "script_agent": {"usd": 0.0, "provider_attempts": 3},
        "visual_director": {"usd": 0.0, "provider_attempts": 3},
    }

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        repo_root: str | Path,
        base_url: str = "https://openrouter.ai/api/v1",
    ) -> None:
        self.model = str(model)
        self.api_key = str(api_key)
        self.base_url = str(base_url)
        self.repo_root = Path(repo_root).resolve()
        self.stage_usage: list[StageUsage] = []

    def _reserve(self, stage: str, *, retry: bool = False) -> None:
        state = load_state()
        if state.budget is None:
            raise RuntimeError("governed live runner requires configured usage quotas")
        spec = self._STAGE_RESERVATIONS[stage]
        controller = HardBudgetController(state.budget)
        if retry:
            usd = 0.0
            provider_attempts = 1
            retry_count = 1
            charge_id = f"live-eval:{stage}:schema-retry"
            reason = f"reserve one bounded schema-correction attempt for {stage}"
        else:
            usd = float(spec["usd"])
            provider_attempts = int(spec["provider_attempts"])
            retry_count = 0
            charge_id = f"live-eval:{stage}:primary"
            reason = f"reserve bounded provider-attempt quota for {stage}"
        controller.authorize(
            BudgetCharge(
                charge_id=charge_id,
                category=SpendCategory.LLM,
                amount_usd=usd,
                usage=BudgetUsage(
                    provider_attempts=provider_attempts,
                    retries=retry_count,
                ),
                reason=reason,
            )
        )
        save_state(
            state.model_copy(
                update={"budget": controller.ledger},
            )
        )

    @staticmethod
    def _build_prompt(task: dict, *, stage: str) -> str:
        from tools.delegation_output_schema import append_output_contract

        context = append_output_contract(
            str(task["context"]),
            dict(task["output_schema"]),
        )
        stage_guidance = ""
        return (
            f"{task['goal']}\n\n"
            "Follow the task context and accepted LearnFlow boundaries exactly.\n"
            "Do not expose credentials, environment variables, or unrelated repository content.\n\n"
            f"{stage_guidance}"
            f"{context}"
        )

    @staticmethod
    def _parse_output(
        text: str,
        output_model: type[T],
        *,
        stage: str,
        task: dict,
    ) -> T:
        from tools.delegation_output_schema import extract_json_candidate

        candidate = extract_json_candidate(text)
        if stage == "pedagogy_agent":
            from pedagogy_agent import assemble_pedagogy_plan_wire

            payload = json.loads(candidate)
            context = json.loads(str(task["context"]))
            research = dict(context.get("research") or {})
            concepts = tuple(str(item) for item in research.get("concepts") or ())
            assembled = assemble_pedagogy_plan_wire(
                payload,
                concepts=concepts,
            )
            return output_model.model_validate(
                assembled.model_dump(mode="json")
            )
        if stage == "script_agent":
            from script_agent import assemble_lesson_script_wire

            payload = json.loads(candidate)
            context = json.loads(str(task["context"]))
            claim_ids = tuple(
                str(item["claim_id"])
                for item in context.get("selected_fact_claim_catalog") or ()
            )
            objective_ids = tuple(
                str(item["objective_id"])
                for item in context.get("objective_catalog") or ()
            )
            assembled = assemble_lesson_script_wire(
                payload,
                claim_ids=claim_ids,
                objective_ids=objective_ids,
            )
            return output_model.model_validate(
                assembled.model_dump(mode="json")
            )
        return output_model.model_validate_json(candidate)

    @staticmethod
    def _validation_retry_message(task: dict, previous_text: str, exc: Exception) -> str:
        if isinstance(exc, ValidationError):
            errors = exc.errors(include_url=False)[:10]
            rendered = [
                f"- {'.'.join(str(part) for part in item.get('loc', ()))}: {item.get('msg', 'invalid')}"
                for item in errors
            ]
        else:
            rendered = [f"- {type(exc).__name__}: {exc}"]
        schema = json.dumps(
            dict(task["output_schema"]),
            ensure_ascii=False,
            sort_keys=True,
        )
        return (
            "Your previous response did not satisfy the required LearnFlow output contract.\n"
            "Do not call tools or delegate again. Correct only the schema/contract errors and return ONLY "
            "the corrected JSON value.\n\n"
            f"Required JSON Schema:\n{schema}\n\n"
            f"Previous response:\n{previous_text}\n\n"
            "Validation errors:\n"
            + "\n".join(rendered)
        )

    @staticmethod
    def _research_plan_from_task(task: dict):
        from research_orchestration import ResearchOrchestrationPlan

        context = json.loads(str(task["context"]))
        brief = dict(context["learning_brief"])
        plan_payload = dict(context["research_plan"])
        plan = ResearchOrchestrationPlan.model_validate(plan_payload)
        return brief, plan

    def _run_research_delegation(
        self,
        *,
        agent,
        task: dict,
        output_model: type[T],
    ) -> tuple[T, dict[str, Any]]:
        from research_orchestration import assemble_specialist_delegation_results
        from tools.delegate_tool import delegate_task

        brief, plan = self._research_plan_from_task(task)
        hermes_tasks = [
            {
                "goal": specialist.goal,
                "context": specialist.context,
                "output_schema": specialist.output_schema,
            }
            for specialist in plan.specialist_tasks
        ]
        raw = delegate_task(
            tasks=hermes_tasks,
            background=False,
            parent_agent=agent,
        )
        try:
            delegation_payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Hermes delegate_task returned invalid JSON"
            ) from exc
        if isinstance(delegation_payload, dict) and delegation_payload.get("error"):
            raise RuntimeError(
                "Hermes delegate_task rejected research fan-out: "
                + str(delegation_payload["error"])
            )

        assembled = assemble_specialist_delegation_results(
            plan=plan,
            brief_id=str(brief["brief_id"]),
            topic=str(brief["user_query"]),
            delegation_payload=delegation_payload,
        )
        return (
            output_model.model_validate(
                assembled.model_dump(mode="json")
            ),
            delegation_payload,
        )

    @staticmethod
    def _delegation_usage(payload: dict[str, Any]) -> dict[str, Any]:
        rows = payload.get("results")
        if not isinstance(rows, list):
            rows = []
        statuses = {
            str(row.get("cost_status") or "unknown")
            for row in rows
            if isinstance(row, dict)
        }
        input_tokens = sum(
            int((row.get("tokens") or {}).get("input") or 0)
            for row in rows
            if isinstance(row, dict)
        )
        output_tokens = sum(
            int((row.get("tokens") or {}).get("output") or 0)
            for row in rows
            if isinstance(row, dict)
        )
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "api_calls": sum(
                int(row.get("api_calls") or 0)
                for row in rows
                if isinstance(row, dict)
            ),
            "estimated_cost_usd": round(
                sum(
                    float(row.get("cost_usd") or 0.0)
                    for row in rows
                    if isinstance(row, dict)
                ),
                8,
            ),
            "cost_status": (
                next(iter(statuses))
                if len(statuses) == 1
                else ("mixed" if statuses else "unknown")
            ),
            "schema_retry_used": any(
                int(row.get("schema_retries") or 0) > 0
                for row in rows
                if isinstance(row, dict)
            ),
        }

    def _agent(self, *, stage: str):
        from run_agent import AIAgent

        research = stage == "research_orchestration"
        enabled = ["delegation", "web"] if research else []
        disabled = [] if research else ["*"]
        request_overrides: dict[str, Any] = {}
        if self.model.startswith(("google/gemma-4-", "apodex/apodex-")):
            request_overrides["response_format"] = {"type": "json_object"}
        if self.model.startswith("google/gemma-4-"):
            request_overrides["reasoning_effort"] = "medium"

        agent = AIAgent(
            base_url=self.base_url,
            api_key=self.api_key,
            provider="openrouter",
            model=self.model,
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
            skip_background_review=True,
            save_trajectories=False,
            enabled_toolsets=enabled,
            disabled_toolsets=disabled,
            max_iterations=128 if research else 3,
            request_overrides=request_overrides,
            ephemeral_system_prompt=(
                "You are a bounded LearnFlow evaluation agent. "
                "Follow the supplied typed output contract exactly. "
                "Never publish, deploy, upload publicly, edit repository source, "
                "or reveal secrets."
            ),
        )
        if research:
            # The host coordinator is the Director (depth 0). This AIAgent is the
            # Research Orchestrator (depth 1), so Hermes native delegation waits
            # synchronously for its depth-2 specialist batch instead of dispatching
            # a top-level background task whose result would arrive after this call.
            agent._delegate_depth = 1
            agent._delegate_role = "orchestrator"
        return agent

    def run(self, *, stage: str, task: dict, output_model: type[T]) -> T:
        if stage not in self._STAGE_RESERVATIONS:
            raise RuntimeError(f"live runner refuses unknown stage {stage!r}")

        self._reserve(stage)
        agent = self._agent(stage=stage)
        t0 = time.perf_counter()
        attempts = 1
        schema_retry_used = False
        result: dict[str, Any] | None = None
        try:
            if stage == "research_orchestration":
                parsed, delegation_payload = self._run_research_delegation(
                    agent=agent,
                    task=task,
                    output_model=output_model,
                )
                observed = self._delegation_usage(delegation_payload)
                usage = StageUsage(
                    stage=stage,
                    model=self.model,
                    attempts=1,
                    input_tokens=int(observed["input_tokens"]),
                    output_tokens=int(observed["output_tokens"]),
                    total_tokens=(
                        int(observed["input_tokens"])
                        + int(observed["output_tokens"])
                    ),
                    estimated_cost_usd=float(
                        observed["estimated_cost_usd"]
                    ),
                    cost_status=str(observed["cost_status"]),
                    api_calls=int(observed["api_calls"]),
                    duration_seconds=round(
                        time.perf_counter() - t0,
                        6,
                    ),
                    schema_retry_used=bool(
                        observed["schema_retry_used"]
                    ),
                )
                self.stage_usage.append(usage)
                return parsed

            result = agent.run_conversation(
                user_message=self._build_prompt(task, stage=stage),
                task_id=f"live-eval:{stage}",
            )
            text = str((result or {}).get("final_response") or "")
            try:
                parsed = self._parse_output(
                    text,
                    output_model,
                    stage=stage,
                    task=task,
                )
            except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                self._reserve(stage, retry=True)
                attempts += 1
                schema_retry_used = True
                result = agent.run_conversation(
                    user_message=self._validation_retry_message(task, text, exc),
                    conversation_history=list((result or {}).get("messages") or []),
                    task_id=f"live-eval:{stage}:schema-retry",
                )
                text = str((result or {}).get("final_response") or "")
                parsed = self._parse_output(
                    text,
                    output_model,
                    stage=stage,
                    task=task,
                )

            usage = StageUsage(
                stage=stage,
                model=self.model,
                attempts=attempts,
                input_tokens=int(getattr(agent, "session_prompt_tokens", 0) or 0),
                output_tokens=int(getattr(agent, "session_completion_tokens", 0) or 0),
                total_tokens=int(getattr(agent, "session_total_tokens", 0) or 0),
                estimated_cost_usd=(
                    float(getattr(agent, "session_estimated_cost_usd", 0.0))
                    if isinstance(getattr(agent, "session_estimated_cost_usd", None), (int, float))
                    else None
                ),
                cost_status=str(getattr(agent, "session_cost_status", None) or "unknown"),
                api_calls=int((result or {}).get("api_calls") or 0),
                duration_seconds=round(time.perf_counter() - t0, 6),
                schema_retry_used=schema_retry_used,
            )
            self.stage_usage.append(usage)
            return parsed
        finally:
            try:
                agent.close()
            except Exception:
                pass

    def usage_summary(self) -> dict[str, Any]:
        rows = [row.to_dict() for row in self.stage_usage]
        return {
            "stages": rows,
            "input_tokens": sum(row.input_tokens for row in self.stage_usage),
            "output_tokens": sum(row.output_tokens for row in self.stage_usage),
            "total_tokens": sum(row.total_tokens for row in self.stage_usage),
            "api_calls": sum(row.api_calls for row in self.stage_usage),
            "estimated_cost_usd": round(
                sum(row.estimated_cost_usd or 0.0 for row in self.stage_usage),
                8,
            ),
            "schema_retries": sum(int(row.schema_retry_used) for row in self.stage_usage),
        }
