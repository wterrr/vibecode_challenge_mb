"""V3-25: runnable, locally hosted-free, masked-label exploratory reviewer packets.

Strictly *diagnostic* V3-22 vs V3-24 on ONE previously exposed Binary Search
lesson. This is not the frozen V3-16 12-topic V2D/V3 confirmatory experiment.
Ratings cannot be treated as human until independent consent/identity checks
occur outside this software. No publishing, model, network or participant actions.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
from statistics import mean

from .lesson_quality import QualityEvidenceError, _probe
from .native_hd_lesson import _source_evidence, verify_hd, _sha
from .teaching_storyboard import VIDEO, RECEIPT, verify_teaching_video

VERSION="v3-25-masked-reviewer-pair-v1"
STUDY="learnflow-v3-25-exposed-binary-search-exploratory"
SEED="v3-25-20261009-locked-before-human-responses"
RATERS=("R01","R02")
DIMS=(
    "clarity","representation_adequacy","pedagogy_sequence",
    "subtitle_readability","cognitive_load",
    "pointer_index_legibility","candidate_vs_leftmost_understanding",
    "audio_intelligibility","visual_hierarchy",
)
PRIMARY=("clarity","representation_adequacy")
ISSUE_CATEGORIES=("aesthetic","readability","pedagogy","technical","audio","no_issue")
ANCHORS={"1":"unusable/incorrect","2":"confusing",
         "3":"understandable with significant issues",
         "4":"clear, cohesive and accurate","5":"exemplary clarity and accuracy"}
TRANSFER={
    "A":"For sorted [1, 3, 3, 3, 8], what is the leftmost zero-based index of 3? Explain the leftward check.",
    "B":"For sorted [2, 2, 5, 7, 7], what is the leftmost zero-based index of 7? Explain the leftward check.",
}
SOURCE_FILES={
    "baseline":"native_hd/v3_22_binary_search_native_720p.mp4",
    "refined":"native_pedagogical/v3_24_leftmost_teaching_720p.mp4",
}

def require(ok:bool, code:str)->None:
    if not ok:raise QualityEvidenceError("V3_25_"+code)


def _read_json(path:Path)->dict:
    require(path.is_file() and not path.is_symlink(),"MISSING_OR_SYMLINKED_JSON")
    data=json.loads(path.read_text(encoding="utf-8"))
    require(type(data) is dict,"INVALID_JSON_OBJECT")
    return data


def canonical_media(root:Path)->dict:
    """Independently recompute source proof, true frame and copied AAC provenance."""
    source=root/"source_v3_20"
    baseline=root/SOURCE_FILES["baseline"]
    candidate=root/SOURCE_FILES["refined"]
    require(baseline.is_file() and candidate.is_file()
            and not baseline.is_symlink() and not candidate.is_symlink(),
            "MISSING_OR_SYMLINKED_REAL_VIDEO")
    v22=_read_json(root/"native_hd/v3_22_native_hd_receipt.json")
    v24=_read_json(root/"native_pedagogical"/RECEIPT)
    check22=verify_hd(source_folder=source,output=baseline,receipt=v22)
    check24=verify_teaching_video(source_folder=source,output=candidate,receipt=v24)
    require(len(check22["pointer_continuity"])==len(check24["settled_transition_checks"])==3,
            "SEMANTIC_CONTINUITY_NOT_CERTIFIED")
    common=("source_trace_sha256","original_srt_sha256","original_aac_packet_sha256")
    require(v22["source_trace_sha256"]==v24["source_trace_sha256"]
            and v22["subtitle_source_sha256"]==v24["original_srt_sha256"]
            and v22["audio_adts_sha256"]==v24["original_aac_packet_sha256"]
            and v22["event_proof_sha256"]==v24["source_event_proof_sha256"],
            "UNMATCHED_VISUAL_ONLY_ABLATION")
    for mp4 in (baseline,candidate):
        video,audio=_probe(mp4)
        require(int(video["width"])==1280 and int(video["height"])==720
                and video["r_frame_rate"]=="24/1" and int(video["nb_frames"])==1082,
                "INCOMPARABLE_VIDEO_TIMELINE")
    return {"baseline_sha256":_sha(baseline),
            "refined_sha256":_sha(candidate),
            "audio_packet_sha256":v22["audio_adts_sha256"],
            "source_trace_sha256":v22["source_trace_sha256"],
            "event_proof_sha256":v22["event_proof_sha256"],
            "subtitle_source_sha256":v22["subtitle_source_sha256"],
            "input_source":_sha(source/"after_v3_20_real_audio_video.mp4"),
            "size":[1280,720],"fps":24,"frames":1082,
            "source_case":"Binary Search target=15 leftmost index=5",
            "visual_only_change":True}


def assignment()->dict:
    # Equal exposure/order for TWO predeclared rater slots; hash determines
    # first ordering; complementary second slot. Not statistically blinded.
    parity=int(hashlib.sha256((SEED+"|"+RATERS[0]).encode()).hexdigest(),16)%2
    first=("baseline","refined") if parity==0 else ("refined","baseline")
    second=tuple(reversed(first))
    return {"R01":{"A":first[0],"B":first[1]},
            "R02":{"A":second[0],"B":second[1]}}


def make_manifest(root:Path)->dict:
    m=canonical_media(root)
    p=assignment()
    return {"checkpoint":"V3-25","version":VERSION,"study_id":STUDY,
            "scope":"EXPLORATORY_KNOWN_BINARY_SEARCH_SINGLE_TOPIC_ONLY",
            "excluded_from_frozen_v3_16_confirmatory_12_topic_benchmark":True,
            "masked_labels_not_double_blind":True,
            "human_recruitment_authorized":False,
            "participants_observed":0,
            "scores_observed":0,
            "independent_review_verified":"NOT_RUN",
            "outcome":"UNMEASURED",
            "student_ready":"BLOCKED",
            "production":"BLOCKED",
            "reviewer_slots":list(RATERS),"rater_assignment":p,
            "rubric_dimensions":list(DIMS),
            "co_primary":list(PRIMARY),
            "score_anchors":ANCHORS,"media":m,
            "word_level_alignment":"UNMEASURED",
            "human_learning_transfer":"UNMEASURED",
            "voice_rights":"UNVERIFIED","paid_provider_calls":0}


def _html(config:dict)->str:
    # Rendered as standalone file with locally linked *real* encoded videos.
    # No fetch, analytics, storage, external CSS, cookies, JS frameworks.
    payload=json.dumps(config,ensure_ascii=True,separators=(",",":")).replace("<","\\u003c")
    return r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>LearnFlow exploratory video review</title>
<style>
:root{font-family:system-ui,-apple-system,sans-serif;color:#eee;background:#111}
*{box-sizing:border-box}body{margin:0 auto;max-width:1200px;padding:28px}
header{border-bottom:1px solid #555;margin-bottom:20px}h1{font-size:1.7rem}
p,li{line-height:1.6;color:#cbd0d7}.warn{border-left:3px solid #e6b76b;padding:12px 18px;background:#24201b}
.section{border:1px solid #454545;border-radius:10px;padding:20px;margin:24px 0}
video{width:100%;max-height:80vh;background:black;border-radius:7px}
fieldset{border:0;margin:14px 0;padding:0}
label{display:block;margin-top:12px;color:#ddd}
input,textarea,select{font:inherit;border-radius:6px;padding:8px;max-width:100%;background:#292929;color:#fff;border:1px solid #777}
textarea{width:100%;min-height:76px}
button{padding:12px 22px;border-radius:6px;font:inherit;cursor:pointer;background:#b8dced;color:#101820}
small{color:#a9a9ae}.score{display:grid;grid-template-columns:minmax(260px,1fr) 160px;align-items:center;gap:10px}
</style></head><body>
<header><h1>LearnFlow visual explanation review</h1>
<p>Anonymous diagnostic feedback · two real, source-matched 720p lessons · no account or network required</p></header>
<div class="warn"><strong>Participation is not yet authorized.</strong>
This package is a dry-run instrument for future, separately consented reviewers. Do not use it to recruit
participants or claim scientific learning improvement. Variant labels are masked, but visual differences may reveal the condition.
Please avoid names, emails or other identifying information.</div>
<section class="section"><h2>Review environment</h2>
<label>Screen diagonal (inches) <input id="screen" type="number" min="4" max="120" step=".1"></label>
<label>Approx. viewing distance (cm) <input id="distance" type="number" min="10" max="1000"></label>
<p><small>Audio intelligibility can be affected by the playback device. Please use the same setup for both clips.</small></p>
<label><input id="consent" type="checkbox"> I have separately been invited and consented to an exploratory review, and will not claim my answers are an approved formal study.</label>
</section><div id="clips"></div>
<section class="section">
<h2>Download review response</h2><p>Scores must be entered for both videos. An exported JSON is a self-report,
not cryptographic proof of human identity, informed consent or actual watch time.
This page does not send data anywhere.</p>
<button id="export" type="button">Download JSON response</button>
<p id="status" role="status" aria-live="polite"></p>
</section>
<script>const config=__CONFIG__;
const clips=document.getElementById('clips');
const ids=['A','B'],dims=config.rubric_dimensions;
const watched={A:false,B:false};
const labels={
clarity:'How clear is the visual explanation?',
representation_adequacy:'Is this representation appropriate for the idea?',
pedagogy_sequence:'Does the explanation build in logical order?',
subtitle_readability:'Can you read the captions at your distance?',
cognitive_load:'How manageable is unnecessary mental load (5=low)?',
pointer_index_legibility:'Can you read LOW/HIGH/MID and array indices?',
candidate_vs_leftmost_understanding:'Does the candidate-to-leftmost logic make sense?',
audio_intelligibility:'Can you understand the spoken English?',
visual_hierarchy:'Do title, action, and example have clear priorities?'
};
for(const id of ids){
 const section=document.createElement('section');section.className='section';
 const h=document.createElement('h2');h.textContent='Video '+id;section.append(h);
 const vid=document.createElement('video');
 vid.controls=true;vid.preload='metadata';vid.playsInline=true;
 vid.src=config.video_sources[id];vid.setAttribute('aria-label','Video '+id);
 vid.addEventListener('ended',()=>{watched[id]=true;document.getElementById('seen-'+id).textContent='Player reached the end (self-report only).';});
 section.append(vid);
 const note=document.createElement('p');note.id='seen-'+id;
 note.textContent='Watch the complete video with sound before scoring.';section.append(note);
 for(const dim of dims){
  const row=document.createElement('div');row.className='score';
  const lbl=document.createElement('label');lbl.textContent=labels[dim]||dim;
  lbl.htmlFor=id+'-'+dim;
  const select=document.createElement('select');select.id=lbl.htmlFor;
  select.innerHTML='<option value="">Choose 1–5</option>'+[1,2,3,4,5].map(n=>'<option value="'+n+'">'+n+' — '+config.score_anchors[n]+'</option>').join('');
  row.append(lbl,select);section.append(row);
 }
 const critical=document.createElement('label');
 critical.textContent='Did you notice a critical factual/semantic error?';
 const radio=document.createElement('select');radio.id='critical-'+id;
 radio.innerHTML='<option value="">Choose</option><option value="no">No</option><option value="yes">Yes</option><option value="unsure">Unsure</option>';
 critical.append(radio);section.append(critical);
 const timestamp=document.createElement('label');timestamp.textContent='Timestamp of a positive or negative observation (seconds)';
 const when=document.createElement('input');when.type='number';when.id='timestamp-'+id;when.min='0';when.max='45.084';when.step='.001';timestamp.append(when);section.append(timestamp);
 const issueLabel=document.createElement('label');issueLabel.textContent='Primary type of this observation (for timestamped issue inventory)';
 const issueType=document.createElement('select');issueType.id='issue-category-'+id;
 issueType.innerHTML='<option value="">Select issue category</option>'+
 ['aesthetic','readability','pedagogy','technical','audio','no_issue']
 .map(v=>'<option value="'+v+'">'+v+'</option>').join('');
 issueLabel.append(issueType);section.append(issueLabel);
 const reasons=document.createElement('label');reasons.textContent='Why did you rate this video this way? Mention LOW/HIGH/MID or the duplicate example as appropriate.';
 const field=document.createElement('textarea');field.id='notes-'+id;field.maxLength=1500;reasons.append(field);section.append(reasons);
 const question=document.createElement('p');question.textContent='Unseen application check: '+config.transfer_items[id];section.append(question);
 const answer=document.createElement('textarea');answer.id='answer-'+id;answer.maxLength=500;section.append(answer);
 clips.append(section);
}
document.getElementById('export').addEventListener('click',()=>{
 const status=document.getElementById('status');status.textContent='';
 const screen=Number(document.getElementById('screen').value);
 const distance=Number(document.getElementById('distance').value);
 if(!document.getElementById('consent').checked || screen<4 || screen>120 || distance<10 || distance>1000){
  status.textContent='Provide consent confirmation and viewing device/distance.';return;}
 const scores={};
 for(const id of ids){
  if(!watched[id]){status.textContent='The player for Video '+id+' has not reached its end.';return;}
  const ratings={};
  for(const dim of dims){
   const val=Number(document.getElementById(id+'-'+dim).value);
   if(!Number.isInteger(val)||val<1||val>5){status.textContent='Missing rating: '+id+' / '+dim;return;}
   ratings[dim]=val;
  }
  const notes=document.getElementById('notes-'+id).value.trim();
  const answer=document.getElementById('answer-'+id).value.trim();
  const critical=document.getElementById('critical-'+id).value;
  const category=document.getElementById('issue-category-'+id).value;
  const stamp=Number(document.getElementById('timestamp-'+id).value);
  if(notes.length<15 || answer.length<4 || !['yes','no','unsure'].includes(critical) ||
      !['aesthetic','readability','pedagogy','technical','audio','no_issue'].includes(category) ||
      !document.getElementById('timestamp-'+id).value || stamp<0 || stamp>45.084){
   status.textContent='For '+id+', include critical-error response, a timestamp, observation (≥15 characters) and application answer.';return;}
  scores[id]={ratings,critical_error:critical,issue_category:category,
             observation_seconds:stamp,observation:notes,
             transfer_answer:answer,player_reached_end:true,
             media_sha256:config.media_sha256[id]};
 }
 const submission={schema_version:'v3-25-rater-response-v1',
  study_id:config.study_id,reviewer_id:config.reviewer_id,
  package_sha256:config.package_sha256,
  self_reported_consent:true,self_reported_independent_review:true,
  viewing_screen_inches:screen,viewing_distance_cm:distance,
  submissions:scores,submitted_at_utc:new Date().toISOString(),
  mechanism:'OFFLINE_BROWSER_SELF_REPORT_NOT_IDENTITY_PROOF'};
 const blob=new Blob([JSON.stringify(submission,null,2)+'\n'],{type:'application/json'});
 const link=document.createElement('a');link.href=URL.createObjectURL(blob);
 link.download=config.reviewer_id+'_review_response.json';
 link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000);
 status.textContent='JSON file created locally. Share only by an independently approved review channel.';
});
</script></body></html>""".replace("__CONFIG__",payload)


def _rater_config(manifest:dict,rid:str)->dict:
    mapping=manifest["rater_assignment"][rid]
    media=manifest["media"]
    digests={"baseline":media["baseline_sha256"],"refined":media["refined_sha256"]}
    out={
        "reviewer_id":rid,"study_id":STUDY,
        "video_sources":{"A":"clip_A.mp4","B":"clip_B.mp4"},
        "media_sha256":{k:digests[v] for k,v in mapping.items()},
        "rubric_dimensions":list(DIMS),"score_anchors":ANCHORS,
        "transfer_items":TRANSFER,
        "review_type":"EXPLORATORY_MASKED_LABELS_NOT_FULL_BLIND",
        "no_network":True,
    }
    # Bind assignment to study and exact pair, but hide actual variant labels
    # from the reviewer. SHA leaks variant only to somebody with study admin access.
    out["package_sha256"]=hashlib.sha256(json.dumps(
        out,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return out


def _validate_manifest(m:dict)->None:
    require(m["study_id"]==STUDY and m["version"]==VERSION
            and m["human_recruitment_authorized"] is False
            and m["participants_observed"]==m["scores_observed"]==0
            and m["independent_review_verified"]=="NOT_RUN"
            and m["student_ready"]==m["production"]=="BLOCKED"
            and m["excluded_from_frozen_v3_16_confirmatory_12_topic_benchmark"] is True
            and m["rater_assignment"]==assignment(),"FALSE_HUMAN_OR_BLINDING_CLAIM")


def create_packets(*,media_root:Path,output_dir:Path)->dict:
    require(output_dir.is_dir() and not output_dir.is_symlink(),"UNSAFE_OUTPUT_DIR")
    require(not list(output_dir.iterdir()),"DO_NOT_OVERWRITE_REVIEW_PACKET")
    m=make_manifest(media_root)
    _validate_manifest(m)
    # Admin holds identity mapping; NEVER ship the full folder to a rater.
    admin=output_dir/"ADMIN_NOT_FOR_RATERS"
    admin.mkdir()
    for rid in RATERS:
        root=output_dir/("REVIEWER_"+rid)
        root.mkdir()
        config=_rater_config(m,rid)
        for clip,variant in m["rater_assignment"][rid].items():
            path=media_root/SOURCE_FILES[variant]
            destination=root/("clip_"+clip+".mp4")
            shutil.copy2(path,destination)
            require(_sha(destination)==config["media_sha256"][clip],
                    "COPIED_VIDEO_SHA_DRIFT")
        (root/"review.html").write_text(_html(config),encoding="utf-8")
        (root/"README.txt").write_text(
            "Offline reviewer package. Only use after independent consent/recruitment authorization.\n"
            "Open review.html locally in your browser, play BOTH clips, score and export your JSON response.\n"
            "This folder has neither variant identity key nor a study result.\n",encoding="utf-8")
        (root/"packet_metadata.json").write_text(json.dumps({
            "checkpoint":"V3-25","study_id":STUDY,
            "reviewer_code":rid,"package_sha256":config["package_sha256"],
            "video_sha256":config["media_sha256"],
            "consent_and_human_review":"NOT_YET_AUTHORIZED"
        },indent=2)+"\n")
        require("baseline" not in (root/"review.html").read_text()
                and "refined" not in (root/"review.html").read_text(),
                "RATER_IDENTITY_LEAKED")
    (admin/"assignment_AND_SOURCE_DO_NOT_SHARE.json").write_text(
        json.dumps(m,indent=2)+"\n",encoding="utf-8")
    (admin/"EXPECTED_TRANSFER_ANSWERS_DO_NOT_SHARE.json").write_text(json.dumps({
        "A":{"leftmost":1,"explanation":"keep checking left after equality"},
        "B":{"leftmost":3,"explanation":"keep checking left after equality"},
        "warning":"Different probes + within-subject carryover mean NO causal transfer-gain inference"
    },indent=2)+"\n")
    # Output receipt itself must NEVER elevate human-quality/release.
    status={"checkpoint":"V3-25","study_id":STUDY,"state":"REVIEW_PACKAGES_CREATED_NOT_A_HUMAN_STUDY",
        "media":m["media"],"rater_slots":len(RATERS),
        "human_ratings":0,"human_participants":0,
        "visual_primary_metrics":"UNMEASURED",
        "unseen_learning_gain":"UNMEASURED",
        "commercial_rights":"UNVERIFIED",
        "publish":"BLOCKED","recruitment":"NOT_AUTHORIZED"}
    (output_dir/"engineering_receipt.json").write_text(json.dumps(status,indent=2)+"\n")
    return status


def attest_source_manifest(*,admin_manifest:dict,media_root:Path)->None:
    """Fail closed against a self-rehashed ADMIN JSON made for another video."""
    _validate_manifest(admin_manifest)
    require(admin_manifest.get("media")==canonical_media(media_root),
            "ADMIN_MANIFEST_DOES_NOT_MATCH_ACTUAL_SOURCE_MP4")


def inspect_submissions(*,admin_manifest:dict,responses:list[dict])->dict:
    """Fail closed; descriptive results cannot grant student readiness or release."""
    _validate_manifest(admin_manifest)
    accepted={}
    for record in responses:
        require(type(record) is dict and record.get("schema_version")=="v3-25-rater-response-v1"
                and record.get("study_id")==STUDY and record.get("reviewer_id") in RATERS,
                "SUBMISSION_SCHEMA_OR_REVIEWER")
        rid=record["reviewer_id"]
        require(rid not in accepted,"DUPLICATE_REVIEWER")
        cfg=_rater_config(admin_manifest,rid)
        require(record.get("package_sha256")==cfg["package_sha256"]
                and record.get("self_reported_consent") is True
                and record.get("self_reported_independent_review") is True
                and record.get("mechanism")=="OFFLINE_BROWSER_SELF_REPORT_NOT_IDENTITY_PROOF",
                "UNTRUSTED_RATER_PROVENANCE")
        a,b=record.get("viewing_screen_inches"),record.get("viewing_distance_cm")
        require(type(a) in (int,float) and 4<=a<=120
                and type(b) in (int,float) and 10<=b<=1000
                and record.get("submitted_at_utc"),"MISSING_VIEWING_CONTEXT")
        clips=record.get("submissions")
        require(type(clips) is dict and set(clips)=={"A","B"},
                "INCOMPLETE_TWO_CLIP_SESSION")
        for label,body in clips.items():
            require(type(body) is dict and body.get("media_sha256")==cfg["media_sha256"][label]
                    and body.get("player_reached_end") is True,
                    "VIDEO_SHA_OR_UNWATCHED")
            ratings=body.get("ratings")
            require(type(ratings) is dict and set(ratings)==set(DIMS)
                    and all(type(v) is int and 1<=v<=5 for v in ratings.values()),
                    "MISSING_OR_INVALID_RUBRIC")
            note=body.get("observation");answer=body.get("transfer_answer")
            t=body.get("observation_seconds")
            require(type(note) is str and 15<=len(note.strip())<=1500
                    and type(answer) is str and 4<=len(answer.strip())<=500
                    and type(t) in (float,int) and 0<=t<=45.084
                    and body.get("critical_error") in ("yes","no","unsure")
                    and body.get("issue_category","unclassified_legacy") in (*ISSUE_CATEGORIES,"unclassified_legacy"),
                    "MISSING_TIMESTAMP_OR_RATIONALE")
        accepted[rid]=record
    ready=(set(accepted)==set(RATERS))
    if not ready:
        return {"checkpoint":"V3-25","state":"NO_REAL_INDEPENDENT_RATINGS" if not responses else "INCOMPLETE_SELF_REPORTED_DATA",
                "received_submissions":len(accepted),
                "primary_metrics":"UNMEASURED",
                "human_independence_verified":False,
                "student_ready":"BLOCKED","publication":"BLOCKED"}
    outcomes={}
    for rid,record in accepted.items():
        assignment=admin_manifest["rater_assignment"][rid]
        for label,variant in assignment.items():
            outcomes[(rid,variant)]=record["submissions"][label]["ratings"]
    deltas={dim:[outcomes[(rid,"refined")][dim]-outcomes[(rid,"baseline")][dim]
                 for rid in RATERS] for dim in DIMS}
    disagreements={
        variant:[dim for dim in PRIMARY
                 if abs(outcomes[("R01",variant)][dim]-
                        outcomes[("R02",variant)][dim])>=2]
        for variant in SOURCE_FILES
    }
    inventory=[
        {"reviewer_code":rid,"source_label":label,
         "variant_admin_only":admin_manifest["rater_assignment"][rid][label],
         "timestamp_seconds":body["observation_seconds"],
         "category":body.get("issue_category","unclassified_legacy"),
         "critical_error_self_report":body["critical_error"],
         "observation_self_report":body["observation"]}
        for rid,record in sorted(accepted.items())
        for label,body in sorted(record["submissions"].items())
    ]
    category_counts={k:sum(1 for x in inventory if x["category"]==k)
                     for k in (*ISSUE_CATEGORIES,"unclassified_legacy")}
    # No 95% CI or student gain from n=2 self-reports. No automatic "human PASS".
    return {"checkpoint":"V3-25",
            "state":"TWO_UNVERIFIED_SELF_REPORTS_NOT_HUMAN_STUDY_PASS",
            "received_submissions":len(accepted),
            "descriptive_deltas_refined_minus_baseline":
              {k:{"values":v,"mean":mean(v)} for k,v in deltas.items()},
            "third_independent_adjudicator_required":any(disagreements.values()),
            "primary_rater_disagreements":disagreements,
            "timestamped_issue_inventory_self_reported":inventory,
            "issue_counts_by_category_self_reported":category_counts,
            "not_confirmatory_v3_16":True,
            "human_independence_verified":False,
            "unseen_learning_gain":"UNMEASURED",
            "student_ready":"BLOCKED","publication":"BLOCKED"}
