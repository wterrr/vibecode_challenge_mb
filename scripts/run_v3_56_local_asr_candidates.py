#!/usr/bin/env python3
"""V3-56 OPTIONAL native local-ASR experiment (NOT executed in V3-56: weights absent).

No model name, remote download, external provider call, pretrained weights in repository,
or automatic publication of machine transcript. Produce an ASR CANDIDATE only.
Requires locally preinstalled faster-whisper and a *verified*, licensed CTranslate2
English model directory with model.bin; user/media rights apply independently.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
PREG=ROOT/"research/v3_56_native_speech_grounding_preregister.json"
MEDIA_SHA="439e154fffbb8696a37753d765c4f64bc06d25fbb17cb3d98bcc842045d85cb9"


def sha_file(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()


def require_local_model(model_dir,licence_receipt):
    folder=Path(model_dir).resolve(strict=True)
    weights=folder/"model.bin"
    if not folder.is_dir() or not weights.is_file():
        raise RuntimeError("ASR_LOCAL_MODEL_WEIGHTS_MISSING")
    m=json.loads(Path(licence_receipt).read_text(encoding="utf-8"))
    if m.get("model_sha256")!=sha_file(weights) or not m.get("model_source") or not m.get("license"):
        raise RuntimeError("ASR_MODEL_HASH_LICENSE_NOT_VERIFIED")
    if not m.get("redistribution_cleared_or_local_use_permitted"):
        raise RuntimeError("ASR_MODEL_RIGHTS_NOT_CLEARED")
    return folder, m


def run(args):
    preg=json.loads(PREG.read_text(encoding="utf-8"))
    video=Path(args.video).resolve(strict=True)
    if sha_file(video)!=MEDIA_SHA or preg["video"]["sha256"]!=MEDIA_SHA:
        raise RuntimeError("ORIGINAL_VIDEO_SHA_MISMATCH")
    model_path,license_info=require_local_model(args.model_dir,args.model_license)
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("ASR_RUNTIME_UNAVAILABLE__NO_MODEL_API_FALLBACK") from exc
    model=WhisperModel(str(model_path),device="cpu",compute_type="int8",local_files_only=True)
    cues={
        "mole":109,"running_sentence":269,"query_motivating":357,
        "query_to_key":458,"score_matrix":514,"softmax":589,"mask":691,
        "values":815,"weighting":862,"multihead":1231,"output":1349,
        "return_context":1413
    }
    assert list(cues)==preg["locked_anchor_order"]
    result={"checkpoint":"V3-56","input_sha256":MEDIA_SHA,
            "asr_model_sha256":license_info["model_sha256"],
            "asr_license":license_info["license"],
            "asr_model_source":license_info["model_source"],
            "input_rights":"USER_UPLOADED_MEDIA_NOT_COPIED_TO_GIT",
            "scope":"OFFLINE_ASR_CANDIDATE_NOT_NATIVE_GROUND_TRUTH",
            "manually_heard_and_verified":False,
            "native_word_level_alignment":"UNVERIFIED",
            "segments":[]}
    with tempfile.TemporaryDirectory(prefix="v356_asr_private_") as tmp:
        for anchor,cue in cues.items():
            start=max(0,cue-10)
            duration=50
            wav=Path(tmp)/(anchor+".wav")
            subprocess.run(["ffmpeg","-nostdin","-v","error","-ss",str(start),
                "-t",str(duration),"-i",str(video),"-vn","-ac","1","-ar","16000",
                "-y",str(wav)],check=True,timeout=80)
            segments,info=model.transcribe(str(wav),language="en",beam_size=3,
                condition_on_previous_text=False,word_timestamps=True)
            records=[]
            for s in segments:
                words=[{"word":w.word,"approx_start_s":round(start+w.start,2),
                        "approx_end_s":round(start+w.end,2)} for w in (s.words or [])
                        if w.start is not None and w.end is not None]
                records.append({"approx_start_s":round(start+s.start,2),
                    "approx_end_s":round(start+s.end,2),"text":s.text,
                    "words_candidate_only":words})
            result["segments"].append({"anchor_id":anchor,"caption_proxy_s":cue,
                "audio_slice_s":[start,start+duration],"candidate_segments":records,
                "native_audio_human_verification":"REQUIRED_BEFORE_PROMOTION"})
    out=Path(args.output).resolve()
    if str(out).startswith(str(ROOT)) and not args.allow_private_local_repo:
        raise RuntimeError("ASR_TRANSCRIPT_PRIVATE_OUTPUT_OUTSIDE_REPO_REQUIRED")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--video",required=True)
    p.add_argument("--model-dir",required=True,help="LOCAL verified CTranslate2 model directory, never a remote model alias")
    p.add_argument("--model-license",required=True,help="JSON model_source, license, model_sha256, redistribution_cleared_or_local_use_permitted")
    p.add_argument("--output",required=True,help="Private local path, do not commit transcripts")
    p.add_argument("--allow-private-local-repo",action="store_true",help="not recommended")
    args=p.parse_args()
    run(args)
    print("ASR_CANDIDATES_WRITTEN__NOT_NATIVE_WORD_GROUND_TRUTH")


if __name__=="__main__":
    main()
