"""Strict contracts for durable LearnFlow job/profile definitions."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator

from agent_contracts import AgentContractError, ContractModel


def _tupleize(value: Any):
    return tuple(value) if isinstance(value, list) else value


class WorkerRole(str, Enum):
    RESEARCH = "research"
    PRODUCTION = "production"
    REVIEW = "review"


class WorkerProfileSpec(ContractModel):
    role: WorkerRole
    profile_name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    always_load_skills: tuple[str, ...] = Field(default_factory=tuple)
    max_in_progress: int = Field(default=1, ge=1, le=4)

    @field_validator("profile_name")
    @classmethod
    def _profile_name(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for ch in value):
            raise AgentContractError("profile_name must be lowercase alphanumeric/hyphen/underscore")
        return value

    @field_validator("description")
    @classmethod
    def _description(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise AgentContractError("profile description cannot be blank")
        return value

    @field_validator("always_load_skills", mode="before")
    @classmethod
    def _tuple_skills(cls, value: Any):
        return _tupleize(value)

    @field_validator("always_load_skills")
    @classmethod
    def _skills(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        cleaned = tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
        if len(cleaned) != len(value) or len(cleaned) != len(set(cleaned)):
            raise AgentContractError("always_load_skills must contain unique non-empty names")
        return cleaned


class DurableTaskSpec(ContractModel):
    key: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    role: WorkerRole
    body: str = Field(..., min_length=1)
    parents: tuple[str, ...] = Field(default_factory=tuple)
    priority: int = 0
    max_runtime_seconds: int = Field(default=1800, ge=60, le=21600)
    max_retries: int = Field(default=2, ge=1, le=5)
    skills: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("key")
    @classmethod
    def _key(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-" for ch in value):
            raise AgentContractError("task key must be lowercase alphanumeric/hyphen")
        return value

    @field_validator("title", "body")
    @classmethod
    def _text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise AgentContractError("task text cannot be blank")
        return value

    @field_validator("parents", "skills", mode="before")
    @classmethod
    def _tuples(cls, value: Any):
        return _tupleize(value)

    @field_validator("parents", "skills")
    @classmethod
    def _string_tuples(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        cleaned = tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
        if len(cleaned) != len(value) or len(cleaned) != len(set(cleaned)):
            raise AgentContractError("task tuple fields must contain unique non-empty strings")
        return cleaned


class DurableJobTemplate(ContractModel):
    template_id: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    tasks: tuple[DurableTaskSpec, ...] = Field(..., min_length=1)

    @field_validator("tasks", mode="before")
    @classmethod
    def _tuple_tasks(cls, value: Any):
        return _tupleize(value)

    @model_validator(mode="after")
    def _graph_integrity(self) -> "DurableJobTemplate":
        keys = [task.key for task in self.tasks]
        if len(keys) != len(set(keys)):
            raise AgentContractError("durable task keys must be unique")
        seen: set[str] = set()
        for task in self.tasks:
            unknown_or_forward = [parent for parent in task.parents if parent not in seen]
            if unknown_or_forward:
                raise AgentContractError(
                    f"task {task.key!r} has unknown/forward parents {unknown_or_forward!r}"
                )
            seen.add(task.key)
        roles = {task.role for task in self.tasks}
        required = {WorkerRole.RESEARCH, WorkerRole.PRODUCTION, WorkerRole.REVIEW}
        if roles != required:
            raise AgentContractError(
                f"durable lesson workflow must use exactly roles {sorted(r.value for r in required)!r}"
            )
        return self


class SeededLessonJob(ContractModel):
    job_id: str = Field(..., min_length=1)
    template_id: str = Field(..., min_length=1)
    workspace_path: str = Field(..., min_length=1)
    task_ids: dict[str, str] = Field(..., min_length=1)

    @field_validator("job_id")
    @classmethod
    def _job_id(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for ch in value):
            raise AgentContractError("job_id must be lowercase alphanumeric/hyphen/underscore")
        return value

    @field_validator("workspace_path")
    @classmethod
    def _absolute_workspace(cls, value: str) -> str:
        path = Path(value)
        if not path.is_absolute():
            raise AgentContractError("workspace_path must be absolute")
        return str(path)
