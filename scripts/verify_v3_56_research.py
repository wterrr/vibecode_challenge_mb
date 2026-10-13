#!/usr/bin/env python3
"""V3-56 offline research protocol integrity; no API, no rendering, no production changes."""
from __future__ import annotations
import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]
REG="benchmarks/learnflowbench/v3/v3_56_pedagogical_agent_research_preregister.json"
MATRIX="research/v3_56_3b1b_lesson_evidence.json"
ARCH="research/v3_56_agent_prompt_architecture.json"
PROTOCOL="research/v3_56_abc_evaluation_protocol.json"
PARENT="42dd591e4c5ce52f3d1bf251810c111d0019ab4a"
FIRST="665b85526f4d0ae7ae0473f7701b3d12e894d3ce"


def require(condition, reason):
    if not condition: raise AssertionError("V356_"+reason)

def load(name):
    return json.loads((ROOT/name).read_text(encoding="utf-8"))

def check() -> dict:
    p,m,a,e=(load(path) for path in (REG,MATRIX,ARCH,PROTOCOL))
    require(p["parent_sha"]==PARENT and m["frozen_registration_first_commit"]==FIRST,
            "REGISTERED_PARENT_CHANGED")
    require(p["safety"]=={"max_model_provider_posts":0,"no_main_merge":True,
            "production":"BLOCKED","v2_core_mutations":0},"SAFETY_BUDGET_CHANGED")
    require(p["v355_frozen_receipts"]["technical_result"]=="PASS_BOUNDED" and
            p["v355_frozen_receipts"]["creative_quality"]=="NO_GO_UNRATED",
            "V355_QUALITY_LAUNDERED")
    rows=m["rows"]; catalog=p["study_catalog"]
    require(len(rows)>=15 and len(rows)==len(catalog) and len({x["lesson_id"] for x in rows})==len(rows),
            "SOURCE_COVERAGE")
    require({x["lesson_id"] for x in rows}=={x["id"] for x in catalog},"SOURCE_SELECTION_CHANGED")
    mandatory=set(p["required_matrix_fields"])
    require(len(mandatory)==len(p["required_matrix_fields"]),"MATRIX_FIELDS_DUPLICATE")
    for row in rows:
        require(mandatory.issubset(row),"LESSON_EVIDENCE_FIELDS")
        require(row["read_url"].startswith("https://www.3blue1brown.com/lessons/"),"EXTERNAL_LESSON_SOURCE")
        require(row["evidence_read"]["status"]=="DIRECT_OFFICIAL_READ_PAGE_OPENED","READ_NOT_VERIFIED")
        require(row["evidence_video"]["status"]=="NOT_VIEWED_END_TO_END" and
                row["evidence_video"]["timestamp"]=="UNKNOWN","FABRICATED_TIMECODES")
        require(row["mental_model_entry"]["status"].endswith("INTERPRETATION"),"MISATTRIBUTED_COGNITIVE_DESIGN")
        require(row["potential_misconception"]["status"].startswith("INFERRED"),"MISATTRIBUTED_LEARNER_DATA")
    require(sum(row["evidence_source"]["status"]=="MATCHED_SOURCE_FILE_INSPECTED_NOT_RUN"
                for row in rows)>=3,"INSUFFICIENT_SOURCE_CODE_SAMPLES")
    require(len({x["cluster"] for x in rows})>=6,"INSUFFICIENT_TOPIC_DIVERSITY")
    Draft202012Validator.check_schema(a["schema"])
    require(a["origin"]=="RESEARCH_PROPOSED_SIDE_CAR_NOT_PRODUCTION","PROMPT_INTEGRATION_FORGED")
    require(len(a["roles"])==5 and
       {x["role"] for x in a["roles"]}=={
        "pedagogy_agent","script_agent","visual_director","creative_motion_director","pedagogical_visual_critic"},
        "AGENT_ROLE_COVERAGE")
    require("creative_scene_graph.py" in str(a["existing_reuse_audit"]),"MISSING_REUSE_FIRST")
    require(len(a["host_owned_invariants"])>=7,"MISSING_HOST_GATES")
    v=e["variants"]; require([x["id"] for x in v]==["A","B","C"],"AB_C_MISSING")
    require(v[0]["renderer"]==v[1]["renderer"],"PROMPT_AB_NOT_MATCHED")
    require(v[1]["prompt"]==v[2]["prompt"],"RENDERER_BC_NOT_MATCHED")
    require(len(e["dataset"]["frozen_preregistered_heldout_topics"])>=4,"HELDOUT_TOO_SMALL")
    require(e["inference"]["max_requests_per_topic_arm"]==1 and
            e["inference"]["retry_budget"]==0,"FAIR_BUDGET")
    require(e["status"].startswith("DESIGNED_ONLY") and
            e["human_evaluation_results"] is None,"FABRICATED_RESULTS")
    require(e["gate"]["V356_model_or_product_go"]=="NOT_ALLOWED","MODEL_OR_PRODUCTION_GATE_BYPASSED")
    return {"checkpoint":"V3-56",
            "result":"RESEARCH_SPEC_CONTRACT_GO_ONLY__MEDIA_TIMECODES_UNVERIFIED",
            "read_lessons":len(rows),
            "matched_source_code_samples":sum(row["evidence_source"]["status"]=="MATCHED_SOURCE_FILE_INSPECTED_NOT_RUN" for row in rows),
            "human_rating":"UNRATED",
            "full_lesson_videos_end_to_end":"NOT_VIEWED",
            "model_api_requests":0,"v2_core_edits":0,
            "production":"BLOCKED"}

if __name__=="__main__":
    print(json.dumps(check(),sort_keys=True,indent=2))
