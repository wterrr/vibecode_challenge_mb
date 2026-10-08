"""V3-09 source-grounded pedagogy and finite hero allocation compiler.

Reuses Hermes Pedagogy/Script/Fact gates rather than inventing new research truth.
Every selected teaching moment is bound to approved claims, known objectives,
real script segments and verified V3-02 beats. Output remains a proposal:
neither renderer readiness nor student learning improvement is asserted.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Literal

from pydantic import Field, model_validator

from agent_contracts import (
    EvidenceGraph, LearningBrief, LessonScript, PedagogyPlan, ResearchPack,
)
from fact_verification import FactVerificationReport
from learnflow_v2.concepts import ConceptRegistry
from learnflow_v2.repair import compute_content_hash
from script_agent.gate import validate_lesson_script, require_visual_director_ready
from .models import (
    SemanticContractError, V3Model, VisualTeachingPlan, RepresentationType,
)

VERSION = "v3-09-pedagogy-hero-planner-v1"


class PrerequisiteEdge(V3Model):
    """An explicitly proposed edge, never inferred from an ordered list."""
    prerequisite_concept: str = Field(min_length=1)
    dependent_concept: str = Field(min_length=1)


class MisconceptionBinding(V3Model):
    misconception_id: str = Field(min_length=1)
    correction_beat_id: str = Field(min_length=1)


class PedagogyPlannerRequest(V3Model):
    prerequisite_edges: tuple[PrerequisiteEdge, ...] = ()
    misconception_bindings: tuple[MisconceptionBinding, ...] = ()
    total_visual_units: int = Field(strict=True, ge=2, le=100)
    hero_count_limit: int = Field(default=2, strict=True, ge=1, le=3)

    @model_validator(mode="after")
    def _unique(self):
        edges = [(e.prerequisite_concept, e.dependent_concept) for e in self.prerequisite_edges]
        if len(edges) != len(set(edges)):
            raise ValueError("V3_09_DUPLICATE_PREREQUISITE_EDGE")
        ids = [b.misconception_id for b in self.misconception_bindings]
        if len(ids) != len(set(ids)):
            raise ValueError("V3_09_DUPLICATE_MISCONCEPTION_BINDING")
        return self


class PrerequisiteDAG(V3Model):
    concept_ids: tuple[str, ...]
    declared_edges: tuple[PrerequisiteEdge, ...]
    # An empty edge set is an honest unknown-dependency DAG, not inferred proof.
    inferred_edges: Literal[0] = 0


class ObjectiveCoverage(V3Model):
    objective_id: str
    segment_ids: tuple[str, ...] = Field(min_length=1)
    beat_ids: tuple[str, ...] = Field(min_length=1)
    assessment_probe_ids: tuple[str, ...] = Field(min_length=1)


class MisconceptionCoverage(V3Model):
    misconception_id: str
    claim_ids: tuple[str, ...] = Field(min_length=1)
    correction_beat_id: str
    script_segment_id: str
    correction: str


class TeachingMoment(V3Model):
    beat_id: str
    section_id: str
    objective_ids: tuple[str, ...] = Field(min_length=1)
    approved_claim_ids: tuple[str, ...] = Field(min_length=1)
    misconception_ids: tuple[str, ...] = ()
    representation: RepresentationType
    essential_state_change: str = Field(min_length=1)
    priority_score: int = Field(strict=True, ge=0)
    allocated_section_units: int = Field(strict=True, ge=1)


class SectionBudget(V3Model):
    section_id: str
    allocated_units: int = Field(strict=True, ge=1)
    maximum_units: int = Field(strict=True, ge=1)


class HeroAblationPair(V3Model):
    """Identical source and total budget. No human-learning score is fabricated."""
    control_input_sha256: str
    total_visual_units: int
    uniform: tuple[SectionBudget, ...]
    prioritized: tuple[SectionBudget, ...]
    priority_shift_units: int = Field(strict=True, ge=0)
    status: Literal["REBALANCED_OFFLINE", "UNIFORM_FALLBACK_NO_CAPACITY"]
    human_clarity_delta: Literal["UNMEASURED"] = "UNMEASURED"
    learning_gain: Literal["UNMEASURED"] = "UNMEASURED"

    @model_validator(mode="after")
    def _budget(self):
        if sum(x.allocated_units for x in self.uniform) != self.total_visual_units:
            raise ValueError("V3_09_UNIFORM_BUDGET_LEAK")
        if sum(x.allocated_units for x in self.prioritized) != self.total_visual_units:
            raise ValueError("V3_09_HERO_BUDGET_LEAK")
        if [(s.section_id,s.maximum_units) for s in self.uniform] != [
            (s.section_id,s.maximum_units) for s in self.prioritized
        ]:
            raise ValueError("V3_09_ABLATION_SECTION_OR_CAP_DRIFT")
        for s in (*self.uniform,*self.prioritized):
            if s.allocated_units > s.maximum_units:
                raise ValueError("V3_09_SECTION_BUDGET_EXCEEDED")
        if self.status == "UNIFORM_FALLBACK_NO_CAPACITY" and self.uniform != self.prioritized:
            raise ValueError("V3_09_FALLBACK_NOT_UNIFORM")
        return self


class GroundedPedagogyPlan(V3Model):
    planner_version: Literal["v3-09-pedagogy-hero-planner-v1"] = VERSION
    lesson_id: str
    source_hashes: dict[str, str]
    source_decision_sha256: str
    prerequisite_graph: PrerequisiteDAG
    objectives: tuple[ObjectiveCoverage, ...]
    misconceptions: tuple[MisconceptionCoverage, ...]
    section_mental_models: tuple[tuple[str, str, str], ...]
    hero_moments: tuple[TeachingMoment, ...]
    ablation: HeroAblationPair
    status: Literal["VALIDATED_OFFLINE_PLAN_NO_RENDERER_PROOF"] = "VALIDATED_OFFLINE_PLAN_NO_RENDERER_PROOF"
    render_ready: Literal[False] = False
    independent_human_review: Literal["UNMEASURED"] = "UNMEASURED"
    # Model mutation is caught by verify_grounded_pedagogy_plan from originals.
    decision_sha256: str


def _fail(reason: str):
    raise SemanticContractError("V3_09_" + reason)


def _verified_sources(*, brief, research, evidence, fact_report, pedagogy, script, visual, registry):
    # Reuse exactly the existing reviewed Hermes gates.
    try:
        validated = validate_lesson_script(
            script, brief=brief, pack=research, graph=evidence,
            fact_report=fact_report, pedagogy=pedagogy,
        )
        require_visual_director_ready(validated)
    except Exception as exc:
        _fail("UPSTREAM_PEDAGOGY_SCRIPT_GATE_FAILED:" + str(exc))
    if (brief.language != visual.constraints.language or
        brief.learner_level != visual.constraints.learner_level or
        brief.target_duration_minutes != visual.constraints.target_duration_minutes):
        _fail("LEARNER_PROFILE_OR_DURATION_DRIFT")
    if {o.objective_id for o in pedagogy.learning_objectives} != set(visual.learning_objective_ids):
        _fail("LEARNING_OBJECTIVE_IDENTITY_DRIFT")
    segment_ids = tuple(x.segment_id for x in script.segments)
    beat_segments = tuple(x.script_segment_ref for x in visual.beats)
    if segment_ids != beat_segments:
        _fail("SCRIPT_BEAT_ORDER_OR_COVERAGE_DRIFT")
    approved = set(fact_report.approved_claim_ids)
    for s in script.segments:
        if not set(s.claim_ids) <= approved:
            _fail("SCRIPT_CONTAINS_BLOCKED_CLAIM")
    for b in visual.beats:
        s = next(x for x in script.segments if x.segment_id == b.script_segment_ref)
        sec = next(x for x in visual.sections if x.section_id == b.section_ref)
        if not set(b.claim_refs) <= approved or not set(b.claim_refs) <= set(s.claim_ids):
            _fail("BEAT_CLAIM_NOT_APPROVED_OR_SCRIPT_GROUNDED")
        if not s.objective_ids or not set(s.objective_ids) <= set(sec.objective_refs):
            _fail("BEAT_OBJECTIVE_SECTION_DRIFT")
        for ref in b.concept_refs:
            try:
                item=registry.get(ref.concept_id)
            except Exception:
                _fail("UNKNOWN_CANONICAL_CONCEPT")
            if item.canonical_key != ref.canonical_key:
                _fail("CANONICAL_CONCEPT_KEY_MISMATCH")
    for ref in (*visual.prerequisite_refs, *visual.misconception_refs):
        try:
            item=registry.get(ref.concept_id)
        except Exception:
            _fail("UNKNOWN_PLAN_CONCEPT")
        if item.canonical_key != ref.canonical_key:
            _fail("PLAN_CONCEPT_KEY_MISMATCH")
    coverage = {x for sec in visual.sections for x in sec.objective_refs}
    if coverage != set(visual.learning_objective_ids):
        _fail("UNEXPLAINED_SECTION_OBJECTIVE")
    sources = {
        "brief":compute_content_hash(brief),
        "research":compute_content_hash(research),
        "evidence":compute_content_hash(evidence),
        "fact_report":compute_content_hash(fact_report),
        "pedagogy":compute_content_hash(pedagogy),
        "script":compute_content_hash(script),
        "visual":compute_content_hash(visual),
        "registry":compute_content_hash(registry.to_schema()),
    }
    return sources, approved


def _dag(pedagogy: PedagogyPlan, request: PedagogyPlannerRequest) -> PrerequisiteDAG:
    concepts=pedagogy.concept_order
    order={s:i for i,s in enumerate(concepts)}
    adjacency=defaultdict(list)
    for edge in request.prerequisite_edges:
        a,b=edge.prerequisite_concept,edge.dependent_concept
        if a not in order or b not in order:
            _fail("UNDECLARED_PREREQUISITE_CONCEPT")
        if a==b or order[a] >= order[b]:
            _fail("CYCLIC_OR_OUT_OF_ORDER_PREREQUISITE")
        adjacency[a].append(b)
    # Honest explicit DAG: order constraint plus independent cycle test.
    visited=set()
    active=set()
    def visit(node):
        if node in active:
            _fail("PREREQUISITE_CYCLE")
        if node in visited:
            return
        active.add(node)
        for target in adjacency[node]:
            visit(target)
        active.remove(node)
        visited.add(node)
    for concept in concepts:
        visit(concept)
    return PrerequisiteDAG(concept_ids=concepts,declared_edges=request.prerequisite_edges)


def _objective_coverage(pedagogy, script, visual):
    result=[]
    for objective in pedagogy.learning_objectives:
        oid=objective.objective_id
        ids=tuple(s.segment_id for s in script.segments if oid in s.objective_ids)
        beats=tuple(b.beat_id for b in visual.beats if b.script_segment_ref in ids)
        probes=tuple(p.probe_id for p in pedagogy.assessment_probes if oid in p.objective_ids)
        if not ids or not beats or not probes:
            _fail("OBJECTIVE_WITHOUT_SEGMENT_BEAT_OR_ASSESSMENT")
        result.append(ObjectiveCoverage(objective_id=oid,segment_ids=ids,
                                        beat_ids=beats,assessment_probe_ids=probes))
    return tuple(result)


def _misconceptions(pedagogy, script, visual, request):
    refmap={b.misconception_id:b.correction_beat_id for b in request.misconception_bindings}
    if set(refmap) != {x.misconception_id for x in pedagogy.misconceptions}:
        _fail("MISCONCEPTION_BINDINGS_INCOMPLETE")
    beats={x.beat_id:x for x in visual.beats}
    segments={x.segment_id:x for x in script.segments}
    result=[]
    for misconception in pedagogy.misconceptions:
        bid=refmap[misconception.misconception_id]
        beat=beats.get(bid)
        if beat is None or not set(misconception.claim_ids) <= set(beat.claim_refs):
            _fail("MISCONCEPTION_UNGROUNDED_BEAT")
        seg=segments[beat.script_segment_ref]
        # A declared correction must truly appear in the script/subtitle,
        # not only in an LLM-authored invisible planning rationale.
        source=" ".join((seg.spoken_text,seg.subtitle_text)).casefold()
        if " ".join(misconception.correction.split()).casefold() not in " ".join(source.split()):
            _fail("MISCONCEPTION_CORRECTION_MISSING_FROM_SCRIPT")
        result.append(MisconceptionCoverage(
            misconception_id=misconception.misconception_id,
            claim_ids=misconception.claim_ids,correction_beat_id=bid,
            script_segment_id=seg.segment_id,correction=misconception.correction,
        ))
    return tuple(result)


def _uniform(section_ids:tuple[str,...], caps:dict[str,int], total:int)->dict[str,int]:
    if total<len(section_ids) or total>sum(caps.values()):
        _fail("INFEASIBLE_FIXED_TOTAL_BUDGET")
    units={sid:1 for sid in section_ids}
    remaining=total-len(section_ids)
    while remaining:
        eligible=[s for s in section_ids if units[s]<caps[s]]
        if not eligible:
            _fail("INFEASIBLE_UNIFORM_BUDGET")
        sid=min(eligible,key=lambda s:(units[s],section_ids.index(s)))
        units[sid]+=1
        remaining-=1
    return units


def _prioritized(section_ids, caps, uniform, hero_sids):
    allocation=dict(uniform)
    protected=set(hero_sids)
    moved=0
    for hero in hero_sids:
        while allocation[hero]<caps[hero]:
            donors=[s for s in section_ids if s not in protected and allocation[s]>1]
            if not donors:
                break
            donor=max(donors,key=lambda s:(allocation[s],-section_ids.index(s)))
            allocation[donor]-=1
            allocation[hero]+=1
            moved+=1
    return allocation,moved


def compile_pedagogy_and_hero(*, brief:LearningBrief, research:ResearchPack,
                              evidence:EvidenceGraph, fact_report:FactVerificationReport,
                              pedagogy:PedagogyPlan, script:LessonScript,
                              visual:VisualTeachingPlan, registry:ConceptRegistry,
                              request:PedagogyPlannerRequest)->GroundedPedagogyPlan:
    sources,approved=_verified_sources(brief=brief,research=research,
       evidence=evidence,fact_report=fact_report,pedagogy=pedagogy,
       script=script,visual=visual,registry=registry)
    graph=_dag(pedagogy,request)
    coverage=_objective_coverage(pedagogy,script,visual)
    misconceptions=_misconceptions(pedagogy,script,visual,request)
    focus=defaultdict(list)
    for m in misconceptions:
        focus[m.correction_beat_id].append(m.misconception_id)
    segments={s.segment_id:s for s in script.segments}
    sections={s.section_id:s for s in visual.sections}
    section_ids=tuple(sections.keys())
    caps={sid:s.visual_complexity_budget for sid,s in sections.items()}
    uniform=_uniform(section_ids,caps,request.total_visual_units)
    candidates=[]
    for index, beat in enumerate(visual.beats):
        sec=sections[beat.section_ref]
        seg=segments[beat.script_segment_ref]
        if (not sec.hero_candidate or not beat.expected_visible_state_change or
            not beat.claim_refs or not seg.objective_ids):
            continue
        reps=tuple(r for r in sec.representation_options if r!=RepresentationType.CONCEPT_CARD)
        if not reps:
            continue
        priority=round(beat.importance*100) + (50 if focus[beat.beat_id] else 0)
        candidates.append(((-priority,index),beat,seg,reps[0],priority))
    candidates.sort(key=lambda x:x[0])
    selected=candidates[:request.hero_count_limit]
    hero_sids=tuple(dict.fromkeys(entry[1].section_ref for entry in selected))
    allocation,moved=_prioritized(section_ids,caps,uniform,hero_sids)
    status=("REBALANCED_OFFLINE" if moved else "UNIFORM_FALLBACK_NO_CAPACITY")
    hero=tuple(TeachingMoment(
        beat_id=beat.beat_id,section_id=beat.section_ref,
        objective_ids=tuple(seg.objective_ids),approved_claim_ids=beat.claim_refs,
        misconception_ids=tuple(focus[beat.beat_id]),representation=rep,
        essential_state_change=beat.expected_visible_state_change,
        priority_score=priority,allocated_section_units=allocation[beat.section_ref]
    ) for _,beat,seg,rep,priority in selected)
    def budgets(state):
        return tuple(SectionBudget(section_id=s,allocated_units=state[s],
                                   maximum_units=caps[s]) for s in section_ids)
    control=compute_content_hash({
        "sources":sources,"request":request.model_dump(mode="json"),
        "uniform_total":request.total_visual_units,
    })
    ablation=HeroAblationPair(
        control_input_sha256=control,total_visual_units=request.total_visual_units,
        uniform=budgets(uniform),prioritized=budgets(allocation),
        priority_shift_units=moved,status=status,
    )
    data=dict(
        lesson_id=visual.lesson_id,source_hashes=sources,
        source_decision_sha256=control,prerequisite_graph=graph,
        objectives=coverage,misconceptions=misconceptions,
        section_mental_models=tuple((s.section_id,s.learner_state_before,s.learner_state_after)
                                    for s in visual.sections),
        hero_moments=hero,ablation=ablation
    )
    # V2 canonical_json accepts JSON-safe structures, not nested Pydantic
    # instances inside plain dicts. Serialize the typed artifact first.
    candidate=GroundedPedagogyPlan(**data,decision_sha256="PENDING")
    digest=compute_content_hash(candidate.model_dump(mode="json",exclude={"decision_sha256"}))
    return GroundedPedagogyPlan(**data,decision_sha256=digest)


def verify_grounded_pedagogy_plan(*, candidate:GroundedPedagogyPlan, **inputs)->None:
    """Recompile from source, including budget and approvals; never trust just a hash."""
    expected=compile_pedagogy_and_hero(**inputs)
    if candidate.model_dump(mode="json")!=expected.model_dump(mode="json"):
        _fail("FORGED_STALE_OR_MUTATED_PLANNING_OUTPUT")
