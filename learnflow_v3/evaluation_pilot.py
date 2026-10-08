"""V3-16 locked paired pilot / ablation protocol and strictly synthetic rehearsal.

Reuses V3-01 immutable 12-topic protocol, LearnFlowBench corpus/hashes, V2
content hashing. This module has no model/video-generation, human recruitment,
participant-data transfer or publication side effects. The public rater packet
never contains the identity mapping; execution remains unauthorized.
"""
from __future__ import annotations

import hashlib
import math
import random
import statistics
from enum import Enum
from typing import Literal

from pydantic import Field, model_validator

from learnflow_bench import corpus_sha256, load_corpus
from learnflow_v2.repair import compute_content_hash
from .models import V3Model, SemanticContractError

VERSION="v3-16-blinded-pilot-manifest-v1"
PRIMARY=("clarity","representation_adequacy")
SECONDARY=("pedagogy_sequence","subtitle_readability","cognitive_load")
RUBRIC=PRIMARY+SECONDARY
ARMS=("v2d_frozen","v3_candidate")
N=12
BOOTSTRAP=10000
ABLATIONS={
    "E1":"FROZEN_V2_VS_SEMANTIC_GUARDS_ONLY",
    "E2":"SAME_SCRIPT_AUDIO_EVIDENCE_SEED_DIFFERENT_PATTERN",
    "E3":"SAME_RENDERER_AND_CONTENT_BUDGET_PEDAGOGY_PLAN_ONLY",
    "E4":"SAME_TOTAL_RENDER_TIME_UNIFORM_VS_HERO",
    "E5":"SAME_CONTENT_UNGROUNDED_VS_GROUNDED_MOTION_CUES",
    "E6":"SAME_SCENE_STATIC_VS_KEYFRAME_AWARE_LAYOUT",
    "E7":"SAME_ALGORITHM_PROBLEM_FREEFORM_VS_CERTIFIED_TRACE",
    "E8":"SAME_INJECTED_DEFECT_FULL_REGENERATE_VS_LOCAL_REPAIR",
    "E9":"SAME_ARTIFACT_DETERMINISTIC_QA_VS_QA_PLUS_CRITIC",
    "E10":"MATCHED_TOPIC_SPECIALIZED_VS_LEGAL_HUMAN_REFERENCE",
}


def _reject(s):
    raise SemanticContractError("V3_16_"+s)


def _model_hash(item):
    return compute_content_hash(item.model_dump(mode="json"))


class BlindSlot(V3Model):
    topic_id:str
    topic_query_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    domain:Literal["cs","math","physics","biology","chemistry","history_general"]
    difficulty:Literal["easy","medium","hard"]
    anonymous_slots:Literal[("A","B")]=("A","B")
    video_a:Literal[None]=None
    video_b:Literal[None]=None
    rater_instructions:Literal["ASSIGN_BLIND_DOMAIN_COMPETENT_INDEPENDENT_RATERS"]="ASSIGN_BLIND_DOMAIN_COMPETENT_INDEPENDENT_RATERS"


class AblationRow(V3Model):
    ablation_id:Literal["E1","E2","E3","E4","E5","E6","E7","E8","E9","E10"]
    controlled_contrast:str
    status:Literal["NOT_RUN"]="NOT_RUN"
    samples:Literal[0]=0
    effect_size:Literal[None]=None
    user_authorized:Literal[False]=False

    @model_validator(mode="after")
    def _strict(self):
        if self.controlled_contrast!=ABLATIONS[self.ablation_id]:
            raise ValueError("V3_16_UNREGISTERED_ABLATION_CONTRAST")
        return self


class PilotManifest(V3Model):
    version:Literal["v3-16-blinded-pilot-manifest-v1"]=VERSION
    prereg_protocol_id:Literal["learnflow-v3-01-tier1-20261008"]="learnflow-v3-01-tier1-20261008"
    frozen_protocol_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    frozen_corpus_sha256:Literal["4f0e0fc81dee7580df93a1d912b9485de7e5eb1c9fdda699576b48729bf4ab8f"]="4f0e0fc81dee7580df93a1d912b9485de7e5eb1c9fdda699576b48729bf4ab8f"
    status:Literal["DESIGN_READY_UNEXECUTED"]="DESIGN_READY_UNEXECUTED"
    topic_slots:tuple[BlindSlot,...]=Field(min_length=N,max_length=N)
    ablation_plan:tuple[AblationRow,...]=Field(min_length=10,max_length=10)
    subject_count:Literal[0]=0
    evaluated_pair_count:Literal[0]=0
    v2_videos:Literal[0]=0
    v3_videos:Literal[0]=0
    human_scores_state:Literal["UNMEASURED"]="UNMEASURED"
    paired_quality_effect_state:Literal["UNMEASURED"]="UNMEASURED"
    rater_agreement_state:Literal["UNMEASURED"]="UNMEASURED"
    study_permissions:Literal["NOT_AUTHORIZED"]="NOT_AUTHORIZED"
    model_provider_calls:Literal[0]=0
    paid_api_authorized:Literal[False]=False
    publish_authorized:Literal[False]=False
    mapping_in_public_artifact:Literal[False]=False
    manifest_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _integrity(self):
        from scripts.verify_v3_benchmark_protocol import TOPIC_IDS
        if tuple(s.topic_id for s in self.topic_slots)!=TOPIC_IDS:
            raise ValueError("V3_16_SELECTED_TOPICS_CHANGED")
        if tuple(a.ablation_id for a in self.ablation_plan)!=tuple(ABLATIONS):
            raise ValueError("V3_16_ABLATION_OMISSION")
        if self.manifest_sha256!=compute_content_hash(
            self.model_dump(mode="json",exclude={"manifest_sha256"})
        ):
            raise ValueError("V3_16_MANIFEST_SHA_TAMPER")
        return self


def private_assignment(protocol:dict,topic_id:str)->dict[str,str]:
    """Private in-memory only; NEVER serialize with public rater packet.

    Existing frozen rule is deterministic and is not cryptographic blinding:
    rater recruitment materials must not reveal repo/protocol/seed or identity.
    """
    from scripts.verify_v3_benchmark_protocol import TOPIC_IDS
    if topic_id not in TOPIC_IDS:_reject("TOPIC_NOT_PREREGISTERED")
    seed=protocol["sampling"]["seed"]
    token=f"{seed}|presentation|{topic_id}"
    first="v2d_frozen" if int(hashlib.sha256(token.encode()).hexdigest(),16)%2==0 else "v3_candidate"
    return {"A":first,"B":next(a for a in ARMS if a!=first)}


def build_manifest(protocol:dict)->PilotManifest:
    from scripts.verify_v3_benchmark_protocol import TOPIC_IDS,SOURCE_SHA256,validate
    validate(protocol)    # verifies untouched source, exact IDs and all authorizations
    if corpus_sha256()!=SOURCE_SHA256:_reject("CORPUS_CHANGED")
    topics={t.topic_id:t for t in load_corpus().topics}
    public=[]
    for topic_id in TOPIC_IDS:
        t=topics[topic_id]
        public.append(BlindSlot(
            topic_id=topic_id,domain=t.domain.value,difficulty=t.difficulty.value,
            topic_query_sha256=compute_content_hash({"topic_id":topic_id,"query":t.query}),
        ).model_dump(mode="json"))
    values=dict(
        frozen_protocol_sha256=compute_content_hash(protocol),
        topic_slots=public,
        ablation_plan=[AblationRow(ablation_id=k,controlled_contrast=v).model_dump(mode="json")
                       for k,v in ABLATIONS.items()],
    )
    # defaults from PilotManifest must also be included in manifest fingerprint.
    provisional=PilotManifest.model_construct(**values)
    full=provisional.model_dump(mode="json",exclude={"manifest_sha256"})
    values=full|{"manifest_sha256":compute_content_hash(full)}
    return PilotManifest.model_validate(values)


class GenerationAttempt(V3Model):
    topic_id:str
    system:Literal["v2d_frozen","v3_candidate"]
    attempt_id:str=Field(min_length=1,max_length=100)
    state:Literal["NOT_RUN","FAILED","VALID_VIDEO"]
    failure_code:str|None=None
    real_video_sha256:str|None=None
    actual_usd_cost:float|None=None
    wall_seconds:float|None=None
    provider_roundtrips:int|None=Field(default=None,ge=0)
    provenance:Literal["AUTHOR_SEEDED_SYNTHETIC","UNEXECUTED"]="UNEXECUTED"
    human_trial:Literal[False]=False

    @model_validator(mode="after")
    def _consistent(self):
        if self.state=="NOT_RUN":
            if any(x is not None for x in (
                self.failure_code,self.real_video_sha256,self.actual_usd_cost,
                self.wall_seconds,self.provider_roundtrips,
            )) or self.provenance!="UNEXECUTED":
                raise ValueError("V3_16_UNRUN_CANNOT_HAVE_OBSERVATIONS")
        else:
            if self.provenance!="AUTHOR_SEEDED_SYNTHETIC":
                raise ValueError("V3_16_REAL_EXECUTION_NOT_AUTHORIZED")
            if self.state=="FAILED" and (
                not self.failure_code or self.real_video_sha256 is not None):
                raise ValueError("V3_16_FAILED_ATTEMPT_MUST_HAVE_REASON_NO_MP4")
            if self.state=="VALID_VIDEO" and (
                self.failure_code is not None or self.real_video_sha256 is None or
                len(self.real_video_sha256)!=64
            ):
                raise ValueError("V3_16_VALID_VIDEO_REQUIRES_SOURCE_HASH")
        if self.actual_usd_cost is not None and (
            not math.isfinite(self.actual_usd_cost) or self.actual_usd_cost<0):
            raise ValueError("V3_16_INVALID_COST")
        if self.wall_seconds is not None and (
            not math.isfinite(self.wall_seconds) or self.wall_seconds<0):
            raise ValueError("V3_16_INVALID_WALL_TIME")
        return self


class BlindedRating(V3Model):
    topic_id:str
    slot:Literal["A","B"]
    rater_id:str=Field(min_length=3,max_length=40,pattern=r"^[a-z][a-z0-9_-]+$")
    ratings:dict[str,int]=Field(min_length=5,max_length=5)
    evidence_note:str=Field(min_length=5,max_length=250)
    origin:Literal["AUTHOR_SEEDED_SYNTHETIC"]="AUTHOR_SEEDED_SYNTHETIC"
    system_identity_disclosed:Literal[False]=False

    @model_validator(mode="after")
    def _valid(self):
        if tuple(sorted(self.ratings))!=tuple(sorted(RUBRIC)):
            raise ValueError("V3_16_INCOMPLETE_RUBRIC")
        if any(type(v) is not int or not 1<=v<=5 for v in self.ratings.values()):
            raise ValueError("V3_16_SCORE_NOT_ORDINAL_1_TO_5")
        return self


class TopicPairResult(V3Model):
    topic_id:str
    domain:str
    difficulty:str
    v2_scores:dict[str,float]
    v3_scores:dict[str,float]
    delta:dict[str,float]
    failed_systems:tuple[str,...]
    score_origin:Literal["AUTHOR_SEEDED_SYNTHETIC"]="AUTHOR_SEEDED_SYNTHETIC"


class PrimaryEffect(V3Model):
    metric:Literal["clarity","representation_adequacy"]
    mean_paired_delta:float
    wins:int=Field(ge=0,le=N)
    ties:int=Field(ge=0,le=N)
    ci_low:float
    ci_high:float
    bootstrap_resamples:Literal[10000]=BOOTSTRAP
    threshold_mean_reached:bool
    threshold_wins_reached:bool


class SyntheticRehearsal(V3Model):
    version:Literal["v3-16-blinded-pilot-manifest-v1"]=VERSION
    status:Literal["AUTHOR_SEEDED_REHEARSAL_ONLY_NOT_HUMAN_EVIDENCE"]="AUTHOR_SEEDED_REHEARSAL_ONLY_NOT_HUMAN_EVIDENCE"
    denominator:Literal[12]=12
    attempts_included:Literal[24]=24
    topic_pairs:tuple[TopicPairResult,...]=Field(min_length=N,max_length=N)
    co_primary_effects:tuple[PrimaryEffect,...]=Field(min_length=2,max_length=2)
    failed_attempts:int=Field(ge=0,le=24)
    complete_valid_mp4_count:int=Field(ge=0,le=24)
    provider_cost_total_usd:float|None
    wall_seconds_total:float|None
    mean_absolute_rater_disagreement:float|None
    critical_safety_errors:Literal[0]=0
    independent_human_data:Literal[False]=False
    actual_human_quality_effect:Literal["UNMEASURED"]="UNMEASURED"
    real_pilot_pass:Literal[False]=False
    publication_blocked:Literal[True]=True
    result_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _check(self):
        if tuple(x.metric for x in self.co_primary_effects)!=PRIMARY:
            raise ValueError("V3_16_PRIMARY_ENDPOINTS_CHANGED")
        if self.result_sha256!=compute_content_hash(
            self.model_dump(mode="json",exclude={"result_sha256"})
        ):
            raise ValueError("V3_16_FORGED_ANALYSIS")
        return self


def _score_system(attempt:GenerationAttempt,ratings:list[BlindedRating]):
    if attempt.state=="NOT_RUN":
        _reject("DO_NOT_SCORE_UNRUN_AS_FAILURE")
    if attempt.state=="FAILED":
        if ratings:_reject("INVALID_VIDEO_FLOOR_MUST_NOT_MASK_HUMAN_RESPONSES")
        return {k:1.0 for k in RUBRIC},[]
    ids=[r.rater_id for r in ratings]
    if len(ids)!=len(set(ids)) or len(ratings) not in (2,3):
        _reject("RATERS_NOT_INDEPENDENT_OR_MISSING")
    a,b=ratings[:2]
    needs_third=any(abs(a.ratings[k]-b.ratings[k])>=2 for k in RUBRIC)
    if needs_third!=(len(ratings)==3):
        _reject("ADJUDICATION_NOT_MATCHED_TO_DISAGREEMENT")
    out={}
    for k in RUBRIC:
        if needs_third:
            out[k]=float(statistics.median([r.ratings[k] for r in ratings]))
        else:
            out[k]=round((a.ratings[k]+b.ratings[k])/2,4)
    return out,[abs(a.ratings[k]-b.ratings[k]) for k in RUBRIC]


def _bootstrap(deltas,seed):
    # Paired resampling at TOPIC level; never treat 24 outputs or raters as IID.
    rng=random.Random(int(hashlib.sha256(seed.encode()).hexdigest(),16))
    n=len(deltas);means=[]
    for _ in range(BOOTSTRAP):
        means.append(sum(deltas[rng.randrange(n)] for _ in range(n))/n)
    means.sort()
    return round(means[249],4),round(means[9749],4)


def rehearsal_analysis(*,protocol:dict,manifest:PilotManifest,
                       attempts:tuple[GenerationAttempt,...],
                       ratings:tuple[BlindedRating,...])->SyntheticRehearsal:
    expected=build_manifest(protocol)
    if manifest!=expected:_reject("FROZEN_MANIFEST_NOT_REPLAYED")
    from scripts.verify_v3_benchmark_protocol import TOPIC_IDS
    identities=[(a.topic_id,a.system) for a in attempts]
    expected_identities=[(topic,arm) for topic in TOPIC_IDS for arm in ARMS]
    if identities!=expected_identities or len(set(x.attempt_id for x in attempts))!=24:
        _reject("ALL_12_PAIRED_ATTEMPTS_REQUIRED_NO_DROPS")
    if any(x.state=="NOT_RUN" for x in attempts):
        _reject("PILOT_UNEXECUTED_CANNOT_BE_ANALYZED")
    present={(r.topic_id,r.slot,r.rater_id) for r in ratings}
    if len(present)!=len(ratings) or any(r.topic_id not in TOPIC_IDS for r in ratings):
        _reject("DUPLICATE_OR_FOREIGN_RATING")
    account={(a.topic_id,a.system):a for a in attempts}
    used=set();disagree=[];pairs=[]
    for slot in manifest.topic_slots:
        mapping=private_assignment(protocol,slot.topic_id)
        scored={}
        for side in ("A","B"):
            system=mapping[side]
            scores=[r for r in ratings if r.topic_id==slot.topic_id and r.slot==side]
            observed,ds=_score_system(account[(slot.topic_id,system)],scores)
            used.update((r.topic_id,r.slot,r.rater_id) for r in scores)
            disagree.extend(ds)
            scored[system]=observed
        v2=scored["v2d_frozen"];v3=scored["v3_candidate"]
        pairs.append(TopicPairResult(
            topic_id=slot.topic_id,domain=slot.domain,difficulty=slot.difficulty,
            v2_scores=v2,v3_scores=v3,
            delta={k:round(v3[k]-v2[k],4) for k in RUBRIC},
            failed_systems=tuple(arm for arm in ARMS if account[(slot.topic_id,arm)].state=="FAILED"),
        ))
    if len(used)!=len(ratings):_reject("ORPHANED_BLINDED_RATING")
    effects=[]
    for metric in PRIMARY:
        arr=[p.delta[metric] for p in pairs]
        wins=sum(x>0 for x in arr)
        effects.append(PrimaryEffect(
            metric=metric,mean_paired_delta=round(statistics.mean(arr),4),
            wins=wins,ties=sum(x==0 for x in arr),
            ci_low=_bootstrap(arr,protocol["analysis"]["bootstrap_seed"]+"|"+metric)[0],
            ci_high=_bootstrap(arr,protocol["analysis"]["bootstrap_seed"]+"|"+metric)[1],
            threshold_mean_reached=statistics.mean(arr)>=.5,
            threshold_wins_reached=wins>=8,
        ))
    costs=[a.actual_usd_cost for a in attempts]
    durations=[a.wall_seconds for a in attempts]
    values=dict(
        version=VERSION,status="AUTHOR_SEEDED_REHEARSAL_ONLY_NOT_HUMAN_EVIDENCE",
        denominator=12,attempts_included=24,topic_pairs=[p.model_dump(mode="json") for p in pairs],
        co_primary_effects=[e.model_dump(mode="json") for e in effects],
        failed_attempts=sum(a.state=="FAILED" for a in attempts),
        complete_valid_mp4_count=sum(a.state=="VALID_VIDEO" for a in attempts),
        provider_cost_total_usd=round(sum(costs),6) if all(v is not None for v in costs) else None,
        wall_seconds_total=round(sum(durations),4) if all(v is not None for v in durations) else None,
        mean_absolute_rater_disagreement=round(statistics.mean(disagree),4) if disagree else None,
        critical_safety_errors=0,independent_human_data=False,
        actual_human_quality_effect="UNMEASURED",real_pilot_pass=False,publication_blocked=True,
    )
    values["result_sha256"]=compute_content_hash(values)
    return SyntheticRehearsal.model_validate(values)


def forbid_actual_study(*_args,**_kwargs):
    _reject("HUMAN_RECRUITMENT_AND_LIVE_EVALUATION_NOT_AUTHORIZED")
