"""V3-64: one unseen 3x4→4x3 heldout lesson. Source-ledger candidate contract.

A bona fide OpenRouter response is required to claim model authoring. Local mock
candidates exist only for preflight tests, never as a substitute for the POST.
"""
from __future__ import annotations
import json,re,math
from hashlib import sha256
from pathlib import Path

VERSION="v3-64-five-role-heldout-storyboard-v1"
TOPIC="array_commutativity_three_by_four"
QUERY="Why does a 3-by-4 array have the same number of objects as a 4-by-3 array?"
LEDGER={"topic_id":TOPIC,"initial_rows":3,"initial_columns":4,
        "rearranged_rows":4,"rearranged_columns":3,
        "number_of_persistent_unit_squares":12,"count_is_conserved":True,
        "initial_product":12,"rearranged_product":12}
STAGES=("QUESTION","SETUP","TRANSFORM","WITNESS","CLOSE")
UNIT_IDS=tuple(f"unit_{i:02d}" for i in range(12))
def digest(obj):
    return sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()
LEDGER_SHA=digest(LEDGER)

def leaf_str(allowed):
    return {"type":"string","enum":list(allowed)}
def obj(props):
    return {"type":"object","additionalProperties":False,"properties":props,
            "required":list(props)}
def textfield(maxn=150):
    return {"type":"string","minLength":18,"maxLength":maxn}

Cognitive=obj({"learner_hypothesis":leaf_str(["turning_array_changes_count","row_count_alone_is_the_answer"]),
               "probe":leaf_str(["track_the_same_twelve","predict_new_row_count"])})
Narrative=obj({"opening":leaf_str(["predict_first","notice_paradox"]),
               "closure":leaf_str(["counting_invariant","multiplication_as_groups"])})
Visual=obj({"representation":leaf_str(["identity_preserving_grid"]),
            "focus":leaf_str(["all_twelve","highlight_first_row","track_corner"]),
            "composition":leaf_str(["single_stage","side_by_side"]),
            "unit_ids":{"type":"array","items":leaf_str(UNIT_IDS),"minItems":12,"maxItems":12}})
Motion=obj({"method":leaf_str(["smooth_morph","staggered_morph"]),
            "transition_frames":{"type":"integer","enum":[60,75,90]},
            "reveal":leaf_str(["AFTER_TRANSFORM"])})
Critic=obj({"failure_to_prevent":leaf_str(["lost_object_identity"]),
            "evidence_needed":leaf_str(["12_IDS_BEFORE_AFTER"]),
            "independent_quality":leaf_str(["UNRATED"])})
Beat=obj({"stage":leaf_str(STAGES),"caption":textfield(),
          "visual_focus":leaf_str(["all_twelve","highlight_first_row","track_corner"]),
          "requested_columns":{"type":"integer","enum":[3,4]},
          "show_numeric_conclusion":{"type":"boolean"}})
SCHEMA=obj({"protocol_version":leaf_str([VERSION]),
            "topic_id":leaf_str([TOPIC]),
            "host_ledger_sha256":{"type":"string","pattern":"^[0-9a-f]{64}$"},
            "cognitive_designer":Cognitive,
            "narrative_designer":Narrative,
            "visual_thinker":Visual,
            "motion_director":Motion,
            "visual_critic":Critic,
            "beats":{"type":"array","items":Beat,"minItems":5,"maxItems":5}})
MAX_WIRE=12000
class Rejected(ValueError): pass

def fail(code):
    raise Rejected("V364_"+code)

def accept(candidate:dict)->dict:
    from jsonschema import Draft202012Validator
    errs=list(Draft202012Validator(SCHEMA).iter_errors(candidate))
    if errs: fail("SCHEMA_REJECTED")
    if candidate["host_ledger_sha256"]!=LEDGER_SHA:fail("LEDGER_FORGED")
    if tuple(candidate["visual_thinker"]["unit_ids"])!=UNIT_IDS:
        # Ordered stable IDs are required; not an arbitrary multiset.
        fail("UNIT_IDENTITY_LOST")
    if candidate["motion_director"]["reveal"]!="AFTER_TRANSFORM":
        fail("PREMATURE_RELEASE")
    for i,b in enumerate(candidate["beats"]):
        if b["stage"]!=STAGES[i]:fail("STAGE_ORDER_BROKEN")
        expected_columns=4 if i<2 else 3
        if b["requested_columns"]!=expected_columns:
            fail("EARLY_OR_INVALID_REARRANGEMENT")
        if b["show_numeric_conclusion"] != (i>=3):
            fail("EARLY_ANSWER_OR_MISSING_PROOF")
        caption=b["caption"].strip()
        if "\n" in caption or "\r" in caption or "<" in caption or ">" in caption:
            fail("UNSAFE_NARRATION")
        if any(x in caption.lower() for x in ("python","javascript","eval(", "ignore previous","publish this")):
            fail("NARRATION_INSTRUCTION_INJECTION")
        nums=re.findall(r"\d+",caption)
        if any(x not in ("3","4","12") for x in nums):
            fail("UNAPPROVED_NUMERIC_CLAIM")
        if i<3 and "12" in nums:
            fail("ANSWER_LEAK_BEFORE_WITNESS")
        if i>=3 and "12" not in nums:
            fail("MISSING_COUNT_EVIDENCE")
        # No empirical learning claims masquerading as host maths.
        if re.search(r"\b(students? learned|proved to improve|always learn|measured learners?)\b",caption,re.I):
            fail("UNMEASURED_EDUCATIONAL_CLAIM")
    return {
        "topic_id":TOPIC,
        "candidate_digest_sha256":digest(candidate),
        "host_ledger_sha256":LEDGER_SHA,
        "persistent_object_ids":UNIT_IDS,
        "approved_math":"3×4=4×3=12",
        "stage_order":STAGES,
        "content_quality":"UNVERIFIED_SEMANTIC_REVIEW_REQUIRED",
        "model_creativity":"EXTERNAL_PROVENANCE_REQUIRED",
        "learner_effect":"NOT_MEASURED","production":"BLOCKED"
    }

def strict_load(payload:bytes)->dict:
    if type(payload) is not bytes or not 0<len(payload)<=MAX_WIRE:
        fail("WIRE_SIZE_INVALID")
    def no_constant(_): fail("NONFINITE_JSON")
    def unique_pairs(pairs):
        d={}
        for k,v in pairs:
            if k in d:fail("DUPLICATE_JSON_KEY")
            d[k]=v
        return d
    try:
        parsed=json.loads(payload.decode("utf-8"),parse_constant=no_constant,
                          object_pairs_hook=unique_pairs)
    except (UnicodeError,json.JSONDecodeError) as e:
        raise Rejected("V364_INVALID_JSON") from e
    if type(parsed) is not dict:fail("WIRE_ROOT_NOT_OBJECT")
    accept(parsed)
    return parsed

def host_test_baseline():
    """Bespoke fixture for offline comparison only. It is NEVER sent to the model."""
    return {"protocol_version":VERSION,"topic_id":TOPIC,"host_ledger_sha256":LEDGER_SHA,
      "cognitive_designer":{"learner_hypothesis":"turning_array_changes_count",
        "probe":"track_the_same_twelve"},
      "narrative_designer":{"opening":"predict_first","closure":"counting_invariant"},
      "visual_thinker":{"representation":"identity_preserving_grid",
         "focus":"all_twelve","composition":"single_stage","unit_ids":list(UNIT_IDS)},
      "motion_director":{"method":"smooth_morph","transition_frames":75,
        "reveal":"AFTER_TRANSFORM"},
      "visual_critic":{"failure_to_prevent":"lost_object_identity",
        "evidence_needed":"12_IDS_BEFORE_AFTER","independent_quality":"UNRATED"},
      "beats":[
        {"stage":"QUESTION","caption":"If we change a three-row array into four rows, do the items disappear?",
         "visual_focus":"all_twelve","requested_columns":4,"show_numeric_conclusion":False},
        {"stage":"SETUP","caption":"Count these same objects, arranged with three rows and four columns.",
         "visual_focus":"highlight_first_row","requested_columns":4,"show_numeric_conclusion":False},
        {"stage":"TRANSFORM","caption":"Keep each square while reorganizing it into four rows and three columns.",
         "visual_focus":"track_corner","requested_columns":3,"show_numeric_conclusion":False},
        {"stage":"WITNESS","caption":"All 12 squares remain: three times four and four times three each give 12.",
         "visual_focus":"all_twelve","requested_columns":3,"show_numeric_conclusion":True},
        {"stage":"CLOSE","caption":"Because the same 12 objects remain, rearrangement changes grouping, not count.",
         "visual_focus":"all_twelve","requested_columns":3,"show_numeric_conclusion":True}
      ]}

def assert_prereg(path:Path):
    r=json.loads(path.read_text())
    if r.get("parent_sha")!="2ef842ba9baf7f56c7a3906b8aa1c793ef437b12" or r.get("registration")!="FIRST_CHILD_COMMIT_BEFORE_IMPLEMENTATION":
        fail("PREREG_SCOPE_DRIFT")
    if r["host_verified_facts"]["object_count"]!=12 or r["new_heldout_query"]!=QUERY:
        fail("TOPIC_ALTERED")
    q=r["request_plan"]
    if not(q["single_http_post_max"]==1 and q["retries"]==0 and
           q["fallback"] is False and q["max_output_tokens"]==2100 and
           q["expected_cost_cap_usd"]==0.02):
        fail("BUDGET_DRIFT")
    return r
