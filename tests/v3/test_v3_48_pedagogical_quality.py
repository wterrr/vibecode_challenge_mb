"""V3-48: adversarial claim scope + prospective blind evaluation safety."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.semantic_scene_wire import SceneWire, decode_model_facing_scene
from learnflow_v3.semantic_scene_offline_fixtures import fixture_cases
from scripts.run_v3_48_pedagogical_quality import blind_order, require, RUBRIC, REG

ROOT = Path(__file__).resolve().parents[2]


def test_preregistered_before_code_and_frozen_pair_sha():
    x = json.loads((ROOT/REG).read_text())
    assert x["registration_kind"] == "PREREGISTRATION_BEFORE_IMPLEMENTATION"
    assert x["parent_sha"] == "f6b3919e304482f8b2691dcf877c15b8990f31ca"
    assert x["sources"]["current_v347"]["run_id"] == 38203160425
    assert x["sources"]["baseline_v346"]["run_id"] == 38200776147
    assert x["objective_acceptance"]["model_api_posts"] == 0
    assert x["objective_acceptance"]["human_effectiveness"] == "NOT_CERTIFIED"
    assert x["cohort_protocol"]["quality_axes"] == list(RUBRIC)
    assert x["cohort_protocol"]["min_independent_reviewers"] >= 3


def alternative_valid_math_unbound_claims():
    """A genuinely different *correct* equation 2/3=4/6.

    The legacy scene's fixed F1/F2/F3 bank still asserts 1/2=2/4, so this
    must be rejected even if all the partition shapes and proof are valid.
    """
    base = deepcopy(fixture_cases()["v345-synthetic-fractions"])
    assert Fraction(2, 3) == Fraction(4, 6)
    template = next(g for g in base["graphics"] if g["kind"] == "tile")
    tiles = []
    for i in range(3):
        g = deepcopy(template)
        g.update(id=f"third{i}", x=round(-4.4+i*.8, 2), y=.5,
                 width=.8, height=1.8, color="TEAL" if i < 2 else "GREY")
        tiles.append(g)
    for i in range(6):
        g = deepcopy(template)
        g.update(id=f"sixth{i}", x=round(1.0+i*.4, 2), y=.5,
                 width=.4, height=1.8, color="TEAL" if i < 4 else "GREY")
        tiles.append(g)
    base["graphics"] = tiles + [g for g in base["graphics"] if g["kind"]=="label"]
    by_id = {g["id"]: g for g in base["graphics"]}
    by_id["left_fraction"]["text"] = "2/3"
    by_id["right_fraction"]["text"] = "4/6"
    by_id["proof"]["text"] = "(2×2)/(3×2) = 4/6"
    a, b = base["partitions"]
    a.update(part_ids=[f"third{i}" for i in range(3)],
             shaded_ids=["third0", "third1"], numerator=2, denominator=3)
    b.update(part_ids=[f"sixth{i}" for i in range(6)],
             shaded_ids=[f"sixth{i}" for i in range(4)],
             numerator=4, denominator=6)
    assert sum(g["width"]*g["height"] for g in tiles[:3]) == pytest.approx(
           sum(g["width"]*g["height"] for g in tiles[3:]))
    assert by_id["proof"]["text"] == "(2×2)/(3×2) = 4/6"
    return base


def test_new_mathematically_valid_fraction_topic_cannot_launder_old_claim_ids():
    with pytest.raises((ValueError, ValidationError),
                       match="V348_UNSUPPORTED_FRACTION_CLAIM_SCOPE"):
        SceneWire.model_validate(alternative_valid_math_unbound_claims())
    with pytest.raises((ValueError, ValidationError), match="V345_HOST_SEMANTIC_SCENE_REJECTED"):
        decode_model_facing_scene(alternative_valid_math_unbound_claims())


@pytest.mark.parametrize("text", ["Check", "Review", "Assume", "Approve"])
def test_new_process_semantics_cannot_launder_old_p2_condition(text):
    raw = deepcopy(fixture_cases()["v345-synthetic-process"])
    next(g for g in raw["graphics"] if g["id"]=="verify")["text"] = text
    with pytest.raises((ValueError, ValidationError),
                       match="V348_UNSUPPORTED_PROCESS_CLAIM_SCOPE"):
        SceneWire.model_validate(raw)
    with pytest.raises((ValueError, ValidationError), match="V345_HOST_SEMANTIC_SCENE_REJECTED"):
        decode_model_facing_scene(raw)


def test_reversed_process_truth_claim_graph_stays_blocked():
    raw = deepcopy(fixture_cases()["v345-synthetic-process"])
    a, b = (next(g for g in raw["graphics"] if g["id"]==key)
            for key in ("start", "finish"))
    a["text"], b["text"] = b["text"], a["text"]
    with pytest.raises((ValueError, ValidationError)):
        decode_model_facing_scene(raw)


def test_existing_legacy_fixtures_and_heldout_id_rekey_still_accepted():
    from scripts.run_v3_47_pedagogical_storytelling import heldout_process
    for key, raw in fixture_cases().items():
        s = decode_model_facing_scene(raw)
        assert s.family in ("fraction_equivalence", "ordered_process")
    process = fixture_cases()["v345-synthetic-process"]
    assert decode_model_facing_scene(heldout_process(process)).family == "ordered_process"


def test_deterministic_blind_pair_has_no_implicit_quality_winner():
    a = blind_order("fraction", "a"*64, "b"*64)
    assert a in (("baseline", "grammar"), ("grammar", "baseline"))
    assert blind_order("fraction", "a"*64, "b"*64) == a
    assert set(a) == {"baseline", "grammar"}


def test_fail_closed_instead_of_scoring_missing_participants():
    with pytest.raises(Blocked, match="V348_MISSING_PARTICIPANTS"):
        require(False, "V348_MISSING_PARTICIPANTS")
    script = (ROOT/"scripts/run_v3_48_pedagogical_quality.py").read_text()
    assert "UNRATED" in script and "NOT_MEASURED" in script
    assert "source_wire_sha256" in script
    assert "V348_FABRICATED_CONDITION_TRUTH" in script
    assert "research_audit" in script and "rater_packet" in script


def test_workflow_no_provider_keys_and_separates_blinded_packet_from_answer_key():
    workflow = (ROOT/".github/workflows/v3-48-pedagogical-quality.yml").read_text()
    assert "run_v3_48_pedagogical_quality.py" in workflow
    assert "38203160425" in workflow and "38200776147" in workflow
    assert "OPENROUTER_API_KEY" not in workflow
    assert "v3_48_blinded_rater_packet" in workflow
    assert "v3_48_private_research_audit" in workflow
    assert "verify_v2_core_freeze.py" in workflow
