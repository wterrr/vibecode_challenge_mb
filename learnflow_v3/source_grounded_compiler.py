"""V3-28: source-bound *offline* linear lesson script/pedagogy/VD compiler.

Receives actual Hermes typed ResearchPack, EvidenceGraph, FactReport, PedagogyPlan,
LessonScript, V3-09 VisualTeachingPlan, V2 Storyboard/SceneGraph. Reuses their
validation gates and derives source-locked point semantics before audio/render.
The author-seeded input builder is strictly a bounded engineering demonstration:
NO independent Research/Script model execution, semantic fact reviewer or
production router activation. Unsupported lesson families always ABSTAIN.
"""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path

from agent_contracts import (
    AssessmentProbe,EvidenceEdge,EvidenceGraph,EvidenceNodeKind,
    EvidenceRelation,LearningBrief,LearningObjective,LessonScript,
    PedagogyExample,PedagogyPlan,ResearchClaim,ResearchPack,
    ScriptSegment,SourceRecord,SourceType,Storyboard,StoryboardScene,
)
from fact_verification import verify_facts
from learnflow_v2.concepts import ConceptRegistry
from learnflow_v2.repair import compute_content_hash
from learnflow_v3.models import VisualTeachingPlan
from learnflow_v3.multidomain_coverage import (
    make_linear_graph,read_source,render_math,guard,VERSION as V327
)
from learnflow_v3.pedagogy_planner import (
    PedagogyPlannerRequest,compile_pedagogy_and_hero,
    verify_grounded_pedagogy_plan,
)
from visual_director import VisualDirectorOutput,validate_visual_director_output
from visual_director.gate import require_core_ready

VERSION="v3-28-research-script-pedagogy-vd-source-compiler-v1"
SEED_FILE="benchmarks/learnflowbench/v3/v3_28_offline_source_seeds.json"
ACCEPTED={
  "LINEAR_SLOPE":("math","https://openstax.org/books/intermediate-algebra-2e/pages/3-2-slope-of-a-line"),
  "CONSTANT_ACCELERATION_VELOCITY":("physics","https://openstax.org/books/college-physics-2e/pages/2-5-motion-equations-for-constant-acceleration-in-one-dimension"),
}

def _snum(n:int)->str:
    return "minus "+str(-n) if n<0 else str(n)

def canonical_claim(*,seed:dict,point)->str:
    if seed["model_kind"]=="LINEAR_SLOPE":
        return f"For x equals {_snum(point.x)}, the value of y is {_snum(point.y)}."
    return (f"At {_snum(point.x)} seconds, velocity is "
            f"{_snum(point.y)} meters per second.")

def author_seeded_contracts(*,topic:dict,seed:dict)->dict:
    """Offline authored demonstration only, *not* a model Research/Script run.

    Inputs remain mutable data. The compiler independently certifies all
    sources, claim/script/beat/point bindings before any sound or video.
    """
    guard(seed["topic_id"]==topic["topic_id"] and
          ACCEPTED.get(seed["model_kind"])==(topic["domain"],seed["source_url"]),
          "SOURCE_SEED_SCOPE_OR_CITATION_MISMATCH")
    guard(type(seed["slope"]) is int and type(seed["intercept"]) is int,
          "NON_INTEGER_MODEL")
    graph,spec=make_linear_graph(
        slope=seed["slope"],intercept=seed["intercept"],
        domain=tuple(seed["x_domain"]))
    # Author-curated cited external textbook + separate local arithmetic
    # verification source: a source URL is not semantic fact verification.
    sources=(
        SourceRecord(source_id="S1",source_type=SourceType.BOOK,
                     title=seed["source_title"],locator=seed["source_url"],
                     publisher="OpenStax"),
        SourceRecord(source_id="S2",source_type=SourceType.OTHER,
                     title="Certified integer polynomial replay",
                     locator="repo://learnflow_v3/math_renderer.py#verify_function_graph"),
    )
    claims=(
        ResearchClaim(claim_id="C1",statement=seed["source_statement"],
                      source_ids=("S1",),confidence=1.0),
        *(ResearchClaim(claim_id=f"CP{i}",statement=canonical_claim(seed=seed,point=p),
                        source_ids=("S2",),confidence=1.0)
          for i,p in enumerate(spec.steps)),
    )
    pack=ResearchPack(pack_id=f"research.{topic['topic_id']}",topic=topic["query"],
                      concepts=("input","output"),sources=sources,claims=claims)
    evidence=EvidenceGraph(
        graph_id=f"evidence.{topic['topic_id']}",
        research_pack_id=pack.pack_id,
        source_ids=("S1","S2"),claim_ids=tuple(x.claim_id for x in claims),
        edges=tuple(EvidenceEdge(edge_id=f"E{i}",from_kind=EvidenceNodeKind.SOURCE,
                     from_id=("S1" if i==0 else "S2"),to_claim_id=claim.claim_id,
                     relation=EvidenceRelation.SUPPORTS)
                    for i,claim in enumerate(claims)))
    fact=verify_facts(pack,evidence)
    guard(set(fact.approved_claim_ids)=={x.claim_id for x in claims},
          "SOURCE_CLAIM_NOT_APPROVED")
    brief=LearningBrief(brief_id=f"brief.{topic['topic_id']}",
                        user_query=topic["query"],learner_level=topic["learner_level"],
                        target_duration_minutes=float(topic["target_duration_minutes"]),
                        language=topic["language"])
    pedagogy=PedagogyPlan(
        plan_id=f"pedagogy.{topic['topic_id']}",
        brief_id=brief.brief_id,research_pack_id=pack.pack_id,
        evidence_graph_id=evidence.graph_id,
        learning_objectives=(
            LearningObjective(objective_id="O1",description="Read each certified plotted point",
                              assessment_criterion="Compute the dependent coordinate"),
            LearningObjective(objective_id="O2",description="Interpret the source-verified linear rate",
                              assessment_criterion="Explain the change per input step")),
        concept_order=("input","output"),
        worked_examples=(PedagogyExample(
            example_id="X1",concept="input",
            description="Certified linear example with each point checked",
            claim_ids=tuple(x.claim_id for x in claims)),),
        assessment_probes=(
            AssessmentProbe(probe_id="P1",prompt="Find the plotted output",
                            expected_outcome="Numerically correct output",objective_ids=("O1",)),
            AssessmentProbe(probe_id="P2",prompt="Explain the slope",
                            expected_outcome="Correct source-grounded rate",objective_ids=("O2",))),
    )
    script=LessonScript(
        script_id=f"script.{topic['topic_id']}",pedagogy_plan_id=pedagogy.plan_id,
        segments=tuple(ScriptSegment(
            segment_id=f"seg-{i}",spoken_text=canonical_claim(seed=seed,point=p),
            subtitle_text=canonical_claim(seed=seed,point=p),
            spoken_language="en",subtitle_language="en",
            claim_ids=("C1",f"CP{i}"),
            objective_ids=(("O1","O2") if i==len(spec.steps)-1 else ("O1",)),
            teaching_function="DEMONSTRATE")
            for i,p in enumerate(spec.steps)))
    visual=VisualTeachingPlan(
        lesson_id=f"lesson.{topic['topic_id']}",
        learning_objective_ids=("O1","O2"),
        sections=(dict(section_id="linear-rate",
                       objective_refs=("O1","O2"),
                       learner_state_before="No plotted point yet",
                       learner_state_after="Can inspect sourced plotted points",
                       visual_teaching_goal="Reveal only exact certified graph points",
                       representation_options=("EQUATION_GRAPH",),
                       visual_complexity_budget=10,hero_candidate=True),),
        beats=tuple(dict(
            beat_id=f"beat-{i}",section_ref="linear-rate",
            script_segment_ref=s.segment_id,claim_refs=s.claim_ids,
            concept_refs=(),
            expected_visible_state_change=f"Reveal source point {i}",
            importance=0.9 if i==len(spec.steps)//2 else 0.6)
            for i,s in enumerate(script.segments)),
        constraints=dict(language=brief.language,learner_level=brief.learner_level,
                         target_duration_minutes=brief.target_duration_minutes))
    registry=ConceptRegistry()
    request=PedagogyPlannerRequest(
        total_visual_units=8,hero_count_limit=1)
    storyboard=Storyboard(
        storyboard_id=f"storyboard.{topic['topic_id']}",script_id=script.script_id,
        scenes=(StoryboardScene(
            scene_id=graph.scene_id,
            script_segment_ids=tuple(s.segment_id for s in script.segments),
            teaching_function="DEMONSTRATE",
            visual_intent="Graph the source-certified linear function step by step"),))
    return dict(topic=topic,seed=seed,graph=graph,spec=spec,brief=brief,research=pack,
                evidence=evidence,fact_report=fact,pedagogy=pedagogy,script=script,
                visual=visual,registry=registry,request=request,storyboard=storyboard)

def compile_linear_source_bound(*,bundle:dict)->tuple[list[dict],dict]:
    """Gates real Hermes+V3-09+VD contracts, then compiles source point events.

    The author seed is checked against a *finite explicitly verified* source
    family; arbitrary free-text research is NOT falsely assumed approved.
    """
    b=bundle;seed=b["seed"];topic=b["topic"]
    guard(ACCEPTED.get(seed["model_kind"])==(topic["domain"],seed["source_url"]),
          "UNSUPPORTED_DOMAIN_SOURCE_MODEL")
    graph,spec=b["graph"],b["spec"]
    known_graph,known_spec=make_linear_graph(
        slope=seed["slope"],intercept=seed["intercept"],
        domain=tuple(seed["x_domain"]))
    guard(compute_content_hash(graph)==compute_content_hash(known_graph)
          and compute_content_hash(spec)==compute_content_hash(known_spec),
          "SOURCE_GRAPH_OR_POLYNOMIAL_CHANGED")
    claims={c.claim_id:c for c in b["research"].claims}
    guard(set(claims)=={"C1",*(f"CP{i}" for i in range(len(spec.steps)))},
          "RESEARCH_CLAIM_COVERAGE_DRIFT")
    guard(claims["C1"].statement==seed["source_statement"]
          and b["research"].sources[0].locator==seed["source_url"],
          "TEXTBOOK_CLAIM_SOURCE_DRIFT")
    for i,p in enumerate(spec.steps):
        guard(claims[f"CP{i}"].statement==canonical_claim(seed=seed,point=p),
              "DERIVED_POINT_CLAIM_SEMANTIC_DRIFT")
    # GENUINE existing gate is invoked; it validates pack, evidence, fact,
    # pedagogy, script/claim/beat coverage, objectives, budget and refs.
    kwargs={key:b[key] for key in ("brief","research","evidence","fact_report",
                                    "pedagogy","script","visual","registry","request")}
    plan=compile_pedagogy_and_hero(**kwargs)
    verify_grounded_pedagogy_plan(candidate=plan,**kwargs)
    vd=VisualDirectorOutput(storyboard=b["storyboard"],scenegraphs=(graph,))
    result=validate_visual_director_output(vd,script=b["script"],registry=b["registry"])
    require_core_ready(result)
    guard(len(b["script"].segments)==len(spec.steps)
          and len(b["visual"].beats)==len(spec.steps),
          "BEAT_SCRIPT_POINT_COUNT_DRIFT")
    events=[]
    for i,(segment,beat,p) in enumerate(
        zip(b["script"].segments,b["visual"].beats,spec.steps,strict=True)):
        guard(segment.segment_id==beat.script_segment_ref
              and beat.claim_refs==segment.claim_ids
              and f"CP{i}" in segment.claim_ids and "C1" in segment.claim_ids,
              "BEAT_SCRIPT_CLAIM_IDENTITY_DRIFT")
        guard(segment.spoken_text==canonical_claim(seed=seed,point=p)
              and segment.subtitle_text==segment.spoken_text,
              "SCRIPT_SEMANTIC_SOURCE_DRIFT")
        events.append({"kind":"SOURCE_POINT","visual_step":i,
                       "text":segment.spoken_text,
                       "source_point_id":p.point_id,"source_value":p.y,
                       "source_claim_ids":list(segment.claim_ids),
                       "beat_id":beat.beat_id,"script_segment_id":segment.segment_id,
                       "objective_ids":list(segment.objective_ids)})
    proof={"status":"VALIDATED_SOURCE_BOUND_LINEAR_BEATS",
           "schema_version":VERSION,"topic_id":topic["topic_id"],
           "family":"FUNCTION_GRAPH",
           "source_sha256":compute_content_hash(b["research"]),
           "evidence_sha256":compute_content_hash(b["evidence"]),
           "fact_report_sha256":compute_content_hash(b["fact_report"]),
           "script_sha256":compute_content_hash(b["script"]),
           "pedagogy_sha256":compute_content_hash(b["pedagogy"]),
           "v3_09_plan_sha256":compute_content_hash(plan),
           "visual_plan_sha256":compute_content_hash(b["visual"]),
           "visual_director_validation":"VD_REAL_GATE_PASSED",
           "storyboard_sha256":compute_content_hash(b["storyboard"]),
           "scenegraph_sha256":compute_content_hash(graph),
           "spec_sha256":compute_content_hash(spec),
           "verified_beats":len(events),
           "cite_source_url":seed["source_url"],
           "external_quote_independently_semantic_fact_checked":False,
           "research_agent_model_called":False,
           "script_agent_model_called":False,
           "visual_director_model_called":False,
           "source_creation":"OFFLINE_AUTHOR_SEEDED_AUTHOR_EXCERPT_AND_ARITHMETIC_PROOF",
           "normal_v3_04_router_promoted":False,
           "publication":"BLOCKED"}
    return events,proof

def run(root:Path,out:Path)->dict:
    guard(out.is_dir() and not any(out.iterdir()),"NONEMPTY_V328_OUTPUT")
    seeds=json.loads((root/SEED_FILE).read_text())
    topics,_=read_source(root)
    targets={x["topic_id"]:x for x in topics}
    guard(len(seeds["cases"])==2 and {x["domain"] for x in seeds["cases"]}==
          {"math","physics"},"SEED_DOMAIN_SET_DRIFT")
    results=[]
    for seed in seeds["cases"]:
        guard(seed["topic_id"] in targets,"NOT_IN_FROZEN_DEVELOPMENT_SET")
        topic=targets[seed["topic_id"]]
        folder=out/topic["topic_id"];folder.mkdir()
        try:
            contracts=author_seeded_contracts(topic=topic,seed=seed)
            events,proof=compile_linear_source_bound(bundle=contracts)
            media=render_math(topic=topic,output=folder,
                              compiled_spec=(contracts["graph"],contracts["spec"]),
                              compiled_events=events,compiler_provenance=proof)
            (folder/"compiler_receipt.json").write_text(
                json.dumps(proof,indent=2)+"\n",encoding="utf-8")
            results.append({"topic_id":topic["topic_id"],"domain":topic["domain"],
                            "status":"OFFLINE_SOURCE_CONTRACT_COMPILER_AND_REAL_AV_PASS",
                            "video_sha256":media["video_sha256"],"beats":len(events),
                            "external_fact_semantic_review":"NOT_RUN",
                            "autonomous_agents":"NOT_RUN"})
        except Exception as exc:
            results.append({"topic_id":topic["topic_id"],"domain":topic["domain"],
                            "status":"FAILED_ACTUAL_COMPILER_ATTEMPT",
                            "reason":type(exc).__name__+":"+str(exc)})
    # Six-domain accountability carried over unchanged: four other domain
    # sources still unsupported, not repackaged as successful audio videos.
    for topic in topics:
        if topic["domain"] not in ("math","physics"):
            results.append({"topic_id":topic["topic_id"],"domain":topic["domain"],
                            "status":"ABSTAIN_UNSUPPORTED_SOURCE_TO_RENDERER",
                            "video_sha256":None})
    guard(len(results)==6,"MISSING_SIX_DOMAIN_LEDGER")
    passed=sum(x["status"]=="OFFLINE_SOURCE_CONTRACT_COMPILER_AND_REAL_AV_PASS" for x in results)
    failures=sum(x["status"]=="FAILED_ACTUAL_COMPILER_ATTEMPT" for x in results)
    receipt={"checkpoint":"V3-28","schema_version":VERSION,
             "seed_sha256":sha256((root/SEED_FILE).read_bytes()).hexdigest(),
             "six_attempt_ledger":results,"denominator":6,
             "bounded_compiler_video_pass_count":passed,
             "attempt_failure_count":failures,"abstain_count":4,
             "autonomous_research_script_director_end_to_end_count":0,
             "full_six_domain_release_gate":"NO_GO",
             "real_human_quality":"UNMEASURED","v3_16_frozen_protocol":"UNCHANGED",
             "paid_api_calls":0,"main_merged":False,"production":"BLOCKED"}
    (out/"v3_28_compiler_coverage.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(f"V3_28_GROUNDED_COMPILER bounded_real_av={passed}/6 failures={failures}/6 "+
          "full_autonomous=0/6 release=NO_GO",flush=True)
    return receipt
