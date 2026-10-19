"""V3-51 sanitized, stage-specific offline diagnostics.

Never persist raw model response, API keys or secret-bearing validator values.
Old V3-50 consumed live attempt is NOT retried or reclassified retroactively.
"""
from __future__ import annotations

from jsonschema import Draft202012Validator
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.model_authored_attention import portable_schema,verify_storyboard
from learnflow_v3.creative_scene_graph import Storyboard,validate


def classify_v350(candidate)->dict:
    issues=list(Draft202012Validator(portable_schema()).iter_errors(candidate))
    if issues:
        return {
          "stage":"json_schema",
          "status":"BLOCKED",
          "code":"V350_MODEL_WIRE_SCHEMA_REJECTED",
          "error_shapes":[
            {"path":".".join(str(k) for k in e.absolute_path)[:100],
             "keyword":str(e.validator)[:50]}
            for e in sorted(issues,key=lambda e:str(e.absolute_path))[:12]],
          "raw_content_stored":False}
    try:
        verify_storyboard(candidate)
    except (Blocked,ValueError,TypeError,KeyError) as exc:
        code=str(exc)
        if not (code.startswith("V350_") and len(code)<=80):
            code="V350_SEMANTIC_REJECTED"
        return {"stage":"host_semantic","status":"BLOCKED","code":code,
                "error_shapes":[],"raw_content_stored":False}
    return {"stage":"accepted","status":"LOCAL_CONTRACT_PASS_ONLY",
            "code":None,"error_shapes":[],"raw_content_stored":False}


def classify_v351(candidate)->dict:
    try:
        Storyboard.model_validate(candidate)
    except Exception:
        return {"stage":"structure","status":"BLOCKED","code":"V351_STRUCTURE_INVALID",
                "raw_content_stored":False}
    try:
        validate(candidate)
    except Blocked as exc:
        code=str(exc)
        if not(code.startswith("V351_") and len(code)<=80):
            code="V351_LOCAL_VALIDATION_REJECTED"
        stage=("evidence" if any(k in code for k in
           ("FACT","RELATION_CLAIM","NARRATION_NUMERIC","VISUAL_FACT"))
           else "topology_or_layout")
        return {"stage":stage,"status":"BLOCKED","code":code,"raw_content_stored":False}
    return {"stage":"accepted","status":"LOCAL_GRAPH_COMPILER_PASS_ONLY",
            "code":None,"raw_content_stored":False}
