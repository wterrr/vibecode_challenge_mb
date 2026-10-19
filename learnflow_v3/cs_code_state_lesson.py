"""V3-31 audited, offline-only CS code/state video from a pinned V3-30 receipt.

Do NOT claim author-original Research for repaired explanations or general Python execution.
The function AST is inspected, never compiled or executed. The existing V3-07
typed CodeWalkthrough verifies numeric arithmetic; ProcessWalkthrough verifies stages.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re

from PIL import Image, ImageDraw

from learnflow_v2.repair import compute_content_hash
from learnflow_v2.scenegraph import SceneGraph
from learnflow_v3.blackboard_style import (
    BLACK, WHITE, GREY, FAINT, YELLOW, CYAN, GREEN, cmu_font, assert_fits,
)
from learnflow_v3.code_process_renderer import (
    CodeLine, CodeStep, CodeWalkthrough, verify_code_walkthrough,
    verify_process_walkthrough,
)
from learnflow_v3.paid_cs_lesson import (
    Blocked, STAGES, SOURCE_URL, build_contracts,
    render_lesson, validate_research, validate_script,
)
from learnflow_v3.multidomain_coverage import read_source, guard
from learnflow_v3.sequence_renderer import SequenceRenderProfile, _ffmpeg_anchor, _mean_absolute_error

VERSION = "v3-31-code-state-semantic-provenance-v1"
EXAMPLE = "def add_two(n):\n    return n + 2\n\nanswer = add_two(3)"
ORIGINAL_MODEL_SCRIPT = (
    "Define a function with def; def introduces its definition, followed by its name and parameter list.",
    "Call add_two with argument three; the call supplies three as input to the function.",
    "Bind parameter n to three for this call; the parameter refers to the input supplied by the argument.",
    "The return statement sends back five from add_two after it uses the supplied input.",
)
ORIGINAL_MODEL_RESEARCH = (
    "A function is a named set of instructions, and its parameter list names the inputs. Worked example: imagine a doubling function with one parameter, number.",
    "Calling that function with 4 supplies 4 as its argument; inside the function, the parameter refers to that call's input, so the calculation uses 4.",
    "It can return 8 after doubling 4. Quick check: if the input were 6, what value should the same function return? (Answer: 12.)",
)
REPAIRED_EXPLANATIONS = (
    "Define add_two with one parameter n. The function body adds two to the input and returns that sum.",
    "Calling add_two with argument 3 binds that same value to parameter n for this call.",
    "With n equal to 3, the expression n plus 2 equals 5, so this function returns 5.",
)
ROUTE = ("define", "call", "bind", "return")
LINE_IDS = ("signature", "body", "invocation")
AUDIO_STEM = "cs_code_state_grounded_720p"


def load_pinned_receipt(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    if (record.get("checkpoint") != "V3-30"
        or record.get("exact_model") != "openai/gpt-6-luna"
        or record.get("live_paid_provider_requests") != 2
        or record.get("locked_topic") != "lfb-002-cs"
        or record.get("rendered_video_sha256") != "1f2a4e7d7ce07ce9163f9702e14ba0cafcd44881f2eb893f9ab4faa4e252cedb"
        or record.get("research_response_sha256") != "90531f95a0d767164594d4e9ad9e5577ae39f39ce55838ba4b4e512ea5e0908f"
        or record.get("script_response_sha256") != "e382761e5420631845fbe46c12a34a524b860e06e59409048a4715f6186c3fc2"):
        raise Blocked("V331_V330_PROVENANCE_MISMATCH")
    if [c["explanation"] for c in record["research_claims"]] != list(ORIGINAL_MODEL_RESEARCH):
        raise Blocked("V331_ORIGINAL_RESEARCH_TAMPER")
    if [s["segment_id"] for s in record["script_segments"]] != [
            "seg-define", "seg-call", "seg-bind", "seg-return"]:
        raise Blocked("V331_SCRIPT_ID_DRIFT")
    if [s["spoken_text"] for s in record["script_segments"]] != list(ORIGINAL_MODEL_SCRIPT):
        raise Blocked("V331_ORIGINAL_SCRIPT_TAMPER")
    if record["source_certificate"].get("sha256_html") != "d1055a285f5916c6c627c080a34211df7408aa3d7601ab1775191324e12dc6bb":
        raise Blocked("V331_SOURCE_HASH_DRIFT")
    if record["source_certificate"]["source_url"] != SOURCE_URL:
        raise Blocked("V331_SOURCE_ORIGIN_DRIFT")
    return record


def consistency_audit(record: dict) -> dict:
    research = record["research_claims"]
    contradictions = []
    for item in research:
        text = item["explanation"].casefold()
        if ("doubl" in text or re.search(r"\b(?:4|6|8|12)\b", text)):
            contradictions.append({
                "claim_id": item["claim_id"], "code": "V331_EXAMPLE_FAMILY_DRIFT",
                "research_explanation_sha256": sha256(item["explanation"].encode()).hexdigest(),
                "canonical_example": "add_two(3) = 5",
            })
    return {"status": "CONFLICT" if contradictions else "CLEAN",
            "canonical_example": "add_two(3) = 5",
            "issues": contradictions, "count": len(contradictions)}


def inspect_fixed_code(source: str = EXAMPLE) -> tuple[dict, ...]:
    """Certify only add_two(n)=n+2 and answer=add_two(3); AST never evaluated."""
    try:
        module = ast.parse(source, mode="exec")
        if len(module.body) != 2:
            raise ValueError("statement_count")
        f, invocation = module.body
        if not isinstance(f, ast.FunctionDef) or f.name != "add_two" or f.decorator_list:
            raise ValueError("function_definition")
        args = f.args
        if (len(args.args) != 1 or args.args[0].arg != "n" or args.posonlyargs
            or args.kwonlyargs or args.defaults or args.kw_defaults
            or args.vararg or args.kwarg or args.kwarg is not None):
            raise ValueError("parameter_contract")
        if len(f.body) != 1 or not isinstance(f.body[0], ast.Return):
            raise ValueError("return_structure")
        expr = f.body[0].value
        if (not isinstance(expr, ast.BinOp) or not isinstance(expr.op, ast.Add)
            or not isinstance(expr.left, ast.Name) or expr.left.id != "n"
            or not isinstance(expr.right, ast.Constant)
            or type(expr.right.value) is not int or expr.right.value != 2):
            raise ValueError("return_expression")
        if (not isinstance(invocation, ast.Assign) or len(invocation.targets) != 1
            or not isinstance(invocation.targets[0], ast.Name)
            or invocation.targets[0].id != "answer"):
            raise ValueError("result_assignment")
        call = invocation.value
        if (not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name)
            or call.func.id != "add_two" or len(call.args) != 1 or call.keywords
            or not isinstance(call.args[0], ast.Constant)
            or type(call.args[0].value) is not int or call.args[0].value != 3):
            raise ValueError("call_argument")
    except (SyntaxError, ValueError, AttributeError, TypeError) as exc:
        raise Blocked("V331_CODE_AST_NOT_CERTIFIED") from exc
    return (
        {"stage": "define", "active_line": "signature", "argument": None,
         "parameter": None, "calculation": None, "returned": None},
        {"stage": "call", "active_line": "invocation", "argument": 3,
         "parameter": None, "calculation": None, "returned": None},
        {"stage": "bind", "active_line": "invocation", "argument": 3,
         "parameter": 3, "calculation": None, "returned": None},
        {"stage": "return", "active_line": "body", "argument": 3,
         "parameter": 3, "calculation": "3 + 2 = 5", "returned": 5},
    )


def certified_integer_replay():
    """Reuse V3-07's actual allowlist AST/state verifier, NOT generic def support."""
    code = ("n = 3", "result = n + 2")
    graph = SceneGraph.model_validate({
        "scene_id": "cs-numeric-subtrace",
        "purpose": "DEMONSTRATE",
        "layout_intent": {"type": "GRID"},
        "nodes": [{"id": "code", "kind": "CODE", "label": "Arithmetic replay", "content": "\n".join(code)}],
        "relations": [],
    })
    spec = CodeWalkthrough(
        scenegraph_sha256=compute_content_hash(graph),
        lines=(CodeLine(line_id="bind-n", source=code[0]),
               CodeLine(line_id="sum", source=code[1])),
        steps=(CodeStep(line_id="bind-n", variables={"n": 3}),
               CodeStep(line_id="sum", variables={"n": 3, "result": 5})),
    )
    verify_code_walkthrough(spec, graph)
    return {"numeric_code_walkthrough_sha256": compute_content_hash(spec),
            "numeric_scenegraph_sha256": compute_content_hash(graph)}


def build_certified_bundle(root: Path, record: dict, *, repair: bool) -> dict:
    audit = consistency_audit(record)
    if audit["status"] != "CONFLICT" or audit["count"] != 3:
        raise Blocked("V331_EXPECTED_ORIGINAL_CONFLICT_MISSING")
    if not repair:
        raise Blocked("V331_SEMANTIC_DRIFT_UNREPAIRED")
    claims = deepcopy(record["research_claims"])
    for c, corrected in zip(claims, REPAIRED_EXPLANATIONS, strict=True):
        c["explanation"] = corrected
    cert = record["source_certificate"]
    # Reuse V3-30's exact source-quote validator and script typed claim gate.
    validate_research({"claims": claims}, cert)
    segments = validate_script({"segments": record["script_segments"]}, claims)
    if segments != record["script_segments"]:
        raise Blocked("V331_NARRATION_UNEXPECTEDLY_MODIFIED")
    topic = next(x for x in read_source(root)[0] if x["topic_id"] == "lfb-002-cs")
    if topic["query_sha256"] != record["topic_hash"]:
        raise Blocked("V331_LOCKED_TOPIC_CHANGED")
    bundle = build_contracts(topic=topic, certificate=cert,
                             claims=claims, segments=segments)
    verify_process_walkthrough(bundle["spec"], bundle["graph"])
    trace = inspect_fixed_code()
    replay = certified_integer_replay()
    if tuple(s["stage"] for s in trace) != ROUTE:
        raise Blocked("V331_TRACE_ORDER_MISMATCH")
    if trace[-1]["calculation"] != "3 + 2 = 5" or trace[-1]["returned"] != 5:
        raise Blocked("V331_ARITHMETIC_INCONSISTENT")
    bundle["_v331_trace"] = trace
    bundle["_v331_audit"] = audit
    bundle["_v331_replay"] = replay
    bundle["_v331_edits"] = [
        {"claim_id": c["claim_id"],
         "reason": "V331_EXAMPLE_FAMILY_DRIFT",
         "before_sha256": sha256(o.encode()).hexdigest(),
         "after_sha256": sha256(c["explanation"].encode()).hexdigest(),
         "author": "HOST_ADAPTIVE_EDIT_NOT_GPT6_LUNA"}
        for c, o in zip(claims, ORIGINAL_MODEL_RESEARCH, strict=True)
    ]
    return bundle


def _render_text(draw, xy, value, font, *, color=WHITE, max_width=None, role="CAPTION", anchor=None):
    if max_width is not None:
        assert_fits(draw, value, font, max_width, role=role)
    draw.text(xy, value, font=font, fill=color, anchor=anchor)


def draw_code_state_frame(bundle: dict, index: int, phase: float,
                          profile: SequenceRenderProfile, narration: str) -> Image.Image:
    trace = bundle["_v331_trace"]
    verify_process_walkthrough(bundle["spec"], bundle["graph"])
    if index < 0 or index >= len(trace) or not 0 <= phase <= 1:
        raise Blocked("V331_INVALID_FRAME_STAGE")
    state = trace[index]
    if state["stage"] != ROUTE[index]:
        raise Blocked("V331_VISUAL_STATE_DRIFT")
    w, h = profile.width, profile.height
    if (w, h) != (1280, 720):
        raise Blocked("V331_FIXED_LAYOUT_ONLY")
    im = Image.new("RGB", (w, h), BLACK)
    d = ImageDraw.Draw(im)
    serif, mono = cmu_font(36), cmu_font(29, mono=True)
    small, caption = cmu_font(22), cmu_font(26)
    d.text((65, 33), "LEARNFLOW   /   COMPUTER SCIENCE", font=small, fill=GREY)
    _render_text(d, (65, 70), "Where does the argument go?", serif, max_width=1120, role="TITLE")
    d.line((65, 134, 1210, 134), fill=FAINT, width=2)
    d.rounded_rectangle((64, 163, 736, 500), radius=14,
                        fill=(11, 12, 15), outline=(42, 44, 49), width=2)
    d.rounded_rectangle((758, 163, 1215, 500), radius=14,
                        fill=(11, 12, 15), outline=(42, 44, 49), width=2)
    d.text((91, 186), "PYTHON", font=small, fill=CYAN)
    d.text((785, 186), "LIVE STATE", font=small, fill=CYAN)
    code_lines = [
        ("signature", "1", "def add_two(n):", 246),
        ("body", "2", "    return n + 2", 315),
        ("invocation", "4", "answer = add_two(3)", 424),
    ]
    for ident, line_num, code, y in code_lines:
        current = ident == state["active_line"]
        if current:
            d.rounded_rectangle((80, y-9, 718, y+46), radius=8,
                                fill=(29, 28, 13))
            d.rectangle((80, y-8, 85, y+44), fill=YELLOW)
            d.line((116, y+48, 116+int(558*max(0,phase)), y+48),
                   fill=YELLOW, width=3)
        _render_text(d, (97, y), line_num, small, color=GREY)
        _render_text(d, (151, y), code, mono,
                     color=YELLOW if current else WHITE if index >= 2 else GREY,
                     max_width=545, role="CODE")
    entries = [
        ("ARGUMENT", "3" if state["argument"] is not None else "—"),
        ("PARAMETER n", "3" if state["parameter"] is not None else "—"),
        ("EVALUATE", state["calculation"] or "—"),
        ("RETURNED", "5" if state["returned"] is not None else "—"),
    ]
    # In each beat, spotlight the newly revealed semantic value so learners
    # can follow argument -> parameter -> return, not stare at four static boxes.
    focused_row = {"define": None, "call": 0, "bind": 1, "return": 3}[state["stage"]]
    for i, (label, value) in enumerate(entries):
        y=239+i*59
        if i == focused_row:
            d.rounded_rectangle((1008, y-12, 1194, y+40), radius=9,
                                fill=(20, 64, 47), outline=GREEN, width=2)
        d.text((785, y), label, font=small, fill=GREY)
        _render_text(d, (1175, y-1), value, cmu_font(28, mono=True),
                     color=GREEN if value!="—" else GREY,
                     max_width=208, role="VALUE", anchor="ra")
        if i<3:
            d.line((785, y+40, 1187, y+40), fill=(36,39,43), width=1)
    # Stage markers follow the verified V3-07 ProcessWalkthrough identity.
    d.line((65, 555, 1210, 555), fill=FAINT, width=2)
    xs=(180,490,803,1110)
    for i,(x,stage) in enumerate(zip(xs,ROUTE)):
        active=i==index
        d.ellipse((x-7,548,x+7,562),
                  fill=YELLOW if active else GREEN if i<index else FAINT)
        d.text((x,570),stage.upper(),font=cmu_font(19),
               fill=YELLOW if active else GREEN if i<index else GREY,anchor="mt")
    # Physical-utterance caption; SRT boundaries are created from its WAV duration.
    d.rectangle((0,606,1280,720),fill=BLACK)
    d.line((65,610,1210,610),fill=FAINT,width=2)
    parts=[]; segment=""
    for word in narration.split():
        candidate=(segment+" "+word).strip()
        if d.textbbox((0,0),candidate,font=caption)[2]>1090 and segment:
            parts.append(segment)
            segment=word
        else:
            segment=candidate
    if segment:parts.append(segment)
    if not 1 <= len(parts) <= 2:
        raise Blocked("V331_CAPTION_OVERFLOW")
    for k,line in enumerate(parts):
        _render_text(d,(640,638+k*32),line,caption,anchor="mt",
                     max_width=1090,role="CAPTION")
    return im


def render_v331(root: Path, input_path: Path, output: Path) -> dict:
    record=load_pinned_receipt(input_path)
    bundle=build_certified_bundle(root,record,repair=True)
    result=render_lesson(bundle,output,frame_drawer=draw_code_state_frame,
                         video_stem=AUDIO_STEM)
    # The reused V3-30 encoder writes a historical live-labelled receipt.
    # Re-label the generated *offline* encoder evidence to avoid incorrectly
    # implying that the V3-31 checkpoint made new provider calls.
    reused_path=output/"cs_live_media_receipt.json"
    encoder_receipt=json.loads(reused_path.read_text())
    encoder_receipt["status"]="REUSED_V330_ENCODER_OFFLINE_TECHNICAL_PASS"
    encoder_receipt["checkpoint"]="V3-31_ENCODER_SUBCOMPONENT"
    encoder_receipt["v331_provider_requests"]=0
    encoder_receipt["script_provenance"]="ORIGINAL_REAL_V330_LUNA_TEXT_REUSED"
    (output/"v3_31_encoder_receipt.json").write_text(
        json.dumps(encoder_receipt,indent=2)+"\n")
    reused_path.unlink()
    # Pixel-level semantic-state distinctions are independently checked on
    # actual decoded encoded video, not just source storyboard metadata.
    profile=SequenceRenderProfile(width=1280,height=720,fps=18,seconds_per_step=1.0)
    path=output/(AUDIO_STEM+".mp4")
    frames=[]
    for beat in result["beats"]:
        k=beat["frame_start"]+beat["frames"]//2
        frames.append(_ffmpeg_anchor(path,at=(k+.4)/18,profile=profile))
    region=(770,218,1196,495)
    deltas=[]
    for before,after in zip(frames,frames[1:]):
        b=before.crop(region); a=after.crop(region)
        delta=_mean_absolute_error(a,b)
        if delta<=0.8:
            raise Blocked("V331_DECODED_STATE_ROI_NOT_CHANGING")
        deltas.append(round(delta,3))
    if len(deltas)!=3:
        raise Blocked("V331_DECODED_BEAT_COUNT")
    # A measurable ROI transition is useful, but does NOT equal word alignment.
    receipt={
        "checkpoint":"V3-31","status":"OFFLINE_CODE_STATE_MEDIA_TECHNICAL_PASS",
        "topic_id":"lfb-002-cs","production":"BLOCKED",
        "v330_actual_provider_requests":2,"v331_provider_requests":0,
        "v330_source_video_sha256":record["rendered_video_sha256"],
        "input_research_model_original": True,
        "corrected_research_author":"HOST_ADAPTIVE_EDIT_NOT_MODEL_OUTPUT",
        "model_authored_script_reused_unmodified":True,
        "semantic_inconsistency_detected":bundle["_v331_audit"],
        "correction_ledger":bundle["_v331_edits"],
        "trace":bundle["_v331_trace"],
        "trace_sha256":compute_content_hash(bundle["_v331_trace"]),
        "numeric_code_replay":bundle["_v331_replay"],
        "process_spec_sha256":compute_content_hash(bundle["spec"]),
        "video_sha256":result["video_sha256"], "frames":result["frames"],
        "fps":result["fps"],"width":result["width"],"height":result["height"],
        "beats":result["beats"],
        "decoded_replay":result["decoded_replay"],
        "aac_rms_per_actual_beat":result["aac_rms_per_actual_beat"],
        "state_region_decoded_delta":deltas,
        "subtitle_sha256":result["subtitle_sha256"],
        "alignment":"SEGMENT_LEVEL_PHYSICAL_WAV_NOT_WORD_LEVEL",
        "pedagogy_model":"NOT_RUN", "visual_director_model":"NOT_RUN",
        "independent_semantic_expert_review":"NOT_RUN",
        "actual_human_readability_review":"NOT_RUN",
        "human_learning_outcome":"UNMEASURED",
        "audio_licensing":"NOT_CLEARED",
        "six_domain_full_autonomy":"NO_GO",
        "final_quality_gate":"NO_GO_FOR_PRODUCTION",
    }
    (output/"v3_31_code_state_receipt.json").write_text(
        json.dumps(receipt,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return receipt
