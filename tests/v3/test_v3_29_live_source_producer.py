"""Actual V3-29 source and 2-stage provider contracts are mutation-tested offline.

Fixture provider/source bytes are NEVER considered real third-party Research.
"""
from __future__ import annotations
from copy import deepcopy
import io
import json
from pathlib import Path
from unittest.mock import Mock
import pytest

from learnflow_v3.independent_source_gate import source_certificate,clean_source_text
from learnflow_v3.live_source_producer import (
  _validate_research,_validate_script,ProviderBlocked,post_free,run_one,
)
from learnflow_v3.source_grounded_compiler import (
  SEED_FILE,author_seeded_contracts
)
from learnflow_v3.multidomain_coverage import read_source
ROOT=Path(__file__).resolve().parents[2]
SEEDS=json.loads((ROOT/SEED_FILE).read_text())["cases"]
TOPICS={x["topic_id"]:x for x in read_source(ROOT)[0]}

def fake_html(kind:str)->bytes:
    text=("3.2 Slope of a Line The slope of the line is the rise divided by "
          "the run. Slope is a rate of change. rise run slope. " if
          kind=="LINEAR_SLOPE" else
          "2.5 Motion Equations for Constant Acceleration "
          "Solving for final velocity, acceleration affects velocity. "
          "constant acceleration velocity. ")
    return ("<html><body><h1>"+text+"</h1><article>"+
            text*20+"</article></body></html>").encode()

@pytest.mark.parametrize("seed",SEEDS,ids=lambda x:x["domain"])
def test_fake_source_fixture_anchor_contract_not_authentic_proof(seed):
    p=source_certificate(seed,html=fake_html(seed["model_kind"]),
                          observed_url=seed["source_url"])
    assert p["status"]=="SOURCE_HTML_ANCHOR_VERIFIED_NOT_INDEPENDENT_SEMANTIC_REVIEW"
    assert p["external_semantic_fact_review"]=="UNMEASURED"
    assert len(p["normalized_text_sha256"])==64
    assert not any(x in p for x in ("html","source_full_text","proof_of_semantics"))

def test_source_html_bad_body_rejects_even_known_url():
    seed=SEEDS[0]
    with pytest.raises(ValueError,match="ANCHORS_NOT_FOUND|TOO_SHORT"):
        source_certificate(seed,html=b"<html>unrelated advertisement</html>",
                          observed_url=seed["source_url"])

def test_redirect_to_other_domain_blocked():
    with pytest.raises(ValueError,match="SOURCE_ORIGIN_OR_REDIRECT_MISMATCH"):
        source_certificate(SEEDS[0],html=fake_html("LINEAR_SLOPE"),
                          observed_url="https://evil.test/spoof")

def test_source_script_injection_cannot_supply_anchor():
    seed=SEEDS[0]
    injected=b"<script>3.2 Slope of a Line rise run slope</script><main>not source content</main>"
    with pytest.raises(ValueError,match="ANCHORS_NOT_FOUND"):
        source_certificate(seed,html=injected,observed_url=seed["source_url"])

def test_hard_fail_paid_model_before_network():
    with pytest.raises(ValueError,match="Paid OpenRouter model is forbidden"):
        post_free(model="openai/gpt-6",key="fake-key",stage="RESEARCH",
                  system="test",user="test",sender=lambda *a,**k: 1)

def test_research_model_output_forged_source_and_claim_rejected():
    seed=SEEDS[0]
    okay={"model_kind":"LINEAR_SLOPE","source_url":seed["source_url"],
          "supported_relation":"rise_over_run"}
    _validate_research(okay,seed)
    for bad in ({**okay,"source_url":SEEDS[1]["source_url"]},
                {**okay,"supported_relation":"unapproved"},
                {**okay,"new_claim":"fabricated"}):
        with pytest.raises(ProviderBlocked,match="UNGROUNDED"):
            _validate_research(bad,seed)

def test_script_model_output_cannot_invent_or_reorder(source_cases=None):
    seed=SEEDS[0];bundle=author_seeded_contracts(topic=TOPICS[seed["topic_id"]],
                                                   seed=seed)
    okay={"segments":[{"segment_id":s.segment_id,"spoken_text":s.spoken_text,
                        "claim_ids":list(s.claim_ids)}
                      for s in bundle["script"].segments]}
    _validate_script(okay,bundle)
    changes=[
      lambda p:p["segments"][0].update(spoken_text="The slope is 900."),
      lambda p:p["segments"][0].update(claim_ids=["C900"]),
      lambda p:p["segments"].pop(),
      lambda p:p["segments"].reverse(),
    ]
    for change in changes:
        bad=deepcopy(okay);change(bad)
        with pytest.raises(ProviderBlocked,match="SCRIPT_"):
            _validate_script(bad,bundle)

class FakeHTTP:
    def __init__(self,payload):self.payload=payload
    def __enter__(self):return self
    def __exit__(self,*a):return False
    def read(self,max_bytes):return json.dumps({
       "choices":[{"finish_reason":"stop",
                   "message":{"content":json.dumps(self.payload)}}],
       "id":"fixture-fake"
    }).encode()

def test_two_stage_real_contract_logic_with_fake_responses_cannot_be_cited_as_live(tmp_path):
    seed=SEEDS[0];bundle=author_seeded_contracts(topic=TOPICS[seed["topic_id"]],
                                                   seed=seed)
    research={"model_kind":"LINEAR_SLOPE","source_url":seed["source_url"],
              "supported_relation":"rise_over_run"}
    script={"segments":[{"segment_id":s.segment_id,"spoken_text":s.spoken_text,
                         "claim_ids":list(s.claim_ids)}
                        for s in bundle["script"].segments]}
    calls=[]
    def sender(req,timeout):
        calls.append(req.full_url)
        return FakeHTTP(research if len(calls)==1 else script)
    def source(seed):
        return source_certificate(seed,html=fake_html("LINEAR_SLOPE"),
                                  observed_url=seed["source_url"])
    result=run_one(root=ROOT,out=tmp_path,model="fixture/safe:free",key="fake-key",
                   sender=sender,fetcher=source,do_render=False)
    assert result["real_provider_requests"]==2
    assert len(calls)==2
    # This is a mock transport; regression explicitly must not be interpreted
    # as live provider proof even though identical function path is exercised.
    assert not (tmp_path/"lfb-020-math").exists()
    assert result["bounded_real_mp4_sha256"] is None
    assert result["research_pack_and_script_origin"].startswith("AUTHOR_SEEDED_")
    assert result["full_autonomous_lesson"]=="NO"

def test_fixture_transport_rejects_fake_second_stage(tmp_path):
    seed=SEEDS[0]
    def sender(req,timeout):
        content={"model_kind":"LINEAR_SLOPE","source_url":seed["source_url"],
                 "supported_relation":"rise_over_run"}
        if b"source_grounded_script_segments" in req.data:
            content={"segments":[{"segment_id":"seg-0","spoken_text":"I made this up!",
                                  "claim_ids":["C1"]}]}
        return FakeHTTP(content)
    def source(seed):
        return source_certificate(seed,html=fake_html("LINEAR_SLOPE"),
                                  observed_url=seed["source_url"])
    with pytest.raises(ProviderBlocked,match="SCRIPT_"):
        run_one(root=ROOT,out=tmp_path,model="fixture/safe:free",key="fake-key",
                sender=sender,fetcher=source,do_render=False)
    assert not (tmp_path/"v3_29_live_witness_receipt.json").exists()
