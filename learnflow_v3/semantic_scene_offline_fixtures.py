"""Offline-only DATA fixtures shaped like hypothetical provider JSON.

This is NOT a Gemini/GPT model response; all scene visuals and narrations
are local human/host test records. Their purpose is protocol coverage only.
"""
from __future__ import annotations

from copy import deepcopy

from learnflow_v3.semantic_scene_wire import SYNTHETIC_ORIGIN

def _g(id,kind,*,x=0,y=0,width=1.0,height=.6,color="WHITE",
       text="",src="",dst=""):
    return {"id":id,"kind":kind,"x":float(x),"y":float(y),
            "width":float(width),"height":float(height),"color":color,
            "text":text,"src":src,"dst":dst}

def _e(kind,target="",*,source="",at=0,span=.1):
    return {"kind":kind,"target":target,"source":source,"at":float(at),"span":float(span)}

def synthetic_fraction_wire():
    tiles=[
      _g("hshade","tile",x=-4.2,y=.5,width=1.2,height=1.8,color="TEAL"),
      _g("hplain","tile",x=-3.,y=.5,width=1.2,height=1.8,color="GREY"),
      _g("qshade1","tile",x=1.2,y=.5,width=.6,height=1.8,color="TEAL"),
      _g("qshade2","tile",x=1.8,y=.5,width=.6,height=1.8,color="TEAL"),
      _g("qplain1","tile",x=2.4,y=.5,width=.6,height=1.8,color="GREY"),
      _g("qplain2","tile",x=3.,y=.5,width=.6,height=1.8,color="GREY")]
    labels=[
      _g("title","label",x=0,y=2.3,text="Compare the same whole",color="WHITE"),
      _g("left_fraction","label",x=-3.6,y=-1.1,text="1/2"),
      _g("right_fraction","label",x=2.1,y=-1.1,text="2/4"),
      _g("proof","label",x=0,y=-2.2,color="YELLOW",text="(1×2)/(2×2) = 2/4"),
      _g("summary","label",x=-.8,y=.5,text="Same whole")]
    beats=[
       {"claim_ids":["F1"],
        "narration":"This rectangle is one whole. Dividing the whole into two equal pieces gives one shaded half and one unshaded half.",
        "events":[_e("show_label","title",at=0,span=.1),
                  _e("reveal_partition","halves",at=.15,span=.1),
                  _e("show_label","left_fraction",at=.3,span=.1),
                  _e("hold",at=.55,span=.35)]},
       {"claim_ids":["F1","F3"],
        "narration":"Watch the same amount become four equal pieces. The shaded part now covers two of those four smaller pieces.",
        "events":[_e("morph_partition","quarters",source="halves",at=0,span=.2),
                  _e("show_label","right_fraction",at=.25,span=.1),
                  _e("hold",at=.6,span=.3)]},
       {"claim_ids":["F2"],
        "narration":"Multiplying both the numerator and denominator by two leaves the fraction unchanged. The visible transformation explains the matching ratio.",
        "events":[_e("show_label","proof",at=.05,span=.15),
                  _e("emphasize","proof",at=.25,span=.15),
                  _e("hold",at=.55,span=.35)]},
       {"claim_ids":["F1","F3"],
        "narration":"Both pictures show an equal shaded share of the same whole. One half and two quarters therefore represent an identical value.",
        "events":[_e("show_label","summary",at=.05,span=.15),
                  _e("emphasize","halves",at=.25,span=.15),
                  _e("emphasize","quarters",at=.45,span=.15),
                  _e("hold",at=.65,span=.3)]}
    ]
    return {"family":"fraction_equivalence","title":"Equivalent fraction partitions",
            "objective":"Connect the same shaded whole to equivalent fractional symbols",
            "graphics":tiles+labels,
            "partitions":[
             {"id":"halves","part_ids":["hshade","hplain"],"shaded_ids":["hshade"],
              "numerator":1,"denominator":2},
             {"id":"quarters","part_ids":["qshade1","qshade2","qplain1","qplain2"],
              "shaded_ids":["qshade1","qshade2"],"numerator":2,"denominator":4}],
            "relations":[{"source":"halves","target":"quarters","multiply_by":2,
                          "proof_label_id":"proof"}],
            "beats":beats}

def synthetic_process_wire():
    graphics=[
     _g("start","node",x=-3,y=0,width=1.8,height=1.2,color="BLUE",text="Start"),
     _g("verify","node",x=0,y=0,width=1.8,height=1.2,color="TEAL",text="Verify"),
     _g("finish","node",x=3,y=0,width=1.8,height=1.2,color="GREEN",text="Finish"),
     _g("edge_start_verify","edge",src="start",dst="verify",color="WHITE"),
     _g("edge_verify_finish","edge",src="verify",dst="finish",color="WHITE"),
     _g("title","label",x=0,y=2.1,text="An ordered process"),
     _g("done","label",x=0,y=-2.0,text="Follow the arrows",color="YELLOW"),
    ]
    beats=[
     {"claim_ids":["P1"],"narration":"The process starts at the left. First reveal the starting state and the verification state so each stage has a clear identity.",
      "events":[_e("show_label","title",at=0,span=.1),
                _e("reveal_node","start",at=.15,span=.15),
                _e("reveal_node","verify",at=.35,span=.15),
                _e("hold",at=.6,span=.3)]},
     {"claim_ids":["P2"],"narration":"From the Start stage, follow the directed arrow into Verify. Verification checks the condition before the process can proceed.",
      "events":[_e("reveal_edge","edge_start_verify",at=0,span=.15),
                _e("traverse_edge","edge_start_verify",at=.2,span=.2),
                _e("reveal_node","finish",at=.5,span=.15),
                _e("hold",at=.7,span=.2)]},
     {"claim_ids":["P3"],"narration":"Once verification is complete, the next directed arrow carries the process to Finish. The arrows explain the intended sequence.",
      "events":[_e("reveal_edge","edge_verify_finish",at=.05,span=.15),
                _e("traverse_edge","edge_verify_finish",at=.25,span=.2),
                _e("show_label","done",at=.55,span=.1),
                _e("hold",at=.7,span=.2)]},
     {"claim_ids":["P3"],"narration":"The complete path begins at Start, passes through Verify, and then reaches Finish. Read each arrow as one ordered transition.",
      "events":[_e("emphasize","finish",at=.1,span=.2),
                _e("hold",at=.4,span=.5)]}
    ]
    return {"family":"ordered_process","title":"Follow an ordered process",
            "objective":"Show a directed path from Start through Verify to Finish",
            "graphics":graphics,"partitions":[],"relations":[],"beats":beats}

def fixture_cases():
    return {"v345-synthetic-fractions":synthetic_fraction_wire(),
            "v345-synthetic-process":synthetic_process_wire()}
