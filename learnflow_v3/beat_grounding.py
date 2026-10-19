"""V3-10 verified trace-to-rendered-beat grounding for V3-06 Binary Search.

Reuses oracle-replayed V3-05 trace/ledger, V2 script/storyboard identity,
V3-06 deterministic drawing + pixel decode. A manifest with plausible times
is not proof: all evidence is recomputed against actual H.264 frames.
Only renderer-synthetic beat intervals are supported; no audio/word timing proof.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Literal

from pydantic import Field, model_validator

from learnflow_v2.repair import compute_content_hash
from .binary_search_trace import BinarySearchTrace, certify_and_route_binary_search
from .models import SemanticContractError, V3Model
from .sequence_renderer import (
    SequenceRenderEvidence, SequenceRenderProfile, RENDERER_VERSION,
    draw_binary_search_frame, _ffmpeg_anchor, _mean_absolute_error,
)

VERSION = "v3-10-binary-beat-pixel-grounding-v1"
MIN_CHANGE = 0.08
MAX_ANCHOR_MAE = 8.0


def _fail(name: str) -> None:
    raise SemanticContractError("V3_10_" + name)


class BoundBeat(V3Model):
    beat_id: str
    script_segment_ref: str
    claim_refs: tuple[str, ...]
    state_ledger_step_id: str
    trace_step_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_object_ids: tuple[str, ...] = Field(min_length=1)
    frame_start: int = Field(ge=0)
    frame_end_exclusive: int = Field(gt=0)
    sample_frame_indices: tuple[int, int, int]
    expected_visible_change: str | None
    static_exception: str | None
    time_anchor_source: Literal["RENDERER_SYNTHETIC_BEAT"] = "RENDERER_SYNTHETIC_BEAT"

    @model_validator(mode="after")
    def _coherence(self):
        if (self.expected_visible_change is None) == (self.static_exception is None):
            raise ValueError("V3_10_BEAT_CHANGE_OR_EXCEPTION_REQUIRED")
        a, b, c = self.sample_frame_indices
        if not self.frame_start <= a < b < c < self.frame_end_exclusive:
            raise ValueError("V3_10_SAMPLE_NOT_IN_BEAT")
        return self


class BeatGroundingManifest(V3Model):
    schema_version: Literal["v3-10-binary-beat-pixel-grounding-v1"] = VERSION
    renderer_family: Literal["STATEFUL_SEQUENCE_BINARY_SEARCH"] = "STATEFUL_SEQUENCE_BINARY_SEARCH"
    provenance: dict[str, str]
    profile: SequenceRenderProfile
    frame_count: int = Field(gt=0)
    beats: tuple[BoundBeat, ...] = Field(min_length=1)
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    audio_sync_verified: Literal[False] = False

    @model_validator(mode="after")
    def _timeline(self):
        if self.beats[0].frame_start != 0 or self.beats[-1].frame_end_exclusive != self.frame_count:
            raise ValueError("V3_10_FRAME_COVERAGE_INCOMPLETE")
        if any(x.frame_end_exclusive != y.frame_start for x, y in zip(self.beats,self.beats[1:])):
            raise ValueError("V3_10_GAP_OR_OVERLAP")
        if len({b.beat_id for b in self.beats}) != len(self.beats):
            raise ValueError("V3_10_DUPLICATE_BEAT")
        return self


class BeatPixelEvidence(V3Model):
    beat_id: str
    target_object_ids: tuple[str, ...]
    sample_frame_indices: tuple[int, int, int]
    frame_anchor_mae: tuple[float, float, float]
    semantic_roi_early_late_delta: float
    preceding_terminal_delta: float | None
    result: Literal["DYNAMIC_OBSERVED", "STATIC_EXCEPTION_SOURCE_VERIFIED"]


class BeatGroundingEvidence(V3Model):
    schema_version: Literal["v3-10-binary-beat-pixel-grounding-v1"] = VERSION
    manifest_sha256: str
    video_sha256: str
    video_bytes: int = Field(gt=0)
    frame_count: int = Field(gt=0)
    beat_count: int = Field(gt=0)
    dynamic_beat_count: int = Field(ge=0)
    dynamic_beat_pass_count: int = Field(ge=0)
    observable_coverage: float = Field(ge=0, le=1)
    per_beat: tuple[BeatPixelEvidence, ...] = ()
    status: Literal["RENDERED_SYNTHETIC_BEAT_GROUNDING_PASS"] = "RENDERED_SYNTHETIC_BEAT_GROUNDING_PASS"
    audio_sync_verified: Literal[False] = False
    independent_semantic_cv_verified: Literal[False] = False
    human_learning_outcome: Literal["UNMEASURED"] = "UNMEASURED"

    @model_validator(mode="after")
    def _coverage(self):
        if (len(self.per_beat) != self.beat_count or
            self.dynamic_beat_count != self.dynamic_beat_pass_count or
            self.observable_coverage != 1):
            raise ValueError("V3_10_INCOMPLETE_GROUNDING_CANNOT_PASS")
        return self


def _provenance(*, trace,plan,pattern,ledger,registry,script,storyboard,scenegraph,profile):
    return {
        "trace": trace.trace_sha256,
        "plan": compute_content_hash(plan),
        "pattern": compute_content_hash(pattern),
        "ledger": compute_content_hash(ledger),
        "registry": compute_content_hash(registry.to_schema()),
        "script": compute_content_hash(script),
        "storyboard": compute_content_hash(storyboard),
        "scenegraph": compute_content_hash(scenegraph),
        "profile": compute_content_hash(profile.model_dump(mode="json")),
        "renderer": RENDERER_VERSION,
    }


def compile_binary_beat_manifest(*, trace: BinarySearchTrace, plan, pattern, ledger,
                                 registry, script, storyboard, scenegraph,
                                 profile: SequenceRenderProfile) -> BeatGroundingManifest:
    """Only legal bindings are derived from a fully recertified V3-05/V3-04 route."""
    certificate = certify_and_route_binary_search(
        trace=trace, plan=plan, pattern=pattern, ledger=ledger,
        registry=registry, script=script, storyboard=storyboard, scenegraph=scenegraph,
    )
    if certificate.route.selected_variant not in ("TRACE_SPOTLIGHT","TRACE_COMPACT"):
        # Valid empty terminal uses a special exception: still specialized sequence.
        if not (not trace.query.values and len(trace.steps)==1
                and trace.steps[0].phase=="COMPLETE"
                and certificate.route.status.value=="ABSTAIN"):
            _fail("ROUTER_NOT_ELIGIBLE")
    if len(trace.steps) != len(plan.beats) or len(ledger.steps) != len(plan.beats):
        _fail("TRACE_BEAT_LEDGER_COUNT_DRIFT")
    if len(script.segments)!=len(plan.beats):
        _fail("SCRIPT_BEAT_COUNT_DRIFT")
    n=profile.frames_per_step()
    if n < 6: _fail("INSUFFICIENT_FRAMES_FOR_TEMPORAL_QA")
    objects=tuple(x.object_id for x in pattern.semantic_objects)
    bindings=[]
    for i, (step,beat,ledger_step,segment) in enumerate(
        zip(trace.steps,plan.beats,ledger.steps,script.segments,strict=True)
    ):
        if ledger_step.beat_ref!=beat.beat_id or beat.script_segment_ref!=segment.segment_id:
            _fail("BEAT_LEDGER_SCRIPT_REORDER")
        if {x.object_id for x in ledger_step.object_states}!=set(objects):
            _fail("STATE_OBJECT_COVERAGE_DRIFT")
        if not set(beat.claim_refs)<=set(segment.claim_ids):
            _fail("BEAT_SCRIPT_CLAIM_DRIFT")
        dynamic=step.phase=="COMPARE"
        if dynamic != bool(beat.expected_visible_state_change):
            _fail("ESSENTIAL_BEAT_PHASE_DRIFT")
        if not dynamic and not beat.allowed_static_justification:
            _fail("TERMINAL_EXCEPTION_UNJUSTIFIED")
        start=i*n
        # Sampling actual encoded frame indices, not estimated narration time.
        offsets=(max(1,round((n-1)*.10)),round((n-1)*.50),min(n-2,round((n-1)*.88)))
        if len(set(offsets)) != 3:
            _fail("INSUFFICIENT_DISTINCT_SAMPLES")
        bindings.append(BoundBeat(
            beat_id=beat.beat_id,script_segment_ref=segment.segment_id,
            claim_refs=beat.claim_refs,state_ledger_step_id=ledger_step.step_id,
            trace_step_sha256=compute_content_hash(step.model_dump(mode="json")),
            target_object_ids=objects,frame_start=start,frame_end_exclusive=start+n,
            sample_frame_indices=tuple(start+j for j in offsets),
            expected_visible_change=beat.expected_visible_state_change,
            static_exception=beat.allowed_static_justification,
        ))
    base={
        "schema_version":VERSION,
        "renderer_family":"STATEFUL_SEQUENCE_BINARY_SEARCH",
        "provenance":_provenance(
            trace=trace,plan=plan,pattern=pattern,ledger=ledger,registry=registry,
            script=script,storyboard=storyboard,scenegraph=scenegraph,profile=profile,
        ),
        "profile":profile.model_dump(mode="json"),
        "frame_count":len(trace.steps)*n,
        "beats":[b.model_dump(mode="json") for b in bindings],
        "audio_sync_verified":False,
    }
    return BeatGroundingManifest(**base,manifest_sha256=compute_content_hash(base))


def _probe(path: Path, profile: SequenceRenderProfile, frames: int)->None:
    cmd=["ffprobe","-v","error","-select_streams","v:0","-show_entries",
         "stream=codec_name,width,height,r_frame_rate,nb_frames",
         "-of","json",str(path)]
    try:
        p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=25)
        probe=json.loads(p.stdout) if p.returncode==0 else {}
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        raise SemanticContractError("V3_10_FFPROBE_UNAVAILABLE_OR_INVALID") from exc
    tracks=probe.get("streams",[])
    if len(tracks)!=1: _fail("VIDEO_TRACK_MISSING_OR_DUPLICATED")
    s=tracks[0]
    if (s.get("codec_name")!="h264" or s.get("width")!=profile.width or
        s.get("height")!=profile.height or
        s.get("r_frame_rate")!=f"{profile.fps}/1" or
        int(s.get("nb_frames",0))!=frames):
        _fail("DECODED_VIDEO_FORMAT_OR_FRAME_COUNT_MISMATCH")


def verify_binary_beat_video(*, trace:BinarySearchTrace, plan, pattern, ledger,
                             registry, script, storyboard, scenegraph,
                             manifest:BeatGroundingManifest,
                             video_evidence:SequenceRenderEvidence,
                             video_path:str|Path,
                             profile:SequenceRenderProfile)->BeatGroundingEvidence:
    """Re-derive every cue from certified source, then inspect actual decoded H264.

    Fixed V3-06 frame cadence only. There is no passed-by-caller video QA switch.
    """
    canonical=compile_binary_beat_manifest(
        trace=trace,plan=plan,pattern=pattern,ledger=ledger,registry=registry,
        script=script,storyboard=storyboard,scenegraph=scenegraph,profile=profile,
    )
    if manifest.model_dump(mode="json")!=canonical.model_dump(mode="json"):
        _fail("TAMPERED_TIMING_OR_SOURCE_MANIFEST")
    path=Path(video_path)
    if not path.is_file() or path.is_symlink():
        _fail("VIDEO_FILE_MISSING_OR_SYMLINK")
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    size=path.stat().st_size
    if (video_evidence.video_sha256!=digest or video_evidence.video_bytes!=size or
        video_evidence.source_trace_sha256!=trace.trace_sha256 or
        video_evidence.source_ledger_sha256!=canonical.provenance["ledger"] or
        video_evidence.width!=profile.width or video_evidence.height!=profile.height or
        video_evidence.fps!=profile.fps or video_evidence.frame_count!=canonical.frame_count or
        video_evidence.renderer_version!=RENDERER_VERSION or
        not video_evidence.decoded_semantic_frames_pass):
        _fail("UNTRUSTED_OR_STALE_RENDER_EVIDENCE")
    _probe(path,profile,canonical.frame_count)
    source_manifest=compute_content_hash({
        "trace":trace.trace_sha256,"ledger":canonical.provenance["ledger"],
        "route":certify_and_route_binary_search(
            trace=trace,plan=plan,pattern=pattern,ledger=ledger,
            registry=registry,script=script,storyboard=storyboard,scenegraph=scenegraph,
        ).route.decision_hash,
        "profile":profile.model_dump(mode="json"),"renderer":RENDERER_VERSION,
    })
    if video_evidence.source_manifest_hash!=source_manifest:
        _fail("RENDER_SOURCE_MANIFEST_MISMATCH")
    # Semantic ROI excludes title and subtitle regions; title pulse cannot
    # satisfy a required algorithmic state change.
    focus=(round(profile.width*.05),round(profile.height*.245),
           round(profile.width*.95),round(profile.height*.695))
    # Also include detail/result text and verify full-image against exact step.
    semantic=(round(profile.width*.05),round(profile.height*.24),
              round(profile.width*.95),round(profile.height*.86))
    captions={s.segment_id:s.spoken_text for s in script.segments}
    result=[]
    previous=None
    for i,b in enumerate(canonical.beats):
        views=[]
        errors=[]
        for frame in b.sample_frame_indices:
            phase=(frame-b.frame_start)/max(1,profile.frames_per_step()-1)
            actual=_ffmpeg_anchor(path,at=(frame+.4)/profile.fps,profile=profile)
            expected=draw_binary_search_frame(
                trace=trace,step_index=i,progress=phase,
                subtitle=captions[b.script_segment_ref],profile=profile,
            )
            err=_mean_absolute_error(actual,expected,rect=semantic)
            if err>MAX_ANCHOR_MAE:
                _fail(f"SEMANTIC_FRAME_MISMATCH beat={b.beat_id} frame={frame} mae={err:.3f}")
            errors.append(round(err,3))
            views.append(actual)
        change=_mean_absolute_error(views[0],views[-1],rect=focus)
        prev_delta=None
        if b.expected_visible_change:
            if change<MIN_CHANGE:
                _fail(f"ESSENTIAL_BEAT_NOT_VISUALLY_OBSERVED beat={b.beat_id}")
            status="DYNAMIC_OBSERVED"
        else:
            # Static terminal is legal ONLY after verified terminal source, and
            # if it is not the sole empty-array step, must show a new result.
            if previous is not None:
                prev_delta=_mean_absolute_error(previous,views[1],rect=semantic)
                if prev_delta<1.0:
                    _fail(f"TERMINAL_RESULT_NOT_VISIBLE beat={b.beat_id}")
            status="STATIC_EXCEPTION_SOURCE_VERIFIED"
        result.append(BeatPixelEvidence(
            beat_id=b.beat_id,target_object_ids=b.target_object_ids,
            sample_frame_indices=b.sample_frame_indices,
            frame_anchor_mae=tuple(errors),
            semantic_roi_early_late_delta=round(change,3),
            preceding_terminal_delta=round(prev_delta,3) if prev_delta is not None else None,
            result=status,
        ))
        previous=views[1]
    dyn=sum(x.expected_visible_change is not None for x in canonical.beats)
    passed=sum(x.result=="DYNAMIC_OBSERVED" for x in result)
    if passed!=dyn:_fail("MISSING_ESSENTIAL_EVENT")
    return BeatGroundingEvidence(
        manifest_sha256=canonical.manifest_sha256,video_sha256=digest,
        video_bytes=size,frame_count=canonical.frame_count,
        beat_count=len(result),dynamic_beat_count=dyn,
        dynamic_beat_pass_count=passed,
        observable_coverage=1.0,per_beat=tuple(result),
    )
