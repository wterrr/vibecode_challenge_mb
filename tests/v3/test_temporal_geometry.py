"""V3-11 swept geometry, intermediate text, subtitle, adversarial/pixel QA."""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v3.models import SemanticContractError
from learnflow_v3.temporal_geometry import (
    TemporalBox,TemporalLayoutPlan,TemporalGeometryCertificate,
    certify_temporal_layout,verify_temporal_certificate,sample_layout,
)
from learnflow_v3.temporal_demo_renderer import (
    TemporalRenderEvidence,render_certified_temporal_demo,verify_temporal_render,
)
from scripts.verify_v3_temporal_geometry import demo_layout


def alter(fn,base=None):
    data=(base or demo_layout()).model_dump(mode="json")
    fn(data)
    return TemporalLayoutPlan.model_validate(data)


def test_safe_baseline_certifies_every_frame_and_swept_intervals():
    plan=demo_layout()
    certificate=certify_temporal_layout(plan)
    verify_temporal_certificate(plan=plan,candidate=certificate)
    assert certificate.frame_count==49
    assert certificate.tested_frames==49
    assert certificate.critical_collisions==0
    assert certificate.subtitle_intrusions==0
    assert certificate.checked_text_bounds>0
    assert certificate.analytic_pair_segments>0
    assert certificate.conservative_pair_subdivisions>0
    assert certificate.video_publication_ready is False
    assert certificate.audio_timing_verified is False


def test_deterministic_compiler_source_replay():
    p=demo_layout()
    a=certify_temporal_layout(p)
    b=certify_temporal_layout(TemporalLayoutPlan.model_validate(p.model_dump(mode="json")))
    assert a.model_dump(mode="json")==b.model_dump(mode="json")
    changed=alter(lambda x:x["tracks"][1]["keyframes"][-1]["box"].update(x=263))
    with pytest.raises(SemanticContractError,match="FORGED_OR_STALE_CERTIFICATE"):
        verify_temporal_certificate(plan=changed,candidate=a)
    forged=a.model_copy(update={"source_hash":"a"*64})
    with pytest.raises(SemanticContractError,match="FORGED_OR_STALE_CERTIFICATE"):
        verify_temporal_certificate(plan=p,candidate=forged)


def test_continuous_crossing_in_fractional_frame_cannot_hide_between_samples():
    """Both integer-time endpoints are safe; collision only at frame 23.5."""
    def crossing(d):
        a,b=d["tracks"][1],d["tracks"][2]
        a["interpolation"]=b["interpolation"]="LINEAR"
        a["keyframes"]=[
            {"frame":0,"box":{"x":200,"y":140,"width":2,"height":20}},
            {"frame":23,"box":{"x":200,"y":140,"width":2,"height":20}},
            {"frame":24,"box":{"x":210,"y":140,"width":2,"height":20}},
            {"frame":48,"box":{"x":210,"y":140,"width":2,"height":20}},
        ]
        b["keyframes"]=[
            {"frame":0,"box":{"x":210,"y":140,"width":2,"height":20}},
            {"frame":23,"box":{"x":210,"y":140,"width":2,"height":20}},
            {"frame":24,"box":{"x":200,"y":140,"width":2,"height":20}},
            {"frame":48,"box":{"x":200,"y":140,"width":2,"height":20}},
        ]
    p=alter(crossing)
    assert sample_layout(p,23)[1][1].right < sample_layout(p,23)[2][1].x
    assert sample_layout(p,24)[2][1].right < sample_layout(p,24)[1][1].x
    with pytest.raises(SemanticContractError,match="SWEPT_COLLISION"):
        certify_temporal_layout(p)


def test_incompatible_easing_cannot_get_false_analytic_certificate():
    def crossing(d):
        a,b=d["tracks"][1],d["tracks"][2]
        a["keyframes"]=[
            {"frame":0,"box":{"x":80,"y":160,"width":70,"height":30}},
            {"frame":48,"box":{"x":430,"y":160,"width":70,"height":30}},
        ]
        b["keyframes"]=[
            {"frame":0,"box":{"x":430,"y":160,"width":70,"height":30}},
            {"frame":24,"box":{"x":295,"y":160,"width":70,"height":30}},
            {"frame":48,"box":{"x":80,"y":160,"width":70,"height":30}},
        ]
        a["interpolation"]="LINEAR"
        b["interpolation"]="SMOOTHSTEP"
    p=alter(crossing)
    with pytest.raises(SemanticContractError,match="FRAME_COLLISION|INTERMEDIATE_COLLISION|UNPROVEN_NONLINEAR_SWEEP"):
        certify_temporal_layout(p)


def test_subtitle_intrusion_even_if_endpoint_is_safe():
    def into_band(d):
        track=d["tracks"][1]
        track["keyframes"].insert(1,{
            "frame":24,"box":{"x":160,"y":291,"width":120,"height":30}
        })
    with pytest.raises(SemanticContractError,match="SUBTITLE_INTRUSION"):
        certify_temporal_layout(alter(into_band))


def test_caption_must_remain_inside_its_banded_region():
    with pytest.raises(SemanticContractError,match="CAPTION_OUTSIDE_RESERVED_BAND"):
        certify_temporal_layout(alter(lambda d:d["tracks"][3]["keyframes"][-1]["box"].update(y=277)))


def test_intermediate_frame_clipping_is_fatal():
    def clip(d):
        d["tracks"][1]["keyframes"].insert(1,{
            "frame":25,"box":{"x":-3,"y":132,"width":140,"height":54}})
    with pytest.raises(SemanticContractError,match="FRAME_CLIPPING"):
        certify_temporal_layout(alter(clip))


def test_font_morph_would_overflow_at_narrow_intermediate_layout():
    def morph(d):
        title=d["tracks"][0]
        title["keyframes"].insert(1,{
            "frame":24,"box":{"x":50,"y":30,"width":105,"height":50},
            "text":"TEMPORAL GEOMETRY","font_px":28,
        })
    with pytest.raises(SemanticContractError,match="INTERMEDIATE_TEXT_OVERFLOW"):
        certify_temporal_layout(alter(morph))


def test_label_reflow_is_not_accepted_as_invisible_continuity():
    def reflow(d):
        track=d["tracks"][3]
        track["keyframes"][-1]["text"]="A very long explanatory subtitle that should not silently get cut off"
    with pytest.raises(SemanticContractError,match="INTERMEDIATE_TEXT_OVERFLOW"):
        certify_temporal_layout(alter(reflow))


def test_excessive_motion_and_overanimated_scene_fail_closed():
    p=alter(lambda d:d.update(max_pixels_per_frame=1))
    with pytest.raises(SemanticContractError,match="EXCESSIVE_MOTION_PER_FRAME"):
        certify_temporal_layout(p)
    def overload(d):
        d["max_simultaneously_moving"]=1
    with pytest.raises(SemanticContractError,match="EXCESSIVE_SIMULTANEOUS_MOTION"):
        certify_temporal_layout(alter(overload))


def test_untrusted_geometry_values_identity_and_timing_are_rejected():
    with pytest.raises(ValidationError):
        TemporalBox(x=float("nan"),y=1,width=4,height=5)
    with pytest.raises(ValidationError):
        TemporalBox(x=2,y=4,width=float("inf"),height=5)
    with pytest.raises(ValidationError,match="DUPLICATE_OBJECT_ID"):
        alter(lambda d:d["tracks"][1].update(object_id="title"))
    with pytest.raises(ValidationError,match="INCOMPLETE_OBJECT_TIMELINE"):
        alter(lambda d:d["tracks"][2]["keyframes"][-1].update(frame=30))
    with pytest.raises(ValidationError):
        alter(lambda d:d["tracks"][1].update(interpolation="UNKNOWN_CUBIC"))
    with pytest.raises(ValidationError):
        alter(lambda d:d["tracks"][0]["keyframes"][0].update(font_px=None))


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    directory=tmp_path_factory.mktemp("temporal_v3_11")
    plan=demo_layout()
    cert=certify_temporal_layout(plan)
    video=directory/"certified.mp4"
    evidence=render_certified_temporal_demo(plan=plan,certificate=cert,output_path=video)
    return plan,cert,video,evidence


def test_real_h264_clip_with_decoded_anchor_and_certificate(rendered):
    plan,cert,video,evidence=rendered
    assert video.stat().st_size>1000
    assert evidence.frame_count==49
    assert len(evidence.anchor_indices)==5
    assert max(evidence.decoded_anchor_mae)<8
    assert evidence.production_pipeline_integrated is False
    verify_temporal_render(plan=plan,certificate=cert,evidence=evidence,video_path=video)


def test_stale_or_tampered_video_and_metadata_fail_on_real_bytes(rendered,tmp_path):
    plan,cert,video,evidence=rendered
    forged=evidence.model_copy(update={"video_sha256":"f"*64})
    with pytest.raises(SemanticContractError,match="STALE_OR_FORGED_RENDER_EVIDENCE"):
        verify_temporal_render(plan=plan,certificate=cert,
                               evidence=forged,video_path=video)
    bad=tmp_path/"changed.mp4"
    bad.write_bytes(video.read_bytes()+b"\x00BREAK")
    with pytest.raises(SemanticContractError,match="STALE_OR_FORGED_RENDER_EVIDENCE"):
        verify_temporal_render(plan=plan,certificate=cert,
                               evidence=evidence,video_path=bad)


def test_modified_layout_rejects_prior_pixel_certificate(rendered):
    plan,cert,video,evidence=rendered
    changed=alter(lambda d:d["tracks"][1]["keyframes"][-1]["box"].update(x=245))
    with pytest.raises(SemanticContractError,match="FORGED_OR_STALE_CERTIFICATE"):
        verify_temporal_render(plan=changed,certificate=cert,
                               evidence=evidence,video_path=video)


def test_fake_source_rehashed_evidence_does_not_override_rendered_frames(rendered):
    plan,cert,video,evidence=rendered
    changed=alter(lambda d:d["tracks"][1]["keyframes"][-1]["box"].update(x=243))
    new_cert=certify_temporal_layout(changed)
    from learnflow_v2.repair import compute_content_hash
    forged=evidence.model_copy(update={
        "plan_sha256":compute_content_hash(changed.model_dump(mode="json")),
        "certificate_sha256":compute_content_hash(new_cert.model_dump(mode="json")),
    })
    with pytest.raises(SemanticContractError,match="DECODED_GEOMETRY_FRAME_MISMATCH|STALE_PIXEL_ANCHORS"):
        verify_temporal_render(plan=changed,certificate=new_cert,
                               evidence=forged,video_path=video)


def test_unsafe_output_never_overwrites_existing_video(rendered):
    plan,cert,video,evidence=rendered
    before=hashlib.sha256(video.read_bytes()).hexdigest()
    with pytest.raises(SemanticContractError,match="UNSAFE_OUTPUT"):
        render_certified_temporal_demo(plan=plan,certificate=cert,output_path=video)
    assert before==hashlib.sha256(video.read_bytes()).hexdigest()


def test_no_unmeasured_publication_claims(rendered):
    _,cert,_,e=rendered
    raw=cert.model_dump(mode="json")
    raw["video_publication_ready"]=True
    with pytest.raises(ValidationError):
        TemporalGeometryCertificate.model_validate(raw)
    raw=e.model_dump(mode="json")
    raw["production_pipeline_integrated"]=True
    with pytest.raises(ValidationError):
        TemporalRenderEvidence.model_validate(raw)
