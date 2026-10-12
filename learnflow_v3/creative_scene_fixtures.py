"""Three preregistered HOST storyboards, not model outputs or generic topic proof.

Compositions, node counts, scene counts, ordering and object kinds differ.
The *compiler* is not informed which storyboard ID it is compiling.
"""
from __future__ import annotations
from copy import deepcopy

from learnflow_v3.creative_scene_graph import VERSION,ORIGIN,ledger,digest


def n(id,kind,fact=None,*,region="CENTER",tone="primary",label=None):
    return {"id":id,"kind":kind,"fact_ref":fact,"label":label,
            "region":region,"tone":tone}

def r(id,src,dst,kind):
    return {"id":id,"source":src,"target":dst,"kind":kind}

def a(kind,target,source=None,destination=None):
    return {"kind":kind,"target":target,"source":source,"destination":destination}

def beat(scene,claims,words,actions):
    return {"scene_id":scene,"claims":claims,"narration":words,"actions":actions}

WORDS={
 "query":"Imagine a single query asking which pieces of information matter. Its matches with two keys guide the flow, while each token also owns a value vector.",
 "score":"We compare the query with the keys through dot products, then scale those scores by the square root of the key dimension to keep matching stable.",
 "softmax":"Those scaled compatibility scores become attention weights after softmax. Notice that the visual bars express different contributions and together represent one normalized distribution.",
 "mix":"A new context vector forms by combining the value vectors, weighted by attention strengths. No value is copied alone; both contribute to the result.",
 "mix2":"The combined representation is made from the values using the normalized weights. We can now read the context as a mixture rather than a single selected token.",
 "rephrase":"Look at the completed visual. A query does not choose a single winner; different value vectors contribute according to their relative compatibility with the query."
}

def fixtures()->dict[str,dict]:
    h=digest(ledger())
    first={
     "version":VERSION,"origin":ORIGIN,"evidence_sha256":h,
     "title":"Attention as an Information Network",
     "scenes":[
       {"id":"network","title":"Query meets the keys","layout":"PROCESS","nodes":[
        n("ask","SHAPE","q",region="LEFT",tone="accent"),
        n("leftkey","SHAPE","key_a",region="CENTER"),
        n("rightkey","SHAPE","key_b",region="RIGHT"),
        n("scoreleft","MATH","score_a",region="BOTTOM_LEFT"),
        n("scoreright","MATH","score_b",region="BOTTOM_RIGHT")],
        "relations":[
         r("leftmatch","ask","leftkey","COMPARES_WITH"),
         r("rightmatch","ask","rightkey","COMPARES_WITH"),
         r("scorepath","leftkey","scoreleft","FLOW"),
         r("otherscore","rightkey","scoreright","FLOW")]},
       {"id":"mixture","title":"Softmax then the context","layout":"COMPARISON","nodes":[
        n("weightleft","CHART","weight_a",tone="primary"),
        n("weightright","CHART","weight_b",tone="secondary"),
        n("scoreleft","MATH","score_a"),
        n("context","SHAPE","context",tone="accent"),
        n("valueleft","MATH","value_a"),
        n("valueright","MATH","value_b")],
        "relations":[
         r("to_context_left","weightleft","context","FLOW"),
         r("to_context_right","weightright","context","FLOW")]}
      ],
     "beats":[
      beat("network",["A1"],WORDS["query"],[
          a("reveal","ask"),a("reveal","leftkey"),a("reveal","rightkey"),
          a("connect","leftmatch"),a("connect","rightmatch")]),
      beat("network",["A2"],WORDS["score"],[
          a("reveal","scoreleft"),a("reveal","scoreright"),
          a("connect","scorepath"),a("connect","otherscore"),a("emphasize","scoreleft")]),
      beat("mixture",["A2","A3"],WORDS["softmax"],[
          a("reveal","scoreleft"),a("reveal","weightleft"),
          a("reveal","weightright")]),
      beat("mixture",["A4"],WORDS["mix"],[
          a("reveal","context"),a("reveal","valueleft"),a("reveal","valueright"),
          a("connect","to_context_left"),a("connect","to_context_right")])
     ]}
    second={
     "version":VERSION,"origin":ORIGIN,"evidence_sha256":h,
     "title":"An Attention Comparison Board",
     "scenes":[
       {"id":"pairing","title":"Which key matches the query","layout":"GRID","nodes":[
         n("query","MATH","q",region="TOP"),
         n("keya","SHAPE","key_a",region="BOTTOM_LEFT"),
         n("keyb","SHAPE","key_b",region="BOTTOM_RIGHT")],
         "relations":[r("patha","query","keya","COMPARES_WITH")]},
       {"id":"board","title":"Scores compared with weights","layout":"COMPARISON","nodes":[
         n("scorea","MATH","score_a",tone="primary"),
         n("scoreb","MATH","score_b",tone="secondary"),
         n("weigha","CHART","weight_a",tone="primary"),
         n("weighb","CHART","weight_b",tone="secondary"),
         n("caption","TEXT",label="Relative Match Strength",tone="accent")],
         "relations":[r("normalize","scorea","weigha","TRANSFORMS_INTO")]},
       {"id":"solution","title":"A fresh context vector","layout":"FREEFORM","nodes":[
         n("output","SHAPE","context",region="CENTER",tone="accent"),
         n("formula","EQUATION","formula",region="TOP"),
         n("va","MATH","value_a",region="BOTTOM_LEFT"),
         n("vb","MATH","value_b",region="BOTTOM_RIGHT")],
         "relations":[r("derive","formula","output","DEPENDS_ON")]}
     ],
     "beats":[
      beat("pairing",["A1"],WORDS["query"],[
          a("reveal","query"),a("reveal","keya"),
          a("reveal","keyb"),a("connect","patha")]),
      beat("board",["A2"],WORDS["score"],[
          a("reveal","scorea"),a("reveal","scoreb"),
          a("emphasize","scorea")]),
      beat("board",["A3"],WORDS["softmax"],[
          a("reveal","weigha"),a("reveal","weighb"),
          a("connect","normalize"),a("reveal","caption")]),
      beat("solution",["A4"],WORDS["mix2"],[
          a("reveal","formula"),a("reveal","output"),
          a("reveal","va"),a("reveal","vb"),a("connect","derive")]),
     ]}
    third={
     "version":VERSION,"origin":ORIGIN,"evidence_sha256":h,
     "title":"Where the Attention Result Comes From",
     "scenes":[
       {"id":"semantics","title":"The choice starts with matching","layout":"FREEFORM","nodes":[
         n("left","MATH","q",region="LEFT",tone="accent"),
         n("ka","SHAPE","key_a",region="TOP_RIGHT"),
         n("kb","SHAPE","key_b",region="BOTTOM_RIGHT"),
         n("val","TEXT",label="Two Different Keys",region="BOTTOM_LEFT")],
         "relations":[r("compareb","left","kb","COMPARES_WITH")]},
       {"id":"bridge","title":"Numbers become proportions","layout":"GRID","nodes":[
         n("sa","MATH","score_a",tone="primary"),
         n("sb","MATH","score_b",tone="secondary"),
         n("wa","CHART","weight_a",tone="accent"),
         n("wb","CHART","weight_b",tone="primary")],
         "relations":[r("became","sa","wa","TRANSFORMS_INTO")]},
       {"id":"combiner","title":"Mix the information together","layout":"FREEFORM","nodes":[
         n("v1","MATH","value_a",region="LEFT"),
         n("v2","MATH","value_b",region="RIGHT"),
         n("out","SHAPE","context",region="CENTER",tone="accent"),
         n("math","EQUATION","formula",region="TOP")],
         "relations":[r("inputa","v1","out","FLOW"),
           r("inputb","v2","out","FLOW")]}
     ],
     "beats":[
      beat("semantics",["A1"],WORDS["query"],[
          a("reveal","left"),a("reveal","ka"),a("reveal","kb"),
          a("connect","compareb"),a("reveal","val")]),
      beat("bridge",["A2"],WORDS["score"],[
          a("reveal","sa"),a("reveal","sb"),a("emphasize","sa")]),
      beat("bridge",["A3"],WORDS["softmax"],[
          a("reveal","wa"),a("reveal","wb"),a("connect","became")]),
      beat("combiner",["A4"],WORDS["mix"],[
          a("reveal","v1"),a("reveal","v2"),a("reveal","out"),
          a("connect","inputa"),a("connect","inputb")]),
      beat("combiner",["A4"],WORDS["rephrase"],[
          a("reveal","math"),a("emphasize","out")])
     ]}
    return {k:deepcopy(v) for k,v in zip(
      ("tokens_as_network","scores_as_comparison","heldout_symbolic_rewrite"),
      (first,second,third))}
