#!/usr/bin/env python3
"""V3-26 real Chromium E2E on two original locally distributed reviewer HTML kits.

ALL form ratings exported here are SYNTHETIC automation fixtures and deleted.
HTMLMediaElement ended events are exercised by real seeking and decoding, NOT
evidence of a person watching a whole lecture, hearing audio or giving consent.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageStat
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.independent_quality_pilot import (
    DIMS,RATERS,attest_source_manifest,assignment
)
from scripts.aggregate_v3_25_quality_responses import run as aggregate

def check(flag,what):
    if not flag:raise AssertionError("V3_26_"+what)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def audio_probe(path):
    data=json.loads(subprocess.check_output(
        ["ffprobe","-v","error","-select_streams","a:0",
         "-show_entries","stream=codec_name,channels","-of","json",str(path)],text=True))
    tracks=data.get("streams",[])
    check(len(tracks)==1 and tracks[0]["codec_name"]=="aac"
          and tracks[0]["channels"]>=1,"REAL_AAC_STREAM_MISSING")
    decoded=subprocess.run(["ffmpeg","-nostdin","-hide_banner","-v","info",
                            "-i",str(path),"-map","0:a:0","-vn","-af",
                            "volumedetect","-f","null","-"],
                           capture_output=True,text=True,timeout=60,check=True)
    match=re.search(r"max_volume:\s*(-?[\d.]+)\s*dB",decoded.stderr)
    check(match is not None and float(match.group(1))>-65,
          "REAL_AAC_NOT_DECODABLE_OR_SILENT")
    return {"codec":"aac","decodable_nonsilent":True,"db_max":float(match.group(1)),
            "audible_to_human":"NOT_VERIFIED"}

def open_video(page,index,code,out):
    video=page.locator("video").nth(index)
    try:
        page.wait_for_function("""i=>{
          const v=document.querySelectorAll('video')[i];
          return v && v.readyState>=2 && Number.isFinite(v.duration)
            && v.videoWidth===1280 && v.videoHeight===720;
        }""",arg=index,timeout=18000)
    except Exception as e:
        debug=video.evaluate("""v=>({
          currentSrc:v.currentSrc,readyState:v.readyState,networkState:v.networkState,
          duration:v.duration,width:v.videoWidth,height:v.videoHeight,
          errorCode:v.error?v.error.code:null,
          errorMessage:v.error?v.error.message:null,
          canH264Aac:v.canPlayType('video/mp4; codecs="avc1.42E01E, mp4a.40.2"'),
          userAgent:navigator.userAgent
        })""")
        print("V3_26_BROWSER_MEDIA_DIAGNOSTIC="+json.dumps(debug),flush=True)
        raise AssertionError("V3_26_REAL_BROWSER_MEDIA_NOT_DECODED") from e
    m=video.evaluate("""v=>({duration:v.duration,
      width:v.videoWidth,height:v.videoHeight,
      aac_supported:v.canPlayType('audio/mp4; codecs="mp4a.40.2"')})""")
    check(44<m["duration"]<46 and m["aac_supported"]!="",
          "BROWSER_VIDEO_OR_AUDIO_CODEC_MISSING")
    video.evaluate("""async v=>{
        v.muted=false;v.volume=0.7;v.currentTime=13;
        await new Promise((ok,err)=>{
           if(!v.seeking){ok();return;}
           v.addEventListener('seeked',ok,{once:true});
           v.addEventListener('error',err,{once:true});
        });
        await v.play();
    }""")
    previous=video.evaluate("v=>v.currentTime")
    page.wait_for_timeout(1000)
    current=video.evaluate("v=>v.currentTime")
    check(current>previous+.3,"REAL_CHROMIUM_PLAY_DID_NOT_ADVANCE")
    video.evaluate("v=>v.pause()")
    screenshot=out/(code+"_video_"+str(index)+"_decoded.png")
    video.screenshot(path=str(screenshot))
    image=Image.open(screenshot).convert("RGB")
    check(image.width>600 and image.height>300
          and max(ImageStat.Stat(image).stddev)>12,
          "BROWSER_PAINTED_BLANK_H264")
    video.evaluate("""async v=>{
       v.currentTime=v.duration-0.5;
       await new Promise((ok,err)=>{
          if(!v.seeking){ok();return;}
          v.addEventListener('seeked',ok,{once:true});
          v.addEventListener('error',err,{once:true});
       });
       await v.play();
    }""")
    page.wait_for_function(
        "i=>document.querySelectorAll('video')[i].ended",
        arg=index,timeout=16000)
    check("reached the end" in page.locator("#seen-"+"AB"[index]).inner_text(),
          "BROWSER_ENDED_NOT_REFLECTED_IN_UI")
    return {"clip":"AB"[index],"source_dimensions":[m["width"],m["height"]],
            "actual_seconds_played_before_smoke_seek":round(current-previous,3),
            "real_H264_pixels":True,"unmuted_media_element":True,
            "browser_ended_event":True,"frame_png":screenshot.name,
            "real_full_length_human_watch":"NOT_CLAIMED"}

def automate_one(browser,packets,code,out):
    kit=packets/("REVIEWER_"+code)
    html=(kit/"review.html").read_text(encoding="utf-8")
    check(not (kit/"ADMIN_NOT_FOR_RATERS").exists()
          and "baseline" not in html and "refined" not in html,
          "REVIEWER_MAPPING_LEAK")
    check(not re.search(r"https?://",html)
          and not re.search(r"<script[^>]*\bsrc\s*=",html,re.I),
          "EXTERNAL_NETWORK_CODE_IN_OFFLINE_REVIEWER")
    meta=json.loads((kit/"packet_metadata.json").read_text(encoding="utf-8"))
    context=browser.new_context(accept_downloads=True,viewport={"width":1440,"height":900})
    page=context.new_page()
    errors=[];requests=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.on("request",lambda x:requests.append(x.url))
    try:
        # Tests shipped local review.html, not server-mocked or injected HTML.
        page.goto((kit/"review.html").resolve().as_uri(),wait_until="load",timeout=25000)
        check(page.title()=="LearnFlow exploratory video review"
              and page.locator("video").count()==2,"OFFLINE_BROWSER_STARTUP")
        page.locator("#export").click()
        check("consent confirmation" in page.locator("#status").inner_text(),
              "MISSING_CONSENT_NOT_REJECTED")
        page.locator("#screen").fill("15.6")
        page.locator("#distance").fill("60")
        page.locator("#consent").check()
        page.locator("#export").click()
        check("has not reached its end" in page.locator("#status").inner_text(),
              "MISSING_PLAYBACK_NOT_REJECTED")
        played=[];audio=[]
        for i,label in enumerate("AB"):
            target=kit/("clip_"+label+".mp4")
            check(sha(target)==meta["video_sha256"][label],
                  "WRONG_SOURCE_VIDEO_BYTES")
            audio.append(audio_probe(target))
            played.append(open_video(page,i,code,out))
        page.locator("#export").click()
        check("Missing rating: A / clarity" in page.locator("#status").inner_text(),
              "EMPTY_RUBRIC_NOT_REJECTED")
        for label in "AB":
            for dim in DIMS:
                page.locator("#"+label+"-"+dim).select_option("3")
            page.locator("#critical-"+label).select_option("no")
            page.locator("#timestamp-"+label).fill("26.75")
            page.locator("#notes-"+label).fill(
                "SYNTHETIC BROWSER TEST ONLY: candidate and green outline are source-grounded.")
            page.locator("#answer-"+label).fill(
                "SYNTHETIC TEST ONLY: index 1, continue searching left after equality.")
        page.locator("#export").click()
        check("include critical-error response" in page.locator("#status").inner_text(),
              "MISSING_ISSUE_CATEGORY_NOT_REJECTED")
        page.locator("#issue-category-A").select_option("readability")
        page.locator("#issue-category-B").select_option("pedagogy")
        page.locator("#timestamp-A").fill("")
        page.locator("#export").click()
        check("include critical-error response" in page.locator("#status").inner_text(),
              "MISSING_TIMESTAMP_NOT_REJECTED")
        page.locator("#timestamp-A").fill("26.75")
        with page.expect_download(timeout=15000) as download_event:
            page.locator("#export").click()
        download=download_event.value
        check(download.suggested_filename==code+"_review_response.json",
              "WRONG_DOWNLOADED_FILENAME")
        response_path=out/("SYNTHETIC_AUTOMATED_"+code+".json")
        download.save_as(response_path)
        response=json.loads(response_path.read_text(encoding="utf-8"))
        check(response["reviewer_id"]==code
              and response["package_sha256"]==meta["package_sha256"]
              and response["submissions"]["A"]["issue_category"]=="readability"
              and response["submissions"]["B"]["issue_category"]=="pedagogy"
              and all(set(response["submissions"][l]["ratings"])==set(DIMS)
                      for l in "AB"),"INVALID_ACTUAL_BROWSER_EXPORTED_JSON")
        check(not errors and all(x.startswith("file://") or x.startswith("blob:")
                                 for x in requests),"BROWSER_REMOTE_REQUEST_OR_JS_ERROR")
        page.screenshot(path=str(out/(code+"_full_offline_review_page.png")),
                        full_page=True)
        return {"slot":code,"playback":played,"audio":audio,
                "negative_tests":["consent","unwatched","rubric","category","timestamp"],
                "external_requests":0,"js_exceptions":len(errors),
                "local_file_real_browser":True},response_path
    finally:
        context.close()

def run(media,packets,output):
    check(output.is_dir() and not any(output.iterdir()),
          "OUTPUT_DIRECTORY_NOT_EMPTY")
    manifest=json.loads((packets/"ADMIN_NOT_FOR_RATERS/assignment_AND_SOURCE_DO_NOT_SHARE.json").read_text())
    attest_source_manifest(admin_manifest=manifest,media_root=media)
    check(manifest["rater_assignment"]==assignment(),"A_B_ASSIGNMENT_INVALID")
    browser_records=[];paths=[]
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(
            channel="chrome",headless=True,
            args=["--no-sandbox","--autoplay-policy=no-user-gesture-required",
                                "--allow-file-access-from-files","--disable-dev-shm-usage"])
        try:
            for rid in RATERS:
                row,path=automate_one(browser,packets,rid,output)
                browser_records.append(row);paths.append(path)
        finally: browser.close()
    scratch=output/"SYNTHETIC_ONLY_NOT_TO_PUBLISH"
    scratch.mkdir()
    for p in paths:p.rename(scratch/p.name)
    imported=aggregate(
        admin_manifest=packets/"ADMIN_NOT_FOR_RATERS/assignment_AND_SOURCE_DO_NOT_SHARE.json",
        responses=scratch,output=output/"temporary_synthetic_import.json",source_dir=media)
    check(imported["state"]=="TWO_UNVERIFIED_SELF_REPORTS_NOT_HUMAN_STUDY_PASS"
          and len(imported["timestamped_issue_inventory_self_reported"])==4
          and imported["issue_counts_by_category_self_reported"]["readability"]==2
          and imported["issue_counts_by_category_self_reported"]["pedagogy"]==2
          and imported["student_ready"]==imported["publication"]=="BLOCKED",
          "BROWSER_TO_IMPORT_PIPELINE_UNVERIFIED")
    for p in scratch.iterdir():p.unlink()
    scratch.rmdir()
    (output/"temporary_synthetic_import.json").unlink()
    report={"checkpoint":"V3-26","engineering":"REAL_CHROMIUM_E2E_PASS",
            "browser_rater_packages":browser_records,
            "real_human_ratings":0,"human_participants":0,
            "human_study":"NOT_RUN","human_audio_quality":"UNMEASURED",
            "actual_independent_learning_gain":"UNMEASURED",
            "browser_ended_event_after_smoke_seek_not_real_full_watching":True,
            "synthetic_browser_response_json_retained":0,
            "v3_16_frozen_prereg":"UNCHANGED",
            "human_recruitment":"NOT_AUTHORIZED",
            "production":"BLOCKED","paid_api_calls":0}
    (output/"v3_26_browser_engineering_receipt.json").write_text(
        json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("V3_26_CHROMIUM=PASS file_url=2 real_h264_aac=4 real_playback=True")
    print("V3_26_UI=PASS rubric_download_import_missing_inputs_negative=True")
    print("V3_26_HUMANS=NOT_RUN participants=0 actual_ratings=0 release=BLOCKED")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--media-dir",type=Path,required=True)
    p.add_argument("--reviewer-packets",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    run(args.media_dir,args.reviewer_packets,args.output_dir)
