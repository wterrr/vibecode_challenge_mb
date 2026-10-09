#!/usr/bin/env python3
"""V3-21: audit REAL V3-20 output without inventing a quality or human PASS."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from learnflow_v3.lesson_quality import audit_media

def produce(source_dir: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = audit_media(source_dir, contact_sheet=output_dir/"v3_21_real_video_frame_contact_sheet.jpg")
    assert report["integrity_gate"] == "PASS"
    assert report["student_ready_gate"] == report["production_release"] == "BLOCKED"
    assert report["human_visual_quality"] == report["human_comprehension"] == "UNMEASURED"
    assert report["measured_word_alignment"] == "UNMEASURED"
    assert report["before"]["frame_count"] == 538 and report["after"]["frame_count"] == 541
    assert report["after"]["utterance_count"] == 10
    assert len(report["apply_to_next_observe_continuity"]) == 3
    (output_dir/"v3_21_real_media_quality_evidence.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("V3_21_MEDIA_INTEGRITY=PASS actual_h264_aac_srt_and_pixel_continuity=True")
    print(f"V3_21_ISSUES={len(report['issues'])} audited_from_actual_video=True")
    print("V3_21_HUMAN_EDUCATION_QUALITY=UNMEASURED production=BLOCKED")
    return report

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source-dir",required=True,type=Path)
    p.add_argument("--output-dir",required=True,type=Path)
    a = p.parse_args()
    produce(a.source_dir,a.output_dir)
