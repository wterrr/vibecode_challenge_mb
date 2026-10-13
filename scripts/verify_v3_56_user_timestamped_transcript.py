#!/usr/bin/env python3
"""Verify scoped 3B1B user transcript timecodes vs original native-film witness receipts.

Default CI verifies provenance records only. With --source-path, also recomputes
SHA-256 and all 449 source segments against the actual user-provided transcript.
With --video-path, verifies full original MP4 SHA-256 (not ASR / native word sync).
No original transcript, 3B1B frames, or copyrighted media stored in repository.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RECEIPT=ROOT/"research/v3_56_user_timestamped_transcript_receipt.json"
PREVIOUS=ROOT/"research/v3_56_attention_native_caption_alignment.json"
TRANSCRIPT_SHA="4a6eed896d548af41526e4995b66d7ef35951a6bfdfe1d106ee8764d2a98f3a5"
VIDEO_SHA="439e154fffbb8696a37753d765c4f64bc06d25fbb17cb3d98bcc842045d85cb9"
ANCHORS=["mole","running_sentence","query_motivating","query_to_key","score_matrix","softmax",
         "mask","values","weighting","multihead","output","return_context"]
TIME_RE=re.compile(r"\((\d{1,2}):(\d{2})\)")


def require(cond, label):
    if not cond:
        raise AssertionError("V356_USER_TRANSCRIPT_"+label)


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):
            h.update(b)
    return h.hexdigest()


def parse_timestamp_segments(text):
    matches=list(TIME_RE.finditer(text))
    require(bool(matches),"MISSING_TIMESTAMPS")
    out=[]
    for i,m in enumerate(matches):
        t=60*int(m.group(1))+int(m.group(2))
        require(int(m.group(2))<60,"INVALID_SECONDS")
        s=text[m.end():(matches[i+1].start() if i+1<len(matches) else len(text))]
        fragment=s.strip().replace("\n"," ")
        out.append({"t":t,"line":text.count("\n",0,m.start())+1,
                    "event_index":i,"segment_sha256":sha_bytes(fragment.encode("utf-8"))})
    times=[p["t"] for p in out]
    require(times==sorted(set(times)),"NON_MONOTONIC_OR_DUPLICATE")
    return out


def validate_receipt(doc, previous):
    src=doc["source"]
    vid=doc["native_video"]
    require(doc["checkpoint"]=="V3-56" and doc["pr_number"]==90,"WRONG_SCOPE")
    require(src["origin"]=="USER_UPLOADED_TRANSCRIPT_TEXT_WITH_TIMECODES" and
            src["file_sha256"]==TRANSCRIPT_SHA and
            src["file_bytes"]==31405 and src["parsed_timestamped_segments"]==449 and
            src["distinct_timestamps"]==449 and src["first_transcript_time_s"]==0 and
            src["last_transcript_cue_s"]==1545 and src["timecodes_monotonic"] is True,
            "SOURCE_METADATA")
    require(src["asr_engine_model_or_human_verification_provenance"]=="NOT_PROVIDED" and
            src["not_verified_against_native_pcm"] is True,"UNSUPPORTED_ASR_CLAIM")
    require(vid["sha256"]==VIDEO_SHA and abs(vid["duration_s"]-1569.191429)<0.001 and
            vid["source_evidence_level"]=="ACTUAL_NATIVE_VISIBLE_FRAME_SAMPLES",
            "VIDEO_PROVENANCE")
    old={r["anchor_id"]:r for r in previous["alignment_rows"]}
    rows=doc["rows"]
    require(len(rows)==12 and [x["anchor_id"] for x in rows]==ANCHORS and
            set(old)==set(ANCHORS),"ANCHOR_SET")
    for row in rows:
        t=row["user_transcript_cue_s"]
        a,b=row["video_sampled_visible_change_interval_s"]
        require(isinstance(t,int) and 0<=t<=1545,"TIMECODE_INVALID")
        require(isinstance(a,int) and isinstance(b,int) and b-a==2 and
                0<=a<b<vid["duration_s"],"NATIVE_WITNESS_BOUND")
        require(row["transcript_cue_to_visible_window_offset_s"]==[a-t,b-t] and
                row["caption_to_video_relation_classification"]=="PROVISIONAL_TRANSCRIPT_TO_VIDEO_ONLY",
                "ILLEGITIMATE_SPEECH_DELAY")
        for key in ("source_segment_utf8_sha256","native_decoded_luma_sha256"):
            require(re.fullmatch(r"[0-9a-f]{64}",row[key]) is not None,"HASH_FIELD")
        require(row["source_event_index_zero_based"]>=0 and
                1<=row["source_file_line"]<=64,"SOURCE_EVENT_LOCATION")
        require(row["native_decoded_frame_at_s"]>=0 and
                row["native_decoded_frame_at_s"]<vid["duration_s"] and
                row["native_visual_witness_vi"],"NATIVE_FRAME_DESCRIPTION")
        require(row["speech_words_verified_in_native_audio"] is False and
                row["actual_speech_onset_s"] is None and
                row["native_word_alignment_accuracy"] is None,
                "FAKE_NATIVE_SPEECH")
    g=doc["conclusion"]
    require(doc["rigor"]["native_word_alignment_count"]==0 and
            doc["rigor"]["text_to_native_visual_correspondence_count"]==12 and
            doc["rigor"]["no_model_api"] is True and
            doc["rigor"]["production"]=="BLOCKED" and
            g["twelve_anchors_temporal_text_to_native_frame_grounding"]=="BOUNDED_PASS" and
            g["independent_native_audio_word_accuracy"]=="NO_GO" and
            g["reliable_native_word_level_alignment"]=="NOT_VERIFIED" and
            g["production"]=="BLOCKED",
            "FAKE_GO")
    return {"checkpoint":"V3-56","timestamped_segments":449,"anchors":12,
            "user_supplied_text_native_frame_correspondence":"BOUNDED_PASS",
            "independent_native_speech_alignment":"NO_GO",
            "core_or_production_changed":False,"model_api_calls":0,
            "production":"BLOCKED"}


def check(source_path=None,video_path=None):
    doc=json.loads(RECEIPT.read_text(encoding="utf-8"))
    old=json.loads(PREVIOUS.read_text(encoding="utf-8"))
    result=validate_receipt(doc,old)
    if source_path is not None:
        raw=Path(source_path)
        require(file_sha(raw)==TRANSCRIPT_SHA,"SOURCE_HASH_MISMATCH")
        parsed=parse_timestamp_segments(raw.read_text(encoding="utf-8"))
        require(len(parsed)==449,"TIMESTAMP_COUNT")
        require([p["t"] for p in parsed][0]==0 and parsed[-1]["t"]==1545,
                "TIMESTAMP_RANGE")
        for row in doc["rows"]:
            event=parsed[row["source_event_index_zero_based"]]
            require(event["t"]==row["user_transcript_cue_s"] and
                    event["line"]==row["source_file_line"] and
                    event["segment_sha256"]==row["source_segment_utf8_sha256"],
                    "SEGMENT_MISMATCH")
        result["original_transcript_hash_and_12_segments"]="PASS"
    if video_path is not None:
        require(file_sha(video_path)==VIDEO_SHA,"VIDEO_HASH_MISMATCH")
        result["original_video_hash"]="PASS"
    return result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-path",default=None,help="User upload; optional in CI, never commit")
    ap.add_argument("--video-path",default=None,help="Original full MP4; optional in CI, never commit")
    args=ap.parse_args()
    print(json.dumps(check(args.source_path,args.video_path),ensure_ascii=False,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
