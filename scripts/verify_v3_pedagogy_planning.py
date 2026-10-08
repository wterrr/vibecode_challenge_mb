#!/usr/bin/env python3
"""V3-09 offline deterministic fixture. Not an LLM-generated lesson or human study."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from agent_contracts.lesson import LessonScript, ScriptSegment
from learnflow_v2.concepts import ConceptRegistry
from learnflow_v2.concepts.schema import ConceptEntry
from learnflow_v3.models import VisualTeachingPlan
from learnflow_v3.pedagogy_planner import (
    PedagogyPlannerRequest, compile_pedagogy_and_hero, verify_grounded_pedagogy_plan,
)
from tests.hermes.test_pedagogy_agent import fixture, good_plan


def offline_demo():
    brief, research, evidence, fact_report = fixture()
    pedagogy = good_plan(brief, research, evidence)
    segments = (
        ScriptSegment(segment_id="intro",spoken_text="Wrong idea. Correct idea.",
                      subtitle_text="Correct idea.",spoken_language="en",
                      subtitle_language="en",claim_ids=("C1",),
                      objective_ids=("O1",),teaching_function="DEMONSTRATE"),
        ScriptSegment(segment_id="summary",spoken_text="The first concept connects to the second.",
                      subtitle_text="Connect the concepts.",spoken_language="en",
                      subtitle_language="en",claim_ids=("C1",),
                      objective_ids=("O2",),teaching_function="EXPLAIN"),
    )
    script=LessonScript(script_id="script.offline.v3-09",pedagogy_plan_id=pedagogy.plan_id,
                        segments=segments)
    registry=ConceptRegistry()
    registry.register(ConceptEntry(concept_id="concept-first",canonical_key="concept:first",label="First concept"))
    registry.register(ConceptEntry(concept_id="concept-second",canonical_key="concept:second",label="Second concept"))
    visual=VisualTeachingPlan(
        lesson_id="lesson-v3-09-offline",learning_objective_ids=("O1","O2"),
        prerequisite_refs=({"concept_id":"concept-first","canonical_key":"concept:first"},),
        misconception_refs=({"concept_id":"concept-first","canonical_key":"concept:first"},),
        sections=(
            {"section_id":"show","objective_refs":("O1",),
             "learner_state_before":"Mistaken idea", "learner_state_after":"Correct explanation",
             "visual_teaching_goal":"Show the verified state transition",
             "representation_options":("WORKED_EXAMPLE_BOARD",),
             "visual_complexity_budget":8,"hero_candidate":True},
            {"section_id":"reflect","objective_refs":("O2",),
             "learner_state_before":"Knows first concept",
             "learner_state_after":"Can connect the concepts",
             "visual_teaching_goal":"Consolidate the approved relationship",
             "representation_options":("PROCESS_FLOW",),
             "visual_complexity_budget":8,"hero_candidate":False},
        ),
        beats=(
            {"beat_id":"correct-idea","section_ref":"show","script_segment_ref":"intro",
             "claim_refs":("C1",),"concept_refs":({"concept_id":"concept-first",
             "canonical_key":"concept:first"},),"expected_visible_state_change":"Replace the misconception",
             "importance":0.96},
            {"beat_id":"consolidate","section_ref":"reflect","script_segment_ref":"summary",
             "claim_refs":("C1",),"concept_refs":({"concept_id":"concept-second",
             "canonical_key":"concept:second"},),
             "allowed_static_justification":"Summary reuses the relationship without new state",
             "importance":0.40},
        ),
        constraints={"language":brief.language,"learner_level":brief.learner_level,
                     "target_duration_minutes":brief.target_duration_minutes},
    )
    request=PedagogyPlannerRequest(
        prerequisite_edges=({"prerequisite_concept":"first","dependent_concept":"second"},),
        misconception_bindings=({"misconception_id":"M1",
                                 "correction_beat_id":"correct-idea"},),
        total_visual_units=10,hero_count_limit=2,
    )
    return dict(brief=brief,research=research,evidence=evidence,fact_report=fact_report,
                pedagogy=pedagogy,script=script,visual=visual,registry=registry,
                request=request)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-file",type=Path,required=True)
    a=parser.parse_args()
    sources=offline_demo()
    result=compile_pedagogy_and_hero(**sources)
    verify_grounded_pedagogy_plan(candidate=result,**sources)
    a.output_file.parent.mkdir(parents=True,exist_ok=True)
    a.output_file.write_text(json.dumps(result.model_dump(mode="json"),indent=2,
                                       ensure_ascii=False)+"\n",encoding="utf-8")
    assert result.ablation.total_visual_units==10
    assert result.ablation.priority_shift_units==3
    assert result.ablation.learning_gain=="UNMEASURED"
    print("V3_09_PEDAGOGY_HERO=PASS objectives=2 misconceptions=1 "
          "hero_moments=1 budget=10 baseline=5,5 hero=8,2 "
          "human_learning=UNMEASURED")
    print("V3_09_SOURCE_HASH="+result.source_decision_sha256)


if __name__=="__main__":
    main()
