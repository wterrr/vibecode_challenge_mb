"""V3-32: typed source-bound lesson semantics. No LLM or arbitrary Python execution.

A source publisher quote is evidence of generic def/argument/return semantics,
not an endorsement of a worked numerical example. Worked arithmetic is proven
separately by V3-07's bounded assignment-AST verifier. Generated Research and
Script are deterministic HOST compiler outputs, never relabeled GPT-6 prose.
"""
from __future__ import annotations
import ast
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Literal
from pydantic import Field, model_validator
from learnflow_v3.models import V3Model
from learnflow_v3.paid_cs_lesson import Blocked, SOURCE_URL, validate_research
from learnflow_v3.cs_code_state_lesson import load_pinned_receipt
from learnflow_v3.code_process_renderer import CodeLine,CodeStep,CodeWalkthrough,verify_code_walkthrough
from learnflow_v2.scenegraph import SceneGraph
from learnflow_v2.repair import compute_content_hash

STAGES=("define","call","bind","evaluate","return")
CLAIM_IDS=("C_DEFINE","C_BIND","C_BIND","C_RETURN","C_RETURN")
SUPPORTED_OPS={"+":ast.Add,"-":ast.Sub}


class WorkedExample(V3Model):
    function_name:str=Field(pattern=r"^[a-z][a-z0-9_]{1,19}$")
    parameter:str=Field(pattern=r"^[a-z][a-z0-9_]{0,10}$")
    destination:str=Field(pattern=r"^[a-z][a-z0-9_]{0,12}$")
    operator:Literal["+","-"]
    constant:int=Field(ge=1,le=20)
    argument:int=Field(ge=1,le=25)
    result:int=Field(ge=-20,le=45)
    source_code:str=Field(min_length=30,max_length=220)

    @model_validator(mode="after")
    def arithmetic_and_source(self):
        v=self.argument+self.constant if self.operator=="+" else self.argument-self.constant
        if v!=self.result:
            raise ValueError("V332_EXAMPLE_RESULT_DRIFT")
        try:
            tree=ast.parse(self.source_code,mode="exec")
            if len(tree.body)!=2: raise ValueError("statement count")
            f,assignment=tree.body
            if not isinstance(f,ast.FunctionDef) or f.name!=self.function_name or f.decorator_list or f.returns is not None or f.type_comment is not None or len(f.body)!=1:
                raise ValueError("function")
            a=f.args
            if (len(a.args)!=1 or a.args[0].arg!=self.parameter or a.posonlyargs or a.kwonlyargs
                or a.defaults or a.kw_defaults or a.vararg is not None or a.kwarg is not None):
                raise ValueError("param")
            ret=f.body[0]
            if not isinstance(ret,ast.Return) or not isinstance(ret.value,ast.BinOp):
                raise ValueError("return")
            exp=ret.value
            if (not isinstance(exp.op,SUPPORTED_OPS[self.operator]) or
                not isinstance(exp.left,ast.Name) or exp.left.id!=self.parameter or
                not isinstance(exp.right,ast.Constant) or type(exp.right.value) is not int or
                exp.right.value!=self.constant):
                raise ValueError("expression")
            if (not isinstance(assignment,ast.Assign) or len(assignment.targets)!=1 or
                not isinstance(assignment.targets[0],ast.Name) or
                assignment.targets[0].id!=self.destination):
                raise ValueError("destination")
            call=assignment.value
            if (not isinstance(call,ast.Call) or not isinstance(call.func,ast.Name) or
                call.func.id!=self.function_name or len(call.args)!=1 or call.keywords or
                not isinstance(call.args[0],ast.Constant) or type(call.args[0].value) is not int or
                call.args[0].value!=self.argument):
                raise ValueError("call")
        except (SyntaxError,ValueError,TypeError,AttributeError) as exc:
            raise ValueError("V332_UNSAFE_OR_DRIFTED_EXAMPLE_AST") from exc
        return self


class SourceClaim(V3Model):
    claim_id:Literal["C_DEFINE","C_BIND","C_RETURN"]
    source_id:Literal["S1"]
    quote:str=Field(min_length=28,max_length=240)
    sha256_source:str=Field(min_length=64,max_length=64)


class LessonBeat(V3Model):
    stage:Literal["define","call","bind","evaluate","return"]
    objective_id:Literal["O1","O2","O3"]
    claim_ids:tuple[str,...]=Field(min_length=1,max_length=1)
    semantic_event_id:str=Field(pattern=r"^event-(define|call|bind|evaluate|return)$")
    visual_state_key:str=Field(pattern=r"^state-(define|call|bind|evaluate|return)$")
    active_code_role:Literal["signature","invocation","body"]
    spoken_text:str=Field(min_length=28,max_length=240)
    # A causal event is scheduled as a fractional point in the physically
    # measured utterance; no fabricated word timestamp.
    event_fraction:float=Field(ge=.08,le=.85)


class LessonSemanticContract(V3Model):
    version:Literal["v3-32-typed-five-beat-v1"]
    topic_id:Literal["lfb-002-cs"]
    source_url:str
    source_sha256:str=Field(min_length=64,max_length=64)
    objective_ids:tuple[str,...]
    claims:tuple[SourceClaim,...]=Field(min_length=3,max_length=3)
    example:WorkedExample
    research_explanations:tuple[str,...]=Field(min_length=3,max_length=3)
    research_provenance:Literal["HOST_DETERMINISTIC_SOURCE_TRACE_COMPILER"]
    beats:tuple[LessonBeat,...]=Field(min_length=5,max_length=5)
    deprecated_model_research_status:Literal["REJECTED_EXAMPLE_DRIFT"]

    @model_validator(mode="after")
    def link_contract(self):
        if self.source_url!=SOURCE_URL or self.objective_ids!=("O1","O2","O3"):
            raise ValueError("V332_SOURCE_OR_OBJECTIVE_MISMATCH")
        if tuple(x.claim_id for x in self.claims)!=("C_DEFINE","C_BIND","C_RETURN"):
            raise ValueError("V332_SOURCE_CLAIM_ORDER_DRIFT")
        if any(x.sha256_source!=self.source_sha256 for x in self.claims):
            raise ValueError("V332_SOURCE_HASH_DRIFT")
        if tuple(b.stage for b in self.beats)!=STAGES:
            raise ValueError("V332_BEAT_ORDER_DRIFT")
        if any(b.semantic_event_id!="event-"+b.stage or
               b.visual_state_key!="state-"+b.stage or
               b.claim_ids!=(CLAIM_IDS[i],) for i,b in enumerate(self.beats)):
            raise ValueError("V332_EVENT_OR_CLAIM_ID_DRIFT")
        if tuple(b.objective_id for b in self.beats)!=("O1","O2","O2","O3","O3"):
            raise ValueError("V332_OBJECTIVE_SEQUENCE_DRIFT")
        if tuple(b.active_code_role for b in self.beats)!=(
            "signature","invocation","invocation","body","body"):
            raise ValueError("V332_CODE_ROLE_DRIFT")
        if (self.research_explanations!=compiled_research(self.example) or
            tuple(b.spoken_text for b in self.beats)!=compiled_narration(self.example)):
            raise ValueError("V332_RESEARCH_OR_SCRIPT_NOT_SOURCE_TRACE_GROUNDED")
        return self


def compiled_research(e:WorkedExample)->tuple[str,...]:
    return (
        f"The definition of {e.function_name} names {e.parameter} as its input parameter; the body computes {e.parameter} {e.operator} {e.constant}.",
        f"Calling {e.function_name} with argument {e.argument} supplies exactly {e.argument} to parameter {e.parameter} for this invocation.",
        f"The calculation {e.argument} {e.operator} {e.constant} gives {e.result}; the return value is assigned to {e.destination}.",
    )


def compiled_narration(e:WorkedExample)->tuple[str,...]:
    verb="plus" if e.operator=="+" else "minus"
    return (
        f"First, def introduces the function {e.function_name}. The parameter {e.parameter} is a name for its input, and the body will use that parameter.",
        f"Now call {e.function_name} with argument {e.argument}. Watch the input value leave the call and move toward the parameter.",
        f"The value {e.argument} binds to parameter {e.parameter} for this call. Inside the function, {e.parameter} now means {e.argument}.",
        f"Evaluate the return expression: {e.parameter} is {e.argument}, so {e.argument} {verb} {e.constant} equals {e.result}. Follow the calculation before returning.",
        f"Finally the function returns {e.result}. The call finishes, and the returned value {e.result} is stored in {e.destination}.",
    )


def audited_model_research(record:dict,example:WorkedExample)->dict:
    """Rejection, never silent correction of provider-produced prose."""
    claims=record["research_claims"]
    if len(claims)!=3: raise Blocked("V332_RESEARCH_CLAIM_COUNT")
    allowed={example.argument,example.constant,example.result}
    reasons=[]
    for item in claims:
        text=item["explanation"].casefold()
        nums={int(n) for n in re.findall(r"(?<![a-z_])\d+(?![a-z_])",text)}
        drift=bool(nums-allowed) or bool(re.search(r"\b(doubl\w*|trip\w*|halv\w*)\b",text))
        if drift:
            reasons.append({"claim_id":item["claim_id"],"error_code":"V332_PROVIDER_EXAMPLE_DRIFT",
                            "original_explanation_sha256":sha256(item["explanation"].encode()).hexdigest()})
    return {"decision":"REJECT" if reasons else "PROVISIONALLY_COMPATIBLE",
            "model":"openai/gpt-6-luna","issues":reasons,
            "provisional_not_independent_fact_review":True}


def compile_lesson(record:dict,example:WorkedExample)->tuple[LessonSemanticContract,dict]:
    audit=audited_model_research(record,example)
    if audit["decision"]!="REJECT":
        raise Blocked("V332_V330_AUDIT_EXPECTED_REJECT")
    c=record["source_certificate"]
    validate_research({"claims":record["research_claims"]},c)
    if c["source_url"]!=SOURCE_URL or not c["sha256_html"]:
        raise Blocked("V332_UNVERIFIED_SOURCE")
    b=tuple(LessonBeat(stage=stage,objective_id=("O1","O2","O2","O3","O3")[i],
            claim_ids=(CLAIM_IDS[i],),semantic_event_id="event-"+stage,
            visual_state_key="state-"+stage,
            active_code_role=("signature","invocation","invocation","body","body")[i],
            spoken_text=compiled_narration(example)[i],
            event_fraction=(.15,.35,.45,.38,.55)[i])
            for i,stage in enumerate(STAGES))
    contract=LessonSemanticContract(
        version="v3-32-typed-five-beat-v1",topic_id="lfb-002-cs",
        source_url=c["source_url"],source_sha256=c["sha256_html"],
        objective_ids=("O1","O2","O3"),
        claims=tuple(SourceClaim(claim_id=item["claim_id"],source_id="S1",
                                quote=item["quote"],sha256_source=c["sha256_html"])
            for item in record["research_claims"]),
        example=example,research_explanations=compiled_research(example),
        research_provenance="HOST_DETERMINISTIC_SOURCE_TRACE_COMPILER",
        beats=b,deprecated_model_research_status="REJECTED_EXAMPLE_DRIFT")
    # Prove host generated explanations cite EXACT SAME certified 3 quotations,
    # and no fabricated sources were added; publisher source is not arithmetic proof.
    validate_research({"claims":[{"claim_id":c.claim_id,"quote":c.quote,
        "explanation":txt} for c,txt in zip(contract.claims,contract.research_explanations)]},
        record["source_certificate"])
    return contract,audit


def verify_numeric_replay(e:WorkedExample)->dict:
    op=e.operator
    a,b=(f"{e.parameter} = {e.argument}",
         f"result = {e.parameter} {op} {e.constant}")
    graph=SceneGraph.model_validate({
        "scene_id":"lesson-numeric-assignment-replay","purpose":"DEMONSTRATE",
        "layout_intent":{"type":"GRID"},
        "nodes":[{"id":"code","kind":"CODE","label":"Verified state","content":a+"\n"+b}],
        "relations":[]})
    spec=CodeWalkthrough(
        scenegraph_sha256=compute_content_hash(graph),
        lines=(CodeLine(line_id="bind",source=a),CodeLine(line_id="evaluate",source=b)),
        steps=(CodeStep(line_id="bind",variables={e.parameter:e.argument}),
               CodeStep(line_id="evaluate",variables={e.parameter:e.argument,"result":e.result})))
    verify_code_walkthrough(spec,graph)
    return {"scenegraph_sha256":compute_content_hash(graph),
            "codewalkthrough_sha256":compute_content_hash(spec),
            "certified_final_value":e.result}


def default_example()->WorkedExample:
    return WorkedExample(
        function_name="add_two",parameter="n",destination="answer",
        operator="+",constant=2,argument=3,result=5,
        source_code="def add_two(n):\n    return n + 2\n\nanswer = add_two(3)")


def load_contract(root:Path)->tuple[LessonSemanticContract,dict]:
    record=load_pinned_receipt(root/"reports"/"v3_31_v330_real_receipt_subset.json")
    from learnflow_v3.multidomain_coverage import read_source
    topic=next(x for x in read_source(root)[0] if x["topic_id"]=="lfb-002-cs")
    if topic["query_sha256"]!=record["topic_hash"]:
        raise Blocked("V332_FROZEN_TOPIC_IDENTITY")
    c,a=compile_lesson(record,default_example())
    verify_numeric_replay(c.example)
    return c,a
