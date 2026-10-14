#!/usr/bin/env python3
"""V3-73: Three versioned SILENT native MP4 QA witnesses + V3-72 reuse adapter.

The geometry gate runs BEFORE rendering and uses the same immutable Frame IR
consumed by Pillow. Does not certify arbitrary external MP4s or learner gains.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learnflow_v3.pedagogical_storytelling_slice import font
from learnflow_v3.v372_timeline_safe_renderer import (
    frame_geometry as v372_frame_geometry
)
from learnflow_v3.generalized_temporal_visual_qa import (
    WIDTH, HEIGHT, FPS, Frame, Rect, Object, Edge,
    marker, make_text, validate_frame, validate_timeline, render_frame,
)

REG = ROOT / "benchmarks/learnflowbench/v3/v3_73_temporal_qa_preregister.json"

# No topic names or evidence ledger values appear in the validator.
# These are three declared held-out *diagnostic* scene fixtures, NOT narrated
# lessons and not representative of all generated scenes.
BLUEPRINTS = {
    "h731_math_numberline": {
        "heading": "Mathematics | Tracking equivalence",
        "subtitle": "A single marker preserves identity on the number line.",
        "boxes": [(100, 290, 320, 398, "0"), (820, 290, 1060, 398, "1")],
        "marker_name": "one_point", "color": "#36bec6"
    },
    "h732_biology_signal": {
        "heading": "Biology | Signal relay",
        "subtitle": "Observe an external signal between separate cells.",
        "boxes": [(170, 290, 430, 398, "CELL A"), (730, 290, 990, 398, "CELL B")],
        "marker_name": "relay_token", "color": "#67c59c"
    },
    "h733_computer_science_flow": {
        "heading": "Computer Science | Ordered handoff",
        "subtitle": "A token moves between nodes; CHECK remains separate.",
        "boxes": [(90, 290, 310, 398, "INPUT"),
                  (550, 290, 780, 398, "UPDATE"),
                  (960, 290, 1180, 398, "CHECK")],
        "marker_name": "state_token", "color": "#e4b255"
    },
}


def require(ok: bool, code: str):
    if not ok:
        raise ValueError("V373_RUN_" + code)


def _node_label(object_id: str, value: str, rect: Rect):
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    f = font(29)
    b = d.textbbox((0, 0), value, font=f)
    x = round((rect.left+rect.right-(b[2]-b[0]))/2-b[0])
    y = round((rect.top+rect.bottom-(b[3]-b[1]))/2-b[1])
    return make_text(object_id + "_label", value, x, y, fontsize=29,
                     parent_id=object_id)


def heldout_frames(case_id: str, total: int = 45) -> tuple[Frame, ...]:
    assert case_id in BLUEPRINTS and total == 45
    cfg = BLUEPRINTS[case_id]
    specs = cfg["boxes"]
    rects = [Rect(*item[:4]) for item in specs]
    edges = [Edge("travel_edge", "node_0", "node_1", 344.0)]
    if len(rects) > 2:
        edges.append(Edge("second_edge", "node_1", "node_2", 344.0))
    frames = []
    start, end = rects[0].right+22, rects[1].left-22
    for n in range(total):
        # Smooth interpolation, constant identity, bounded per-frame velocity.
        progress = n/(total-1)
        x = start+(end-start)*progress
        obs = [make_text("heading", cfg["heading"], 95, 105, fontsize=34),
               make_text("subtitle", cfg["subtitle"], 95, 515, fontsize=22)]
        for i, box in enumerate(rects):
            obs.append(Object(f"node_{i}", "box", box, fill=cfg["color"]
                              if i == 0 else "#29364c"))
            obs.append(_node_label(f"node_{i}", specs[i][4], box))
        obs.append(marker(cfg["marker_name"], x, 344.0, "travel_edge",
                          radius=12))
        frames.append(Frame(n, tuple(obs), tuple(edges)))
    return tuple(frames)


def v372_generic_adapter_audit() -> dict:
    """Adapter reads certified geometry from V3-72, not named topic rules in QA.

    Scans all 355 Attention and 344 Process **registered frame times**. V3-72
    native renderer can draw other objects, so this only certifies exported
    V3-72 score labels/bars and node/marker ROI, not its entire image.
    """
    prereg = json.loads((ROOT / "benchmarks/learnflowbench/v3/"
                         "v3_72_collision_repair_preregister.json").read_text())
    records = {}
    for case in ("attention_reversed_query", "process_heldout_unknown"):
        original = prereg["original_physical_sources"][case]
        n_frames = original["video_frames_expected"]
        bounds = [0] + [round(beat[1]*FPS) for beat in original["beats_s"][:-1]] + [n_frames]
        tested = 0
        for beat in range(5):
            start, stop = bounds[beat], bounds[beat+1]
            for frame_id in range(start, stop):
                k = frame_id-start
                t = min(1.0, k/max(1, int((stop-start)*.58)))
                r = v372_frame_geometry(case, beat, t)
                if case == "attention_reversed_query":
                    from learnflow_v3.pedagogical_storytelling_slice import facts
                    source = facts(case)
                    objects = []
                    for i in range(2):
                        label = f"score {'A' if i==0 else 'B'} = {source['scores'][i]:.3f}"
                        y = 320 if i == 0 else 421
                        title = make_text(f"score_label_{i}", label, 355, y, fontsize=24)
                        require(tuple(title.rect.tuple()) == tuple(r["score_labels"][i]),
                                "V372_TEXT_METADATA_MISMATCH")
                        objects.append(title)
                        objects.append(Object(f"score_bar_{i}", "box",
                                              Rect(*r["score_bars"][i])))
                    snapshot = Frame(k, tuple(objects))
                else:
                    # Pillow ellipse line width is drawn INSIDE its 13px
                    # bounding box: 13px is the conservative raster extent,
                    # while V3-72 uses 16px in its extra-safe bound.
                    center = r["center_x"]
                    obj = (Object("start_node", "box", Rect(100, 283, 360, 393)),
                           Object("action_node", "box", Rect(510, 283, 770, 393)),
                           make_text("action_label", "ACTION", 575, 319,
                                     fontsize=26, parent_id="action_node"))
                    if beat == 2:
                        obs = obj + (marker("v372_marker", center, 337,
                                            "v372_edge", radius=13),)
                        snapshot = Frame(k, obs,
                                         (Edge("v372_edge", "start_node",
                                               "action_node", 337),))
                    else:
                        snapshot = Frame(k, obj)
                validate_frame(snapshot)
                tested += 1
        require(tested == n_frames, "V372_FRAME_COVERAGE")
        records[case] = tested
    return {"original_attention_frames_covered": records["attention_reversed_query"],
            "original_process_frames_covered": records["process_heldout_unknown"],
            "full_exported_ROI_frames_covered": sum(records.values()),
            "QA_SCOPE": "EXPORTED_ROI_NOT_WHOLE_MP4"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(path: Path) -> dict:
    p = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-count_frames", "-show_entries",
        "stream=codec_type,codec_name,width,height,r_frame_rate,nb_read_frames",
        "-of", "json", str(path)], timeout=60))
    streams = {s["codec_type"]: s for s in p["streams"]}
    video = streams["video"]
    require(video["codec_name"] == "h264" and video["width"] == WIDTH and
            video["height"] == HEIGHT and video["r_frame_rate"] == f"{FPS}/1" and
            "audio" not in streams, "SILENT_NATIVE_CODEC_OR_SHAPE")
    return {"frames": int(video["nb_read_frames"]), "codec": "H264",
            "resolution": [WIDTH, HEIGHT], "fps": FPS, "audio": "NONE_DIAGNOSTIC"}


def decode_image(path: Path, time_s: float) -> Image.Image:
    raw = subprocess.check_output([
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-ss", str(time_s), "-i", str(path), "-frames:v", "1",
        "-f", "image2pipe", "-vcodec", "png", "-"], timeout=40)
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    require(im.size == (WIDTH, HEIGHT), "DECODE_DIMENSIONS")
    return im


def write_native(frames: tuple[Frame, ...], path: Path) -> dict:
    passed = validate_timeline(frames, expected_frames=len(frames))
    cmd = ["ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}",
           "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264",
           "-preset", "ultrafast", "-crf", "27", "-pix_fmt", "yuv420p", str(path)]
    with subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
        for state in frames:
            proc.stdin.write(render_frame(state).tobytes())
        proc.stdin.close()
        proc.stdin = None
        err = proc.stderr.read().decode(errors="replace")
        code = proc.wait()
        require(code == 0, "ENCODE_FAILED_" + err[-150:])
    subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                    "-xerror", "-i", str(path), "-map", "0:v:0",
                    "-f", "null", "-"], stdout=subprocess.DEVNULL,
                   check=True, timeout=100)
    data = probe(path)
    require(data["frames"] == len(frames), "NATIVE_FRAME_LOSS")
    first, middle, end = [decode_image(path, sec)
                          for sec in (0, 1.4, 2.8)]
    roi = (300, 305, 820, 385)
    diff_a = sum(ImageStat.Stat(ImageChops.difference(
        first.crop(roi), middle.crop(roi))).mean)
    diff_b = sum(ImageStat.Stat(ImageChops.difference(
        middle.crop(roi), end.crop(roi))).mean)
    require(diff_a > .15 and diff_b > .15, "DECODED_PIXELS_NOT_MOVING")
    return {"sha256": sha256_file(path), **data, "frame_qa": passed,
            "full_native_decode": "PASS",
            "decoded_video_roi_changes": [round(diff_a, 4), round(diff_b, 4)]}


def run(output: Path) -> dict:
    prereg = json.loads(REG.read_text())
    require(prereg["checkpoint"] == "V3-73" and
            prereg["parent"]["sha"] ==
            "149fb7eccdf860eb7ccf9b7b0cf04a493026c0f7",
            "PREREG_PARENT")
    require(not output.exists(), "FRESH_OUTPUT_REQUIRED")
    native_cases = []
    samples = {}
    for h in prereg["locked_holdouts"]:
        name = h["id"]
        require(name in BLUEPRINTS and h["frames"] == 45, "HELDOUT_DRIFT")
        frames = heldout_frames(name)
        samples[name] = frames
    original = v372_generic_adapter_audit()
    output.mkdir(parents=True)
    for item in prereg["locked_holdouts"]:
        case = item["id"]
        mp4 = output / f"{case}_diagnostic_silent.mp4"
        evidence = write_native(samples[case], mp4)
        native_cases.append({"id": case, "domain": item["domain"], **evidence})
    final = {"checkpoint": "V3-73", "scope": "RESEARCH_DIAGNOSTIC_ONLY",
             "native_heldout_clips": 3,
             "native_video_frames_total": sum(x["frames"] for x in native_cases),
             "v372_adapter": original,
             "results": native_cases,
             "coverage": "3_NEW_DOMAINS_PLUS_EXPORTED_V372_GEOMETRY",
             "unreviewed_external_video": "NOT_CERTIFIED",
             "pedagogical_quality": "UNRATED",
             "student_learning": "NOT_MEASURED",
             "production": "BLOCKED", "model_requests": 0}
    (output / "v373_native_qa_receipt.json").write_text(
        json.dumps(final, indent=2, sort_keys=True) + "\n")
    return final


if __name__ == "__main__":
    arg = argparse.ArgumentParser()
    arg.add_argument("--output-dir", required=True, type=Path)
    args = arg.parse_args()
    print(json.dumps(run(args.output_dir), indent=2))
