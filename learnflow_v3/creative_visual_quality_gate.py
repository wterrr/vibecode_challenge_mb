"""V3-54 native decoded-frame visual quality proxy, not a human rater.

Measures sample occupancy, non-static pacing and pairwise visible difference.
Deliberately does not use OCR, screenshots as model ground truth, pixel SHA
alone or fabricated pedagogy/legibility ratings.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import numpy as np

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.process_edge_visual_qa import _frame
from learnflow_v3.visual_quality_system import BG

SAMPLES=(.14,.31,.49,.70,.87)
OCCUPANCY_MIN=.002
OCCUPANCY_MAX=.70
TEMPORAL_MAE_MIN=1.5
PAIRWISE_MAE_MIN=2.5
RGB_BG=tuple(bytes.fromhex(BG.lstrip("#")))


def measure_frames(frames:list[np.ndarray])->dict:
    if len(frames)!=len(SAMPLES):
        raise Blocked("V354_MISSING_DECODED_SAMPLES")
    shapes=[frame.shape for frame in frames]
    if any(s!=(720,1280,3) for s in shapes):
        raise Blocked("V354_FRAME_FORMAT_WRONG")
    occupancy=[];pixels=[]
    bg=np.array(RGB_BG,dtype=np.int16)
    for frame in frames:
        if not np.issubdtype(frame.dtype,np.integer):
            raise Blocked("V354_FRAME_NOT_INTEGER_RGB")
        px=frame.astype(np.int16)
        # Robust to RGB/BGR: max-channel Euclidean-like contrast.
        diff=np.max(np.abs(px-bg),axis=-1)
        occupancy.append(float(np.mean(diff>38)))
        pixels.append(sha256(frame.tobytes()).hexdigest())
    if sum(OCCUPANCY_MIN<=o<=OCCUPANCY_MAX for o in occupancy)<3:
        raise Blocked("V354_EMPTY_OR_EXCESSIVELY_FILLED_SCENE")
    temporal=[
      float(np.mean(np.abs(frames[i].astype(np.int16)-
                           frames[i-1].astype(np.int16))))
      for i in range(1,len(frames))]
    if max(temporal)<TEMPORAL_MAE_MIN:
        raise Blocked("V354_VISUALLY_STATIC_STORY")
    return {
      "normalized_sample_positions":list(SAMPLES),
      "non_background_pixel_fractions":occupancy,
      "temporal_frame_mae":temporal,
      "sample_frame_sha256":pixels,
      "max_temporal_difference":max(temporal),
      "interpretation":"PHYSICAL_PIXEL_PROXY_NOT_READABILITY_OR_PEDAGOGICAL_QUALITY",
    }


def inspect_native(movie:Path,frames_count:int):
    if frames_count<100:raise Blocked("V354_VIDEO_TOO_SHORT")
    ids=[min(frames_count-2,max(1,round((frames_count-1)*v))) for v in SAMPLES]
    frames=[_frame(movie,k) for k in ids]
    d=measure_frames(frames)
    d["actual_frames"]=ids
    return d,frames


def distinguish(cases:list[tuple[str,list[np.ndarray],str]])->list[dict]:
    if len(cases)!=3:raise Blocked("V354_THREE_VARIANTS_REQUIRED")
    if len({item[2] for item in cases})!=3:
        raise Blocked("V354_STRUCTURAL_SCENEGRAPHS_IDENTICAL")
    pairs=[]
    for i in range(len(cases)):
        for j in range(i+1,len(cases)):
            name_a,left,_=cases[i];name_b,right,_=cases[j]
            metrics=[float(np.mean(np.abs(a.astype(np.int16)-b.astype(np.int16))))
                     for a,b in zip(left,right)]
            if max(metrics)<PAIRWISE_MAE_MIN:
                raise Blocked("V354_STORYBOARDS_ONLY_METADATA_DIFFER")
            pairs.append({
              "first":name_a,"second":name_b,
              "five_normalized_frame_mae":metrics,
              "peak_visible_difference":max(metrics),
              "interpretation":"DISTINCT_RENDERED_CONTENT_NOT_HIGH_TEACHING_QUALITY"})
    return pairs
