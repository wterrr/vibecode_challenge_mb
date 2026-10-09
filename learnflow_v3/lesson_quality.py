"""V3-21: independent, bounded *media* quality audit of real V3-20 artifacts.

Never conflates physical utterance start, audible PCM energy or black-board
pixels with word-forced alignment, intelligibility, human learning or 3B1B parity.
Fail closed on tampering; report observed defects and explicitly blocked gates.
No external models, provider calls or video modification.
"""
from __future__ import annotations

from array import array
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

from PIL import Image, ImageDraw, ImageStat, ImageChops

VERSION = "v3-21-real-media-quality-v1"
FILES = {
    "before": ("before_v3_19_real_audio_video.mp4", "before_v3_19.receipt.json", "before_v3_19.srt"),
    "after": ("after_v3_20_real_audio_video.mp4", "after_v3_20.receipt.json", "after_v3_20.srt"),
}
SRT_LINE = re.compile(r"^(\d\d):(\d\d):(\d\d),(\d\d\d) --> (\d\d):(\d\d):(\d\d),(\d\d\d)$")


class QualityEvidenceError(ValueError):
    """Corrupt source evidence must not become a passing quality report."""


def _require(test: bool, name: str) -> None:
    if not test:
        raise QualityEvidenceError("V3_21_" + name)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _call(argv: list[str], timeout: int = 150) -> bytes:
    p = subprocess.run(argv, capture_output=True, timeout=timeout, check=False)
    _require(p.returncode == 0, "MEDIA_DECODE_FAILURE")
    return p.stdout


def _probe(path: Path) -> tuple[dict, dict]:
    result = json.loads(_call([
        "ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(path)], timeout=25))
    video = next((s for s in result["streams"] if s["codec_type"] == "video"), None)
    audio = next((s for s in result["streams"] if s["codec_type"] == "audio"), None)
    _require(video is not None and audio is not None, "MISSING_AUDIO_OR_VIDEO")
    _require(video["codec_name"] == "h264" and audio["codec_name"] == "aac",
             "UNEXPECTED_MEDIA_CODECS")
    return video, audio


def _seconds(stamp: str) -> float:
    m = re.fullmatch(r"(\d\d):(\d\d):(\d\d),(\d\d\d)", stamp)
    _require(m is not None, "BAD_SRT_TIMESTAMP")
    h, mm, ss, ms = map(int, m.groups())
    _require(mm < 60 and ss < 60, "BAD_SRT_CLOCK")
    return 3600*h + 60*mm + ss + ms/1000


def parse_srt(path: Path) -> list[tuple[float, float, str]]:
    raw = path.read_text(encoding="utf-8-sig").strip()
    chunks = re.split(r"\n\s*\n", raw)
    out = []
    for index, chunk in enumerate(chunks, start=1):
        lines = chunk.splitlines()
        _require(len(lines) >= 3 and lines[0].strip() == str(index), "SRT_CUE_ID")
        pieces = lines[1].split(" --> ")
        _require(len(pieces) == 2, "SRT_CUE_FORMAT")
        a, b = (_seconds(x) for x in pieces)
        text = " ".join(line.strip() for line in lines[2:])
        _require(text and a < b and (not out or a >= out[-1][1] - .003),
                 "SRT_OVERLAP_OR_EMPTY")
        out.append((a, b, text))
    return out


def _pcm(path: Path) -> array:
    raw = _call(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path),
                 "-map", "0:a:0", "-ac", "1", "-ar", "16000",
                 "-f", "s16le", "pipe:1"], timeout=150)
    _require(len(raw) >= 32000 and len(raw) % 2 == 0, "EMPTY_DECODED_PCM")
    a = array("h")
    a.frombytes(raw)
    return a


def _audio_metrics(samples: array, segments: list[dict]) -> dict:
    overall_peak = max(abs(x) for x in samples) / 32768
    clipped = sum(abs(x) >= 31130 for x in samples)
    entries = []
    for p in segments:
        start = int(round(p["seconds_start"] * 16000))
        end = int(round((p["seconds_start"] + p["raw_spoken_duration_seconds"]) * 16000))
        chunk = samples[start:end]
        _require(len(chunk) > 4000, "SPEECH_INTERVAL_TOO_SHORT")
        energy = math.sqrt(sum(float(x)*x for x in chunk)/len(chunk)) / 32768
        words = len(p["text"].split())
        wpm = 60 * words / p["raw_spoken_duration_seconds"]
        entries.append({
            "event_kind": p.get("event_kind", p["role"]),
            "start_seconds": round(p["seconds_start"], 3),
            "spoken_duration_seconds": round(p["raw_spoken_duration_seconds"], 3),
            "words": words,
            "words_per_minute": round(wpm, 1),
            "decoded_aac_rms": round(energy, 6),
        })
        _require(energy >= .004, "SILENT_SPOKEN_EVENT")
    return {
        "decoded_pcm_sample_rate": 16000, "decoded_pcm_samples": len(samples),
        "peak_normalized": round(overall_peak, 6),
        "over_95pct_full_scale_samples": clipped,
        "utterances": entries,
    }


def _frames(path: Path, width: int, height: int, indices: list[int]) -> list[Image.Image]:
    _require(indices == sorted(set(indices)) and len(indices) < 35,
             "INVALID_SAMPLING_REQUEST")
    expression = "+".join(f"eq(n\\,{k})" for k in indices)
    data = _call(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path),
                  "-vf", "select=" + expression,
                  "-vsync", "0", "-pix_fmt", "rgb24", "-f", "rawvideo",
                  "pipe:1"], timeout=180)
    frame_size = width * height * 3
    _require(len(data) == frame_size * len(indices), "UNEXPECTED_SAMPLED_FRAME_COUNT")
    return [Image.frombytes("RGB", (width,height),
                            data[i*frame_size:(i+1)*frame_size])
            for i in range(len(indices))]


def _contact_sheet(frames: list[Image.Image], labels: list[str], out: Path) -> None:
    # Full native resolution per thumbnail; annotation OUTSIDE the video canvas.
    width, height = frames[0].size
    cols = 2
    rows = math.ceil(len(frames)/cols)
    result = Image.new("RGB", (cols*width, rows*(height+30)), (20,20,20))
    d = ImageDraw.Draw(result)
    for i,(frame,label) in enumerate(zip(frames,labels,strict=True)):
        x = (i%cols)*width
        y = (i//cols)*(height+30)
        result.paste(frame,(x,y))
        d.text((x+8,y+height+7),label,fill=(230,230,230))
    result.save(out, quality=90)


def audit_media(folder: Path, *, contact_sheet: Path | None = None) -> dict:
    """Evaluate actual bytes and produce a *blocked* educational-release scorecard.

    No user-supplied PASS statuses. All authored thresholds are diagnostic,
    not substitutes for a prospective blinded user study.
    """
    directory = Path(folder)
    comparison_file = directory/"v3_20_before_after_qa.json"
    _require(comparison_file.is_file(), "MISSING_SOURCE_COMPARISON")
    comparison = json.loads(comparison_file.read_text(encoding="utf-8"))
    _require(comparison.get("checkpoint") == "V3-20"
             and comparison.get("production_release") == "BLOCKED"
             and comparison.get("word_level_alignment") == "UNMEASURED"
             and comparison.get("human_pedagogy_quality") == "UNMEASURED",
             "FABRICATED_BASELINE_CLAIMS")
    profiles = {}
    for key, (name, receipt_name, srt_name) in FILES.items():
        video_path, receipt_path, subtitle_path = (
            directory/name, directory/receipt_name, directory/srt_name)
        _require(all(p.is_file() and not p.is_symlink()
                     for p in (video_path,receipt_path,subtitle_path)),
                 "MISSING_MEDIA_SOURCE")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        _require(_sha(video_path) == receipt["video_sha256"]
                 and _sha(subtitle_path) == receipt["subtitle_sha256"]
                 and receipt["source_trace_sha256"]
                    == comparison[key]["source_trace_sha256"],
                 "RECEIPT_SOURCE_OR_HASH_MISMATCH")
        video, audio = _probe(video_path)
        n, w, h = int(video["nb_frames"]), int(video["width"]), int(video["height"])
        _require(n == receipt["total_frames"] and w*9 == h*16,
                 "MEDIA_DIMENSION_OR_FRAME_DRIFT")
        _require(video["r_frame_rate"] == "12/1"
                 and abs(n/12-receipt["duration_seconds"]) < .002,
                 "VIDEO_RATE_OR_DURATION_DRIFT")
        cues = parse_srt(subtitle_path)
        _require(len(cues) == len(receipt["segments"]), "SUBTITLE_EVENT_COUNT_DRIFT")
        prev_end = 0
        for i,(cue, event) in enumerate(zip(cues,receipt["segments"],strict=True)):
            start,end,text = cue
            _require(event["frame_start"] == prev_end
                     and event["frame_end_exclusive"] > prev_end,
                     "VIDEO_EVENT_FRAME_SEQUENCE")
            _require(text == event["text"]
                     and abs(start-event["subtitle_start"]) <= .002
                     and abs(end-event["subtitle_end"]) <= .002,
                     "SUBTITLE_SPOKEN_EVENT_DRIFT")
            if key == "after":
                _require(event.get("event_id") and event.get("event_kind"),
                         "AFTER_EVENT_IDENTITY_MISSING")
            prev_end = event["frame_end_exclusive"]
        _require(abs(prev_end-n) <= 1, "EVENT_VIDEO_END_MISMATCH")
        audio_measure = _audio_metrics(_pcm(video_path),receipt["segments"])
        _require(audio_measure["over_95pct_full_scale_samples"] == 0,
                 "AUDIBLE_PCM_CLIPPING")
        profiles[key] = {
            "video_sha256": _sha(video_path), "srt_sha256": _sha(subtitle_path),
            "width": w, "height": h, "fps": 12, "frame_count": n,
            "duration_seconds": round(n/12,6), "speech": audio_measure,
            "utterance_count": len(receipt["segments"])
        }
    before, after = profiles["before"], profiles["after"]
    _require(comparison["before"]["sha256"] == before["video_sha256"]
             and comparison["after"]["sha256"] == after["video_sha256"],
             "SAME_SOURCE_VIDEO_ATTESTATION_DRIFT")
    proof = json.loads((directory/"after_v3_20.event_proof.json").read_text(encoding="utf-8"))
    post_receipt = json.loads((directory/FILES["after"][1]).read_text(encoding="utf-8"))
    _require(proof["proof_sha256"] == post_receipt["event_proof_sha256"]
             == comparison["comparison_attestation_sha256"]
             and proof["event_count"] == after["utterance_count"]
             and proof["source_trace_sha256"] == post_receipt["source_trace_sha256"]
             and proof["published"] is False
             and proof["word_phoneme_alignment"] == "UNMEASURED",
             "UNTRUSTED_EVENT_PROOF")
    post_events = post_receipt["segments"]
    chosen = sorted(set([0, after["frame_count"]-1] +
        [e["frame_start"] for e in post_events] +
        [e["frame_end_exclusive"]-1 for e in post_events
         if e["event_kind"] == "APPLY"] ))
    images = _frames(directory/FILES["after"][0], after["width"], after["height"], chosen)
    keyed = dict(zip(chosen,images,strict=True))
    continuity = []
    for i,e in enumerate(post_events[:-1]):
        following = post_events[i+1]
        if e["event_kind"] != "APPLY" or following["event_kind"] not in ("OBSERVE","RESULT"):
            continue
        a, b = e["frame_end_exclusive"]-1, following["frame_start"]
        _require(b == a+1 and a in keyed and b in keyed
                 and e["visual_step"] == following["visual_step"],
                 "EVENT_CONTINUITY_SOURCE_DRIFT")
        crop = (0,80,after["width"],235)
        diff = ImageChops.difference(keyed[a].crop(crop),keyed[b].crop(crop))
        mae = sum(ImageStat.Stat(diff).mean)/3
        _require(mae < 2.0, "VISIBLE_SEMANTIC_POINTER_REWIND")
        continuity.append({"before_frame":a,"after_frame":b,
                           "after_start_seconds": round(b/12,3),
                           "decoded_roi_mae":round(mae,6)})
    _require(len(continuity) >= 2, "MISSING_SPOKEN_CHANGE_BOUNDARY")
    if contact_sheet is not None:
        contact_sheet.parent.mkdir(parents=True,exist_ok=True)
        subset = [0] + [e["frame_start"] for e in post_events if
                        e["event_kind"] in ("OBSERVE","APPLY","RESULT","RECAP")]
        subset = sorted(set(subset))
        _contact_sheet([keyed[k] for k in subset],
                       [f"Frame {k} / {k/12:.3f}s" for k in subset],contact_sheet)
    issues = [
        {"id":"LEGIBILITY_PREVIEW_ONLY","severity":"P0_PRODUCT_GATE",
         "at_seconds":0., "evidence":f"actual decoded {after['width']}x{after['height']} at {after['fps']}fps",
         "finding":"Below preregistered 1280x720 audience-review resolution. Native video contains small index, explanatory and subtitle text; no human-distance readability measurement.",
         "status":"BLOCKED"},
        {"id":"WORD_LEVEL_AND_PRONUNCIATION_UNVERIFIED","severity":"P1",
         "at_seconds":round(post_events[2]["seconds_start"],3),
         "evidence":"one separate eSpeak WAV per semantic utterance; 10 source SRT cues; no independent ASR or phoneme timing",
         "finding":"Event starts are physically measured, not precise word onsets or proof of intelligibility/naturalness.",
         "status":"UNMEASURED"},
        {"id":"PEDAGOGY_AND_AESTHETIC_PREFERENCE_UNMEASURED","severity":"P0_RELEASE_GATE",
         "at_seconds":round(post_events[2]["seconds_start"],3),
         "evidence":"one deterministic Binary Search lesson; no independent blinded learner ratings or learning gain",
         "finding":"No valid empirical evidence of learner comprehension, 3B1B parity or multi-topic quality.",
         "status":"BLOCKED"},
        {"id":"VOICE_OUTPUT_COMMERCIAL_RIGHTS","severity":"P0_RELEASE_GATE",
         "at_seconds":0.,"evidence":post_receipt["speech_license_note"],
         "finding":"License and generated voice/data distribution rights not independently cleared.",
         "status":"BLOCKED"},
    ]
    for v in after["speech"]["utterances"]:
        if v["words_per_minute"] > 190 or v["words_per_minute"] < 75:
            issues.append({"id":"PACING_OUTLIER_"+v["event_kind"]+"_"+str(v["start_seconds"]),
                           "severity":"P2_REVIEW","at_seconds":v["start_seconds"],
                           "evidence":f"{v['words_per_minute']} words/minute measured from spoken PCM length and authored text",
                           "finding":"Pace outlier requires human ear assessment, not an automatic failure of comprehension.",
                           "status":"REVIEW"})
    report = {
        "checkpoint":"V3-21","version":VERSION,
        "scope":"OFFLINE_ACTUAL_MEDIA_BINARY_SEARCH_ONLY",
        "artifact_source":"V3-20 same-input actual MP4, SRT, JSON and source event proof",
        "before":before, "after":after, "apply_to_next_observe_continuity":continuity,
        "issues":issues, "integrity_gate":"PASS",
        "student_ready_gate":"BLOCKED","production_release":"BLOCKED",
        "measured_word_alignment":"UNMEASURED",
        "independent_transcript_as_heard":"UNMEASURED",
        "human_comprehension":"UNMEASURED",
        "human_visual_quality":"UNMEASURED",
        "cross_topic_generalization":"UNMEASURED",
        "providers_called":0,
        "claim":"Machine-checked media integrity and selected continuous frames; no educational effectiveness claim"
    }
    return report
