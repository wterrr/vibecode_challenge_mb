#!/usr/bin/env python3
"""Offline V3-01 preregistration guard, reusing frozen LearnFlowBench contracts."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from learnflow_bench import corpus_sha256, load_corpus

PROTOCOL_PATH = ROOT / "benchmarks/learnflowbench/v3/preregistered_pilot_v1.json"
SOURCE_SHA256 = "4f0e0fc81dee7580df93a1d912b9485de7e5eb1c9fdda699576b48729bf4ab8f"
BASE_SHA = "a06e0b0b5f35e9147b4081da7ed7f7934affe0c6"
SEED = "learnflow-v3-01-20261008-stratified-v1"
STRATA = (
    ("cs", "easy"), ("cs", "hard"), ("math", "easy"), ("math", "medium"),
    ("physics", "medium"), ("physics", "hard"), ("biology", "easy"),
    ("biology", "hard"), ("chemistry", "easy"), ("chemistry", "medium"),
    ("history_general", "medium"), ("history_general", "hard"),
)
TOPIC_IDS = (
    "lfb-006-cs", "lfb-016-cs", "lfb-019-math", "lfb-026-math",
    "lfb-046-physics", "lfb-050-physics", "lfb-052-biology",
    "lfb-064-biology", "lfb-069-chemistry", "lfb-078-chemistry",
    "lfb-092-history-general", "lfb-094-history-general",
)


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def recompute_sample(corpus) -> tuple[str, ...]:
    out = []
    for domain, difficulty in STRATA:
        options = [
            x for x in corpus.topics
            if x.domain.value == domain and x.difficulty.value == difficulty
            and x.topic_id != "lfb-005-cs"
        ]
        require(bool(options), "empty sampling stratum")
        chosen = min(
            options,
            key=lambda t: (
                hashlib.sha256(f"{SEED}|{t.topic_id}".encode("utf-8")).hexdigest(),
                t.topic_id,
            ),
        )
        out.append(chosen.topic_id)
    return tuple(out)


def validate(payload: dict) -> dict:
    require(isinstance(payload, dict), "payload not an object")
    require(payload.get("schema_version") == "v3-preregistered-pilot-v1", "version drift")
    require(payload.get("state") == "FROZEN_PROTOCOL_UNEXECUTED", "premature benchmark execution")
    src = payload.get("source", {})
    require(src.get("corpus_sha256") == SOURCE_SHA256, "pinned corpus hash modified")
    require(src.get("baseline_commit") == BASE_SHA, "baseline revision modified")
    require(src.get("corpus_id") == "learnflowbench-v1-100" and src.get("topic_count") == 100, "corpus metadata drift")
    require(corpus_sha256() == SOURCE_SHA256, "IMMUTABLE_CORPUS_CHANGED")
    corpus = load_corpus()
    require(corpus.frozen and len(corpus.topics) == 100, "corpus integrity")
    sam = payload.get("sampling", {})
    require(sam.get("seed") == SEED and sam.get("method") == "minimum_SHA256(seed|topic_id)_per_locked_domain_difficulty_stratum", "sampling rule changed")
    require(tuple((s["domain"], s["difficulty"]) for s in sam.get("strata", [])) == STRATA, "stratification changed")
    require(sam.get("excluded_diagnostic_ids") == ["lfb-005-cs"], "contaminated diagnostic not excluded")
    chosen = tuple(sam.get("topic_ids", []))
    require(chosen == TOPIC_IDS and chosen == recompute_sample(corpus), "TOPIC_SELECTION_CHANGED")
    require(len(chosen) == len(set(chosen)) == 12 and sam.get("selection_count") == 12, "duplicate/unbalanced topic count")
    require(sam.get("replacements_allowed") is False, "posthoc topic replacements enabled")
    lookup = {t.topic_id: t for t in corpus.topics}
    require(Counter(lookup[x].domain.value for x in chosen) == {x: 2 for x in (
        "cs", "math", "physics", "biology", "chemistry", "history_general")}, "domain imbalance")
    require(Counter(lookup[x].difficulty.value for x in chosen) == {
        "easy": 4, "medium": 4, "hard": 4}, "difficulty imbalance")
    comp = payload.get("comparisons", {})
    require(comp.get("systems") == ["v2d_frozen", "v3_candidate"], "system selection drift")
    require(comp.get("v2d_implementation_ref") == BASE_SHA, "comparator revision drift")
    require(comp.get("mode") == "FUTURE_NOT_RUN" and comp.get("v3_implementation_state") == "NOT_IMPLEMENTED", "unsupported quality claim")
    require(comp.get("denominator") == "ALL_12_ASSIGNED_PAIRS", "survivor-biased denominator")
    model = comp.get("free_model_policy", {})
    require(model.get("model_slug") == "nvidia/nemotron-3.5-lightning:free", "model changed without amendment")
    require(model.get("availability") == "UNVERIFIED_NOT_PROBED", "unverified availability declared")
    require(model.get("allow_paid") is False and model.get("allow_paid_fallback") is False, "paid model fallback permitted")
    require(model.get("same_model_for_paired_systems") is True, "unequal model treatment")
    require(model.get("auto_retry") is False and model.get("attempts_per_topic_per_system") == 1, "retry bias")
    require(model.get("if_unavailable") == "STOP_AND_VERSION_AMEND_BEFORE_RUNNING", "unregistered model swap")
    human = payload.get("human", {})
    require(human.get("min_blinded_raters", 0) >= 2 and human.get("independent") is True, "blind rater deficiency")
    require(human.get("identity_key_kept_blind") is True, "blinding information leaked")
    require(human.get("third_rater_if_absolute_difference_ge") == 2, "adjudication changed")
    require(human.get("score_invalid_video") == 1 and human.get("unrun_data") == "UNMEASURED", "invalid/missing output conflated")
    require(human.get("no_complete_case_only_headline") is True, "survivorship bias")
    require(len(human.get("anchors", {})) == 5, "incomplete ordinal rubric")
    metrics = payload.get("metrics", [])
    require(len(metrics) >= 12 and len({m["id"] for m in metrics}) == len(metrics), "missing/duplicate metrics")
    require([m["id"] for m in metrics if m.get("primary")] == ["clarity", "representation_adequacy"], "primary endpoint drift")
    require(all(m.get("status") == "UNMEASURED" and "value" not in m for m in metrics), "outcome leakage")
    analysis = payload.get("analysis", {})
    require(analysis.get("unit") == "paired_topic_n12", "unit of analysis")
    require(analysis.get("both_mean_deltas_at_least") == 0.5 and analysis.get("min_topic_wins_each") == 8, "threshold posthoc change")
    require("10000" in analysis.get("confidence_interval", ""), "confidence procedure missing")
    require(analysis.get("hard_safety_noninferiority") is True, "safety hard gates removed")
    hard = payload.get("hard_gates", {})
    for key in ("critical_semantic_errors_max", "fatal_geometry_or_caption_errors_max", "unsafe_export_max"):
        require(hard.get(key) == 0, f"safety threshold raised: {key}")
    require(hard.get("core_freeze_required") is True and hard.get("unmeasured_cannot_pass") is True, "safety bypass")
    records = payload.get("outcome_records", {})
    require(records.get("include_failed_attempts") is True and records.get("drop_failures") is False and records.get("substitute_topics") is False, "failed trial omission")
    require(records.get("primary_quality_only_human") is True, "automated aesthetics treated as human")
    perms = payload.get("permission", {})
    for flag in ("live_generation_authorized", "paid_api_authorized", "human_participants_authorized", "publish_authorized"):
        require(perms.get(flag) is False, f"unapproved activity: {flag}")
    require(perms.get("cost_cap_usd") == "UNSET_REQUIRES_EXPLICIT_APPROVAL", "cost budget approval absent")
    return {"selected_topics": 12, "corpus_sha256": SOURCE_SHA256}


def main() -> int:
    try:
        data = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        result = validate(data)
        print("V3_BENCHMARK_PREREG=PASS topics=12 domains=6 easy=4 medium=4 hard=4")
        print(f"corpus_sha256={result['corpus_sha256']}")
        print("LIVE_PROVIDER=NOT_AUTHORIZED")
        return 0
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(f"V3_BENCHMARK_PREREG=FAIL {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
