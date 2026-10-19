#!/usr/bin/env python3
"""V3-96 independent real Chromium UI → actual local V3-95 HTTP → GPT → MP4 proof.

Do NOT run twice with paid mode. The unique GitHub Action trigger blocks retry.
Offline mode has NO API key and exercises only a known ABSTAIN before network.
"""
from __future__ import annotations
import argparse
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from learnflow_v3.v395_prompt_to_video import supported_query
from learnflow_v3.v364_native_array_compiler import decode_movie,file_sha,probe

PROMPT="How can a 3 by 4 grid of squares turn into a 4 by 3 array and keep the same total?"
PREREG=ROOT/"benchmarks/learnflowbench/v3/v3_96_one_real_browser_gpt_ui_preregister.json"
MODEL="openai/gpt-6-luna"
ORIGINAL_V393_SHA="1060c980edf45213642606c04beb80d3f115ae7dafd920580a778c226238f96a"

def require(ok,reason):
    if not ok:raise RuntimeError("V396_"+reason)

def verify_prereg():
    p=json.loads(PREREG.read_text())
    require(p["checkpoint"]=="V3-96" and
       p["parent"]=={"pr":132,"head_sha":"cd2f131e2310006078c06052be296256b5488a32"} and
       p["frozen_novel_prompt"]==PROMPT and
       p["model"]["slug"]==MODEL and p["model"]["one_paid_post_max"]==1 and
       p["model"]["retry"]==0 and p["model"]["allow_fallback"] is False and
       p["safety"]["no_restart_live_job"] is True and
       p["safety"]["no_main_merge"] is True,"PREREG_MUTATED")
    require(supported_query(PROMPT)==PROMPT,"NEW_PROMPT_NOT_ADMITTED")
    return p

def run(host,out,*,live=False,artifacts=None):
    verify_prereg()
    require(not out.exists(),"OUTPUT_FOLDER_EXISTS")
    out.mkdir(parents=True)
    from playwright.sync_api import sync_playwright
    receipt={"checkpoint":"V3-96","mode":"REAL_PAID_BROWSER" if live else "NO_PAID_BROWSER_PREFLIGHT",
             "query_sha256":sha256(PROMPT.encode()).hexdigest(),
             "provider_posts":"NOT_CONFIRMED","result":"STARTED","ui":"CHROMIUM_PLAYWRIGHT",
             "mock_model_used":False,"paid_model_authorized":bool(live),
             "human_quality":"UNRATED","production":"BLOCKED"}
    def save():
        (out/"v396_browser_receipt.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    save()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        context=browser.new_context(viewport={"width":1365,"height":900},
                                    accept_downloads=False,
                                    service_workers="block")
        page=context.new_page()
        page.set_default_timeout(50_000)
        page.goto(host+"/create",wait_until="networkidle",timeout=60_000)
        require(page.locator("#v395-ai-preview-form").count()==1,"REAL_APP_FORM_NOT_FOUND")
        require(page.locator("#v395-query").is_visible(),"INPUT_NOT_VISIBLE")
        if not live:
            require(not os.environ.get("OPENROUTER_API_KEY"),
                    "OFFLINE_PREFLIGHT_MUST_HAVE_ZERO_PROVIDER_CREDENTIALS")
            page.locator("#v395-query").fill(
                "Explain photosynthesis in a 3x4 square grid and a 4x3 grid for beginners.")
            page.locator("#v395-paid-consent").check()
            with page.expect_response(lambda r:r.request.method=="POST" and
                                      r.url.endswith("/api/v3/ai/array-preview"),
                                      timeout=30_000) as intercepted:
                page.locator("#v395-submit").click()
            response=intercepted.value
            require(response.status==422,"UNSUPPORTED_QUERY_WAS_NOT_ABSTAINED")
            require("ABSTAIN_" in str(response.json().get("detail","")),"OFFTOPIC_REASON_MISSING")
            require(page.locator("#v395-video").get_attribute("src") is None,
                    "OFFTOPIC_LEAKED_VIDEO")
            page.screenshot(path=str(out/"v396_offline_abstain_ui.png"),full_page=True)
            receipt.update(result="CHROMIUM_UI_OFFTOPIC_ABSTAIN_BEFORE_ANY_PROVIDER",
                           provider_posts=0,ui_http_status=422)
            save()
            browser.close()
            return receipt
        require(artifacts is not None and artifacts.exists(),"ARTIFACT_STORE_NOT_PRESENT")
        page.locator("#v395-query").fill(PROMPT)
        page.locator("#v395-paid-consent").check()
        require(page.locator("#v395-paid-consent").is_checked(),"PAID_CONSENT_NOT_CLICKED")
        require(page.locator("#v395-query").input_value()==PROMPT,"NEW_USER_PROMPT_NOT_TYPED")
        page.screenshot(path=str(out/"v396_before_paid_click.png"),full_page=True)
        print("V396_BROWSER_TYPED_NOVEL_PROMPT_AND_CLICKED_PAID_CONSENT",flush=True)
        receipt.update(result="USER_ACTIVATED_ONE_PAID_GPT_SUBMISSION",provider_posts="UNKNOWN_UNTIL_SERVER_RECEIPT")
        save()
        with page.expect_response(
             lambda response:response.request.method=="POST"
                 and response.url.endswith("/api/v3/ai/array-preview"),
             timeout=630_000) as result_wait:
            page.locator("#v395-submit").click()
        response=result_wait.value
        payload=response.request.post_data_json
        require(payload=={"query":PROMPT,"language":"en","paid_consent":True},
                "BROWSER_BODY_NOT_SAME_AS_HUMAN_INPUT")
        receipt["ui_http_status"]=response.status
        result=response.json()
        if response.status!=200:
            receipt["result"]="GENUINE_BROWSER_HTTP_REJECTED_NO_RETRY"
            receipt["http_error_code"]=str(result.get("detail",""))[:130]
            # V3-95 intentionally removes partial videos. V3-96 preserves only
            # its sanitized provider proof outside preview-servable folders.
            audits=list((artifacts/"v395safeaudit").glob("*.json"))
            if len(audits)==1:
                safe=json.loads(audits[0].read_text())
                for src,dest in (
                    ("provider_posts","provider_posts"),("model_observed","actual_model"),
                    ("finish_reason","finish_reason"),
                    ("provider_reported_cost_usd","provider_reported_cost_usd"),
                    ("result","server_host_gate_result")):
                    if src in safe:receipt[dest]=safe[src]
                receipt["server_receipt_sha256"]=sha256(audits[0].read_bytes()).hexdigest()
                (out/"v396_sanitized_failed_provider_receipt.json").write_text(
                    json.dumps(safe,indent=2,sort_keys=True)+"\n")
            save()
            page.screenshot(path=str(out/"v396_failed_browser_ui.png"),full_page=True)
            browser.close()
            return receipt
        require(result.get("status")=="REAL_GPT_NATIVE_TECHNICAL_PREVIEW_NOT_PRODUCTION",
                "BROWSER_RETURNED_NONREAL_GPT_RESULT")
        require(result.get("model")==MODEL,"BROWSER_INCORRECT_ACTUAL_MODEL")
        require(result.get("query_sha256")==receipt["query_sha256"],"QUERY_SHA_MISMATCH")
        require(result.get("video_url","").startswith("/api/v3/ai/array-preview/"),
                "NOT_PRIVATE_PREVIEW_URL")
        preview_id=result["preview_id"]
        require(len(preview_id)==39 and preview_id.startswith("v395gpt"),
                "PREVIEW_ID_NOT_UNGUESSABLE_FORMAT")
        page.wait_for_function(
          """() => {const x=document.getElementById('v395-video');
                   return x && x.style.display !== 'none' && x.getAttribute('src');}""",
          timeout=25_000)
        video_url=page.locator("#v395-video").get_attribute("src")
        require(video_url==result["video_url"],"HTML_VIDEO_SRC_NOT_REAL_API_URL")
        page.screenshot(path=str(out/"v396_real_gpt_result_ui.png"),full_page=True)
        data=(artifacts/preview_id/"v395_preview_receipt.json")
        require(data.is_file(),"REAL_PROVIDER_SERVER_RECEIPT_MISSING")
        r=json.loads(data.read_text())
        receipt["provider_posts"]=r.get("provider_posts")
        receipt["actual_model"]=r.get("model_observed")
        receipt["finish_reason"]=r.get("finish_reason")
        receipt["storyboard_origin"]=r.get("storyboard_origin")
        receipt["provider_reported_cost_usd"]=r.get("provider_reported_cost_usd")
        receipt["storyboard_sha256"]=r.get("storyboard_sha256")
        receipt["accepted_source_sha256"]=r.get("accepted_source_sha256")
        receipt["host_ledger_sha256"]=r.get("host_ledger_sha256")
        receipt["frame_count"]=r.get("native_video_frames")
        receipt["video_sha256"]=r.get("native_video_sha256")
        receipt["video_url"]=video_url
        receipt["private_preview_id_sha256"]=sha256(preview_id.encode()).hexdigest()
        save()
        require(r["result"]=="NEW_GPT_TO_NATIVE_TECHNICAL_PASS",
                "REAL_PROVIDER_TO_NATIVE_NOT_PASS")
        require(r["storyboard_origin"]=="GENUINE_NEW_GPT_POST","NOT_NEW_REAL_GPT_POST")
        require(r["model_observed"]==MODEL and r["finish_reason"]=="stop",
                "REAL_GPT_MODEL_OR_FINISH_INVALID")
        require(r["provider_posts"]==1 and r["retry_count"]==0 and
                r["fallback_count"]==0,"REAL_GPT_POST_OR_RETRY_POLICY_FAILURE")
        require(r["storyboard_sha256"]!=ORIGINAL_V393_SHA,
                "STORYBOARD_IDENTICAL_TO_HISTORICAL_JSON")
        require(r["final_video"]=="VERIFIED_PRIVATE_DEVELOPER_PREVIEW",
                "UNVERIFIED_MEDIA_EXPOSED")
        require(Decimal(r["provider_reported_cost_usd"])<=Decimal(".01"),
                "PROVIDER_COST_TOO_HIGH")
        require(r["timeline_geometry"]["geometry_pass"] is True,
                "FULL_TIMELINE_COLLISION_AUDIT_FAILED")
        require(r["timeline_geometry"]["timeline_frames_audited"]==r["native_video_frames"],
                "TIMELINE_AUDIT_INCOMPLETE")
        require(r["native_video_frames"]>100,"NOT_REAL_NARRATED_FULL_VIDEO")
        mp4=artifacts/preview_id/"native_pair"/"model_unverified.mp4"
        require(mp4.is_file(),"MODEL_RENDERED_MP4_MISSING")
        require(file_sha(mp4)==result["video_sha256"],"NATIVE_GPT_MP4_SHA_MISMATCH")
        require(probe(mp4)==result["frame_count"],"NATIVE_GPT_MP4_FRAMES_WRONG")
        decode_movie(mp4)
        # This GET exercises exact path that the HTML <video> element uses.
        resp=context.request.get(host+video_url,timeout=180_000)
        require(resp.status==200 and "video/mp4" in resp.headers.get("content-type",""),
                "UI_REAL_VIDEO_GET_FAILED")
        mp4_content=resp.body()
        require(sha256(mp4_content).hexdigest()==file_sha(mp4),
                "BROWSER_VIDEO_BYTES_NOT_MODEL_MP4")
        (out/"v396_REAL_NEW_GPT_UI_video.mp4").write_bytes(mp4_content)
        # Validate actual browser loaded metadata, not merely JS DOM string.
        try:
            page.wait_for_function(
                "() => document.getElementById('v395-video').readyState >= 1",
                timeout=25000)
            receipt["browser_html5_video_metadata"]="LOADED"
        except Exception:
            receipt["browser_html5_video_metadata"]="NOT_CONFIRMED_MEDIA_DOWNLOAD_VERIFIED"
        from learnflow_v3.v364_native_array_compiler import snap
        snap(mp4,11.7).save(out/"v396_real_frame_11_7s.png")
        snap(mp4,22.0).save(out/"v396_real_frame_22_0s.png")
        receipt.update(result="GENUINE_GPT_NEW_PROMPT_BROWSER_UI_TO_NATIVE_MP4_TECHNICAL_PASS",
                       browser_ui_paid_consent=True,
                       browser_http_post_verified=True,
                       private_video_http_get_sha_verified=True,
                       decoded_native_mp4=True,
                       topic_scope="ONLY_3_BY_4_TO_4_BY_3",
                       independent_human_review="NOT_RUN",
                       production="BLOCKED")
        save()
        print("V396_REAL_GPT_BROWSER_FORM_CLICK_TO_NATIVE_MP4_PASS",flush=True)
        browser.close()
        return receipt

if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--server-url",default="http://127.0.0.1:8765")
    cli.add_argument("--output",type=Path,required=True)
    cli.add_argument("--offline",action="store_true")
    cli.add_argument("--live-one-paid-post",action="store_true")
    cli.add_argument("--artifacts",type=Path)
    args=cli.parse_args()
    require(args.offline!=args.live_one_paid_post,"EXACTLY_ONE_MODE_REQUIRED")
    r=run(args.server_url,args.output,live=args.live_one_paid_post,artifacts=args.artifacts)
    print("V396_RESULT",r["result"],flush=True)
    required=("GENUINE_GPT_NEW_PROMPT_BROWSER_UI_TO_NATIVE_MP4_TECHNICAL_PASS"
              if args.live_one_paid_post else "CHROMIUM_UI_OFFTOPIC_ABSTAIN_BEFORE_ANY_PROVIDER")
    if r["result"]!=required:sys.exit(2)
