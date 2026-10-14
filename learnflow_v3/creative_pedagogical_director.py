"""V3-62: evidence-bound prospective pedagogical direction; no model API.

Host-derived exact facts and approved claim ledger are authoritative.
A future model may suggest one of the finite visual styles; this checkpoint
does NOT evaluate real model-authored storyboards nor issue publication grants.
"""
from __future__ import annotations
from dataclasses import dataclass, replace, asdict
from fractions import Fraction
from hashlib import sha256
import json

CASES=("probability_complement_3_of_8","constant_speed_distance","water_reaction_balance")
ACTS=("QUESTION","SETUP","TRANSFORM","WITNESS","CLOSE")
STYLE=("focus_first","witness_first")
CLAIMS={
 CASES[0]:("PROB_TOTAL","PROB_PARTITION","PROB_COMPLEMENT","PROB_SUM_ONE","PROB_SUM_ONE"),
 CASES[1]:("PHY_RATE","PHY_TICKS","PHY_DISTANCE","PHY_END","PHY_END"),
 CASES[2]:("CHEM_REACTANTS","CHEM_REARRANGE","CHEM_CONSERVE","CHEM_BALANCE","CHEM_BALANCE")
}
REFERENTS={CASES[0]:"eight_outcomes",CASES[1]:"moving_marker",CASES[2]:"six_persistent_atoms"}
TITLES={CASES[0]:"What remains outside the event?",CASES[1]:"How far can a steady speed carry us?",CASES[2]:"Can molecules change without losing atoms?"}
WORDS={
 CASES[0]:(
 "There are eight equally likely outcomes. Three belong to the event. What remains?",
 "Keep the same eight outcomes in view. Three are highlighted as belonging to the event.",
 "Now separate all five remaining outcomes. Do not change or remove the total of eight.",
 "Three plus five is eight. The complement is five out of eight, and together they form one.",
 "The entire sample space remains the same. Complement means everything outside the event."),
 CASES[1]:(
 "At a constant speed of three metres each second, where will the marker be after four seconds?",
 "We start at zero. The same marker moves along one straight distance track.",
 "Move one second at a time, three metres each time. Track its position without jumping ahead.",
 "Four steps of three metres make twelve metres. Each step preserves the speed.",
 "Distance equals speed multiplied by elapsed time, under this constant speed assumption."),
 CASES[2]:(
 "Two hydrogen molecules and one oxygen molecule can form how many water molecules?",
 "Count the atoms first. We have four hydrogen atoms and two oxygen atoms, with stable identities.",
 "Rearrange those six same atoms into two groups. This is an inventory diagram, not a reaction mechanism.",
 "The two groups each contain two hydrogen atoms and one oxygen atom. None has vanished.",
 "The balanced equation is two H two plus O two gives two H two O. Atom counts match."))}
HIGHLIGHTS={
 CASES[0]:("one sample space","3 highlighted outcomes","5 others emerge","3/8 + 5/8 = 1","complement"),
 CASES[1]:("3 m per second","start 0 m","four equal jumps","4 x 3 = 12 m","constant speed"),
 CASES[2]:("2 H2 and O2","4 H + 2 O","rearrange six atoms","2 x H2O","atom inventory")
}
LAYOUTS={CASES[0]:"PARTITION_GRID",CASES[1]:"DISTANCE_TRACK",CASES[2]:"ATOM_INVENTORY"}
SCHEMA="v3-62-pedagogical-director-v1"
ORIGIN="HOST_AUTHORED_DETERMINISTIC_NOT_LLM"
class Blocked(ValueError):
    pass

def fail(code):
    raise Blocked("V362_"+code)

def digest(o):
    return sha256(json.dumps(o,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()

def exact_facts(case_id):
    if case_id==CASES[0]:
        a,b=Fraction(3,8),Fraction(5,8)
        assert a+b==1
        return {"total":8,"selected":3,"remaining":5,"selected_fraction":"3/8",
                "remaining_fraction":str(b),"sum":"1"}
    if case_id==CASES[1]:
        velocity=3;seconds=4
        return {"velocity_m_per_s":velocity,"elapsed_s":seconds,
                "positions_m":[velocity*i for i in range(seconds+1)],
                "final_distance_m":velocity*seconds}
    if case_id==CASES[2]:
        reactants={"H":2*2,"O":1*2}
        product={"H":2*2,"O":2}
        assert reactants==product
        return {"reactants":"2 H2 + O2","products":"2 H2O",
                "reactant_atoms":reactants,"product_atoms":product,
                "conserved":True,"reaction_kinetics":"NOT_CLAIMED"}
    fail("UNSUPPORTED_HELDOUT_FAMILY")

@dataclass(frozen=True)
class DirectedAct:
    act:str
    claim_id:str
    referent_id:str
    narration:str
    highlight:str
    witness_kind:str

@dataclass(frozen=True)
class DirectedStory:
    version:str
    origin:str
    case_id:str
    evidence_sha256:str
    layout:str
    visual_style:str
    acts:tuple[DirectedAct,...]
    publication_allowed:bool=False
    word_level_alignment:str="UNMEASURED"

def candidate(case_id, style="focus_first"):
    facts=exact_facts(case_id)
    if style not in STYLE:fail("STYLE_NOT_SUPPORTED")
    acts=tuple(DirectedAct(act=act,claim_id=CLAIMS[case_id][i],
       referent_id=REFERENTS[case_id],narration=WORDS[case_id][i],
       highlight=HIGHLIGHTS[case_id][i],witness_kind=(
       "QUESTION_HOLD" if i==0 else "STATIC_PRECONDITION" if i==1
       else "CERTIFIED_TRANSFORMATION" if i==2 else
       "EXACT_INVARIANT" if i==3 else "CLOSURE"))
       for i,act in enumerate(ACTS))
    plan=DirectedStory(SCHEMA,ORIGIN,case_id,digest(facts),
                       LAYOUTS[case_id],style,acts)
    validate(plan)
    return plan

def validate(story:DirectedStory):
    if not isinstance(story,DirectedStory):
        fail("DIRECTOR_TYPED_PLAN_REQUIRED")
    if story.case_id not in CASES:
        fail("OUTSIDE_REGISTERED_HELDOUT")
    if story.version!=SCHEMA or story.origin!=ORIGIN:
        fail("UNTRUSTED_AUTHORSHIP")
    if story.visual_style not in STYLE or story.layout!=LAYOUTS[story.case_id]:
        fail("UNSUPPORTED_LAYOUT_OR_STYLE")
    if story.publication_allowed is not False or story.word_level_alignment!="UNMEASURED":
        fail("UNSUPPORTED_RELEASE_OR_WORD_ALIGNMENT")
    facts=exact_facts(story.case_id)
    if story.evidence_sha256!=digest(facts):
        fail("FROZEN_LEDGER_DRIFT")
    reference=candidate_canonical_acts(story.case_id)
    if len(story.acts)!=5 or tuple(story.acts)!=reference:
        fail("CLAIM_REFERENT_OPERATION_NARRATION_OR_DEPENDENCY_DRIFT")
    return facts

def candidate_canonical_acts(case_id):
    return tuple(DirectedAct(act=act,claim_id=CLAIMS[case_id][i],
       referent_id=REFERENTS[case_id],narration=WORDS[case_id][i],
       highlight=HIGHLIGHTS[case_id][i],witness_kind=(
       "QUESTION_HOLD" if i==0 else "STATIC_PRECONDITION" if i==1
       else "CERTIFIED_TRANSFORMATION" if i==2 else
       "EXACT_INVARIANT" if i==3 else "CLOSURE"))
       for i,act in enumerate(ACTS))

def proposed_visual_choice(raw:dict):
    """Narrow model-facing prospective adapter, NOT proof a model can invent a lesson."""
    if type(raw) is not dict or set(raw)!={"case_id","visual_style","evidence_sha256"}:
        fail("UNTRUSTED_PROPOSAL_FIELDS")
    if any(type(v) is not str for v in raw.values()):
        fail("UNTRUSTED_PROPOSAL_VALUES")
    case=raw["case_id"]
    expected=digest(exact_facts(case))
    if raw["evidence_sha256"]!=expected:
        fail("PROPOSAL_EVIDENCE_FORGED")
    return candidate(case,raw["visual_style"])

def witness(story:DirectedStory, act:int, progress:float):
    facts=validate(story)
    if not isinstance(act,int) or act not in range(5) or type(progress) not in (float,int) or not 0<=progress<=1:
        fail("INVALID_TEMPORAL_QUERY")
    # The result is legally available only after the complete transform.
    arrived=(act>=3)
    if story.case_id==CASES[0]:
        return {"count_total":8,"event_selected":3,
                "remaining_identified":5 if arrived else 0,
                "complement_label_visible":arrived,
                "conserved_count":True}
    if story.case_id==CASES[1]:
        pos=0 if act<2 else round(facts["final_distance_m"]*progress,5) if act==2 else 12
        return {"position_m":pos,"speed_m_per_s":3,
                "final_12_label_visible":arrived,
                "marker_identity":"moving_marker"}
    return {"atoms_H":4,"atoms_O":2,"atom_identities":(
        "H0","H1","H2","H3","O0","O1"),
        "balanced_equation_visible":arrived,
        "chemical_mechanism":"NOT_CLAIMED"}

def receipt(story:DirectedStory):
    validate(story)
    return {"case_id":story.case_id,"frozen_facts_sha":story.evidence_sha256,
       "layout":story.layout,"visual_style":story.visual_style,
       "story_act_sequence":list(ACTS),
       "claim_ids":list(CLAIMS[story.case_id]),
       "persistent_referent":REFERENTS[story.case_id],
       "precondition_before_result":not witness(story,2,.99).get("complement_label_visible",
          witness(story,2,.99).get("final_12_label_visible",
          witness(story,2,.99).get("balanced_equation_visible"))),
       "result_after_transformation":witness(story,3,0).get("complement_label_visible",
          witness(story,3,0).get("final_12_label_visible",
          witness(story,3,0).get("balanced_equation_visible"))),
       "model_creativity":"NOT_TESTED","native_word_alignment":"UNMEASURED",
       "human_quality":"UNRATED","learner_effect":"NOT_MEASURED",
       "production":"BLOCKED"}
