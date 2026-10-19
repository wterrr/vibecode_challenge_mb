#!/usr/bin/env python3
"""V3-89 six-film frozen-artifact masked review packet and human-only quality gate.

This is an evaluation *instrument*; no reviewer exists merely because CI
produced six usable clips. Mask checkpoint/dev labels, not educational content.
No LLM judging, arbitrary replay, substitute render, or invented human scores.
"""
from __future__ import annotations
import argparse
import csv
from collections import Counter,defaultdict
from hashlib import sha256
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/"benchmarks/learnflowbench/v3/v3_89_independent_review_preregister.json"
SCORE_AXES=("semantic_correctness","causal_continuity","readable_layout",
            "narration_visual_timing","pedagogical_usefulness")
FRAME_SIZE=(1280,720)
STATUS_PENDING="PENDING_HUMAN_REVIEW"


def need(ok,reason):
    if not ok:
        raise ValueError("V389_"+reason)


def sha(data):
    return sha256(data).hexdigest()


def registered():
    doc=json.loads(REG.read_text())
    need(doc["checkpoint"]=="V3-89" and
         doc["kind"]=="FIRST_CHILD_PREREG_BEFORE_IMPLEMENTATION" and
         doc["parent"]=={"draft_pr":125,"head_sha":"f6f66334bf4a40fae95af97667d43bf5e18453b5"},
         "UNFROZEN_SOURCE_PR")
    cases=doc["clips"]
    need(len(cases)==doc["machine_controls"]["frozen_denominator"]==6 and
         len({x["sha256"] for x in cases})==6 and
         len({x["case_id"] for x in cases})==6 and
         len(set(doc["masked_order"]))==6 and
         set(doc["masked_order"])==set(doc["reviewer_protocol"]["clip_ids"]),
         "BAD_PRELOCKED_BALANCED_CLIPS")
    families=Counter(x["family"] for x in cases)
    need(families=={"AFFINE":2,"FRACTION_EQUIVALENCE":2,"ORDERED_SEARCH":2},
         "NONBALANCED_REVIEW_FAMILIES")
    need(doc["constraints"]["production"]=="BLOCKED" and
         doc["constraints"]["no_model_api"] is True and
         doc["constraints"]["no_fabricated_human_scores"] is True,
         "RELEASE_BOUNDARY_CHANGED")
    return doc


def _archive_member(archive,member):
    names=archive.namelist()
    need(names.count(member)==1 and
         not member.startswith("/") and ".." not in Path(member).parts,
         "ARCHIVE_FILE_PATH_AMBIGUOUS")
    return archive.read(member)


def _real_probe(movie,expected_frames):
    p=subprocess.run(["ffprobe","-v","error","-count_frames","-show_entries",
                      "stream=codec_type,codec_name,width,height,r_frame_rate,nb_read_frames",
                      "-of","json",str(movie)],capture_output=True,text=True,timeout=80,check=True)
    tracks=json.loads(p.stdout)["streams"]
    v=[s for s in tracks if s.get("codec_type")=="video"]
    a=[s for s in tracks if s.get("codec_type")=="audio"]
    need(len(v)==len(a)==1 and v[0]["codec_name"]=="h264" and
         a[0]["codec_name"]=="aac" and
         (int(v[0]["width"]),int(v[0]["height"]))==FRAME_SIZE and
         v[0]["r_frame_rate"]=="15/1" and
         int(v[0]["nb_read_frames"])==expected_frames,
         "HISTORICAL_NATIVE_MP4_CODEC_FRAME_TAMPER")
    result=subprocess.run(["ffmpeg","-nostdin","-v","error","-xerror",
                           "-i",str(movie),"-map","0:v:0","-f","null","-"],
                          capture_output=True,timeout=160)
    need(result.returncode==0,"HISTORICAL_NATIVE_MP4_FULL_DECODE_FAIL")
    return {"frames":expected_frames,"codec":"h264/aac",
            "fps":15,"resolution":[1280,720],
            "full_video_decode":"PASS"}


def _snapshot(movie,at):
    frame=subprocess.run(["ffmpeg","-nostdin","-v","error","-ss",str(at),
                          "-i",str(movie),"-frames:v","1",
                          "-f","image2pipe","-vcodec","png","-"],
                         capture_output=True,timeout=35,check=True).stdout
    img=Image.open(io.BytesIO(frame))
    img.load()
    need(img.size==FRAME_SIZE,"WRONG_DECODED_REVIEW_SAMPLE_SIZE")
    return img.convert("RGB")


def _contact_strip(movie,masked_id,frames,destination):
    # Three predeclared relative positions: 15%, 50%, 85% of native frames.
    indexes=[int(frames*p) for p in (.15,.50,.85)]
    thumbs=[_snapshot(movie,(i+.35)/15).resize((480,270)) for i in indexes]
    sheet=Image.new("RGB",(1440,310),(10,14,23))
    for i,img in enumerate(thumbs):
        sheet.paste(img,(i*480,40))
    draw=ImageDraw.Draw(sheet)
    # Only neutral labels. Do not leak source family or version.
    draw.text((16,12),f"{masked_id}   /   review frames at 15%, 50%, 85%",
              fill=(230,230,230))
    sheet.save(destination,quality=91)
    return indexes


def _write_public_packet(public,clip_ids):
    instructions="""# Independent lesson review — six anonymized clips

These files are actual unmodified narrated educational MP4s from one project.
Names **mask checkpoint and development/held-out status only**. The mathematical
topic remains visible in the film; this is not a blinded placebo study or
double-blind trial. Do not infer a winner from the clip index.

View each entire film with audio before rating. There are five dimensions:
- semantic_correctness: does the depicted knowledge stay mathematically true?
- causal_continuity: do the same entities visibly change for a clear reason?
- readable_layout: are labels, diagrams and states legible and unambiguous?
- narration_visual_timing: does the changing graphic occur while explained?
- pedagogical_usefulness: would this actually improve a student's intuition?

Rate each dimension as an integer **1** (very poor) to **5** (excellent).
Use 3 for adequate and 4 for good; reserve 5 for exceptional.
If uncertain, describe exact timestamp in notes and score conservatively.
Two distinct people must independently fill every clip; participants should
not see each other's ratings before submission. Pseudonymous reviewer IDs
are acceptable; do not include emails, names or other private identifiers.

Fill the CSV and return it to the project owner. Blank cells mean **UNRATED**.
This packet does not authorize model/AI auto-rating or claim educational gain.
"""
    (public/"README_FOR_REVIEWERS.md").write_text(instructions)
    names=["reviewer_id","clip_id",*SCORE_AXES,"notes"]
    with (public/"BLANK_human_review_scores.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=names)
        w.writeheader()
        for clip in sorted(clip_ids):
            for _ in range(2):
                w.writerow({"clip_id":clip})


def evaluate_human_reviews(path,doc):
    """Only an actually supplied, validated score CSV can move human quality."""
    ids=set(doc["reviewer_protocol"]["clip_ids"])
    if path is None:
        return {"state":STATUS_PENDING,"count_human_ratings":0,
                "reason":"NO_REAL_HUMAN_SUBMISSIONS_RECEIVED",
                "individual_video_quality":"UNRATED","learner_gain":"NOT_MEASURED"}
    need(path.is_file(),"HUMAN_REVIEW_FILE_NOT_FOUND")
    with path.open(newline="") as f:
        reader=csv.DictReader(f)
        need(reader.fieldnames==["reviewer_id","clip_id",*SCORE_AXES,"notes"],
             "HUMAN_RATING_SCHEMA_INVALID")
        rows=list(reader)
    ratings=defaultdict(list)
    for row in rows:
        clip=row["clip_id"];who=row["reviewer_id"].strip()
        need(clip in ids and 2<=len(who)<=48 and
             not any(k=="@" for k in who),
             "REVIEWER_OR_CLIP_IDENTIFIER_INVALID")
        nums=[]
        for key in SCORE_AXES:
            raw=row[key]  # strict exact integer strings; no silent whitespace correction
            need(raw in ("1","2","3","4","5"),"HUMAN_RATING_NOT_INTEGER_1_TO_5")
            nums.append(int(raw))
        need(who not in {x["reviewer_id"] for x in ratings[clip]},
             "DUPLICATE_REVIEWER_FOR_SAME_CLIP")
        ratings[clip].append({"reviewer_id":who,"scores":nums})
    need(set(ratings)==ids and all(len(ratings[k])>=2 for k in ids),
         "HUMAN_REVIEW_NOT_INDEPENDENT_TWO_RATERS_EACH_CLIP")
    summaries={}
    ok=True
    for clip in sorted(ids):
        group=ratings[clip]
        # For odd or even n, inclusive median; no external numeric libraries.
        medians=[]
        for axis in range(len(SCORE_AXES)):
            seq=sorted(x["scores"][axis] for x in group)
            k=len(seq)//2
            medians.append(seq[k] if len(seq)%2 else (seq[k-1]+seq[k])/2)
        total=sum(sum(x["scores"]) for x in group)/(len(group)*len(SCORE_AXES))
        bad_semantic=any(x["scores"][0]<=2 for x in group)
        met=all(v>=3 for v in medians) and total>=4 and not bad_semantic
        ok=ok and met
        summaries[clip]={"rater_count":len(group),"axis_medians":dict(zip(SCORE_AXES,medians)),
                         "all_axes_mean":round(total,4),"semantic_low_flag":bad_semantic,
                         "rubric_threshold_met":met}
    return {"state":"HUMAN_RUBRIC_THRESHOLD_MET_ONLY" if ok else "NOT_ACCEPTED",
            "count_human_ratings":len(rows),"per_clip":summaries,
            "note":"Reviewers are user-supplied pseudonyms; actual independence cannot be established by code.",
            "learner_gain":"NOT_MEASURED","production":"BLOCKED"}


def run(v387:Path,v388:Path,out:Path,human_file=None):
    doc=registered()
    need(not out.exists(),"OUTPUT_DIRECTORY_MUST_BE_FRESH")
    need(v387.is_file() and v388.is_file(),"HISTORICAL_CI_ARTIFACT_ZIP_MISSING")
    public=out/"reviewer_packet"
    admin=out/"admin_only"
    public.mkdir(parents=True)
    admin.mkdir(parents=True)
    inputs={"V3-87":v387,"V3-88":v388}
    mappings=[]
    with zipfile.ZipFile(v387) as a87,zipfile.ZipFile(v388) as a88:
        sources={"V3-87":a87,"V3-88":a88}
        v87=json.loads(_archive_member(a87,"v387_final_report.json"))
        v88=json.loads(_archive_member(a88,"v388_final_report.json"))
        need(v87["checkpoint"]=="V3-87" and v87["source_supported_native"]==3 and
             v87["abstained"]==2 and
             v88["checkpoint"]=="V3-88" and v88["native_pass"]==4 and
             v88["negative_abstain"]==4 and v88["heldout_pass"]==2,
             "HISTORICAL_SOURCE_DENOMINATOR_DRIFT")
        for case,masked in zip(doc["clips"],doc["masked_order"],strict=True):
            archive=sources[case["src_checkpoint"]]
            raw=_archive_member(archive,case["mp4_path"])
            need(sha(raw)==case["sha256"],"NATIVE_VIDEO_SHA256_ORIGIN_CHANGED")
            receipt=json.loads(_archive_member(archive,case["case_id"]+"/native_result_receipt.json"))
            prior_key=("mp4_sha256" if case["src_checkpoint"]=="V3-87"
                       else "native_mp4_sha256")
            need(receipt[prior_key]==case["sha256"] and
                 receipt["id"]==case["case_id"] and
                 receipt["full_native_decode"]=="PASS",
                 "PREVIOUS_REAL_CI_NATIVE_RECEIPT_INCONSISTENT")
            movie=public/(masked+".mp4")
            movie.write_bytes(raw) # identical bytes: NO MEDIA EDITS.
            probe=_real_probe(movie,case["frames"])
            positions=_contact_strip(movie,masked,case["frames"],public/(masked+"_3frames.jpg"))
            mappings.append({**case,"masked_id":masked,
                             "actual_sha256":sha(movie.read_bytes()),
                             "media_validation":probe,
                             "sampled_native_frame_indices":positions})
    _write_public_packet(public,doc["reviewer_protocol"]["clip_ids"])
    assessment=evaluate_human_reviews(human_file,doc)
    admin_report={
        "checkpoint":"V3-89",
        "source_artifact_numbers":[12020402722,12157931417],
        "frozen_source_head":{"V3-87":"94836da45b53499052bd3ccad7cf2a349cb1f2ff",
                              "V3-88":"f6f66334bf4a40fae95af97667d43bf5e18453b5"},
        "verified_actual_native_clip_count":len(mappings),
        "family_balance":dict(Counter(x["family"] for x in mappings)),
        "verified_clip_mapping":mappings,
        "blinding_type":"LABEL_MASKING_ONLY_NOT_DOUBLE_BLIND",
        "film_editing":"NONE_ORIGINAL_SHA256_IDENTICAL",
        "machine_native_evidence":"PASS",
        "real_human_acceptance":assessment,
        "reviewer_count_verified_in_real_world":"UNKNOWN",
        "final_visual_quality":("NOT_PASS_UNTIL_VALID_HUMAN_REVIEW"
                                if assessment["state"]==STATUS_PENDING
                                else "SUBMITTED_HUMAN_RUBRIC_ONLY_NOT_EXPERT_PARITY"),
        "autonomous_llm_authoring":"NOT_TESTED",
        "learner_gain":"NOT_MEASURED",
        "model_api_requests":0,"production":"BLOCKED"
    }
    (admin/"clip_reveal_key_AND_SHA_RECEIPTS.json").write_text(json.dumps(admin_report,indent=2)+"\n")
    machine={k:v for k,v in admin_report.items() if k!="verified_clip_mapping"}
    (admin/"v389_acceptance_status.json").write_text(json.dumps(machine,indent=2)+"\n")
    # Any anonymous reviewer packet must not include admin answer key.
    need(all("v387" not in p.name.lower() and "v388" not in p.name.lower()
             and "heldout" not in p.name.lower() and "development" not in p.name.lower()
             for p in public.iterdir()),"PUBLIC_REVIEWER_FILENAME_LEAK")
    print(json.dumps({"checkpoint":"V3-89","verified_clips":len(mappings),
                      "source_families":3,"technical_media_integrity":"PASS",
                      "human_quality_gate":assessment["state"],
                      "human_ratings":assessment["count_human_ratings"],
                      "production":"BLOCKED"},indent=2))
    return admin_report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--v387-archive",required=True,type=Path)
    p.add_argument("--v388-archive",required=True,type=Path)
    p.add_argument("--output-dir",required=True,type=Path)
    p.add_argument("--human-review-file",type=Path)
    args=p.parse_args()
    run(args.v387_archive,args.v388_archive,args.output_dir,args.human_review_file)
