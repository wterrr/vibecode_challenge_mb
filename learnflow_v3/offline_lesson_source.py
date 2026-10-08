"""Narrow project-owned offline teaching source, not a golden-render test helper.

The example is authored locally, then every derived V2/V3 object is certified
by the original binary oracle and cross-artifact semantic gate. No LLM/SDK.
Only one bounded worked-example family is intentionally supported.
"""
from __future__ import annotations

from dataclasses import dataclass

from agent_contracts.lesson import LessonScript,ScriptSegment,Storyboard,StoryboardScene
from learnflow_v2.concepts import ConceptRegistry
from learnflow_v2.concepts.schema import ConceptEntry
from learnflow_v2.scenegraph import SceneGraph
from learnflow_v2.scenegraph.schema import SceneNode

from .binary_search_trace import (
    BinarySearchTrace,make_binary_search_trace,to_binary_search_state_ledger,
    verify_binary_search_trace,
)
from .models import (
    VisualTeachingPlan,VisualPatternSpec,StateLedger,SemanticContractError,
)


@dataclass(frozen=True)
class BinaryLessonSource:
    trace:BinarySearchTrace
    plan:VisualTeachingPlan
    pattern:VisualPatternSpec
    ledger:StateLedger
    registry:ConceptRegistry
    script:LessonScript
    storyboard:Storyboard
    scenegraph:SceneGraph

    def params(self):
        return {name:getattr(self,name) for name in (
            "plan","pattern","ledger","registry","script","storyboard","scenegraph"
        )}


def build_binary_lesson_source(*,values:tuple[int,...],target:int)->BinaryLessonSource:
    """Create an authored lesson contract independent of scripts/tests/goldens."""
    trace=make_binary_search_trace(values=values,target=target,source_ref="trace:trace-01")
    verify_binary_search_trace(trace)
    registry=ConceptRegistry()
    registry.register(ConceptEntry(
        concept_id="c_alg",canonical_key="concept:algorithm",label="Algorithm"
    ))
    wording=f"Binary search for {target} in [{', '.join(map(str,values))}]"
    beats=[]
    segments=[]
    for i,step in enumerate(trace.steps):
        beat_id=f"beat-{i+1:02d}"
        segment_id=f"seg-{i+1:02d}"
        dynamic=step.phase=="COMPARE"
        beats.append({
            "beat_id":beat_id,"section_ref":"section-01",
            "script_segment_ref":segment_id,
            "claim_refs":("claim-01",),
            "concept_refs":({"concept_id":"c_alg","canonical_key":"concept:algorithm"},),
            "expected_visible_state_change":(
                f"Compare midpoint {step.mid} and update the interval" if dynamic else None
            ),
            "allowed_static_justification":(
                "Display oracle-certified terminal result" if not dynamic else None
            ),
            "importance":0.9,
        })
        segments.append(ScriptSegment(
            segment_id=segment_id,spoken_text=wording+f". {step.action.replace('_',' ').lower()}.",
            subtitle_text=wording,spoken_language="en",subtitle_language="en",
            teaching_function="DEMONSTRATE",claim_ids=("claim-01",),
            objective_ids=("objective-01",),
        ))
    script=LessonScript(
        script_id="script-01",pedagogy_plan_id="pedagogy-01",segments=tuple(segments))
    storyboard=Storyboard(
        storyboard_id="sb-01",script_id="script-01",
        scenes=(StoryboardScene(
            scene_id="scene-01",
            script_segment_ids=tuple(x.segment_id for x in segments),
            teaching_function="DEMONSTRATE",visual_intent=wording,
            concept_refs=("c_alg",),continuity_keys=("concept:algorithm",),
        ),),
    )
    graph=SceneGraph(
        scene_id="scene-01",purpose="DEMONSTRATE",
        layout_intent={"type":"PROCESS","reading_direction":"LEFT_TO_RIGHT"},
        nodes=[SceneNode(
            id="node-01",kind="TEXT",label="Algorithm",
            concept_ref="c_alg",semantic_key="concept:algorithm",
        )],
    )
    plan=VisualTeachingPlan(
        lesson_id="lesson-01",learning_objective_ids=("objective-01",),
        sections=({
            "section_id":"section-01","objective_refs":("objective-01",),
            "learner_state_before":"Unknown",
            "learner_state_after":"Understands example",
            "visual_teaching_goal":"Follow state transitions",
            "representation_options":("WORKED_EXAMPLE_BOARD",),
            "visual_complexity_budget":6,
        },),
        beats=tuple(beats),
        constraints={"language":"en","learner_level":"beginner",
                     "target_duration_minutes":3},
    )
    pattern=VisualPatternSpec(
        pattern_id="pattern-01",scene_id="scene-01",
        pattern_type="WORKED_EXAMPLE_BOARD",
        objective_refs=("objective-01",),
        source_refs=tuple(f"script:{s.segment_id}" for s in segments)+("trace:trace-01",),
        concept_refs=({"concept_id":"c_alg","canonical_key":"concept:algorithm"},),
        state_source={"kind":"VERIFIED_TRACE","ref":"trace:trace-01"},
        semantic_objects=({
            "object_id":"array-01","kind":"SEQUENCE",
            "concept":{"concept_id":"c_alg","canonical_key":"concept:algorithm"},
            "state_ref":"trace:trace-01",
        },),
        visual_constraints={"reading_order":"LEFT_TO_RIGHT"},
        renderer_requirement="STATEFUL_SEQUENCE",
    )
    ledger=to_binary_search_state_ledger(
        trace=trace,pattern=pattern,beat_refs=tuple(b.beat_id for b in plan.beats))
    return BinaryLessonSource(trace=trace,plan=plan,pattern=pattern,ledger=ledger,
                              registry=registry,script=script,
                              storyboard=storyboard,scenegraph=graph)
