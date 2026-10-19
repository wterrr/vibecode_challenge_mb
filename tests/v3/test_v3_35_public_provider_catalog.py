"""Tests for V3-35 read-only catalog diagnostics; no model HTTP POST."""
from __future__ import annotations
from io import BytesIO
import json
from urllib.error import HTTPError
from learnflow_v3.provider_catalog_preflight import (
    CATALOG_URL,EXPECTED_MODEL,probe_public_catalog
)


def test_read_only_public_metadata_and_model_capabilities():
    sent=[]
    payload={"data":{"id":EXPECTED_MODEL,"endpoints":[
        {"provider_name":"OpenAI","tag":"openai",
         "status":0,"supported_parameters":["response_format","structured_outputs","tools"]},
        {"provider_name":"Other","tag":"other",
         "status":0,"supported_parameters":["tools"]},
    ]}}
    class Response:
        def __enter__(self):return BytesIO(json.dumps(payload).encode())
        def __exit__(self,*args):pass
    def sender(request,timeout):
        sent.append(request)
        assert timeout<=10
        assert request.get_method()=="GET"
        assert request.full_url==CATALOG_URL
        assert request.get_header("Authorization") is None
        return Response()
    a=probe_public_catalog(sender=sender)
    assert len(sent)==1 and a["inference_requests"]==0
    assert a["matching_endpoint_count"]==1
    assert a["catalog_status"]=="PUBLIC_MODEL_ENDPOINTS_ADVERTISE_STRUCTURED_OUTPUTS"
    assert a["historical_post_404_root_cause"]=="UNDETERMINED"
    assert a["account_entitlement_tested"] is False


def test_public_404_does_not_become_model_no_go_or_paid_retry():
    def sender(request,timeout):
        raise HTTPError(request.full_url,404,"missing",{},None)
    a=probe_public_catalog(sender=sender)
    assert a["catalog_status"]=="UNAVAILABLE_UNVERIFIED"
    assert a["inference_requests"]==0
    assert a["matching_endpoint_count"] is None
    assert a["historical_post_404_root_cause"]=="UNDETERMINED"


def test_catalog_id_mismatch_rejected():
    raw={"data":{"id":"different/model","endpoints":[]}}
    class Response:
        def __enter__(self):return BytesIO(json.dumps(raw).encode())
        def __exit__(self,*args):pass
    a=probe_public_catalog(sender=lambda *_args,**_kwargs:Response())
    assert a["catalog_status"]=="RESPONSE_ID_MISMATCH"
    assert a["inference_requests"]==0
