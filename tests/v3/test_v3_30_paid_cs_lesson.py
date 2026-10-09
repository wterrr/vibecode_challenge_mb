"""Adversarial V3-30 source/model provenance and typed visual-state tests.

Mock HTTP proves rejection logic only, never counts as actual paid model PASS.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys

import pytest
from learnflow_v2.repair import compute_content_hash
from learnflow_v2.scenegraph import SceneGraph
from learnflow_v3.models import SemanticContractError

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from learnflow_v3.paid_cs_lesson import (
    SOURCE_URL, MODEL, CLAIMS, Blocked, build_contracts, fetch_source,
    post_luna, run_one, source_certificate, validate_research, validate_script,
)
from learnflow_v3.multidomain_coverage import read_source
from learnflow_v3.code_process_renderer import (
    ProcessWalkthrough, verify_process_walkthrough,
)

SENTENCES = {
    "C_DEFINE": "The keyword def introduces a function definition. It must be followed by the function name and the parenthesized list of formal parameters. The statements that form the body of the function start at the next line, and must be indented.",
    "C_BIND": "The actual parameters (arguments) to a function call are introduced in the local symbol table of the called function when it is called; thus, arguments are passed using call by value.",
    "C_RETURN": "The return statement returns with a value from a function.",
}
WORDS = [
    "Here we use def to define a function that holds a small rule and gives it a readable name.",
    "This call supplies argument three to the named function, letting us follow what happens when an input arrives.",
    "The parameter named n receives three for this call, so the body can use that value in its calculation.",
    "The return statement sends back five after adding two, which completes our small worked example with a known answer.",
]


def source():
    blob = "<html><body><h1>Defining Functions</h1><p>" + "</p><p>".join(SENTENCES.values()) + "</p></body></html>"
    # Enforce substantial source size without altering published paragraphs.
    return source_certificate((blob + "<!-- " + "x" * 3100 + " -->").encode(), SOURCE_URL)


def research(certificate):
    return {"claims": [
        {"claim_id": cid,
         "quote": certificate["spans"][cid][:min(100, len(certificate["spans"][cid]))],
         "explanation": "This published passage explains the named concept in a function call, including its role for learners."}
        for cid in CLAIMS]}


def script():
    return {"segments": [
        {"segment_id": sid, "claim_ids": [cid], "spoken_text": text}
        for sid, cid, text in zip(("seg-define", "seg-call", "seg-bind", "seg-return"),
                                  ("C_DEFINE", "C_BIND", "C_BIND", "C_RETURN"), WORDS, strict=True)]}


def test_real_publisher_origin_and_actual_section_required():
    cert = source()
    assert cert["status"] == "OFFICIAL_PYTHON_HTML_QUOTE_ANCHORS_VERIFIED"
    assert all(cid in cert["spans"] for cid in CLAIMS)
    raw = b"<html>" + b"x" * 3500 + b"</html>"
    with pytest.raises(Blocked, match="ANCHOR_MISSING"):
        source_certificate(raw, SOURCE_URL)
    with pytest.raises(Blocked, match="SOURCE_REDIRECT_ORIGIN"):
        source_certificate(raw, "https://evil.example/3/tutorial/controlflow.html")


def test_quote_tamper_and_claim_ids_rejected():
    cert = source()
    payload = research(cert)
    assert len(validate_research(payload, cert)) == 3
    forged = copy.deepcopy(payload)
    forged["claims"][1]["quote"] = "An entirely invented sentence masquerading as documentation."
    with pytest.raises(Blocked, match="UNGROUNDED"):
        validate_research(forged, cert)
    forged = copy.deepcopy(payload)
    forged["claims"][1]["claim_id"] = "C_DEFINE"
    with pytest.raises(Blocked, match="CLAIM_ID"):
        validate_research(forged, cert)


def test_script_new_narration_nonidentical_and_fail_closed():
    cert = source()
    claims = validate_research(research(cert), cert)
    assert len(validate_script(script(), claims)) == 4
    forged = copy.deepcopy(script())
    forged["segments"][1]["claim_ids"] = ["C_RETURN"]
    with pytest.raises(Blocked, match="CLAIM_OR_ORDER"):
        validate_script(forged, claims)
    forged = copy.deepcopy(script())
    forged["segments"][2]["spoken_text"] += " The output is 999."
    with pytest.raises(Blocked, match="SCRIPT_UNSAFE"):
        validate_script(forged, claims)
    forged = copy.deepcopy(script())
    forged["segments"][3]["spoken_text"] = "return"
    with pytest.raises(Blocked, match="SCRIPT_UNSAFE"):
        validate_script(forged, claims)


def test_host_process_is_finite_and_scenegraph_tampering_fails():
    cert = source()
    topic = next(x for x in read_source(ROOT)[0] if x["topic_id"] == "lfb-002-cs")
    bundle = build_contracts(topic=topic, certificate=cert,
                             claims=validate_research(research(cert), cert),
                             segments=validate_script(script(), research(cert)["claims"]))
    assert len(bundle["script"].segments) == 4
    assert bundle["engine_example"] == "host_certified_add_two_3_equals_5"
    verify_process_walkthrough(bundle["spec"], bundle["graph"])
    assert [s.active_node_id for s in bundle["spec"].steps] == ["define", "call", "bind", "return"]
    changed = bundle["graph"].model_dump(mode="json")
    changed["nodes"][2]["label"] = "Wrong parameter"
    graph = SceneGraph.model_validate(changed)
    with pytest.raises(SemanticContractError, match="HASH_MISMATCH"):
        verify_process_walkthrough(bundle["spec"], graph)
    wrong = bundle["spec"].model_dump(mode="json")
    wrong["scenegraph_sha256"] = compute_content_hash(graph)
    wrong["steps"][2]["via_edge_id"] = "edge-0"
    with pytest.raises(SemanticContractError, match="TOPOLOGY_REPLAY"):
        verify_process_walkthrough(ProcessWalkthrough.model_validate(wrong), graph)


class FakeResponse:
    def __init__(self, content, url=SOURCE_URL):
        self.content = content
        self.url = url
        self.headers = {}
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, max_bytes):
        return self.content[:max_bytes]
    def geturl(self):
        return self.url


def test_model_transport_is_exact_paid_luna_and_no_fallback():
    received = []
    def sender(request, timeout):
        payload = json.loads(request.data)
        received.append(payload)
        return FakeResponse(json.dumps({
            "id": "response-1", "choices": [{"finish_reason": "stop",
                                            "message": {"content": json.dumps({"status": "hi"})}}],
        }).encode())
    output, receipt = post_luna(key="fake-credential", stage="RESEARCH",
                                message={"topic": "functions"}, sender=sender)
    assert output == {"status": "hi"}
    assert receipt["actual_request_count"] == 1
    assert received[0]["model"] == MODEL == "openai/gpt-6-luna"
    assert received[0]["provider"]["allow_fallbacks"] is False
    assert len(received[0]["messages"]) == 2
    with pytest.raises(Blocked, match="MODEL_OR_SECRET"):
        post_luna(key="", stage="RESEARCH", message={})


def test_two_independent_model_outputs_not_authored_fixture(tmp_path):
    mocked = [research(source()), script()]
    requests = []
    def sender(request, timeout):
        data = json.loads(request.data)
        requests.append(data)
        output = mocked.pop(0)
        return FakeResponse(json.dumps({"id": "opaque-" + str(len(requests)),
            "choices": [{"finish_reason": "stop",
                         "message": {"content": json.dumps(output)}}]}).encode())
    receipt = run_one(root=ROOT, out=tmp_path, key="fake-credential",
                      fetcher=source, sender=sender, make_video=False)
    assert receipt["status"] == "LIVE_AUTHORED_CS_SCRIPT_AND_SOURCE_PASS"
    assert receipt["live_paid_provider_requests"] == 2
    assert receipt["rendered_video_sha256"] is None
    assert receipt["source_certificate"]["status"].startswith("OFFICIAL_PYTHON")
    assert len(requests) == 2
    assert not mocked
    assert receipt["production"] == "BLOCKED"
    assert (tmp_path / "v3_30_live_receipt.json").is_file()


def test_model_cannot_make_unverified_numeric_fact_look_valid(tmp_path):
    m = script()
    m["segments"][3]["spoken_text"] = WORDS[3].replace("five", "nine")
    out = source()
    def sender(request, timeout):
        response = research(out) if b'"C_DEFINE"' not in request.data else m
        return FakeResponse(json.dumps({"choices": [{"finish_reason": "stop",
                    "message": {"content": json.dumps(response)}}]}).encode())
    with pytest.raises(Blocked):
        run_one(root=ROOT, out=tmp_path, key="fake-credential",
                fetcher=source, sender=sender, make_video=False)
