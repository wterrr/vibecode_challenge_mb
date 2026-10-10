"""V3-35 one-shot constrained JSON scene authoring (NOT free-form model Python).

This is an independent preregistered attempt after V3-34's UNKNOWN validation
failure. Structural normalization removes wire-transport placeholder fields
ONLY: it does not fix missing claims, invalid coordinates, narration, visuals,
or unsafe commands. Those fail the original CreativeScene validators.
"""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request,urlopen

from learnflow_v3.creative_manim_ablation import CreativeScene,Blocked
from learnflow_v3.creative_manim_runner import MODEL,API,prompt

SCHEMA_VERSION="v3-35-one-shot-structured-json-v1"
REGISTRATION="benchmarks/learnflowbench/v3/v3_35_structured_scene_preregister.json"
COLORS=["WHITE","TEAL","YELLOW","BLUE","ORANGE","GREEN","GREY"]
KINDS=["text","rectangle","circle","dot"]
MOVES=["show","move","emphasize","remove","wait"]
CLAIMS=["F1","F2","F3"]


def strict_wire_schema()->dict:
    # Portable strict JSON Schema subset: no defaults, anyOf, optional fields,
    # pattern constraints, dynamic refs, or arbitrary/additional properties.
    # Pydantic imposes rich conditional/safety rules AFTER schema decoding.
    motion={
      "type":"object","additionalProperties":False,
      "properties":{
        "action":{"type":"string","enum":MOVES},
        "target":{"type":"string","description":"Graphic id; empty string for wait."},
        "x":{"type":"number","description":"Target position only used by move; otherwise 0."},
        "y":{"type":"number","description":"Target position only used by move; otherwise 0."}
      },
      "required":["action","target","x","y"]
    }
    graphic={
      "type":"object","additionalProperties":False,
      "properties":{
        "id":{"type":"string","description":"Unique lowercase Python-safe identifier, e.g. left_block."},
        "kind":{"type":"string","enum":KINDS},
        "x":{"type":"number"},"y":{"type":"number"},
        "color":{"type":"string","enum":COLORS},
        "text":{"type":"string","description":"Required for kind=text, else empty string."},
        "width":{"type":"number","description":"Rectangle width or 1 otherwise."},
        "height":{"type":"number","description":"Rectangle height or 0.6 otherwise."},
        "radius":{"type":"number","description":"Dot/circle radius or 0.45 otherwise."}
      },
      "required":["id","kind","x","y","color","text","width","height","radius"]
    }
    beat={
      "type":"object","additionalProperties":False,
      "properties":{
        "claim_ids":{"type":"array","items":{"type":"string","enum":CLAIMS},
                     "description":"Only verified factual claims voiced in this beat."},
        "narration":{"type":"string","description":"At least 12 spoken words explaining visual mechanism, 65-270 characters."},
        "visual_goal":{"type":"string","description":"Teaching purpose, not a camera command."},
        "actions":{"type":"array","items":motion,
                   "description":"2-6 sequential show/move/emphasize/remove/wait object actions."}
      },
      "required":["claim_ids","narration","visual_goal","actions"]
    }
    root={
      "type":"object","additionalProperties":False,
      "properties":{
        "title":{"type":"string"},
        "learning_objective":{"type":"string"},
        "objects":{"type":"array","items":graphic,
                   "description":"5-22 uniquely named objects for the entire lesson."},
        "beats":{"type":"array","items":beat,
                 "description":"Exactly four beats and all three approved claim IDs represented."}
      },
      "required":["title","learning_objective","objects","beats"]
    }
    verify_schema(root)
    return root


def verify_schema(schema:dict)->None:
    def walk(node:dict,path:str):
        if node.get("type")=="object":
            properties=node.get("properties",{})
            if node.get("additionalProperties") is not False or sorted(node.get("required",[]))!=sorted(properties):
                raise Blocked("V335_NOT_STRICT_REQUIRED_FIELDS:"+path)
            for key,inner in properties.items():walk(inner,path+"."+key)
        elif node.get("type")=="array":
            walk(node["items"],path+"[]")
        elif node.get("type") not in ("string","number","integer","boolean"):
            raise Blocked("V335_UNKNOWN_JSON_SCHEMA_NODE:"+path)
    walk(schema,"root")


def preflight(root:Path)->dict:
    manifest=json.loads((root/REGISTRATION).read_text())
    parent=json.loads((root/"benchmarks/learnflowbench/v3/v3_34_scene_ablation_preregister.json").read_text())
    if (not manifest["preregistered_before_implementation"] or
        manifest["topic_id"]!=parent["topic_id"] or
        manifest["topic_query_sha256"]!=parent["topic_query_sha256"] or
        manifest["max_model_http_requests"]!=1 or
        manifest["immutable_model"]!=MODEL or
        manifest["strict_output_format"]!="OpenRouter response_format json_schema strict=true, provider.require_parameters=true" or
        manifest["provider_fallback"] is not False or
        manifest["provider_retries"]!=0):
        raise Blocked("V335_ONE_SHOT_PREREGISTRATION_DRIFT")
    verify_schema(strict_wire_schema())
    return manifest


def normalize_wire(raw:dict)->dict:
    """Remove required transport placeholders, never silently fix semantics."""
    if set(raw)!={"title","learning_objective","objects","beats"}:
        raise Blocked("V335_RESPONSE_FIELD_SET_DRIFT")
    normalized={
      "title":raw["title"],"learning_objective":raw["learning_objective"],
      "objects":raw["objects"],"beats":[]}
    if not isinstance(raw["beats"],list):
        raise Blocked("V335_BEATS_NOT_LIST")
    for beat in raw["beats"]:
        if not isinstance(beat,dict) or set(beat)!={"claim_ids","narration","visual_goal","actions"}:
            raise Blocked("V335_BEAT_FIELD_SET_DRIFT")
        if not isinstance(beat["actions"],list):
            raise Blocked("V335_ACTIONS_NOT_LIST")
        acts=[]
        for action in beat["actions"]:
            if not isinstance(action,dict) or set(action)!={"action","target","x","y"}:
                raise Blocked("V335_ACTION_FIELD_SET_DRIFT")
            name=action["action"]
            if name=="wait":
                if action["target"]!="":
                    raise Blocked("V335_WAIT_TARGET_NOT_EMPTY")
                # x/y must be zero for unused coordinate fields.
                if action["x"]!=0 or action["y"]!=0:
                    raise Blocked("V335_WAIT_UNUSED_COORD_NOT_ZERO")
                acts.append({"action":"wait"})
            elif name=="move":
                if not action["target"]:
                    raise Blocked("V335_MOVE_MISSING_TARGET")
                acts.append(action)
            elif name in ("show","remove","emphasize"):
                if action["x"]!=0 or action["y"]!=0:
                    raise Blocked("V335_NONMOVE_UNUSED_COORD_NOT_ZERO")
                acts.append({"action":name,"target":action["target"]})
            else:
                raise Blocked("V335_UNKNOWN_ACTION")
        normalized["beats"].append({
          "claim_ids":beat["claim_ids"],
          "narration":beat["narration"],
          "visual_goal":beat["visual_goal"],
          "actions":acts
        })
    # Explicitly add author from OBSERVED provider envelope elsewhere; the
    # model may not claim it is a different model by outputting string fields.
    return normalized


def _failure(out:Path,*,status:str,request_attempts:int,response_sha:str|None,
             code:str,detail:list[dict]|None=None,usage:dict|None=None):
    report={
      "checkpoint":"V3-35","status":status,
      "model":MODEL,"model_request_attempts":request_attempts,
      "model_response_sha256":response_sha,
      "sanitized_error_code":code,
      "validation_error_shapes":detail or [],
      "provider_reported_usage":usage,
      "raw_model_text_in_artifact":False,
      "retry_count":0,"provider_fallback":False,
      "production":"BLOCKED"
    }
    (out/"v3_35_structured_failure.json").write_text(json.dumps(report,indent=2)+"\n")


def one_shot_structured(key:str,out:Path,*,sender=None)->tuple[dict,dict]:
    if not key or len(key)<10:
        _failure(out,status="BLOCKED_PRE_REQUEST",request_attempts=0,response_sha=None,
                 code="V335_API_KEY_NOT_CONFIGURED")
        raise Blocked("V335_API_KEY_NOT_CONFIGURED")
    schema=strict_wire_schema()
    p=prompt()
    # Provider strict output support is endpoint-dependent. Hard require the
    # parameter; if unavailable BLOCK rather than silently stripping format.
    payload={
      "model":MODEL,"temperature":.65,"max_tokens":6500,
      "provider":{"allow_fallbacks":False,"require_parameters":True},
      "response_format":{"type":"json_schema",
          "json_schema":{"name":"learnflow_creative_scene_v335","strict":True,"schema":schema}},
      "messages":[
        {"role":"system","content":"You are a creative educational motion designer. Express the strongest visual explanation possible using the provided finite animation primitives. Output a single schema-conforming JSON object. Do not provide executable code or fabricate factual sources."},
        {"role":"user","content":json.dumps({
          **p,
          "schema":schema,
          "wire_rules":[
            "EVERY graphic has all fields id, kind, x, y, color, text, width, height, radius. Set unused graphic fields to defaults, and text='' for non-text kinds.",
            "EVERY action has action, target, x, y. For show/emphasize/remove set x=0 and y=0. For wait set target='' x=0 y=0. For move use actual coordinates.",
            "Exactly 4 beats. Show each graphic before move/emphasize/remove. No repeated show.",
            "Approved numeric tokens only: 1, 2, 4, 0.5, 50. Use original visual interpretations only.",
            "Do not add model_author: provenance is supplied by the host."
          ]
        },ensure_ascii=False)}
      ]
    }
    request=Request(API,data=json.dumps(payload).encode(),method="POST",
      headers={"Authorization":"Bearer "+key,"Content-Type":"application/json",
        "HTTP-Referer":"https://github.com/wterrr/vibecode_challenge_mb",
        "X-Title":"LearnFlow V3-35 one shot provider structured scene schema"})
    (out/"v3_35_request_attempt.json").write_text(json.dumps({
      "checkpoint":"V3-35","model":MODEL,"attempted_http_requests":1,
      "response_format":"json_schema_strict","provider_require_parameters":True,
      "provider_fallback":False,"retries":0
    },indent=2)+"\n")
    try:
        with (sender or urlopen)(request,timeout=125) as conn:
            wire=conn.read(220_000)
    except HTTPError as exc:
        code=f"V335_HTTP_{exc.code}"
        _failure(out,status="BLOCKED_PROVIDER_HTTP",request_attempts=1,response_sha=None,code=code)
        raise Blocked(code) from None
    except (URLError,TimeoutError):
        _failure(out,status="BLOCKED_PROVIDER_TRANSPORT",request_attempts=1,response_sha=None,
                 code="V335_NETWORK_OR_TIMEOUT")
        raise Blocked("V335_NETWORK_OR_TIMEOUT") from None
    try:
        response=json.loads(wire.decode("utf-8"))
        results=response["choices"]
        if not isinstance(results,list) or len(results)!=1:
            raise Blocked("V335_AMBIGUOUS_PROVIDER_RESPONSE")
        selected=results[0]
        if selected.get("finish_reason")!="stop":
            raise Blocked("V335_TRUNCATED_OR_FILTERED_PROVIDER_RESPONSE")
        raw=selected["message"]["content"]
        if not isinstance(raw,str) or len(raw)>45000:
            raise Blocked("V335_PROVIDER_CONTENT_INVALID")
    except (KeyError,TypeError,ValueError,IndexError,UnicodeDecodeError) as exc:
        code=str(exc) if isinstance(exc,Blocked) else "V335_BAD_PROVIDER_RESPONSE_ENVELOPE"
        _failure(out,status="BLOCKED_PROVIDER_FORMAT",request_attempts=1,response_sha=None,code=code)
        raise Blocked(code) from None
    response_hash=sha256(raw.encode("utf-8")).hexdigest()
    usage=response.get("usage",{})
    # Never persist original untrusted model prose. Persist EXACT reasons
    # structurally, without model-text/Pydantic "input" leakage.
    try:
        wire_plan=json.loads(raw)
        normalized=normalize_wire(wire_plan)
        normalized["model_author"]=MODEL
        plan=CreativeScene.model_validate(normalized)
    except Exception as exc:
        from pydantic import ValidationError
        errors=[{"path":".".join(str(p) for p in e["loc"])[:100],
                 "type":str(e["type"])[:80]}
                 for e in exc.errors(include_url=False)[:60]] if isinstance(exc,ValidationError) else []
        code=str(exc) if isinstance(exc,Blocked) else (
          "V335_PYDANTIC_SEMANTIC_REJECT" if isinstance(exc,ValidationError)
          else "V335_UNPARSEABLE_SCHEMA_OUTPUT")
        _failure(out,status="BLOCKED_AFTER_REAL_MODEL_RESPONSE",
                 request_attempts=1,response_sha=response_hash,code=code,
                 detail=errors,usage=usage)
        raise Blocked("V335_SCENE_REJECTED") from None
    receipt={
      "stage":"REAL_MODEL_SCHEMA_CONSTRAINED_SCENE",
      "model":MODEL,
      "model_response_sha256":response_hash,
      # Bridge observed provider JSON to the strict normalized scene actually
      # handed to the host compiler (not raw prompt/output preservation).
      "validated_plan_canonical_sha256":sha256(json.dumps(
          plan.model_dump(mode="json"),sort_keys=True,separators=(",",":")
      ).encode("utf-8")).hexdigest(),
      "provider_response_id_sha256":sha256(str(response.get("id","")).encode()).hexdigest(),
      "actual_provider_requests":1,"no_retry":True,"no_fallback":True,
      "provider_require_parameters":True,
      "strict_json_schema_sha256":sha256(json.dumps(schema,sort_keys=True).encode()).hexdigest(),
      "normalization_only_transport_placeholders":True,
      "usage":usage
    }
    (out/"v3_35_structured_provider_receipt.json").write_text(
        json.dumps(receipt,indent=2)+"\n")
    # Return typed-normalized dict to the ALREADY independently gated V3-34
    # runner. No user-authored Python passes into the sandbox.
    return plan.model_dump(mode="json"),receipt
