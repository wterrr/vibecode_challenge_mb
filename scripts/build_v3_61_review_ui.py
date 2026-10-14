#!/usr/bin/env python3
"""V3-61: package frozen V3-60 A/B/C clips into a zero-network reviewer app.

No admin key, real ratings, human identifiers, or model API calls are read.
The HTML cannot prove actual human attention; only original participants can.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_v3_60_independent_review import (
    FIELDS, template_rows, spec as v360_spec, verify_packet, sha
)

REG = ROOT/"benchmarks/learnflowbench/v3/v3_61_offline_review_ui_preregister.json"
ASSET = ROOT/"learnflow_v3/review_ui"
FORBIDDEN = ("original_motion", "static_end_state", "causal_reveal",
             "admin_treatment_key", "v359_results", "http://", "https://",
             "fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon")


def require(ok, label):
    if not ok:
        raise ValueError("V361_" + label)


def preregistered():
    reg = json.loads(REG.read_text(encoding="utf-8"))
    parent = v360_spec()
    require(reg["checkpoint"] == "V3-61" and
            reg["registered_before_implementation"] is True and
            reg["registration_kind"] == "FIRST_CHILD_COMMIT" and
            reg["parent_sha"] == "42dfb0216ea82c9fe22d7995e1f99fd02acbe0d1",
            "PREREG_DRIFT")
    require(reg["masked_clips_sha256"] == parent["masked_clips_sha256"] and
            reg["source_native_artifact_id"] == 11863660782 and
            tuple(reg["source_rating_fields"]) == FIELDS,
            "FROZEN_SOURCE_DRIFT")
    return reg


def html_document(config: dict, name: str) -> str:
    # A safe inert JSON script tag: cannot prematurely close <script>.
    cfg = json.dumps(config, ensure_ascii=True, sort_keys=True).replace("<", "\\u003c")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self'; style-src 'self'; media-src 'self' file:; img-src 'self' data:; connect-src 'none'; object-src 'none'; form-action 'none'; base-uri 'none'">
<title>Masked Lesson Video Review — Assigned Form {name}</title>
<link rel="stylesheet" href="v361.css">
<script type="application/json" id="frozen-configuration">{cfg}</script>
<script src="v361_reviewer.js" defer></script>
</head>
<body>
<header>
  <p class="eyebrow">Independent assessment · offline only</p>
  <h1>Video lesson review</h1>
  <p class="muted">You are rating three versions of each of three short lessons.
  The letter A/B/C is an anonymous clip identifier, not a rating or treatment.
  The design is condition-masked, not double-blind. Videos never leave your device.</p>
</header>
<main>
  <section class="panel" aria-label="Reviewer identification">
    <div class="row"><strong>Assigned form {name} / 03</strong><span class="muted">Nine clips · five criteria</span></div>
    <label for="rater-id">Assigned anonymous reviewer ID
      <input id="rater-id" type="text" required minlength="3" maxlength="40"
       pattern="[A-Za-z0-9_-]{{3,40}}" placeholder="e.g. reviewer_08" autocomplete="off"
       spellcheck="false" aria-describedby="private-hint">
    </label>
    <p id="private-hint" class="small">Use the pseudonym your study coordinator assigned.
    No names, emails or identifiable data. Ratings stay in this browser until you export CSV.
    Reloading loses unsaved input.</p>
  </section>
  <section class="panel" aria-label="Lesson player">
    <div class="row"><h2 id="progress">Clip 1 of 9</h2><span id="clip-id" class="muted"></span></div>
    <div class="video-wrap">
      <video id="clip-video" controls preload="metadata" playsinline
       aria-label="Current blinded educational video"></video>
    </div>
    <p id="watch-state" class="small" role="status">Not yet played to end</p>
    <p class="small">Please watch the entire video before scoring. Seeking straight to
    the end does not count as a complete playback. You may replay as needed.
    Browser playback checks cannot establish human attention; be truthful when attesting.</p>
  </section>
  <section class="panel" aria-label="Five pedagogical ratings">
    <h2>Rate this clip</h2>
    <p class="small">Score each criterion 1 (very poor or misleading), 2 (major defects),
    3 (adequate), 4 (good), or 5 (very clear). Select confidence on the same scale.</p>
    <div id="rating-fields" class="review-grid"></div>
    <label for="failure-notes">Timestamped observations and problems
      <textarea id="failure-notes" rows="4" placeholder="e.g. 6.5s: answer shown before its proof"></textarea>
    </label>
    <p><button id="timestamp" type="button" class="secondary">Insert current video time</button></p>
    <p class="small">For ANY criterion scored 1 or 2, include a specific timestamp and problem.
    If unable to rate this clip, stop and tell the coordinator: scores may not be invented or imputed.</p>
    <label class="attest"><input type="checkbox" id="attest-full">
      I personally watched this entire clip and these are my own ratings.</label>
    <div id="message" class="message" role="status" aria-live="polite"></div>
    <div class="row">
      <button id="previous" type="button" class="secondary">← Previous clip</button>
      <button id="next" type="button">Save and continue →</button>
    </div>
    <p id="export" hidden role="status">No scores have been uploaded. A CSV download was initiated
    locally. Send it to your coordinator, who must seal all ratings BEFORE unmasking the treatment key.</p>
  </section>
</main>
<footer>V3-61 research instrument · No analytics or network requests ·
  Pedagogical quality UNRATED until external human review · Learning gain NOT MEASURED
  · No release approval.</footer>
</body>
</html>"""


def build(clips: Path, out: Path, *, full_decode: bool = False) -> dict:
    require(not out.exists(), "OUTPUT_EXISTS")
    reg = preregistered()
    evidence = verify_packet(clips, decode=full_decode)
    require(evidence["media_integrity"] == "PASS_NATIVE_MASKED", "MEDIA_GATE")
    js = (ASSET/"v361_reviewer.js").read_text(encoding="utf-8")
    css = (ASSET/"v361.css").read_text(encoding="utf-8")
    for forbidden in FORBIDDEN:
        require(forbidden not in js and forbidden not in css,
                "TREATMENT_OR_NETWORK_LEAK_" + forbidden.replace(":", "_"))
    out.mkdir(parents=True)
    (out/"media").mkdir()
    (out/"v361_reviewer.js").write_text(js, encoding="utf-8")
    (out/"v361.css").write_text(css, encoding="utf-8")
    for name, digest in sorted(reg["masked_clips_sha256"].items()):
        require(re.fullmatch(r"[a-z0-9_]+_[ABC]\.mp4", name) is not None,
                "CLIP_NAME_INVALID")
        shutil.copyfile(clips/name, out/"media"/name)
        require(sha(out/"media"/name) == digest, "PACKAGED_SHA_DRIFT")
    for i in range(3):
        rows = template_rows(v360_spec(), i)
        ids = [{"case_id":r["case_id"], "clip_id":r["clip_id"]} for r in rows]
        require(len(ids) == 9 and len(set(r["clip_id"] for r in ids)) == 9,
                "REVIEWER_ORDER_INVALID")
        cfg = {"checkpoint": "V3-61", "form_number": i+1, "clips": ids}
        document = html_document(cfg, f"{i+1:02d}")
        for forbidden in FORBIDDEN:
            require(forbidden not in document, "HTML_TREATMENT_OR_NETWORK_LEAK")
        (out/f"reviewer_{i+1:02d}.html").write_text(document, encoding="utf-8")
    (out/"MASKED_MANIFEST.json").write_text(json.dumps({
        "checkpoint": "V3-61", "clips": reg["masked_clips_sha256"],
        "reviewer_count": 0, "treatment_mapping": "WITHHELD",
        "human_quality": "UNRATED", "learning_gain": "NOT_MEASURED",
        "production": "BLOCKED"
    }, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    (out/"START_HERE.txt").write_text(
        "OFFLINE MASKED REVIEW, NO MODEL/TELEMETRY/NETWORK.\n"
        "Coordinator: assign one original reviewer_01.html, _02.html or _03.html"
        " to each real external participant; the same assignment should be"
        " retained if they need to restart. Do not include admin treatment"
        " mapping. Double-click assigned HTML while retaining its adjacent"
        " v361.css, v361_reviewer.js and media/ files. Use recent desktop Chrome"
        " or Firefox with local MP4 playback enabled. Human rater watches 9"
        " videos fully, enters scores and pseudonym, clicks export to download"
        " one 9-row CSV. If export is blocked, ask coordinator for help."
        " No ratings are transmitted/stored by this kit. The coordinator merges"
        " the originals, verifies consent/conflicts/independence, and calls"
        " V3-60 seal BEFORE opening separate admin mapping."
        " The reviewer UI cannot prove human attention or reviewer identity."
        " Empty/no submissions means UNRATED; no learning gain measured.\n",
        encoding="utf-8")
    all_files = [x for x in out.rglob("*") if x.is_file()]
    require(len(all_files) == 16, "UNEXPECTED_PACKAGE_FILES")
    return {
        "checkpoint": "V3-61", "gate": "PACKAGED_OFFLINE_MASKED",
        "native_media_verified": True,
        "full_decode_on_this_execution": full_decode,
        "masked_movies": 9, "assigned_forms": 3,
        "html": 3, "remote_submissions": 0, "rater_count": 0,
        "human_quality": "UNRATED", "learning_gain": "NOT_MEASURED",
        "production": "BLOCKED"
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clips-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--full-decode", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(args.clips_dir, args.output, full_decode=args.full_decode),
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
