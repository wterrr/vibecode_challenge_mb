"""V3-88 bounded, NON-AUTONOMOUS cross-family semantic planning.

Source reuse:
* V3-49 host-verified fraction claim hashes and V3-47 grammar adapter.
* V3-81 exact EQUIVALENT_PARTITION operator.
* V3-05 replayed LEFTMOST binary-search trace + stdlib bisect_left.

Prompts contain only values, not authored scene actions or narration. Only these
two validated semantic families can emit native pedagogical motion.
"""
from __future__ import annotations
from fractions import Fraction
from hashlib import sha256
import json
import re

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.grounded_fraction_claims import FractionTopic,ground,verify,build
from learnflow_v3.v381_generic_semantic_operators import calculate,parse_value,encode
from learnflow_v3.binary_search_trace import make_binary_search_trace,verify_binary_search_trace

FRACTION = re.compile(r"Can ([0-9]+)/([0-9]+) and ([0-9]+)/([0-9]+) show the same shaded amount\?")
SEARCH = re.compile(r"Find the leftmost index of (-?[0-9]+) in \[([0-9,\- ]+)\]\.")
FAMILIES = frozenset({"FRACTION_EQUIVALENCE","ORDERED_SEARCH"})
MAX_CELLS = 12


def check(ok, reason):
    if not ok:
        raise Blocked("V388_"+reason)


def digest(x):
    return sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def _fraction(row):
    m=FRACTION.fullmatch(row["question"])
    check(m is not None,"FRACTION_PROMPT_NOT_IN_VALIDATED_GRAMMAR")
    n,d,nt,dt=map(int,m.groups())
    check(d>=2 and d<=6 and n>0 and n<d and 1<=dt<=12 and
          dt%d==0 and 2<=dt//d<=3 and nt==n*(dt//d),
          "FRACTION_EQUIVALENCE_NOT_VERIFIED")
    topic=FractionTopic(topic_id="frac"+sha256(row["question"].encode()).hexdigest()[:16],
                        numerator=n,denominator=d,factor=dt//d,
                        target_numerator=nt,target_denominator=dt)
    verified=ground(topic)
    verify(verified)
    lesson,adapter,transform_plan=build(verified)
    # Host-only V3-81 operator must independently preserve exact ratio.
    old={"kind":"fraction","n":n,"d":d}
    factor={"kind":"scalar","n":dt//d,"d":1}
    exact=encode(calculate("EQUIVALENT_PARTITION",
                           [parse_value(old),parse_value(factor)]))
    check(exact=={"kind":"fraction","n":nt,"d":dt} and
          Fraction(n,d)==Fraction(nt,dt),
          "V381_CROSS_FAMILY_PARTITION_ORACLE_MISMATCH")
    claim_ids=[x.claim_id for x in verified.claims]
    check(claim_ids==["F1","F2","F3"],"V349_CLAIM_IDENTITIES_CHANGED")
    intro=(f"Imagine one whole divided into {d} equal parts. "
           f"{n} of those parts are shaded. Count the original partitions.")
    transform=(f"Subdivide every original part into {dt//d} equal smaller pieces. "
               f"There are now {dt} equal pieces, with {nt} shaded. "
               "The shaded amount itself does not change.")
    conclusion=(f"Both partitions are equivalent. "
                f"{n} over {d} equals {nt} over {dt}. "
                "The same whole has the same shaded fraction despite the new boundaries.")
    items=[
        {"phase":"ORIENT","claim_ids":["F1"],"action":"REVEAL_ORIGINAL_PARTITION","narration":intro},
        {"phase":"TRANSFORM","claim_ids":["F1","F3"],"action":"SUBDIVIDE_EXISTING_EQUAL_WHOLE","narration":transform},
        {"phase":"INTERPRET","claim_ids":["F2","F3"],"action":"SHOW_EXACT_FRACTION_IDENTITY","narration":conclusion},
    ]
    return {
      "family":"FRACTION_EQUIVALENCE","case_id":row["id"],"origin":"V349_HOST_VERIFIED_NOT_MODEL",
      "input_sha256":sha256(row["question"].encode()).hexdigest(),
      "source_sha256":verified.source_sha256,
      "source_semantic_proof_sha256":digest({"source":verified.source_sha256,
                                            "claims":[c.model_dump() for c in verified.claims]}),
      "v347_grammar_atom_count":len(transform_plan) if isinstance(transform_plan,(list,tuple)) else 1,
      "typed_claims":claim_ids,"visual_operator":"PARTITION_REFINEMENT",
      "ratio":[n,d,nt,dt],"subdivision_factor":dt//d,
      "shade_exact":[n,d],"refined_exact":[nt,dt],"shaded_area_equal":True,
      "scripted_semantic_events":items,"model_authorship":False,
    }


def _search(row):
    m=SEARCH.fullmatch(row["question"])
    check(m is not None,"SEARCH_PROMPT_NOT_IN_VALIDATED_GRAMMAR")
    target=int(m.group(1))
    parts=[x.strip() for x in m.group(2).split(",")]
    check(all(re.fullmatch(r"-?[0-9]+",x) for x in parts) and
          3<=len(parts)<=MAX_CELLS,"SEARCH_ARRAY_NOT_SMALL_BOUNDED_INTEGERS")
    values=tuple(map(int,parts))
    check(values==tuple(sorted(values)) and all(-100<=x<=100 for x in values)
          and -100<=target<=100,
          "SEARCH_UNSORTED_OR_OUT_OF_BOUNDS")
    trace=make_binary_search_trace(values=values,target=target,
                                  source_ref="trace:v388:"+sha256(row["question"].encode()).hexdigest()[:20])
    proof=verify_binary_search_trace(trace)
    check(proof.trace_sha256==trace.trace_sha256 and
          proof.step_count==len(trace.steps),
          "V305_ORACLE_HASH_OR_STEP_MISMATCH")
    events=[]
    for i,step in enumerate(trace.steps):
        if step.phase=="COMPARE":
            if step.action=="DISCARD_LEFT":
                discard=list(range(step.low,step.mid+1))
                relation="lower than"
            elif step.action=="KEEP_LEFT":
                discard=list(range(step.mid,step.high+1))
                relation="higher than"
            else:
                discard=list(range(step.mid+1,step.high+1))
                relation="equal to"
            narration=(
                f"The active search bounds are low {step.low} and high {step.high}. "
                f"Compare middle index {step.mid}, containing {step.observed}, "
                f"which is {relation} the target {target}. "
                + ("Save this candidate and search its left side for an earlier match."
                   if step.action=="RECORD_CANDIDATE" else
                   "Discard the region that cannot contain the leftmost target.")
            )
            events.append({"phase":"COMPARE","claim_ids":[f"STEP_{i:02d}"],
                           "action":step.action,"low":step.low,"mid":step.mid,"high":step.high,
                           "observed":step.observed,"next_low":step.next_low,"next_high":step.next_high,
                           "candidate":step.candidate_index,"discard":discard,
                           "narration":narration})
        else:
            candidate=proof.oracle_index
            narration=(f"The search is complete. The leftmost index containing {target} "
                       f"is {candidate}. The earlier candidates were checked by the verified trace."
                       if candidate is not None else
                       f"The search is complete. No index contains {target}; the result is not found.")
            events.append({"phase":"COMPLETE","claim_ids":[f"STEP_{i:02d}"],
                           "action":step.action,"candidate":candidate,
                           "narration":narration})
    check(len(events)==len(trace.steps) and len(events)<=7,
          "SEARCH_ANIMATION_TRACE_UNSUPPORTED")
    return {
        "family":"ORDERED_SEARCH","case_id":row["id"],"origin":"V305_REPLAYED_TRACE_NOT_MODEL",
        "input_sha256":sha256(row["question"].encode()).hexdigest(),
        "source_sha256":trace.trace_sha256,
        "source_semantic_proof_sha256":digest(proof.model_dump(mode="json")),
        "typed_claims":[x["claim_ids"][0] for x in events],
        "visual_operator":"ORDERED_ELIMINATION_WITH_CANDIDATE",
        "values":list(values),"target":target,"result_index":proof.oracle_index,
        "trace_replayed_every_step":True,
        "trace_sha256":trace.trace_sha256,
        "scripted_semantic_events":events,"model_authorship":False,
    }


def compile_case(row):
    check(isinstance(row,dict) and set(["id","question","family","role"]).issubset(row),
          "UNVERIFIED_CASE_SCHEMA")
    family=row["family"]
    if family=="FRACTION_EQUIVALENCE":
        fn=_fraction
    elif family=="ORDERED_SEARCH":
        fn=_search
    else:
        return {"id":row["id"],"family":family,"status":"ABSTAIN",
                "reason":"NO_TYPED_PROVEN_SOURCE_FAMILY","video":None}
    try:
        plan=fn(row)
    except (Blocked,ValueError,TypeError,AssertionError) as ex:
        return {"id":row["id"],"family":family,"status":"ABSTAIN",
                "reason":"FAILED_HOST_SEMANTIC_ORACLE","video":None}
    return {"id":row["id"],"family":family,"status":"SUPPORTED_HOST_ONLY",
            "plan":plan}


def registered(root):
    p=json.loads((root/"benchmarks/learnflowbench/v3/v3_88_cross_family_preregister.json").read_text())
    check(p["checkpoint"]=="V3-88" and
          p["protocol"]=="FIRST_COMMIT_PREREG_BEFORE_STORYBOARD_RENDERER" and
          p["parent"]["sha"]=="94836da45b53499052bd3ccad7cf2a349cb1f2ff" and
          p["acceptance"]["model_api"]==0 and
          p["acceptance"]["production"]=="BLOCKED",
          "PRELOCKED_PROTOCOL_CHANGED")
    rows=p["cases"]
    check(len(rows)==8 and p["fixed_case_ids"]==[r["id"] for r in rows] and
          len({r["id"] for r in rows})==8 and
          sum(r["role"]=="heldout" for r in rows)==2,
          "PRELOCKED_DENOMINATOR_REPLACED")
    return p
