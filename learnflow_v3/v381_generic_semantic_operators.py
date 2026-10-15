"""V3-81 topic-independent, bounded arithmetic semantic operator interpreter.

The host recomputes exact rational values before handing a finite, typed trace
to a trusted compiler. No branch on topic/domain/fixture IDs; not arbitrary
algebra, LLM code, dimensional physics proof, or free-text fact checking.
"""
from __future__ import annotations
from fractions import Fraction
from hashlib import sha256
import json
import re

from learnflow_v3.creative_manim_ablation import Blocked

OPS = frozenset({"SCALE", "ADD", "EQUIVALENT_PARTITION"})
IDENT = re.compile(r"^[a-z][a-z0-9_]{1,48}$")
MAX_PARTS = 24


def need(ok, reason):
    if not ok:
        raise Blocked("V381_" + reason)


def number(x):
    need(type(x) is int and -10000 <= x <= 10000, "NOT_BOUNDED_EXACT_INTEGER")
    return x


def parse_value(raw):
    need(isinstance(raw, dict), "VALUE_NOT_OBJECT")
    kind = raw.get("kind")
    if kind == "scalar":
        need(set(raw) == {"kind", "n", "d"}, "SCALAR_SCHEMA")
        n, d = number(raw["n"]), number(raw["d"])
        need(0 < d <= 10000, "ZERO_OR_NEGATIVE_DENOMINATOR")
        return ("scalar", Fraction(n, d))
    if kind == "vector":
        need(set(raw) == {"kind", "items"}, "VECTOR_SCHEMA")
        parts = raw["items"]
        need(isinstance(parts, list) and 1 <= len(parts) <= 4, "VECTOR_DIMENSION")
        values = [parse_value(p) for p in parts]
        need(all(v[0] == "scalar" for v in values), "VECTOR_NON_SCALAR")
        return ("vector", tuple(v[1] for v in values))
    if kind == "fraction":
        need(set(raw) == {"kind", "n", "d"}, "FRACTION_SCHEMA")
        n, d = number(raw["n"]), number(raw["d"])
        need(0 <= n <= d <= MAX_PARTS and d > 0, "UNSAFE_PARTITION")
        return ("fraction", (n, d))
    raise Blocked("V381_UNSUPPORTED_TYPED_VALUE")


def encode(value):
    k, v = value
    if k == "scalar":
        return {"kind": k, "n": v.numerator, "d": v.denominator}
    if k == "vector":
        return {"kind": k, "items": [encode(("scalar", x)) for x in v]}
    return {"kind": k, "n": v[0], "d": v[1]}


def fmt(value):
    k, v = value
    if k == "scalar":
        return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"
    if k == "vector":
        return "[" + ", ".join(fmt(("scalar", n)) for n in v) + "]"
    return f"{v[0]}/{v[1]}"


def calculate(op, args):
    need(len(args) == 2, "OPERATOR_ARITY")
    a, b = args
    if op == "SCALE":
        if a[0] == "scalar" and b[0] == "scalar":
            return ("scalar", a[1] * b[1])
        if a[0] == "scalar" and b[0] == "vector":
            return ("vector", tuple(a[1] * x for x in b[1]))
        if a[0] == "vector" and b[0] == "scalar":
            return ("vector", tuple(x * b[1] for x in a[1]))
        raise Blocked("V381_UNSUPPORTED_SCALE_TYPES")
    if op == "ADD":
        if a[0] == b[0] == "scalar":
            return ("scalar", a[1] + b[1])
        if a[0] == b[0] == "vector":
            need(len(a[1]) == len(b[1]), "VECTOR_DIMENSION_MISMATCH")
            return ("vector", tuple(x + y for x, y in zip(a[1], b[1], strict=True)))
        raise Blocked("V381_UNSUPPORTED_ADD_TYPES")
    if op == "EQUIVALENT_PARTITION":
        need(a[0] == "fraction" and b[0] == "scalar", "PARTITION_INPUT_TYPES")
        factor = b[1]
        need(factor.denominator == 1 and 1 < factor.numerator <= 12,
             "PARTITION_FACTOR_INVALID")
        n, d = a[1]
        nn, dd = n * factor.numerator, d * factor.numerator
        need(dd <= MAX_PARTS and Fraction(n, d) == Fraction(nn, dd),
             "PARTITION_NON_EQUIVALENT_OR_TOO_LARGE")
        return ("fraction", (nn, dd))
    raise Blocked("V381_UNSUPPORTED_OPERATION")


def validate_case(case):
    need(isinstance(case, dict) and set(case) ==
         {"id", "domain", "role", "title", "facts", "claims", "operations"},
         "CASE_SCHEMA")
    for field in ("id", "domain"):
        need(isinstance(case[field], str) and bool(IDENT.fullmatch(case[field])),
             "INVALID_CASE_ID")
    need(case["role"] in ("development", "heldout"), "INVALID_CASE_ROLE")
    need(isinstance(case["title"], str) and 10 <= len(case["title"]) <= 90
         and "\n" not in case["title"], "INVALID_TITLE")
    facts, claims, actions = case["facts"], case["claims"], case["operations"]
    need(isinstance(facts, dict) and 2 <= len(facts) <= 20, "MISSING_FACT_LEDGER")
    need(isinstance(claims, dict) and 1 <= len(claims) <= 12, "MISSING_CLAIMS")
    need(isinstance(actions, list) and 2 <= len(actions) <= 8,
         "INVALID_OPERATION_COUNT")
    state = {}
    for key, raw in facts.items():
        need(isinstance(key, str) and bool(IDENT.fullmatch(key)), "BAD_FACT_ID")
        state[key] = parse_value(raw)
    for key, statement in claims.items():
        need(isinstance(key, str) and re.fullmatch(r"[A-Z][A-Z0-9]{0,8}", key)
             and isinstance(statement, str) and 15 <= len(statement) <= 270
             and "\n" not in statement, "INVALID_CLAIM")
    events = []
    for index, act in enumerate(actions):
        need(isinstance(act, dict) and set(act) ==
             {"id", "kind", "inputs", "expected", "claim_id", "narration"},
             "ACTION_SCHEMA")
        oid, kind, refs = act["id"], act["kind"], act["inputs"]
        need(isinstance(oid, str) and bool(IDENT.fullmatch(oid))
             and oid not in state, "DUPLICATE_OUTPUT_OR_INVALID_ID")
        need(kind in OPS, "UNSUPPORTED_OPERATION")
        need(isinstance(refs, list) and len(refs) == 2
             and all(isinstance(x, str) and x in state for x in refs),
             "FORWARD_OR_UNGROUNDED_REFERENCE")
        need(act["claim_id"] in claims, "UNBOUND_CLAIM")
        narration = act["narration"]
        need(isinstance(narration, str) and 65 <= len(narration) <= 400
             and "\n" not in narration, "UNSAFE_OR_SHORT_NARRATION")
        lhs = [state[x] for x in refs]
        result = calculate(kind, lhs)
        expected = parse_value(act["expected"])
        need(result == expected, "CLAIMED_ARITHMETIC_NOT_HOST_VERIFIED")
        state[oid] = result
        events.append({
            "index": index, "id": oid, "kind": kind, "refs": list(refs),
            "operands": [encode(x) for x in lhs], "actual": encode(result),
            "operand_text": [f"{key} = {fmt(value)}" for key, value in zip(refs, lhs, strict=True)],
            "result_text": f"{oid} = {fmt(result)}",
            "claim_id": act["claim_id"], "claim_text": claims[act["claim_id"]],
            "narration": narration,
            "host_arithmetic_attested": True,
            "origin": "HOST_PREREGISTERED_EXACT_RATIONAL_NOT_MODEL"
        })
    digest = sha256(json.dumps(case, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "version": "v3-81-bounded-topic-independent-arithmetic-v1",
        "case_id": case["id"], "domain": case["domain"], "role": case["role"],
        "title": case["title"], "input_sha256": digest,
        "events": events, "state": {k: encode(v) for k, v in state.items()},
        "native_operator_kinds": sorted({e["kind"] for e in events}),
        "all_numeric_outputs_verified": True,
        "natural_language_claim_truth_verified": False,
        "model_authoring": "NOT_TESTED",
        "generalization": "BOUNDED_FOUR_HOST_CASES_NOT_UNIVERSAL"
    }
