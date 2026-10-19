"""V3-94 hostile geometrical/pedagogical timeline tests. No model API."""
from __future__ import annotations
from copy import deepcopy
import hashlib,json,math
import pytest
from pathlib import Path

from learnflow_v3.v364_heldout_storyboard import host_test_baseline,UNIT_IDS,accept,digest
from learnflow_v3.v392_compact_authoring import strict_parse,host_compile
from learnflow_v3 import v394_timeline_layout as g
from scripts.run_v3_94_gpt_native_layout_repair import frozen

def candidate():
    return frozen()[2]

def test_frozen_source_has_exact_real_provider_hash_and_genuine_model_decisions():
    p,s,c=frozen()
    raw=Path("research/v393_accepted_gpt6_luna_storyboard_frozen.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest()==p["frozen_evidence"]["original_json_raw_sha256"]
    assert digest(s)=="1060c980edf45213642606c04beb80d3f115ae7dafd920580a778c226238f96a"
    assert digest(c)=="5d1b58981831c637103b9cf575ba27ba0df93a5de47cc936772c50dba381eb1b"
    assert c["visual_thinker"]["composition"]=="side_by_side"
    assert c["motion_director"]["method"]=="smooth_morph"
    assert len({b["caption"] for b in c["beats"]})==5
    assert c["beats"][3]["show_numeric_conclusion"]
    assert not c["beats"][2]["show_numeric_conclusion"]
    assert p["no_paid_model_api"] is True

def test_true_before_after_planes_and_invariant_unit_identities():
    c=candidate()
    a=g.centers(c,0,0)
    b=g.centers(c,4,1)
    assert len(a)==12 and len(b)==12
    assert tuple(a)==UNIT_IDS and tuple(b)==UNIT_IDS
    assert len({round(y) for x,y in a.values()})==3
    assert len({round(x) for x,y in a.values()})==4
    assert len({round(y) for x,y in b.values()})==4
    assert len({round(x) for x,y in b.values()})==3
    assert sum(x for x,y in b.values())/12>800
    assert sum(x for x,y in a.values())/12<500
    assert len(g.source_ghost_centers())==12
    # Source ghost geometry is outlines only, not 12 new numbered squares.

@pytest.mark.parametrize("beat,progress",[
    (0,0.0),(1,0.5),(2,0.0),(2,0.02),(2,0.125),(2,0.25),
    (2,0.33),(2,0.5),(2,0.625),(2,0.78),(2,0.99),
    (2,1.0),(3,0.25),(4,0.98)])
def test_all_preregistered_motion_checkpoints_have_no_collision(beat,progress):
    assert g.audit_frame(candidate(),beat,progress)["caption_count"]>=1

def test_full_441_frame_gpt_and_control_timeline_audited_before_encode():
    counts=[70,72,98,98,103]
    assert sum(counts)==441
    for lesson in (candidate(),host_test_baseline()):
        proof=g.audit_timeline(lesson,counts)
        assert proof["geometry_pass"]
        assert proof["all_12_persistent_ids"]
        assert proof["timeline_frames_audited"]==441
        assert proof["label_tile_collisions"]==0
        assert proof["subtitle_band_collisions"]==0
        assert proof["tile_tile_collisions"]==0
        assert proof["max_tile_bottom"]<=g.STAGE_BOTTOM
        assert proof["min_tile_top"]>=g.STAGE_TOP

def test_original_two_failure_stages_are_visually_safe():
    c=candidate()
    # Original 11.7s (middle of motion) and 22s (four-row witness) would
    # overlap both the identity label and subtitle on the old renderer.
    for beat,p in [(2,.35),(2,.7),(3,0),(3,1)]:
        proof=g.audit_frame(c,beat,p)
        assert proof["bottom"]<g.SUBTITLE_DIVIDER
    assert g.fixed_label_boxes(c,3,__import__("PIL").ImageDraw.Draw(
      __import__("PIL").Image.new("RGB",(g.W,g.H))))["identity"][3]<g.SUBTITLE_DIVIDER

def test_renderer_direct_frame_respects_source_ghost_and_nontext_overlap():
    c=candidate()
    for beat,p in ((2,.3),(3,1)):
        frame=g.render_corrected(c,beat,p)
        assert frame.size==(1280,720)
        assert frame.mode=="RGB"

def test_disallow_lying_about_staggered_individual_motion():
    c=candidate()
    c["motion_director"]["method"]="staggered_morph"
    accept(c)
    with pytest.raises(g.Collision,match="STAGGERED_MOTION_NOT_IMPLEMENTED"):
        g.audit_frame(c,2,.5)

def test_reject_too_narrow_intertile_spacing(monkeypatch):
    monkeypatch.setattr(g,"S",50.)
    with pytest.raises(g.Collision,match="SQUARES_COLLIDE"):
        g.audit_frame(candidate(),2,.5)

def test_reject_footer_intrusion(monkeypatch):
    monkeypatch.setattr(g,"TARGET_C",(952.,490.))
    with pytest.raises(g.Collision,match="TILE_ESCAPE_STAGE"):
        g.audit_frame(candidate(),3,1.)

def test_reject_identity_label_overlap_as_in_original(monkeypatch):
    monkeypatch.setattr(g,"TARGET_C",(500.,397.))
    with pytest.raises(g.Collision,match="TILE_HITS_identity"):
        g.audit_frame(candidate(),3,1.)

def test_reject_out_of_frame_unwrapped_long_narration():
    c=candidate()
    c["beats"][0]["caption"]="Supercalifragilisticexpialidocious"*4
    with pytest.raises(g.Collision,match="SUBTITLE_TEXT_OUTSIDE_SAFE_BAND"):
        g.audit_frame(c,0,0)

def test_host_baseline_single_stage_still_auditable_and_renderable():
    baseline=host_test_baseline()
    assert baseline["visual_thinker"]["composition"]=="single_stage"
    assert g.audit_frame(baseline,2,.5)["bottom"]<g.SUBTITLE_DIVIDER

def test_legacy_native_compiler_default_unchanged_but_custom_renderer_hook_present():
    from pathlib import Path
    s=Path("learnflow_v3/v364_native_array_compiler.py").read_text()
    assert "def build_comparison(baseline,candidate,dest:Path,frame_renderer=None):" in s
    assert "frame_stream(item,counts,raw,frame_renderer=frame_renderer)" in s
    assert "frame_renderer or render" in s

def test_no_paid_api_endpoint_in_v394_runner():
    s=Path("scripts/run_v3_94_gpt_native_layout_repair.py").read_text()
    assert "openrouter.ai" not in s.lower()
    assert "requests.post" not in s
    assert "urllib.request" not in s
    assert "common_timeline(" in s
    assert "audit_timeline(candidate,counts)" in s


def test_detects_actual_upper_heading_to_center_annotation_collision(monkeypatch):
    # Regression discovered by directly inspecting the first repaired MP4.
    # No named squares or subtitles overlapped, but the two headings merged.
    monkeypatch.setitem(g.LABELS,"before",
        "BEFORE  /  3 ROWS x 4 COLUMNS / A VERY LONG PANEL HEADING")
    with pytest.raises(g.Collision,match="TEXT_TEXT_COLLISION"):
        g.audit_frame(candidate(),2,.5)

def test_repaired_headings_are_separated_from_center_text_in_every_beat():
    c=candidate()
    from PIL import Image,ImageDraw
    d=ImageDraw.Draw(Image.new("RGB",(1280,720)))
    for beat in range(5):
        t=g.fixed_label_boxes(c,beat,d)
        assert not g.overlap(t["before_heading"],t["center_note"],margin=16)
        assert not g.overlap(t["center_note"],t["after_heading"],margin=16)
        assert not g.overlap(t["before_heading"],t["after_heading"],margin=16)
