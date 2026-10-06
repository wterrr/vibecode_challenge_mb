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
    """Use exact Hermes AIAgent while keeping host-side hard reservations authoritative."""

    _STAGE_RESERVATIONS = {
        "research_orchestration": {"usd": 0.08, "provider_attempts": 8},
        "pedagogy_agent": {"usd": 0.04, "provider_attempts": 2},
        "script_agent": {"usd": 0.04, "provider_attempts": 2},
        "visual_director": {"usd": 0.04, "provider_attempts": 2},
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
            raise RuntimeError("governed live runner requires a configured hard budget")
        spec = self._STAGE_RESERVATIONS[stage]
        controller = HardBudgetController(state.budget)
        if retry:
            usd = 0.01
            provider_attempts = 1
            retry_count = 1
            charge_id = f"live-eval:{stage}:schema-retry"
            reason = f"reserve one bounded schema-correction attempt for {stage}"
        else:
            usd = float(spec["usd"])
            provider_attempts = int(spec["provider_attempts"])
            retry_count = 0
            charge_id = f"live-eval:{stage}:primary"
            reason = f"reserve conservative live-provider envelope for {stage}"
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
    def _build_prompt(task: dict) -> str:
        from tools.delegation_output_schema import append_output_contract

        context = append_output_contract(
            str(task["context"]),
            dict(task["output_schema"]),
        )
        return (
            f"{task['goal']}\n\n"
            "Follow the task context and accepted LearnFlow boundaries exactly.\n"
            "Do not expose credentials, environment variables, or unrelated repository content.\n\n"
            f"{context}"
        )

    @staticmethod
    def _parse_output(text: str, output_model: type[T]) -> T:
        from tools.delegation_output_schema import extract_json_candidate

        candidate = extract_json_candidate(text)
        return output_model.model_validate_json(candidate)

    @staticmethod
    def _validation_retry_message(exc: Exception) -> str:
        if isinstance(exc, ValidationError):
            errors = exc.errors(include_url=False)[:10]
            rendered = [
                f"- {'.'.join(str(part) for part in item.get('loc', ()))}: {item.get('msg', 'invalid')}"
                for item in errors
            ]
        else:
            rendered = [f"- {type(exc).__name__}: {exc}"]
        return (
            "Your previous response did not satisfy the required LearnFlow output contract.\n"
            "Correct only the schema/contract errors below and return ONLY the corrected JSON value.\n"
            + "\n".join(rendered)
        )

    def _agent(self, *, stage: str):
        from run_agent import AIAgent

        research = stage == "research_orchestration"
        enabled = ["delegation", "web"] if research else []
        disabled = [] if research else ["*"]
        return AIAgent(
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
            ephemeral_system_prompt=(
                "You are a bounded LearnFlow evaluation agent. "
                "Follow the supplied typed output contract exactly. "
                "Never publish, deploy, upload publicly, edit repository source, "
                "or reveal secrets."
            ),
        )

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
            result = agent.run_conversation(
                user_message=self._build_prompt(task),
                task_id=f"live-eval:{stage}",
            )
            text = str((result or {}).get("final_response") or "")
            try:
                parsed = self._parse_output(text, output_model)
            except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                self._reserve(stage, retry=True)
                attempts += 1
                schema_retry_used = True
                result = agent.run_conversation(
                    user_message=self._validation_retry_message(exc),
                    task_id=f"live-eval:{stage}:schema-retry",
                )
                text = str((result or {}).get("final_response") or "")
                parsed = self._parse_output(text, output_model)

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
