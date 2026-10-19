"""V3-57 strict research PEC v3-56 -> bounded host renderer bridge.

Validates the unchanged parent PEC JSON schema AND source-matches its claims,
references, transforms and non-publication constraints against host facts. No
model-generated Python, provider HTTP or V2 Core mutation.
"""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from learnflow_v3.pedagogical_storytelling_slice import Plan,plan,validate,REFERENT,MOTION_BEATS

SCHEMA_PATH="research/v3_56_agent_prompt_architecture.json"
SCOPE_DESCRIPTIONS={
 "attention_reversed_query":(
  "Why a query favors one contextual value instead of another.",
  "The query looks equally relevant to every available key.",
  "Which source gets the greater weight?",
  "weighted_transport",
  "Compare key relevance before transporting weighted value information."),
 "fraction_equivalence":(
  "Why the same shaded share can have different fractional labels.",
  "More pieces necessarily means more shaded area.",
  "Can the amount stay unchanged after subdivision?",
  "area_partition",
  "Keep the physical whole fixed while subdividing its original equal parts."),
 "process_heldout_unknown":(
  "Why reaching a condition gate does not prove its outcome.",
  "A highlighted check node must mean that the condition passed.",
  "What evidence is needed to declare PASS?",
  "graph_state",
  "Trace the path without inferring an unverified condition result.")}

def digest(obj):
 return sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()

def require(c,code):
 if not c:raise ValueError("V357_PEC_"+code)

def schema_for(root):
 data=json.loads((Path(root)/SCHEMA_PATH).read_text(encoding="utf-8"))
 s=data["schema"]
 Draft202012Validator.check_schema(s)
 require(s["title"]=="PedagogicalExplanationContract","PARENT_SCHEMA_ID")
 require(s["version"]=="research-v3-56-proposal-v1" and
         s["status"]=="UNINTEGRATED_RESEARCH_ONLY","PARENT_RESEARCH_SCOPE")
 return s

def build_pec(p,root):
 truth=validate(p);d,m,q,kind,why=SCOPE_DESCRIPTIONS[p.case_id]
 refs=REFERENT[p.case_id]
 transforms=[]
 for b in p.beats:
  if b.index not in MOTION_BEATS[p.case_id]:continue
  transforms.append({
   "operation":b.operation,
   "input_object_ids":[refs],"output_object_ids":[refs],
   "claim_ids":[b.claim_id],"host_evidence_sha256":p.evidence_sha256,
   "precondition":"Host-verified prior semantic state and stable referent",
   "postcondition":"Host-owned finite semantic change in decoded screen region",
   "invariants":["claim_ledger_preserved","referent_identity_preserved",
                 "unverified_condition_not_promoted"],
   "renderer_capability_id":"v357_finite_"+b.operation.lower()})
 indices={i:j for j,i in enumerate(sorted(MOTION_BEATS[p.case_id]))}
 anchors=[{"beat_id":p.case_id+"_"+str(b.index),
           "claim_ids":[b.claim_id],"referenced_object_ids":[refs],
           "referenced_transform_indexes":[indices[b.index]] if b.index in indices else [],
           "relative_order":b.index,"time_source":"ORDER_ONLY"} for b in p.beats]
 witness=[{"witness_id":p.case_id+"_w"+str(b.index),
           "transformation_index":indices.get(b.index),
           "before_state":"Question is unresolved" if b.index==0 else "Previous verified state",
           "after_state":"Question posed" if b.index==0 else "Next certified finite state",
           "witness_region":"PRIMARY_SEMANTIC_VIEW",
           "witness_type":"QUESTION_HOLD" if b.index==0 else (
              "DECODABLE_PIXEL_TRANSITION" if b.index in indices else "STATIC_COMPARISON")}
          for b in p.beats]
 c={"contract_version":"research-v3-56-proposal-v1",
    "scope":{"topic_id":p.case_id,
             "approved_claim_ids":list(dict.fromkeys(b.claim_id for b in p.beats)),
             "host_ledger_sha256":p.evidence_sha256},
    "learning_difficulty":{"description":d,"misconception_hypothesis":m,
       "probe_question":q,"source_scope":"HYPOTHESIZED_FROM_TASK"},
    "target_mental_model":{"model_description":d,
                           "observable_change":"Visible host-verified evidence resolves the initial teaching question."},
    "visual_representation":{"representation_kind":kind,
         "why_this_representation":why,
         "capability_ids":["v357_host_finite_semantics"]},
    "persistent_semantic_objects":[{"object_id":refs,
       "semantic_role":"persistent_target","identity_invariant":"Host-owned same referent across all five beats",
       "claim_ids":list(dict.fromkeys(b.claim_id for b in p.beats))}],
    "verified_transformations":transforms,
    "narration_anchors":anchors,
    "expected_observable_explanation":witness,
    "explanatory_closure":{"return_to_probe":q,
       "known_limitations":["Synthetic host narration, no word-level synchronization",
                           "Not evaluated with independent learners or human quality raters"]},
    "unsupported_capability_outcome":{"state":"DEFERRED_HUMAN_REVIEW",
       "reason_codes":["UNRATED_CREATIVE_TEACHING_QUALITY","NOT_MODEL_AUTHORED"],
       "may_publish":False,"allowed_fallback":"NONE"}}
 validate_pec(c,p,root)
 return c

def validate_pec(c,p,root):
 validate(p)
 spec=schema_for(root)
 failures=sorted(Draft202012Validator(spec).iter_errors(c),
                 key=lambda e:tuple(str(x) for x in e.path))
 require(not failures,"JSON_SCHEMA_"+(failures[0].message[:80] if failures else ""))
 require(c["scope"]=={"topic_id":p.case_id,
   "approved_claim_ids":list(dict.fromkeys(b.claim_id for b in p.beats)),
   "host_ledger_sha256":p.evidence_sha256},"SCOPE_OR_LEDGER_FORGED")
 require(c["learning_difficulty"]["source_scope"]=="HYPOTHESIZED_FROM_TASK",
         "LEARNING_HYPOTHESIS_OVERCLAIM")
 require(c["unsupported_capability_outcome"]["may_publish"] is False and
   c["unsupported_capability_outcome"]["state"]=="DEFERRED_HUMAN_REVIEW",
   "FALSE_PUBLICATION_GO")
 require(c["visual_representation"]["capability_ids"]==["v357_host_finite_semantics"],
         "UNSUPPORTED_RENDERER_CAPABILITY")
 refs=REFERENT[p.case_id]
 require(len(c["persistent_semantic_objects"])==1 and
         c["persistent_semantic_objects"][0]["object_id"]==refs,
         "SEMANTIC_ID_LAUNDERED")
 indices={i:j for j,i in enumerate(sorted(MOTION_BEATS[p.case_id]))}
 require(len(c["verified_transformations"])==len(indices) and
         len(c["narration_anchors"])==len(c["expected_observable_explanation"])==5,
         "OPERATION_COUNT")
 for i,b in enumerate(p.beats):
  anchor=c["narration_anchors"][i];wit=c["expected_observable_explanation"][i]
  require(anchor["beat_id"]==p.case_id+"_"+str(i) and
          anchor["claim_ids"]==[b.claim_id] and
          anchor["referenced_object_ids"]==[refs] and
          anchor["relative_order"]==i and
          anchor["time_source"]=="ORDER_ONLY","NARRATION_ANCHOR")
  expected=[indices[i]] if i in indices else []
  require(anchor["referenced_transform_indexes"]==expected and
          wit["transformation_index"]==indices.get(i) and
          wit["witness_type"]==("QUESTION_HOLD" if i==0 else (
            "DECODABLE_PIXEL_TRANSITION" if i in indices else "STATIC_COMPARISON")),
          "WITNESS_INDEX_FORGED")
  if i in indices:
   t=c["verified_transformations"][indices[i]]
   require(t["operation"]==b.operation and t["claim_ids"]==[b.claim_id] and
     t["input_object_ids"]==t["output_object_ids"]==[refs] and
     t["host_evidence_sha256"]==p.evidence_sha256 and
     t["renderer_capability_id"]=="v357_finite_"+b.operation.lower(),
     "TRANSFORM_OR_FACT_FORGED")
 return {"schema":"V3-56_RESEARCH_PEC_VALIDATED","host_ledger_sha256":p.evidence_sha256,
         "pec_sha256":digest(c),"source":"HOST_SYNTHETIC_NO_MODEL"}
