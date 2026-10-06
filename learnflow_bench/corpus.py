"""Load and hash frozen LearnFlowBench configuration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .models import BenchmarkCandidate, BenchmarkCorpus

ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "benchmarks" / "learnflowbench" / "corpus_v1.json"
CANDIDATES_PATH = ROOT / "benchmarks" / "learnflowbench" / "candidates_v1.json"
CORE_ABLATION_PATH = ROOT / "benchmarks" / "learnflowbench" / "core_ablation_v1.json"
V1_BASELINE_PATH = ROOT / "benchmarks" / "baselines" / "v1" / "baseline.json"
V1_FIXTURE_DIR = ROOT / "benchmarks" / "fixtures" / "v1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_bytes(parts: list[bytes]) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return digest.hexdigest()


def load_corpus(path: str | Path = CORPUS_PATH) -> BenchmarkCorpus:
    return BenchmarkCorpus.model_validate_json(Path(path).read_text(encoding="utf-8"))


def load_candidates(path: str | Path = CANDIDATES_PATH) -> tuple[BenchmarkCandidate, ...]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return tuple(BenchmarkCandidate.model_validate(item) for item in payload["candidates"])


def corpus_sha256() -> str:
    return _sha256(CORPUS_PATH)


def core_ablation_fixture_ids() -> tuple[str, ...]:
    payload = json.loads(CORE_ABLATION_PATH.read_text(encoding="utf-8"))
    return tuple(payload["legacy_v1_fixture_ids"])


def core_fixture_sha256() -> str:
    parts = [CORE_ABLATION_PATH.read_bytes(), V1_BASELINE_PATH.read_bytes()]
    for fixture_id in core_ablation_fixture_ids():
        parts.append((V1_FIXTURE_DIR / f"{fixture_id}.json").read_bytes())
    return _sha256_bytes(parts)
