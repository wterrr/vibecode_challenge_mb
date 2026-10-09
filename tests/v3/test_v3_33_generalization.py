"""V3-33 no leakage, no false generalization/media or human-quality scores."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json,os
import pytest
from pydantic import ValidationError
from learnflow_v3.unseen_domain_quality_audit import (
  SOURCE,FROZEN,SELECTION,MANIFEST,CoverageRow,EducationalGate,EducationalDimension,
  selected_topics,audit_six,current_source_supported_topic_ids,make_quality_gate)
ROOT=Path(__file__).resolve().parents[2]

def test_six_new_exact_frozen_domain_and_query_hashes():
    topics,meta=selected_topics(ROOT)
    assert [r["topic_id"] for r in topics]==[
      "lfb-018-math","lfb-035-physics","lfb-070-chemistry",
      "lfb-053-biology","lfb-001-cs","lfb-085-history-general"]
    assert len(meta["selection_manifest_sha256"])==64
    assert len(meta["prior_v327_topic_ids"])==6
    assert not set(x["topic_id"] for x in topics)&set(current_source_supported_topic_ids(ROOT))
    assert all("binary search" not in r["query"].lower() and
               "add_two" not in r["query"] for r in topics)

def test_all_six_abstain_with_zero_false_media_or_concept_card():
    r=audit_six(ROOT)
    assert r["denominator"]==6 and r["abstain"]==6
    assert r["full_generalization_pass"]==0 and r["partial_new_topic_media_pass"]==0
    assert r["model_api_calls"]==0 and r["production"]=="BLOCKED"
    assert all(x["status"].startswith("ABSTAIN") and
       x["renderer"] is None and x["video_sha256"] is None and
       x["concept_card_fallback"] is False for x in r["rows"])

@pytest.mark.parametrize("kind,reason",[
    ("topic","SELECTION_RULE_OR_TOPIC_DRIFT"),
    ("query_hash","INPUT_QUERY_SHA_MISMATCH"),
    ("wrong_domain","SELECTION_RULE_OR_TOPIC_DRIFT"),
    ("prior_development","TOPIC_LEAKAGE"),
    ("unlocked","SELECTION_NOT_PRECOMMITTED"),
    ("dropped","SIX_DOMAIN_DENOMINATOR_CHANGED")])
def test_manifest_tamper_blocks_before_render(tmp_path,kind,reason):
    for relative in (SOURCE,FROZEN,SELECTION,MANIFEST):
        p=tmp_path/relative;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes((ROOT/relative).read_bytes())
    file=tmp_path/MANIFEST
    m=json.loads(file.read_text())
    if kind=="topic":m["cases"][0]["topic_id"]="lfb-021-math"
    if kind=="query_hash":m["cases"][1]["query_sha256"]="0"*64
    if kind=="wrong_domain":m["cases"][1]["domain"]="math"
    if kind=="prior_development":m["cases"][0]["topic_id"]="lfb-020-math"
    if kind=="unlocked":m["allow_substitution"]=True
    if kind=="dropped":m["cases"].pop()
    file.write_text(json.dumps(m))
    with pytest.raises(ValueError,match=reason):selected_topics(tmp_path)

def test_row_cannot_fabricate_video_claim_source_or_pass():
    row=audit_six(ROOT)["rows"][0]
    for key,value in [
       ("status","PASS"),("certified_source_for_exact_topic",True),
       ("contract_supported",True),("video_sha256","f"*64),
       ("renderer","CONCEPT_CARD"),("concept_card_fallback",True),
       ("generalization_full_e2e",True)]:
        d=deepcopy(row);d[key]=value
        with pytest.raises(ValidationError):CoverageRow.model_validate(d)

def test_eight_dimensional_quality_rubric_cannot_fake_human_scores():
    q=make_quality_gate()
    assert len(q.dimensions)==8 and q.score is None
    assert all(v.status=="NOT_ASSESSED" and v.assessor_count==0 and
               v.score is None for v in q.dimensions)
    for key,value in [("score",100),("production","READY"),
        ("educational_quality_status","PASS"),("dimensions",q.dimensions[:-1])]:
        d=q.model_dump();d[key]=value
        with pytest.raises((ValidationError,ValueError)):EducationalGate.model_validate(d)
    d=q.dimensions[0].model_dump();d["score"]=5
    with pytest.raises(ValidationError):EducationalDimension.model_validate(d)

def test_exact_prior_exposed_control_scope():
    ids=current_source_supported_topic_ids(ROOT)
    assert set(ids)=={"lfb-020-math","lfb-036-physics","lfb-002-cs"}
    assert "lfb-018-math" not in ids and "lfb-001-cs" not in ids

def test_real_old_controls_not_miscounted_as_new_topic_evidence():
    if "V3_33_EVIDENCE_ROOT" not in os.environ:
        pytest.skip("Real MP4 verified after dedicated offline media stage")
    folder=Path(os.environ["V3_33_EVIDENCE_ROOT"])
    report=json.loads((folder/"v3_33_audit_receipt.json").read_text())
    assert report["unseen"]["denominator"]==6 and report["unseen"]["abstain"]==6
    assert report["controls"]["bounded_compiler_video_pass_count"]==2
    assert report["educational"]["controls_in_unseen_denominator"]==0
    assert report["educational"]["any_unseen_domain_video_quality_score"] is None
    assert report["provider_requests"]==0 and report["production"]=="BLOCKED"
    from hashlib import sha256
    from learnflow_v3.multidomain_coverage import _probe
    for case in report["controls"]["six_attempt_ledger"]:
        if case["status"]!="OFFLINE_SOURCE_CONTRACT_COMPILER_AND_REAL_AV_PASS":continue
        mp4=folder/"prior_exposed_controls"/case["topic_id"]/"compiled_linear_narrated_720p.mp4"
        assert mp4.exists() and sha256(mp4.read_bytes()).hexdigest()==case["video_sha256"]
        video,audio=_probe(mp4)
        assert video["codec_name"]=="h264" and audio["codec_name"]=="aac"
        assert (int(video["width"]),int(video["height"]))==(1280,720)
