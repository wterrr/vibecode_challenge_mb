"""V3-28 real typed upstream->semantic->narrated H264 compiler regressions.

No synthetic contract may be misreported as autonomous researcher output.
"""
from __future__ import annotations
from hashlib import sha256
import json
import os
from pathlib import Path
import pytest

from learnflow_v3.multidomain_coverage import read_source
from learnflow_v3.source_grounded_compiler import (
    SEED_FILE,author_seeded_contracts,compile_linear_source_bound,
    canonical_claim,run,
)
ROOT=Path(__file__).resolve().parents[2]

@pytest.fixture(scope="module")
def source_cases():
    seeds=json.loads((ROOT/SEED_FILE).read_text())["cases"]
    topics={x["topic_id"]:x for x in read_source(ROOT)[0]}
    return [(topics[s["topic_id"]],s) for s in seeds]

def test_model_source_two_separate_domains_and_frozen_nonpilot(source_cases):
    assert [x[0]["domain"] for x in source_cases]==["math","physics"]
    assert source_cases[0][1]["model_kind"]!=source_cases[1][1]["model_kind"]
    assert source_cases[0][0]["topic_id"]=="lfb-020-math"
    assert source_cases[1][0]["topic_id"]=="lfb-036-physics"
    assert all(s["source_url"].startswith("https://openstax.org/books/")
               for _,s in source_cases)

@pytest.mark.parametrize("idx",[0,1])
def test_contracts_from_separate_sources_through_real_hermes_pedagogy_and_vd(source_cases,idx):
    topic,seed=source_cases[idx]
    bundle=author_seeded_contracts(topic=topic,seed=seed)
    events,receipt=compile_linear_source_bound(bundle=bundle)
    assert receipt["verified_beats"]==len(events)==5
    assert receipt["visual_director_validation"]=="VD_REAL_GATE_PASSED"
    assert receipt["source_creation"].startswith("OFFLINE_AUTHOR_SEEDED")
    assert receipt["external_quote_independently_semantic_fact_checked"] is False
    assert not receipt["normal_v3_04_router_promoted"]
    assert {v["source_claim_ids"][1] for v in events}=={
        f"CP{i}" for i in range(5)}
    assert all(event["source_value"]==bundle["spec"].steps[i].y
               for i,event in enumerate(events))

def test_reject_misleading_source_domain_fraud(source_cases):
    t,s=source_cases[1]
    fraud={**s,"source_url":source_cases[0][1]["source_url"]}
    with pytest.raises(ValueError,match="V3_27_SOURCE_SEED_SCOPE_OR_CITATION_MISMATCH"):
        author_seeded_contracts(topic=t,seed=fraud)

def test_reject_script_timing_and_spoken_math_fraud(source_cases):
    topic,seed=source_cases[0]
    b=author_seeded_contracts(topic=topic,seed=seed)
    original=b["script"].segments
    mutated=original[0].model_copy(update={"spoken_text":"The line goes up by 900 units."})
    bad=b["script"].model_copy(update={"segments":(mutated,*original[1:])})
    with pytest.raises(ValueError,match="V3_27_SCRIPT_SEMANTIC_SOURCE_DRIFT"):
        compile_linear_source_bound(bundle={**b,"script":bad})

def test_reject_claim_point_fraud(source_cases):
    topic,seed=source_cases[1]
    b=author_seeded_contracts(topic=topic,seed=seed)
    from agent_contracts import ResearchClaim
    originals=b["research"].claims
    changed=originals[1].model_copy(update={"statement":"At 0 seconds velocity is 900."})
    fraudulent=b["research"].model_copy(update={"claims":(originals[0],changed,*originals[2:])})
    with pytest.raises(ValueError,match="V3_27_DERIVED_POINT_CLAIM_SEMANTIC_DRIFT"):
        compile_linear_source_bound(bundle={**b,"research":fraudulent})

def test_reject_beat_script_claim_swap(source_cases):
    topic,seed=source_cases[0]
    b=author_seeded_contracts(topic=topic,seed=seed)
    beats=b["visual"].beats
    swapped=beats[0].model_copy(update={"script_segment_ref":beats[1].script_segment_ref})
    visual=b["visual"].model_copy(update={"beats":(swapped,*beats[1:])})
    with pytest.raises(Exception,match="SCRIPT_BEAT_ORDER_OR_COVERAGE_DRIFT|UPSTREAM_PEDAGOGY_SCRIPT_GATE|BEAT_SCRIPT_CLAIM"):
        compile_linear_source_bound(bundle={**b,"visual":visual})

def test_decoded_real_compiled_mp4_and_untampered_srt():
    out=Path(os.environ["V3_28_MEDIA_DIR"])
    r=json.loads((out/"v3_28_compiler_coverage.json").read_text())
    assert r["denominator"]==6 and len(r["six_attempt_ledger"])==6
    assert r["bounded_compiler_video_pass_count"]==2
    assert r["abstain_count"]==4 and r["attempt_failure_count"]==0
    assert r["autonomous_research_script_director_end_to_end_count"]==0
    assert r["full_six_domain_release_gate"]=="NO_GO" and r["production"]=="BLOCKED"
    for case in r["six_attempt_ledger"]:
        if case["status"]!="OFFLINE_SOURCE_CONTRACT_COMPILER_AND_REAL_AV_PASS":
            assert case["status"]=="ABSTAIN_UNSUPPORTED_SOURCE_TO_RENDERER"
            continue
        folder=out/case["topic_id"]
        movie=folder/"compiled_linear_narrated_720p.mp4"
        captions=folder/"compiled_linear_narrated_720p.srt"
        proof=json.loads((folder/"compiler_receipt.json").read_text())
        physical=json.loads((folder/"compiled_linear_lesson_evidence.json").read_text())
        assert movie.is_file() and captions.is_file()
        assert sha256(movie.read_bytes()).hexdigest()==case["video_sha256"]
        assert physical["video_sha256"]==case["video_sha256"]
        assert physical["real_h264_aac"] is True
        assert physical["fps"]==18 and physical["width"]==1280 and physical["height"]==720
        assert proof["verified_beats"]==len(physical["beats"])==5
        assert len(physical["aac_rms_per_spoken_beat"])==5
        assert min(physical["aac_rms_per_spoken_beat"])>0.003
        assert physical["max_decoded_mae"]<12
        assert physical["research_agent"]=="NOT_EXECUTED"
        assert physical["publication"] if "publication" in physical else physical["production"]=="BLOCKED"
        assert (folder/"compiled_all_beats_decoded_contact_sheet.jpg").is_file()
        assert all(b["source_claim_ids"]==["C1",f"CP{i}"]
                   for i,b in enumerate(physical["beats"]))

def test_seed_output_fail_closed_existing_folder(source_cases,tmp_path):
    topic,seed=source_cases[0]
    from learnflow_v3.multidomain_coverage import render_math
    b=author_seeded_contracts(topic=topic,seed=seed)
    events,proof=compile_linear_source_bound(bundle=b)
    (tmp_path/"existing").write_text("do not overwrite")
    with pytest.raises(ValueError,match="V3_27_NONEMPTY_OUTPUT_FOLDER"):
        render_math(topic=topic,output=tmp_path,compiled_spec=(b["graph"],b["spec"]),
                    compiled_events=events,compiler_provenance=proof)


def test_rendered_physics_display_is_source_bound_and_unit_labeled(source_cases):
    """Regression: generic f(x) alone is not a physics lesson representation."""
    from learnflow_v3.multidomain_coverage import _render_frame
    from learnflow_v3.sequence_renderer import SequenceRenderProfile
    from PIL import ImageChops
    topic,seed=source_cases[1]
    bundle=author_seeded_contracts(topic=topic,seed=seed)
    events,proof=compile_linear_source_bound(bundle=bundle)
    assert all(e["domain_display"]=="PHYSICS_VELOCITY_TIME" for e in events)
    assert all(e["source_slope"]==seed["slope"] for e in events)
    assert "acceleration is" in events[-1]["text"]
    profile=SequenceRenderProfile(width=1280,height=720,fps=18,seconds_per_step=1)
    domain_frame=_render_frame(bundle["spec"],bundle["graph"],events[-1],.5,profile)
    old_style_event={k:v for k,v in events[-1].items()
                     if k not in ("domain_display","source_slope","source_intercept")}
    generic_frame=_render_frame(bundle["spec"],bundle["graph"],old_style_event,.5,profile)
    # The real color pixels of the new domain header + physical axis labels
    # must differ from the original generic f(x) header/axes.
    assert ImageChops.difference(
        domain_frame.crop((0,0,1280,195)),generic_frame.crop((0,0,1280,195))
    ).getbbox() is not None
    assert ImageChops.difference(
        domain_frame.crop((990,400,1250,450)),
        generic_frame.crop((990,400,1250,450))
    ).getbbox() is not None
    tampered={**events[0],"source_slope":-2}
    with pytest.raises(ValueError,match="V3_27_DISPLAY_SOURCE_MODEL_DRIFT"):
        _render_frame(bundle["spec"],bundle["graph"],tampered,.5,profile)
