"""V3-82 constrained query -> source-grounded Hermes contracts -> native V3-81.

No authored operation list, storyboard or narration in selected queries. The user
question is a bounded expression: arbitrary prose, code execution, unverified
scientific concepts and independent model creativity are explicitly unsupported.
Source seeds are historical author-curated references, not live source review.
"""
from __future__ import annotations

import ast
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import re

from agent_contracts import (
    AssessmentProbe, EvidenceEdge, EvidenceGraph, EvidenceNodeKind,
    EvidenceRelation, LearningBrief, LearningObjective, LessonScript,
    PedagogyExample, PedagogyPlan, ResearchClaim, ResearchPack, ScriptSegment,
    SourceRecord, SourceType, Storyboard, StoryboardScene,
)
from fact_verification import verify_facts
from learnflow_v2.concepts import ConceptRegistry
from learnflow_v2.scenegraph.schema import SceneGraph
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.models import VisualTeachingPlan
from learnflow_v3.pedagogy_planner import (
    PedagogyPlannerRequest, compile_pedagogy_and_hero,
    verify_grounded_pedagogy_plan,
)
from learnflow_v3.source_grounded_compiler import ACCEPTED
from learnflow_v3.v381_generic_semantic_operators import (
    calculate, encode, fmt, need as v381_need,
    parse_value, validate_case,
)
from script_agent.gate import validate_lesson_script, require_visual_director_ready
from visual_director import VisualDirectorOutput, validate_visual_director_output
from visual_director.gate import require_core_ready

REG_PATH = "benchmarks/learnflowbench/v3/v3_82_query_evidence_bridge_preregister.json"
SOURCE_PATH = "benchmarks/learnflowbench/v3/v3_28_offline_source_seeds.json"
SAFE_QUESTION = re.compile(r"^What is the result of (.{5,110})\?$")
IDENT = re.compile(r"^[a-z][a-z0-9_]{0,32}$")
EXPECTED_STATEMENTS = {
    "LINEAR_SLOPE": "For a line, slope is the change in y divided by the change in x.",
    "CONSTANT_ACCELERATION_VELOCITY":
        "For motion with constant acceleration, velocity equals initial velocity plus acceleration times elapsed time.",
}


def need(ok, message):
    if not ok:
        raise Blocked("V382_" + message)


def fingerprint(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def registered(root: Path):
    d = json.loads((root / REG_PATH).read_text())
    need(d["checkpoint"] == "V3-82" and d["kind"] == "PREREG_BEFORE_IMPLEMENTATION"
         and d["parent"] == {"pr":118,"sha":"947b05d029e2eadeee34d69ac1739a571c90ecfa"}
         and d["acceptance"]["real_model_calls"] == 0
         and d["acceptance"]["production"] == "BLOCKED", "PREREG_CHANGED")
    c = d["cases"]
    need(len(c) == 5 and [x["role"] for x in c] ==
         ["development","development","heldout","negative","negative"]
         and len({x["id"] for x in c}) == 5
         and d["acceptance"]["native_positive_exact"] == 3
         and d["acceptance"]["negative_abstain_exact"] == 2,
         "CASE_SELECTION_OR_DENOMINATOR_CHANGED")
    return d


def _approved_seed(row, root: Path):
    historical = json.loads((root / SOURCE_PATH).read_text())
    need(historical["schema_version"] == "v3-28-curated-source-input-v1"
         and historical["status"] == "AUTHOR_SEEDED_NOT_AUTONOMOUS_RESEARCH",
         "HISTORICAL_SOURCE_VERSION_DRIFT")
    family = row["source_model"]
    match = [x for x in historical["cases"] if x["model_kind"] == family]
    need(len(match) == 1, "UNREGISTERED_SOURCE_FAMILY")
    seed = match[0]
    need(ACCEPTED.get(family) == (row["domain"], seed["source_url"]),
         "UNSUPPORTED_DOMAIN_OR_SOURCE_URL")
    need(seed["source_statement"] == EXPECTED_STATEMENTS[family]
         and seed["source_title"].startswith("OpenStax"),
         "HISTORICAL_SOURCE_QUOTE_OR_TITLE_DRIFT")
    return seed


def expression_plan(row):
    """AST reads expression from question, not hidden per-topic operation plans."""
    s = SAFE_QUESTION.fullmatch(row["question"])
    need(s is not None, "UNSUPPORTED_USER_QUERY_GRAMMAR")
    try:
        tree = ast.parse(s.group(1), mode="eval")
    except SyntaxError:
        raise Blocked("V382_UNSUPPORTED_USER_QUERY_AST") from None
    facts = row["facts"]
    need(isinstance(facts,dict) and 2 <= len(facts) <= 8, "INVALID_INPUT_FACTS")
    state = {}
    for key, value in facts.items():
        need(isinstance(key,str) and IDENT.fullmatch(key), "INPUT_VARIABLE_IDENTIFIER")
        typed = parse_value(value)
        need(typed[0] == "scalar", "ONLY_SCALAR_EVIDENCE_SUPPORTED")
        state[key] = typed
    steps = []
    def build(node, depth=0):
        need(depth <= 5, "EXPRESSION_TOO_DEEP")
        if isinstance(node, ast.Name):
            need(node.id in state, "UNKNOWN_QUERY_VARIABLE")
            return node.id
        need(isinstance(node,ast.BinOp) and type(node.op) in (ast.Add,ast.Mult),
             "UNSUPPORTED_QUERY_OPERATION_OR_CODE")
        left = build(node.left,depth+1)
        right = build(node.right,depth+1)
        kind = "ADD" if isinstance(node.op,ast.Add) else "SCALE"
        result = calculate(kind,[state[left],state[right]])
        need(result[0] == "scalar" and abs(result[1]) <= 10000
             and result[1].denominator <= 10000, "UNBOUNDED_QUERY_MATH")
        key = f"step_{len(steps)+1:02d}"
        state[key] = result
        verb = "add" if kind == "ADD" else "multiply"
        left_text,right_text=fmt(state[left]),fmt(state[right])
        statement = f"Exact host arithmetic: {left_text} {'+' if kind == 'ADD' else '×'} {right_text} = {fmt(result)}."
        narration = (
            f"Look at {left} with the value {left_text}, and {right} with the value {right_text}. "
            f"We {verb} these two quantities, obtaining the exact result {fmt(result)}. "
            "The visual change shows the inputs becoming this new value without introducing an unverified answer."
        )
        steps.append({
            "id":key,"kind":kind,"inputs":[left,right],
            "expected":encode(result),"claim_id":f"C{len(steps)+1}",
            "narration":narration,
            "canonical_statement":statement,
        })
        return key
    output = build(tree.body)
    need(len(steps) in (2,3,4) and output == steps[-1]["id"],
         "INSUFFICIENT_OR_UNBOUNDED_OPERATION_COVERAGE")
    return steps, output


def _contracts(row, seed, case, trace):
    """Real typed Hermes research/fact/script/pedagogy/VD gates; no fake model origin."""
    sources = (
        SourceRecord(source_id="S1",source_type=SourceType.BOOK,
                     title=seed["source_title"],locator=seed["source_url"],
                     publisher="OpenStax"),
        SourceRecord(source_id="S2",source_type=SourceType.OTHER,
                     title="Exact rational operator verification (V3-81)",
                     locator="repo://learnflow_v3/v381_generic_semantic_operators.py"),
    )
    claims = (
        ResearchClaim(claim_id="C0",statement=seed["source_statement"],
                      source_ids=("S1",),confidence=1.0),
        *(ResearchClaim(claim_id=f"C{i+1}",statement=x["canonical_statement"],
                        source_ids=("S2",),confidence=1.0)
          for i,x in enumerate(case["generated_steps"])),
    )
    research = ResearchPack(pack_id=f"research.{row['id']}",topic=row["question"],
                            concepts=("input","output"),sources=sources,claims=claims)
    evidence = EvidenceGraph(
        graph_id=f"evidence.{row['id']}",research_pack_id=research.pack_id,
        source_ids=("S1","S2"),claim_ids=tuple(c.claim_id for c in claims),
        edges=tuple(EvidenceEdge(edge_id=f"E{i}",from_kind=EvidenceNodeKind.SOURCE,
                                 from_id="S1" if i == 0 else "S2",
                                 to_claim_id=c.claim_id,relation=EvidenceRelation.SUPPORTS)
                    for i,c in enumerate(claims)))
    fact = verify_facts(research,evidence)
    need(set(fact.approved_claim_ids) == {c.claim_id for c in claims},
         "HERMES_FACT_GATE_FAILED")
    brief = LearningBrief(brief_id=f"brief.{row['id']}",
                          user_query=row["question"],learner_level="beginner",
                          target_duration_minutes=1.0,language="en")
    pedagogy = PedagogyPlan(
        plan_id=f"pedagogy.{row['id']}",brief_id=brief.brief_id,
        research_pack_id=research.pack_id,evidence_graph_id=evidence.graph_id,
        learning_objectives=(
            LearningObjective(objective_id="O1",
                              description="Trace each exact arithmetic state",
                              assessment_criterion="Recompute each operation result"),
            LearningObjective(objective_id="O2",
                              description="Explain which source inputs enter each computation",
                              assessment_criterion="Identify original input and derived states")),
        concept_order=("input","output"),
        worked_examples=(PedagogyExample(
            example_id="X1",concept="input",
            description="Compute all query-derived arithmetic transformations",
            claim_ids=tuple(x.claim_id for x in claims)),),
        assessment_probes=(
            AssessmentProbe(probe_id="P1",prompt="Recompute each intermediate result",
                            expected_outcome="Exact source arithmetic",
                            objective_ids=("O1",)),
            AssessmentProbe(probe_id="P2",prompt="Explain how the inputs become the result",
                            expected_outcome="Correct dependency order",
                            objective_ids=("O2",))),)
    segments = tuple(
        ScriptSegment(
            segment_id=f"seg-{i}",spoken_text=e["narration"],
            subtitle_text=e["narration"],spoken_language="en",subtitle_language="en",
            claim_ids=("C0",e["claim_id"]),objective_ids=("O1","O2"),
            teaching_function="DEMONSTRATE")
        for i,e in enumerate(trace["events"]))
    script = LessonScript(script_id=f"script.{row['id']}",
                          pedagogy_plan_id=pedagogy.plan_id,segments=segments)
    visual = VisualTeachingPlan(
        lesson_id=f"lesson.{row['id']}",
        learning_objective_ids=("O1","O2"),
        sections=(dict(section_id="verified-arithmetic",
                       objective_refs=("O1","O2"),
                       learner_state_before="Result not calculated yet",
                       learner_state_after="Can follow each verified operation",
                       visual_teaching_goal="Show the exact arithmetic transformation",
                       representation_options=("WORKED_EXAMPLE_BOARD",),
                       visual_complexity_budget=8,hero_candidate=True),),
        beats=tuple(dict(
            beat_id=f"beat-{i}",section_ref="verified-arithmetic",
            script_segment_ref=seg.segment_id,claim_refs=seg.claim_ids,
            concept_refs=(),
            expected_visible_state_change=f"Reveal calculated output {i}",
            importance=.8 if i == len(segments)-1 else .6)
            for i,seg in enumerate(segments)),
        constraints=dict(language="en",learner_level="beginner",
                         target_duration_minutes=1.0))
    kwargs=dict(brief=brief,research=research,evidence=evidence,
                fact_report=fact,pedagogy=pedagogy,script=script,visual=visual,
                registry=ConceptRegistry(),
                request=PedagogyPlannerRequest(total_visual_units=8,hero_count_limit=1))
    plan = compile_pedagogy_and_hero(**kwargs)
    verify_grounded_pedagogy_plan(candidate=plan,**kwargs)
    # A genuine typed and validated V2 SceneGraph + old Visual Director gate,
    # not a hidden topic-specific storyboard or LLM-selected layout.
    nodes = [
        {"id":ev["id"],"kind":"MATH","label":ev["result_text"],
         "semantic_role":ev["id"],"layout_hint":{"preferred_region":
         ("LEFT" if i==0 else "RIGHT" if i==len(segments)-1 else "CENTER")}}
        for i,ev in enumerate(trace["events"])
    ]
    relations = [
        {"id":f"link_{i}","source":nodes[i]["id"],"target":nodes[i+1]["id"],
         "kind":"FLOW"}
        for i in range(len(nodes)-1)
    ]
    graph = SceneGraph.model_validate({
        "scene_id":f"scene_{row['id']}","concept":"Host-proven arithmetic process",
        "purpose":"DEMONSTRATE","layout_intent":{"type":"PROCESS"},
        "nodes":nodes,"relations":relations})
    storyboard = Storyboard(
        storyboard_id=f"storyboard.{row['id']}",script_id=script.script_id,
        scenes=(StoryboardScene(
            scene_id=graph.scene_id,
            script_segment_ids=tuple(seg.segment_id for seg in segments),
            teaching_function="DEMONSTRATE",
            visual_intent="Follow source-grounded arithmetic operations"),))
    vd = VisualDirectorOutput(storyboard=storyboard,scenegraphs=(graph,))
    gate = validate_visual_director_output(vd,script=script,
                                           registry=kwargs["registry"])
    require_core_ready(gate)
    # Lock identity across script segments, typed visual beats and exact
    # compiler events before reading into the native Manim generator.
    need(len(segments) == len(visual.beats) == len(trace["events"])
         and all(seg.segment_id == beat.script_segment_ref and
                 tuple(seg.claim_ids) == tuple(beat.claim_refs) and
                 e["claim_id"] in seg.claim_ids
                 for seg,beat,e in zip(segments,visual.beats,trace["events"],strict=True)),
         "SCRIPT_VISUAL_NATIVE_CLAIM_DRIFT")
    return {
        "research":research.model_dump(mode="json"),
        "evidence":evidence.model_dump(mode="json"),
        "fact_report":fact.model_dump(mode="json"),
        "script":script.model_dump(mode="json"),
        "visual":visual.model_dump(mode="json"),
        "director_graph":graph.model_dump(mode="json"),
        "pedagogy_gate":"V3_09_VALIDATED",
        "visual_director_gate":"CORE_READY",
        "source_status":"CURATED_HISTORICAL_REFERENCE_NOT_INDEPENDENT_SEMANTIC_PROOF",
    }


def compile_question(row, root: Path):
    need(isinstance(row,dict) and set(row) ==
         {"id","role","domain","source_model","question","title","facts"},
         "CASE_INPUT_SCHEMA")
    if row["role"] == "negative":
        need(row["source_model"] is None and not row["facts"],
             "NEGATIVE_MUST_NOT_SPOOF_SOURCE")
        return {"id":row["id"],"status":"ABSTAIN",
                "reason":"UNSUPPORTED_RESEARCH_AND_SEMANTIC_OPERATOR_FAMILY",
                "video":None,"model_calls":0}
    need(row["role"] in ("development","heldout"),"ROLE_UNSUPPORTED")
    seed = _approved_seed(row,root)
    steps, final_id = expression_plan(row)
    # V3-81 requires fact IDs >= 2 chars; preserve the user's expression
    # verbatim and derive collision-safe internal aliases without case branching.
    alias = {key:(f"var_{key}" if len(key)==1 else key)
             for key in row["facts"]}
    need(len(set(alias.values()))==len(alias),"INTERNAL_ALIAS_COLLISION")
    facts = {alias[key]:value for key,value in row["facts"].items()}
    operations = [{k:v for k,v in step.items() if k!="canonical_statement"}
                  for step in steps]
    for operation in operations:
        operation["inputs"]=[alias.get(x,x) for x in operation["inputs"]]
    generated_case = {
        "id":row["id"],"domain":row["domain"],"role":row["role"],
        "title":row["title"],"facts":facts,
        "claims":{f"C{i+1}":step["canonical_statement"] for i,step in enumerate(steps)},
        "operations":operations}
    trace = validate_case(generated_case)
    need(trace["state"][final_id] == steps[-1]["expected"],"FINAL_QUERY_PROOF_MISMATCH")
    # Presentation is computed ONLY from exact V3-81 attested arithmetic.
    # Internal IDs remain in the signed provenance graph, but do not leak
    # into learner-facing Manim captions (var_m / step_01 are not pedagogy).
    public = {internal:original for original,internal in alias.items()}
    for event in trace["events"]:
        left,right=[parse_value(v) for v in event["operands"]]
        actual=parse_value(event["actual"])
        need(encode(calculate(event["kind"],[left,right])) == encode(actual),
             "DISPLAY_MATH_DIFFERENT_FROM_HOST_PROOF")
        event["operand_text"]=[
            f"{public.get(ref, 'previous result')} = {fmt(value)}"
            for ref,value in zip(event["refs"],(left,right),strict=True)]
        op_symbol="+" if event["kind"]=="ADD" else "×"
        event["result_text"]=f"{fmt(left)} {op_symbol} {fmt(right)} = {fmt(actual)}"
        public[event["id"]]="previous result"
    trace["presentation_provenance"]="VERIFIED_OPERATOR_OUTPUT_REPLAY_NO_MODEL"
    contract = _contracts(row,seed,{"generated_steps":steps},trace)
    return {
        "id":row["id"],"status":"READY_FOR_NATIVE_RESEARCH_ONLY",
        "question":row["question"],"source_url":seed["source_url"],
        "source_reference_kind":"PREVIOUSLY_CURATED_V3_28_NOT_LIVE_VERIFIED",
        "source_sha256":fingerprint(seed),
        "generated_case_sha256":fingerprint(generated_case),
        "generated_plan":generated_case,
        "trace":trace,"contracts":contract,
        "bridge_provenance":"DETERMINISTIC_OFFLINE_HOST_NOT_LLM",
        "human_quality":"UNRATED","model_calls":0,
    }
