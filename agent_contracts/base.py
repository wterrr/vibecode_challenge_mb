"""Shared primitives for LearnFlow agent-control-plane contracts."""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

CONTRACT_SCHEMA_VERSION = "1.0"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class AgentContractError(ValueError):
    """Raised when an agent artifact violates a contract invariant."""


def normalize_id(value: str, *, field_name: str = "identifier") -> str:
    value = value.strip()
    if not _ID_RE.fullmatch(value):
        raise AgentContractError(
            f"{field_name} must match {_ID_RE.pattern!r}; got {value!r}"
        )
    return value


def normalize_text(value: str, *, field_name: str = "text") -> str:
    value = value.strip()
    if not value:
        raise AgentContractError(f"{field_name} cannot be blank")
    return value


def require_unique(values: list[str] | tuple[str, ...], *, label: str) -> None:
    if len(values) != len(set(values)):
        raise AgentContractError(f"{label} must be unique")


def finite_nonnegative(value: Any, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AgentContractError(f"{field_name} must be a finite non-negative number")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise AgentContractError(f"{field_name} must be a finite non-negative number")
    return result


class ContractModel(BaseModel):
    """Immutable, extra-forbid base with deterministic serialization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(default=CONTRACT_SCHEMA_VERSION)

    @field_validator("schema_version")
    @classmethod
    def _schema_version(cls, value: str) -> str:
        if value != CONTRACT_SCHEMA_VERSION:
            raise AgentContractError(
                f"unsupported contract schema_version {value!r}; "
                f"expected {CONTRACT_SCHEMA_VERSION!r}"
            )
        return value

    def to_canonical_json(self) -> str:
        payload = self.model_dump(mode="json", exclude_none=True)
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def content_sha256(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_canonical_json(cls, payload: str):
        return cls.model_validate_json(payload)


class ArtifactRef(ContractModel):
    artifact_type: str = Field(..., min_length=1)
    artifact_id: str = Field(..., min_length=1)
    content_sha256: str | None = None

    @field_validator("artifact_type", "artifact_id")
    @classmethod
    def _ids(cls, value: str, info) -> str:
        return normalize_id(value, field_name=info.field_name)

    @field_validator("content_sha256")
    @classmethod
    def _hash(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().lower()
        if not _SHA256_RE.fullmatch(value):
            raise AgentContractError("content_sha256 must be lowercase SHA-256")
        return value
