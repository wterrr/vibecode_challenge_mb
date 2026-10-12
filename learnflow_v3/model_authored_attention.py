"""V3-50: exact four-beat, model-authored ATTENTION storyboard, host-owned truth.

The genuine model supplies narration and one compositional visual focus per
beat; it NEVER supplies scalar arithmetic, code or an unsupported claim.
This is a bounded demo, not a general Transformer renderer.
"""
from __future__ import annotations
from hashlib import sha256
import json
import math
from pathlib import Path
import re

from jsonschema import Draft202012Validator
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_manim_runner import MODEL
from learnflow_v3.compatible_scene_protocol import _forbid_unsupported

ROOT=Path(__file__).resolve().parents[1]
REG="benchmarks/learnflowbench/v3/v3_50_attention_one_query_preregister.json"
PARENT_SHA="bdc4d6a21fb1e58a50f96b4722f81585e511aee2"
TOPIC="scaled_dot_product_self_attention"
ROLES=("A1","A2","A3","A4")
CLAIMS={
"A1":"In scaled dot-product self-attention a query compares with keys, using learned query, key and value projections.",
"A2":"The query-key dot products are divided by sqrt(d_k) to obtain scaled compatibility logits.",
"A3":"Softmax turns scaled logits into nonnegative attention weights summing to one.",
"A4":"The attention output is a weighted sum of the value vectors."}
TARGETS={
"A1":["query","keys","tokens"],
"A2":["query","keys","scores"],
"A3":["scores","weights","softmax"],
"A4":["weights","values","context"]}


def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=True)


def sha(obj):
    return sha256(canonical(obj).encode()).hexdigest()


def prereg():
    m=json.loads((ROOT/REG).read_text())
    q=m["one_shot_budget"]
    if not (
      m["checkpoint"]=="V3-50-ONE-QUERY-ATTENTION" and
      m["parent_sha"]==PARENT_SHA and
      m["model"]==MODEL and q["max_new_http_posts"]==1 and
      q["max_tokens"]==2800 and q["retries"]==0 and
      q["fallback"] is False and
      q["temperature_parameter_present"] is False and
      q["provider_require_parameters"] is True and
      m["production"]=="BLOCKED"):
        raise Blocked("V350_PREREGISTRATION_DRIFT")
    return m


def exact_example():
    q=(1.,0.);keys=((1.,0.),(0.,1.));values=((1.,0.),(0.,1.))
    d=2
    scores=[sum(u*v for u,v in zip(q,k))/math.sqrt(d) for k in keys]
    exps=[math.exp(s-max(scores)) for s in scores]
    z=sum(exps);weights=[x/z for x in exps]
    context=[sum(w*v[j] for w,v in zip(weights,values)) for j in range(2)]
    if not (abs(scores[0]-1/math.sqrt(2))<1e-12 and scores[1]==0
            and abs(sum(weights)-1)<1e-12 and
            all(abs(context[i]-weights[i])<1e-12 for i in range(2))):
        raise Blocked("V350_COMPUTED_FACTS_INVALID")
    return {"q":[1,0],"k":[[1,0],[0,1]],"v":[[1,0],[0,1]],
       "dk":d,"scores":scores,"weights":weights,"context":context}


def _obj(fields):
    return {"type":"object","additionalProperties":False,
            "properties":fields,"required":list(fields)}


def portable_schema():
    beats={}
    for index,claim in enumerate(ROLES,1):
        fields={
          "claim_id":{"type":"string","enum":[claim]},
          "narration":{"type":"string"},
          "visual_style":{"type":"string","enum":["trace","spotlight","compare"]},
          "focus":{"type":"string","enum":TARGETS[claim]},
          "pace":{"type":"string","enum":["steady","deliberate"]}
        }
        beats[f"beat_{index}"]=_obj(fields)
    doc=_obj({
      "title":{"type":"string"},
      "objective":{"type":"string"},
      "beats":_obj(beats)
    })
    _forbid_unsupported(doc)
    return doc


def request_body():
    m=prereg()
    example=exact_example()
    fact={
      "query":m["user_query"],
      "topic":"Scaled dot-product attention, ONE query and TWO key/value tokens (single head, no causal mask)",
      "source_url":m["source"]["source_url"],
      "approved_claims":CLAIMS,
      "host_verified_exact_numerical_values":{
        "q":example["q"],"keys":example["k"],"values":example["v"],
        "dk":example["dk"],"scores_rounded":[round(x,3) for x in example["scores"]],
        "softmax_weights_rounded":[round(x,3) for x in example["weights"]],
        "weighted_value_output_rounded":[round(x,3) for x in example["context"]]},
      "fixed_stages":["A1 introduces Q,K,V and token lookup",
                      "A2 Q dot K, divide by sqrt(d_k)",
                      "A3 scores pass through softmax to positive normalized weights",
                      "A4 weighted sum of V yields context"],
      "model_may_choose":["spoken explanations in original words","visual_style trace/spotlight/compare",
                          "visual_focus in each stage","pace steady/deliberate","title and objective"],
      "critical_rules":[
        "JSON only and EXACT schema fields; no Python, source references, images, untrusted citations, or Markdown",
        "Exactly four ordered beats. Each claim_id already defines stage and must not change.",
        "Narration 20-42 English words per beat; address approved claim for that beat.",
        "A1 narration explicitly uses the words query and keys; A2 explicitly mentions dot product and scale; A3 explicitly says softmax and weights; A4 explicitly says weighted sum and values.",
        "Use numerical values only if exactly those in host verified example. Avoid extra numbers, training performance, masks or causal claims.",
        "Do NOT claim a value of a real trained Transformer; these are illustrative manually chosen Q,K,V vectors.",
        "Prioritize visual mathematical causality, not static definition slides. No arbitrary output formula or hallucinated source."
      ]}
    body={
      "model":MODEL,"max_tokens":m["one_shot_budget"]["max_tokens"],
      "provider":{"allow_fallbacks":False,"require_parameters":True},
      "response_format":{"type":"json_schema",
         "json_schema":{"name":"learnflow_v350_attention_one_query",
                         "strict":True,"schema":portable_schema()}},
      "messages":[
       {"role":"system","content":"You create an original, understandable scaled dot-product attention lesson storyboard. Choose high-quality focus and delivery per beat, but never invent facts. Output strict JSON, no Python."},
       {"role":"user","content":json.dumps(fact,ensure_ascii=False)}
      ]}
    return body


def verify_storyboard(raw):
    try:
        Draft202012Validator(portable_schema()).validate(raw)
    except Exception:
        raise Blocked("V350_MODEL_WIRE_SCHEMA_REJECTED") from None
    if not 10<=len(raw["title"])<=65 or not 15<=len(raw["objective"])<=130:
        raise Blocked("V350_TITLE_OBJECTIVE_INVALID")
    for i,role in enumerate(ROLES,1):
        b=raw["beats"][f"beat_{i}"]
        words=b["narration"].split()
        if not 17<=len(words)<=48 or not 80<=len(b["narration"])<=340:
            raise Blocked("V350_NARRATION_BOUNDS")
        l=b["narration"].lower()
        if role=="A1" and not ("quer" in l and "key" in l):
            raise Blocked("V350_A1_NOT_GROUNDED")
        if role=="A2" and not ("dot" in l and ("scal" in l or "divid" in l)):
            raise Blocked("V350_A2_NOT_GROUNDED")
        if role=="A3" and not ("softmax" in l and "weight" in l):
            raise Blocked("V350_A3_NOT_GROUNDED")
        if role=="A4" and not ("value" in l and ("weight" in l or "mix" in l)):
            raise Blocked("V350_A4_NOT_GROUNDED")
        # Detect known unsupported quantities but do not claim full semantic NLP proof.
        numbers=re.findall(r"(?<![a-z])\d+(?:\\.\d+)?",l)
        allowed={"0","1","2","0.707","0.67","0.670","0.33","0.330","0.7","0.3"}
        if any(n not in allowed for n in numbers):
            raise Blocked("V350_UNAPPROVED_MODEL_NUMBER")
    return raw


def synthetic_fixture():
    return {
      "title":"How Attention Chooses Information",
      "objective":"See how dot products become normalized weights and a new context vector",
      "beats":{
        "beat_1":{"claim_id":"A1","visual_style":"trace","focus":"query","pace":"steady",
           "narration":"For this example, a query looks across two keys to decide what matters. Each token also has a value vector. We will follow one query as it gathers information."},
        "beat_2":{"claim_id":"A2","visual_style":"compare","focus":"scores","pace":"deliberate",
           "narration":"The query meets each key through a dot product. We scale those matching scores by dividing by the square root of key dimension, before choosing which input to emphasize."},
        "beat_3":{"claim_id":"A3","visual_style":"spotlight","focus":"weights","pace":"steady",
           "narration":"Softmax turns those scaled scores into positive attention weights whose sum is one. The stronger match receives a larger share, but both tokens can still contribute information."},
        "beat_4":{"claim_id":"A4","visual_style":"trace","focus":"context","pace":"deliberate",
           "narration":"Finally, we take a weighted sum of the value vectors. That mixture becomes the context output for this query: attention selects information rather than copying only one token."}
      }}


def beat_object(raw):
    """Reuse original V3-34 WAV-exact physical audio helper."""
    from types import SimpleNamespace
    bs=[SimpleNamespace(narration=raw["beats"][f"beat_{i}"]["narration"],
                        claim_ids=[ROLES[i-1]]) for i in range(1,5)]
    return SimpleNamespace(beats=bs)


def compile_manim(raw,beat_durations):
    """Finite host-owned renderer. Model JSON only controls semantic staging.

    Numeric scores/weights/output are all recomputed from the preregistered
    vectors; generated Python cannot originate in a model response.
    """
    verify_storyboard(raw)
    if len(beat_durations)!=4 or any(not 3<=x<=20 for x in beat_durations):
        raise Blocked("V350_BEAT_CLOCK_INVALID")
    example=exact_example()
    w0,w1=example["weights"]
    def T(name,content,x,y,size=30,color="WHITE"):
        return f"        {name}=Text({content!r},font='CMU Serif',font_size={size},color={color}).move_to([{x},{y},0]).set_z_index(4)"
    lines=[
      "# HOST_COMPILED_V350_ATTENTION_ONE_QUERY_NOT_MODEL_PYTHON",
      "from manim import *",
      "class GeneratedLesson(Scene):",
      "    def construct(self):",
      "        self.camera.background_color='#000000'",
      T("title",raw["title"],0,3.22,34,"WHITE"),
      T("subtitle","One query   |   Two key-value pairs   |   d_k = 2",0,2.76,20,"GREY"),
      T("q_lab","Q = [1, 0]",-4.45,1.34,27,"YELLOW"),
      T("k1_lab","K_A = [1, 0]",.0,1.47,26,"TEAL"),
      T("k2_lab","K_B = [0, 1]",3.15,1.47,26,"BLUE"),
      T("token_a","Token A",-0.05,2.05,24,"TEAL"),
      T("token_b","Token B",3.15,2.05,24,"BLUE"),
      T("v1_lab","V_A = [1, 0]",-0.1,-1.42,25,"TEAL"),
      T("v2_lab","V_B = [0, 1]",3.2,-1.42,25,"BLUE"),
      T("score1",f"s_A = 1 / sqrt(2) = {example['scores'][0]:.3f}",-2.2,-.05,28,"TEAL"),
      T("score2","s_B = 0",-2.2,-.66,28,"BLUE"),
      T("softmax_lbl","softmax(s_A, s_B)",-1.0,.6,29,"WHITE"),
      T("weight1",f"w_A = {w0:.3f}",-1.5,-.2,30,"TEAL"),
      T("weight2",f"w_B = {w1:.3f}",2.2,-.2,30,"BLUE"),
      T("output",f"context = [{example['context'][0]:.3f}, {example['context'][1]:.3f}]",0,-.3,34,"YELLOW"),
      T("formula","Attention(Q,K,V) = softmax(Q K^T / sqrt(d_k)) V",0,2.08,24,"WHITE"),
      "        boxq=SurroundingRectangle(q_lab,color=YELLOW,buff=.25)",
      "        boxk1=SurroundingRectangle(k1_lab,color=TEAL,buff=.18)",
      "        boxk2=SurroundingRectangle(k2_lab,color=BLUE,buff=.18)",
      "        arrow1=Arrow([-3.15,1.25,0],[-1.0,1.47,0],buff=0,color=TEAL,stroke_width=4)",
      "        arrow2=Arrow([-3.10,1.12,0],[2.0,1.43,0],buff=0,color=BLUE,stroke_width=4)",
      "        dot1=Dot(radius=.11,color=TEAL)",
      "        dot2=Dot(radius=.11,color=BLUE)",
      f"        bar1=Rectangle(width=.70,height={w0*2.2:.4f},color=TEAL,fill_opacity=.75).move_to([-1.5,-1.56,0])",
      f"        bar2=Rectangle(width=.70,height={w1*2.2:.4f},color=BLUE,fill_opacity=.75).move_to([2.2,-1.56,0])"
    ]
    def focus(i):
        b=raw["beats"][f"beat_{i+1}"];target=b["focus"]
        targets={"query":"q_lab","keys":"k1_lab","tokens":"token_a",
          "scores":"score1","weights":"weight1","softmax":"softmax_lbl",
          "values":"v1_lab","context":"output"}
        method=b["visual_style"]
        chosen=targets[target]
        if method=="spotlight":
            return f"        self.play(Indicate({chosen},color=YELLOW,scale_factor=1.08),run_time=0.65)"
        if method=="compare":
            return f"        self.play(Circumscribe({chosen},color=YELLOW),run_time=0.65)"
        return f"        self.play(Flash({chosen},color=YELLOW),run_time=0.65)"
    for i,duration in enumerate(beat_durations):
        pace=raw["beats"][f"beat_{i+1}"]["pace"]
        draw=1.7 if pace=="deliberate" else 1.2
        lines.append(f"        # V350_BEAT_{i+1}_START narration_exact_wav_duration {duration:.5f}")
        if i==0:
            lines += [
              f"        self.play(Write(title),FadeIn(subtitle),run_time={draw:.3f})",
              "        self.play(FadeIn(q_lab),FadeIn(k1_lab),FadeIn(k2_lab),"
              "FadeIn(token_a),FadeIn(token_b),FadeIn(boxq),FadeIn(boxk1),FadeIn(boxk2),run_time=1.5)"
            ]
            used=draw+1.5
        elif i==1:
            lines += [
              f"        self.play(Create(arrow1),Create(arrow2),run_time={draw:.3f})",
              "        dot1.move_to(arrow1.get_start()); dot2.move_to(arrow2.get_start())",
              "        self.play(MoveAlongPath(dot1,Line(arrow1.get_start(),arrow1.get_end())),"
              "MoveAlongPath(dot2,Line(arrow2.get_start(),arrow2.get_end())),run_time=1.4)",
              "        self.play(FadeIn(score1),FadeIn(score2),run_time=.65)"
            ]
            used=draw+1.4+.65
        elif i==2:
            lines += [
              "        self.play(FadeOut(score1),FadeOut(score2),FadeOut(arrow1),FadeOut(arrow2),"
              "FadeOut(boxq),FadeOut(boxk1),FadeOut(boxk2),"
              "FadeOut(q_lab),FadeOut(k1_lab),FadeOut(k2_lab),run_time=.6)",
              f"        self.play(FadeIn(softmax_lbl),run_time={draw:.3f})",
              "        self.play(FadeIn(weight1),FadeIn(weight2),"
              "GrowFromEdge(bar1,DOWN),GrowFromEdge(bar2,DOWN),run_time=1.1)"
            ]
            used=.6+draw+1.1
        else:
            lines += [
              "        self.play(FadeOut(softmax_lbl),FadeOut(token_a),FadeOut(token_b),"
              "FadeOut(bar1),FadeOut(bar2),run_time=.7)",
              f"        self.play(FadeIn(v1_lab),FadeIn(v2_lab),run_time={draw:.3f})",
              "        self.play(TransformFromCopy(weight1,output),"
              "Indicate(v1_lab,color=TEAL),Indicate(v2_lab,color=BLUE),run_time=1.1)",
              "        self.play(FadeIn(formula),run_time=.65)"
            ]
            used=.7+draw+1.1+.65
        lines.append(focus(i))
        used+=.65
        if duration-used < .45:
            raise Blocked("V350_SPEECH_BEAT_TOO_SHORT_FOR_HOST_EVENTS")
        lines.append(f"        self.wait({duration-used:.5f})")
    lines.append("        self.wait(.8)  # video-only extra frames trimmed by exact WAV mux")
    code="\n".join(lines)+"\n"
    if any(x in code for x in ("__import__","eval(","exec(","subprocess","import os")):
        raise Blocked("V350_HOST_CODE_SAFETY")
    compile(code,"<host verified attention Manim>","exec")
    return code
