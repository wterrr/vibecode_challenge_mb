"""V3-83 native pixel and host arithmetic geometry audit, not image OCR."""
from __future__ import annotations
from hashlib import sha256
import numpy as np
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.process_edge_visual_qa import _frame
from learnflow_v3.v383_semantic_unit_storytelling import receipts, check

ROI = (140,335,1140,550)


def _colors(frame):
    x0,y0,x1,y1=ROI
    crop=frame[y0:y1,x0:x1].astype("int16")
    R,G,B=crop[:,:,0],crop[:,:,1],crop[:,:,2]
    cyan=(R<160)&(G>155)&(B>150)&((G-R)>60)
    orange=(R>185)&(G>95)&(B<165)&((R-B)>80)
    return int(cyan.sum()),int(orange.sum())


def witness(movie,beat_rows,trace):
    ledger=receipts(trace)
    check(len(beat_rows)==len(ledger),"BEAT_RECEIPT_IDENTITY_DRIFT")
    out=[]
    for i,(beat,proof) in enumerate(zip(beat_rows,ledger,strict=True)):
        start=int(beat["frame_start"])
        before=start+1
        after=start+88
        check(after<start+int(beat["frames"])-3,"NOT_ENOUGH_NATIVE_BEAT_FRAMES")
        pre=_frame(movie,before)
        post=_frame(movie,after)
        check(pre.shape==post.shape==(720,1280,3),"WRONG_DECODED_SIZE")
        pre_c,pre_o=_colors(pre)
        post_c,post_o=_colors(post)
        check(post_c+post_o>=900,"NO_PHYSICAL_UNIT_IN_RESULT_FRAME")
        check(post_c+post_o>pre_c+pre_o+900,"NO_CAUSAL_UNIT_REVEAL")
        check(post_c>=400,"NO_LEFT_OR_REPEATED_SOURCE_TOKENS")
        if proof["operator"]=="ADD":
            check(post_o>=400,"RIGHT_SOURCE_TOKENS_NOT_PRESERVED")
        diff=np.max(np.abs(post[335:550,140:1140].astype("int16")-
                             pre[335:550,140:1140].astype("int16")),axis=2)
        changed=int((diff>35).sum())
        check(changed>1000,"NON_TRANSFORMING_SEMANTIC_CANVAS")
        out.append({**proof,
                    "index":i,"before_frame":before,"after_frame":after,
                    "before_cyan":pre_c,"before_orange":pre_o,
                    "after_cyan":post_c,"after_orange":post_o,
                    "physical_color_pixels_observed":post_c+post_o,
                    "physical_frame_changed_pixels":changed,
                    "before_sha256":sha256(pre.tobytes()).hexdigest(),
                    "after_sha256":sha256(post.tobytes()).hexdigest(),
                    "qualifier":"PIXEL_COLOR_EVIDENCE_NOT_EXACT_TILE_OCR_OR_LEARNER_GAIN"})
    return out
