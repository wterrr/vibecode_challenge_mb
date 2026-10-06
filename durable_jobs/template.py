"""Load the reviewed durable lesson workflow template."""

from __future__ import annotations

import json
from pathlib import Path

from .models import DurableJobTemplate

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "hermes" / "kanban" / "workflows" / "lesson-job.json"


def load_lesson_job_template(path: str | Path = DEFAULT_TEMPLATE) -> DurableJobTemplate:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return DurableJobTemplate.model_validate(payload)
