"""V3-27: pre-frozen denominator, source proof, honest NO-GO and negative tests."""
from __future__ import annotations
from hashlib import sha256
import json
import os
from pathlib import Path
import pytest

from learnflow_v3.multidomain_coverage import (
  SOURCE,SELECTION,FROZEN,ORDER,REASON,VERSION,
  read_source,make_linear_graph,semantic_narration,render_math,run_coverage
)

ROOT=Path(__file__).resolve().parents[2]
@pytest.fixture(scope="module")
def selected():
    return read_source(ROOT)[0]
def test_selection_preregistered_exact_six_and_none_from_frozen(selected):
    locked=json.loads((ROOT/FROZEN).read_text())
    forbidden=set(locked["sampling"]["topic_ids"])|set(locked["sampling"]["excluded_diagnostic_ids"])
    assert len(selected)==6 and [x["domain"] for x in selected]==list(ORDER)
    assert len({x["topic_id"] for x in selected})==6
    assert all(x["topic_id"] not in forbidden for x in selected)
    assert all(sha256(x["query"].encode()).hexdigest()==x["query_sha256"] for x in selected)
    assert {x["topic_id"] for x in selected}=={
      "lfb-002-cs","lfb-020-math","lfb-036-physics","lfb-054-biology",
      "lfb-071-chemistry","lfb-086-history-general"}

def test_source_mutation_must_be_rejected(tmp_path):
    source=json.loads((ROOT/SOURCE).read_text())
    prereg=json.loads((ROOT/FROZEN).read_text())
    selection=json.loads((ROOT/SELECTION).read_text())
    for path,data in ((SOURCE,source),(FROZEN,prereg),(SELECTION,selection)):
        file=tmp_path/path
        file.parent.mkdir(parents=True,exist_ok=True)
        file.write_text(json.dumps(data))
    altered=json.loads((tmp_path/SOURCE).read_text())
    item=next(x for x in altered["topics"] if x["topic_id"]=="lfb-020-math")
    item["query"]="Explain incorrect math for a video"
    (tmp_path/SOURCE).write_text(json.dumps(altered))
    with pytest.raises(ValueError,match="V3_27_TOPIC_SELECTION_DRIFT"):
        read_source(tmp_path)

def test_arbitrary_integer_linear_slope_proof():
    for slope,offset in ((-2,1),(-1,0),(1,1),(2,-1)):
        graph,spec=make_linear_graph(slope=slope,intercept=offset)
        assert spec.coefficients==(offset,slope,0)
        assert all((b.y-a.y)==slope for a,b in zip(spec.steps,spec.steps[1:]))
        beats=semantic_narration(spec)
        assert len(beats)==len(spec.steps)+4
        assert beats[-1]["kind"]=="RECAP"
        assert len({x["source_point_id"] for x in beats})==len(spec.steps)
    with pytest.raises(ValueError,match="V3_27_INVALID_LINEAR_COEFFICIENT"):
        make_linear_graph(slope=0,intercept=0)
    # V3-08 deliberately refuses curves extending beyond its plotted y-axis.
    # Do not weaken this source/visual safety guard just to make a test pass.
    from learnflow_v3.models import SemanticContractError
    with pytest.raises(SemanticContractError,match="V3_08_GRAPH_CURVE_OUTSIDE_SAFE_AXIS"):
        make_linear_graph(slope=-2,intercept=2)

def test_unintegrated_nonmath_cannot_silently_fallback(selected):
    assert all(x in REASON for x in ORDER if x!="math")
    assert "CONCEPT_CARD" not in str(REASON)
    assert next(x for x in selected if x["domain"]=="math")["topic_id"]=="lfb-020-math"

def test_actual_six_attempt_qa_receipt_and_math_mp4():
    root=Path(os.environ["V3_27_MEDIA_DIR"])
    result=json.loads((root/"v3_27_six_domain_coverage.json").read_text())
    assert result["denominator"]==6
    assert result["full_end_to_end_count"]==0
    assert result["full_end_to_end_gate"]=="NO_GO_MULTI_DOMAIN"
    assert [x["domain"] for x in result["dev_topics"]]==list(ORDER)
    assert sum(x["status"]=="ABSTAIN" for x in result["dev_topics"])==5
    assert result["real_video_count"]==1 and result["failed_attempts"]==0
    case=next(x for x in result["dev_topics"] if x["domain"]=="math")
    assert case["status"]=="PARTIAL_NARRATED_SPECIALIZED_RENDER_NOT_FULL_PIPELINE"
    folder=root/case["topic_id"]
    mp4=folder/"bounded_math_slope_narrated_720p.mp4"
    evidence=json.loads((folder/"math_partial_lesson_evidence.json").read_text())
    assert sha256(mp4.read_bytes()).hexdigest()==evidence["video_sha256"]==case["video_sha256"]
    assert evidence["real_h264_aac"] is True
    assert evidence["width"]==1280 and evidence["height"]==720
    assert evidence["fps"]==18 and evidence["frames"]>180
    assert len(evidence["decoded_frame_anchors"])==len(evidence["beats"])>=8
    assert evidence["max_decoded_mae"]<12
    assert all(x>.003 for x in evidence["aac_rms_per_spoken_beat"])
    assert (folder/"math_all_beats_decoded_contact_sheet.jpg").is_file()
    assert evidence["research_agent"]==evidence["pedagogy_agent"]=="NOT_EXECUTED"
    assert evidence["production"]=="BLOCKED"
    assert evidence["word_alignment"]=="UNMEASURED"

def test_no_clobber_even_when_partial_renderer_successful(selected):
    root=Path(os.environ["V3_27_MEDIA_DIR"])
    source=next(x for x in selected if x["domain"]=="math")
    target=root/source["topic_id"]
    with pytest.raises(ValueError,match="V3_27_NONEMPTY_OUTPUT_FOLDER"):
        render_math(topic=source,output=target)

def test_source_topic_mismatch_rejected_even_with_video_renderer(selected,tmp_path):
    fake=next(x for x in selected if x["domain"]=="physics")
    with pytest.raises(ValueError,match="V3_27_NO_CERTIFIED_TOPIC_TO_MATH_ADAPTER"):
        render_math(topic=fake,output=tmp_path)


def test_math_caption_gutter_has_no_leaked_engineering_point_ids():
    """Verify final source-grounded rendered geometry, not raw asset labels."""
    from learnflow_v3.multidomain_coverage import _render_frame
    from learnflow_v3.sequence_renderer import SequenceRenderProfile
    from PIL import Image
    graph,spec=make_linear_graph(slope=1,intercept=1)
    beat=semantic_narration(spec)[4]
    profile=SequenceRenderProfile(width=1280,height=720,fps=18,seconds_per_step=1.0)
    img=_render_frame(spec,graph,beat,.5,profile)
    # y=584..596 is the former V3-08 source label; it must now be
    # entirely clean black and not touch the math graph higher up.
    strip=img.crop((0,584,1280,595))
    assert strip.getbbox() is None
    # Caption begins below its dedicated separator, not on top of it.
    assert img.getpixel((100,598))==(58,65,74)
    assert img.getpixel((100,608))==(0,0,0)
