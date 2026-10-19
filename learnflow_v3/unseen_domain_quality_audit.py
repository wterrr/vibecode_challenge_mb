"""V3-33: preregistered unseen-domain generalization/educational-quality audit.

NO auto content generation: the six new topics are out of exact source-to-topic
certified semantic contracts. Reuse existing math/physics adapters as *controls*,
outside the six-topic denominator. Fail closed on missing representation and
source evidence. Only accepted outputs are real decoded technical media;
quality is separately assessed, never inherited from technical PASS.
"""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
from typing import Literal
from pydantic import Field, model_validator
from learnflow_v3.models import V3Model
from learnflow_v3.multidomain_coverage import ORDER, SOURCE, FROZEN, SELECTION
from learnflow_v3.source_grounded_compiler import SEED_FILE, run as run_v328

VERSION="v3-33-unseen-six-domain-generalization-audit-v1"
MANIFEST="benchmarks/learnflowbench/v3/v3_33_locked_unseen_topics.json"
FORBIDDEN={"lfb-005-cs","lfb-002-cs"}
DOMAIN_NAMES={"math":"Mathematics","physics":"Physics","chemistry":"Chemistry",
              "biology":"Biology","cs":"Computer Science","history_general":"History"}
QUALITY_DIMENSIONS={
    "factual_correctness":"Claims independently verified beyond locator/anchor?",
    "conceptual_clarity":"Beginner understands the target concept after viewing?",
    "explanatory_completeness":"Worked causal steps and knowledge check fully explained?",
    "cognitive_load":"Information pacing/amount suitable for beginner?",
    "visual_hierarchy":"Code/equations/illustrations readable and distinct?",
    "pacing":"Measured scene duration suitable for comprehension?",
    "narration_visual_alignment":"Visible event aligns with measured audio?",
    "visual_creativity":"Motion carries teaching meaning beyond highlight/cards?",
}


def _require(ok:bool,code:str)->None:
    if not ok:raise ValueError("V3_33_"+code)


class CoverageRow(V3Model):
    domain:Literal["math","physics","chemistry","biology","cs","history_general"]
    topic_id:str
    query_sha256:str=Field(min_length=64,max_length=64)
    status:Literal["ABSTAIN_UNSUPPORTED_BOUND_SOURCE_AND_LESSON_SEMANTICS"]
    certified_source_for_exact_topic:Literal[False]
    contract_supported:Literal[False]
    worked_example_verified:Literal[False]
    real_script_and_objective_linked:Literal[False]
    semantic_event_to_renderer_verified:Literal[False]
    reused_family_candidate:str
    renderer:None=None  # Unsupported rows CANNOT claim any renderer, including cards.
    video_sha256:None=None
    concept_card_fallback:Literal[False]
    reason_code:str
    generalization_full_e2e:Literal[False]


class EducationalDimension(V3Model):
    name:str
    question:str
    method:Literal["BLINDED_HUMAN_WITH_EXPERT_RUBRIC","INDEPENDENT_SEMANTIC_EXPERT",
                   "MEASURED_PIXEL_AUDIO_WITH_HUMAN_REVIEW"]
    status:Literal["NOT_ASSESSED"]
    score:None=None
    assessor_count:Literal[0]
    evidence_reference:str|None=None


class EducationalGate(V3Model):
    version:Literal["v3-33-educational-quality-separate-gate-v1"]
    dimensions:tuple[EducationalDimension,...]=Field(min_length=8,max_length=8)
    technical_engineering_status:Literal["CONTROL_MEDIA_ONLY"]
    educational_quality_status:Literal["NOT_ASSESSED_NO_INDEPENDENT_REVIEWERS"]
    production:Literal["BLOCKED"]
    score:None=None
    @model_validator(mode="after")
    def gate(self):
        _require(tuple(d.name for d in self.dimensions)==tuple(QUALITY_DIMENSIONS),
                 "QUALITY_RUBRIC_INCOMPLETE")
        return self


def selected_topics(root:Path)->tuple[list[dict],dict]:
    corpus_bytes=(root/SOURCE).read_bytes()
    corpus=json.loads(corpus_bytes)
    frozen=json.loads((root/FROZEN).read_text())
    prior=json.loads((root/SELECTION).read_text())
    selected=json.loads((root/MANIFEST).read_text())
    _require(corpus["frozen"] is True and len(corpus["topics"])==100,
             "CORPUS_NOT_FROZEN")
    _require(selected["selections_frozen_before_implementation"] is True
             and selected["allow_substitution"] is False,
             "SELECTION_NOT_PRECOMMITTED")
    _require(tuple(selected["domains"])==("math","physics","chemistry",
              "biology","cs","history_general") and len(selected["cases"])==6,
              "SIX_DOMAIN_DENOMINATOR_CHANGED")
    _require(selected["selection_rule"].startswith("For each ORDER domain,"),
             "SELECTION_RULE_CHANGED")
    # Completely separate from V3-27 six development topics as well as 12
    # frozen V3-16 confirmatory and its diagnostic/excluded set.
    exclusions=(set(frozen["sampling"]["topic_ids"]) |
                set(frozen["sampling"]["excluded_diagnostic_ids"]) |
                {x["topic_id"] for x in prior["cases"]} | FORBIDDEN)
    _require(not any(x["topic_id"] in exclusions for x in selected["cases"]),
             "TOPIC_LEAKAGE")
    actual=[];taken=set()
    for domain,manifest_row in zip(selected["domains"],selected["cases"],strict=True):
        eligible=sorted((t for t in corpus["topics"]
            if t["domain"]==domain and t["topic_id"] not in exclusions),
            key=lambda t:t["topic_id"])
        _require(bool(eligible),"NO_AVAILABLE_NEW_TOPICS")
        picked=eligible[0]
        _require(manifest_row["domain"]==domain
                 and manifest_row["topic_id"]==picked["topic_id"]
                 and manifest_row["query"]==picked["query"],
                 "SELECTION_RULE_OR_TOPIC_DRIFT")
        digest=sha256(picked["query"].encode("utf-8")).hexdigest()
        _require(manifest_row["query_sha256"]==digest,
                 "INPUT_QUERY_SHA_MISMATCH")
        _require(picked["topic_id"] not in taken,"DUPLICATE_SELECTED_TOPIC")
        taken.add(picked["topic_id"])
        actual.append({**picked,"query_sha256":digest})
    _require(len(actual)==6,"INCOMPLETE_SIX_DOMAIN_SAMPLE")
    return actual,{
       "selection_manifest_sha256":sha256((root/MANIFEST).read_bytes()).hexdigest(),
       "corpus_sha256":sha256(corpus_bytes).hexdigest(),
       "prior_v327_topic_ids":sorted(x["topic_id"] for x in prior["cases"]),
       "v316_frozen_topic_count":len(frozen["sampling"]["topic_ids"]),
       "selection_rule":selected["selection_rule"]}


def current_source_supported_topic_ids(root:Path)->dict[str,str]:
    """Observed EXACT certified compiler inputs, never genre-only guesses."""
    seeds=json.loads((root/SEED_FILE).read_text())
    _require(seeds["status"]=="AUTHOR_SEEDED_NOT_AUTONOMOUS_RESEARCH",
             "SEED_PROVENANCE_FORGED")
    return {s["topic_id"]:s["model_kind"] for s in seeds["cases"]} | {
        "lfb-002-cs":"V3_32_HOST_CERTIFIED_FUNCTION_EXAMPLE_ONLY"}


def family_candidate(domain:str)->str:
    return {
       "math":"MATH_FUNCTION_GRAPH_ONLY_CERTIFIED_LINEAR",
       "physics":"PHYSICS_VELOCITY_TIME_ONLY_CERTIFIED_LINEAR",
       "chemistry":"NO_CERTIFIED_MOLECULAR_OBJECT_MODEL",
       "biology":"PROCESS_OR_STATE_MACHINES_NO_BIOLOGICAL_FACT_BINDING",
       "cs":"CODE_WALKTHROUGH_ASSIGNMENT_ONLY;FUNCTION_CONTRACT_PINNED_OTHER_TOPIC",
       "history_general":"PROCESS_FLOW_NO_CITED_CAUSAL_CHRONOLOGY",
    }[domain]


def audit_six(root:Path)->dict:
    topics,provenance=selected_topics(root)
    certified=current_source_supported_topic_ids(root)
    rows=[]
    for t in topics:
        _require(t["topic_id"] not in certified,
                 "SELECTED_TOPIC_ALREADY_CERTIFIED_REAUDIT_NEEDED")
        rows.append(CoverageRow(
            domain=t["domain"],topic_id=t["topic_id"],
            query_sha256=t["query_sha256"],
            status="ABSTAIN_UNSUPPORTED_BOUND_SOURCE_AND_LESSON_SEMANTICS",
            certified_source_for_exact_topic=False,contract_supported=False,
            worked_example_verified=False,real_script_and_objective_linked=False,
            semantic_event_to_renderer_verified=False,
            reused_family_candidate=family_candidate(t["domain"]),
            renderer=None,video_sha256=None,concept_card_fallback=False,
            reason_code="NO_SOURCE_CLAIM_AND_WORKED_EXAMPLE_CONTRACT_FOR_EXACT_TOPIC",
            generalization_full_e2e=False).model_dump())
    _require(len(rows)==6 and not any(r["renderer"] or r["video_sha256"] for r in rows),
             "UNAUTHORIZED_MEDIA_ON_UNSUPPORTED_TOPICS")
    return {"checkpoint":"V3-33","version":VERSION,**provenance,
      "denominator":6,"rows":rows,"full_generalization_pass":0,
      "partial_new_topic_media_pass":0,"abstain":6,"unregistered_substitution":0,
      "original_six_domain_v327_media_not_counted_in_new_denominator":True,
      "no_concept_card_fallback":True,"model_api_calls":0,
      "scientific_quality":"NOT_RATED","production":"BLOCKED"}


def make_quality_gate()->EducationalGate:
    methods={
       "factual_correctness":"INDEPENDENT_SEMANTIC_EXPERT",
       "conceptual_clarity":"BLINDED_HUMAN_WITH_EXPERT_RUBRIC",
       "explanatory_completeness":"BLINDED_HUMAN_WITH_EXPERT_RUBRIC",
       "cognitive_load":"BLINDED_HUMAN_WITH_EXPERT_RUBRIC",
       "visual_hierarchy":"MEASURED_PIXEL_AUDIO_WITH_HUMAN_REVIEW",
       "pacing":"MEASURED_PIXEL_AUDIO_WITH_HUMAN_REVIEW",
       "narration_visual_alignment":"MEASURED_PIXEL_AUDIO_WITH_HUMAN_REVIEW",
       "visual_creativity":"BLINDED_HUMAN_WITH_EXPERT_RUBRIC",
    }
    return EducationalGate(version="v3-33-educational-quality-separate-gate-v1",
        dimensions=tuple(EducationalDimension(name=name,question=question,
            method=methods[name],status="NOT_ASSESSED",score=None,assessor_count=0)
            for name,question in QUALITY_DIMENSIONS.items()),
        technical_engineering_status="CONTROL_MEDIA_ONLY",
        educational_quality_status="NOT_ASSESSED_NO_INDEPENDENT_REVIEWERS",
        production="BLOCKED",score=None)


def quality_inventory(root:Path, controls:dict, report:dict)->dict:
    """No numerical pedagogy score without human assessments."""
    dims=make_quality_gate()
    results=[]
    for case in controls["six_attempt_ledger"]:
        if case["status"]!="OFFLINE_SOURCE_CONTRACT_COMPILER_AND_REAL_AV_PASS":
            continue
        folder=root/case["topic_id"]
        evidence=json.loads((folder/"compiled_linear_lesson_evidence.json").read_text())
        decoder={
            "video_sha256":evidence["video_sha256"],
            "beat_count":len(evidence["beats"]),
            "codec_verified":evidence["real_h264_aac"],
            "max_decoded_source_mae":evidence["max_decoded_mae"],
            "min_audio_rms":min(evidence["aac_rms_per_spoken_beat"]),
            "measured_pacing_seconds":evidence["frames"]/evidence["fps"],
        }
        _require(decoder["video_sha256"]==case["video_sha256"] and
                 decoder["codec_verified"] is True and decoder["min_audio_rms"]>.003,
                 "CONTROL_MEDIA_EVIDENCE_CONTRADICTS_COMPILER")
        results.append({"topic_id":case["topic_id"],"role":"PRIOR_EXPOSED_POSITIVE_CONTROL_ONLY",
            "technical":decoder,"educational":dims.model_dump(),
            "human_preference_score":None})
    _require(len(results)==2,"CONTROL_COUNT")
    return {"checkpoint":"V3-33","controls":results,
            "test_set_denominator":report["denominator"],
            "controls_in_unseen_denominator":0,
            "educational_quality":dims.model_dump(),
            "v331_v332_independent_human_quality_review":"NOT_PERFORMED",
            "any_unseen_domain_video_quality_score":None,
            "full_six_domain_human_quality":"NO_GO",
            "production":"BLOCKED"}


def run(root:Path,out:Path)->dict:
    _require(out.is_dir() and not out.is_symlink() and not any(out.iterdir()),
             "OUTPUT_MUST_BE_EMPTY")
    report=audit_six(root)
    selection=out/"selection_and_coverage.json"
    selection.write_text(json.dumps(report,indent=2)+"\n")
    controls_dir=out/"prior_exposed_controls";controls_dir.mkdir()
    controls=run_v328(root,controls_dir)
    _require(controls["bounded_compiler_video_pass_count"]==2 and
             controls["autonomous_research_script_director_end_to_end_count"]==0,
             "CONTROL_BASELINE_CHANGED")
    educational=quality_inventory(controls_dir,controls,report)
    (out/"quality_gate.json").write_text(json.dumps(educational,indent=2)+"\n")
    lines=["# V3-33 unseen-topic coverage (NO substitutions)",
           "","| Domain | Topic ID | Certified factual source | Semantic contract | AV on NEW topic | Verdict |",
           "|---|---|---|---|---|---|"]
    for r in report["rows"]:
        lines.append(f"| {DOMAIN_NAMES[r['domain']]} | {r['topic_id']} | NO | NO | NONE | ABSTAIN |")
    lines+=["",f"**Unseen topics: 0/{report['denominator']} full E2E; "
                 f"{report['abstain']}/{report['denominator']} ABSTAIN.**",
            "The two math/physics videos in prior_exposed_controls/ are OUTSIDE this denominator.",
            "Technical pixels and AAC do not establish learner comprehension or creativity.",
            "No unsupported family was replaced with a CONCEPT_CARD.",""]
    (out/"coverage_matrix.md").write_text("\n".join(lines))
    all_results={"unseen":report,"controls":controls,"educational":educational,
          "production":"BLOCKED","all_six_autonomous_full_stack":"NO_GO",
          "provider_requests":0}
    (out/"v3_33_audit_receipt.json").write_text(json.dumps(all_results,indent=2)+"\n")
    print("V3_33_UNSEEN=0/6_FULLE2E 6/6_ABSTAIN",flush=True)
    print("V3_33_CONTROLS=2_REAL_MATH_PHYSICS_MP4_NOT_UNSEEN",flush=True)
    print("V3_33_EDUCATIONAL=NOT_ASSESSED production=BLOCKED provider_requests=0",flush=True)
    return all_results
