"""V3-07 bounded, standalone CODE and PROCESS video primitives.

No eval/exec, no arbitrary Python or generated Manim. Uses frozen V2
SceneGraph identity and V3-06's decoded MP4 QA primitives. Semantic truth:
code's allowlisted integer assignment AST replay; process graph's exact
typed edge replay. These finite contracts are NOT general code executors.
"""
from __future__ import annotations

import ast
from collections import defaultdict, deque
import hashlib
import os
from pathlib import Path
import subprocess
import time
from typing import Literal

from PIL import Image, ImageDraw
from pydantic import Field, StrictInt, model_validator

from learnflow_v2.repair import compute_content_hash
from learnflow_v2.scenegraph import SceneGraph
from learnflow_v2.scenegraph.enums import LayoutIntent, NodeKind, RelationKind, ScenePurpose
from .blackboard_style import BLACK, WHITE, GREY, FAINT, YELLOW, CYAN, GREEN, RED, VIOLET, cmu_font, assert_fits
from .models import SemanticContractError, V3Model
from .sequence_renderer import SequenceRenderProfile, _ease, _ffmpeg_anchor, _mean_absolute_error

RENDERER_VERSION = "v3-07-blackboard-renderers-v1"
MAX_CODE_LINES = 9
MAX_GRAPH_NODES = 8
FLOW_KINDS = (RelationKind.FLOW, RelationKind.SEQUENCE_BEFORE)


class CodeLine(V3Model):
    line_id: str = Field(min_length=1, max_length=28, pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$")
    source: str = Field(min_length=3, max_length=45)


class CodeStep(V3Model):
    line_id: str
    variables: dict[str, StrictInt] = Field(min_length=1, max_length=8)


class CodeWalkthrough(V3Model):
    scenegraph_sha256: str = Field(min_length=64, max_length=64)
    lines: tuple[CodeLine, ...] = Field(min_length=2, max_length=MAX_CODE_LINES)
    steps: tuple[CodeStep, ...] = Field(min_length=2, max_length=MAX_CODE_LINES)

    @model_validator(mode="after")
    def _shape(self):
        ids = [l.line_id for l in self.lines]
        if len(ids) != len(set(ids)) or [s.line_id for s in self.steps] != ids:
            raise ValueError("CODE_STEP_LINE_IDENTITY_MISMATCH")
        return self


class ProcessStep(V3Model):
    active_node_id: str
    via_edge_id: str | None = None


class ProcessWalkthrough(V3Model):
    scenegraph_sha256: str = Field(min_length=64, max_length=64)
    steps: tuple[ProcessStep, ...] = Field(min_length=2, max_length=MAX_GRAPH_NODES)


class MotionEvidence(V3Model):
    renderer_version: Literal["v3-07-blackboard-renderers-v1"] = RENDERER_VERSION
    family: Literal["CODE_WALKTHROUGH", "PROCESS_FLOW"]
    path: str
    video_sha256: str
    video_bytes: int
    source_hash: str
    scenegraph_hash: str
    frame_count: int
    fps: int
    duration_seconds: float
    sample_frames: tuple[int, ...]
    decoded_mae: tuple[float, ...]
    semantic_roi_delta: tuple[float, ...]
    within_beat_motion_delta: tuple[float, ...]
    stable_object_centers: dict[str, tuple[int, int]]
    video_checks_pass: Literal[True] = True
    wall_seconds: float


def _integer_expr(expr: ast.expr, variables: dict[str, int]) -> int:
    """Own allowlist evaluator. AST is data: NEVER compiled or executed."""
    if isinstance(expr, ast.Constant) and type(expr.value) is int:
        return expr.value
    if isinstance(expr, ast.Name) and expr.id in variables:
        return variables[expr.id]
    if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.USub):
        return -_integer_expr(expr.operand, variables)
    if isinstance(expr, ast.BinOp):
        l, r = _integer_expr(expr.left, variables), _integer_expr(expr.right, variables)
        if isinstance(expr.op, ast.Add):
            return l + r
        if isinstance(expr.op, ast.Sub):
            return l - r
        if isinstance(expr.op, ast.Mult):
            return l * r
        if isinstance(expr.op, ast.FloorDiv) and r != 0:
            return l // r
    raise SemanticContractError("V3_07_UNSUPPORTED_CODE_EXPRESSION")


def verify_code_walkthrough(spec: CodeWalkthrough, graph: SceneGraph) -> None:
    if compute_content_hash(graph) != spec.scenegraph_sha256:
        raise SemanticContractError("V3_07_CODE_GRAPH_HASH_MISMATCH")
    if graph.layout_intent.type not in (LayoutIntent.GRID, LayoutIntent.PROCESS, LayoutIntent.FREEFORM):
        raise SemanticContractError("V3_07_CODE_LAYOUT_UNSUPPORTED")
    if graph.purpose not in (ScenePurpose.EXPLAIN, ScenePurpose.DEMONSTRATE, ScenePurpose.DRILLDOWN):
        raise SemanticContractError("V3_07_CODE_PURPOSE_UNSUPPORTED")
    code_nodes = [n for n in graph.nodes if n.kind == NodeKind.CODE]
    if len(code_nodes) != 1 or len(graph.nodes) != 1 or graph.relations:
        raise SemanticContractError("V3_07_CODE_REQUIRES_ONE_TYPED_CODE_NODE")
    exact_text = "\n".join(line.source for line in spec.lines)
    if code_nodes[0].content != exact_text:
        raise SemanticContractError("V3_07_CODE_SOURCE_SCENEGRAPH_DRIFT")
    variables: dict[str, int] = {}
    for line, step in zip(spec.lines, spec.steps, strict=True):
        try:
            parsed = ast.parse(line.source, mode="exec")
        except (SyntaxError, ValueError) as exc:
            raise SemanticContractError("V3_07_CODE_PARSE_REJECTED") from exc
        if (len(parsed.body) != 1 or not isinstance(parsed.body[0], ast.Assign) or
            len(parsed.body[0].targets) != 1 or
            not isinstance(parsed.body[0].targets[0], ast.Name)):
            raise SemanticContractError("V3_07_CODE_STATEMENT_NOT_ALLOWLISTED")
        identifier=parsed.body[0].targets[0].id
        if identifier.startswith("_") or len(identifier)>18:
            raise SemanticContractError("V3_07_CODE_VARIABLE_UNSAFE")
        value=_integer_expr(parsed.body[0].value, variables)
        if abs(value)>1_000_000:
            raise SemanticContractError("V3_07_CODE_VALUE_OVERFLOW")
        variables[identifier]=value
        if variables != step.variables:
            raise SemanticContractError(f"V3_07_CODE_STATE_REPLAY_MISMATCH:{line.line_id}")


def verify_process_walkthrough(spec: ProcessWalkthrough, graph: SceneGraph) -> None:
    if compute_content_hash(graph) != spec.scenegraph_sha256:
        raise SemanticContractError("V3_07_PROCESS_GRAPH_HASH_MISMATCH")
    if graph.layout_intent.type not in (LayoutIntent.PROCESS, LayoutIntent.HIERARCHY):
        raise SemanticContractError("V3_07_PROCESS_LAYOUT_UNSUPPORTED")
    if graph.purpose not in (ScenePurpose.EXPLAIN, ScenePurpose.DEMONSTRATE):
        raise SemanticContractError("V3_07_PROCESS_PURPOSE_UNSUPPORTED")
    if not 2<=len(graph.nodes)<=MAX_GRAPH_NODES:
        raise SemanticContractError("V3_07_PROCESS_NODE_COUNT_UNSUPPORTED")
    for n in graph.nodes:
        if n.kind not in (NodeKind.TEXT,NodeKind.CONCEPT,NodeKind.SHAPE):
            raise SemanticContractError("V3_07_PROCESS_NODE_KIND_UNSUPPORTED")
        if not n.label or len(n.label)>25:
            raise SemanticContractError("V3_07_PROCESS_LABEL_MISSING_OR_LONG")
    if not graph.relations or any(r.kind not in FLOW_KINDS for r in graph.relations):
        raise SemanticContractError("V3_07_PROCESS_EDGE_KIND_UNSUPPORTED")
    layout_process(graph)  # reject cycle or colliding topology, not flattening it
    edge_ids={r.id:r for r in graph.relations}
    node_ids={n.id for n in graph.nodes}
    if spec.steps[0].active_node_id not in node_ids or spec.steps[0].via_edge_id is not None:
        raise SemanticContractError("V3_07_PROCESS_START_INVALID")
    for before, now in zip(spec.steps, spec.steps[1:]):
        rel=edge_ids.get(now.via_edge_id)
        if rel is None or rel.source!=before.active_node_id or rel.target!=now.active_node_id:
            raise SemanticContractError("V3_07_PROCESS_TOPOLOGY_REPLAY_MISMATCH")


def layout_process(graph: SceneGraph, profile: SequenceRenderProfile | None = None) -> dict[str, tuple[int,int]]:
    """Stable DAG layered layout; reject unsupported cycles or crowded topology."""
    profile=profile or SequenceRenderProfile()
    indegree={n.id:0 for n in graph.nodes}
    outgoing=defaultdict(list)
    for rel in graph.relations:
        outgoing[rel.source].append(rel.target)
        indegree[rel.target]+=1
    starts=sorted(n for n,d in indegree.items() if d==0)
    if not starts:
        raise SemanticContractError("V3_07_PROCESS_CYCLIC_GRAPH")
    q=deque(starts)
    ranks={name:0 for name in starts}
    visited=0
    while q:
        n=q.popleft()
        visited+=1
        for child in sorted(outgoing[n]):
            ranks[child]=max(ranks.get(child,0),ranks[n]+1)
            indegree[child]-=1
            if indegree[child]==0:q.append(child)
    if visited!=len(graph.nodes):
        raise SemanticContractError("V3_07_PROCESS_CYCLIC_GRAPH")
    layers=defaultdict(list)
    for name,rank in ranks.items():layers[rank].append(name)
    if len(layers)>4 or any(len(group)>3 for group in layers.values()):
        raise SemanticContractError("V3_07_PROCESS_TOPOLOGY_TOO_DENSE")
    w,h=profile.width,profile.height
    coords={}
    for rank,group in sorted(layers.items()):
        for j,name in enumerate(sorted(group)):
            x=round(w*(0.18+0.64*rank/max(1,len(layers)-1)))
            y=round(h*(0.53 + (j-(len(group)-1)/2)*0.24))
            coords[name]=(x,y)
    if len(coords)!=len(graph.nodes) or any(abs(x1-x2)<155*w/960 and abs(y1-y2)<65*h/540
       for i,(x1,y1) in enumerate(coords.values()) for x2,y2 in list(coords.values())[i+1:]):
        raise SemanticContractError("V3_07_PROCESS_NODE_COLLISION")
    return coords


def _header(draw, profile, title: str):
    w,h=profile.width,profile.height
    sx,sy=w/960,h/540
    font=cmu_font(round(35*sy))
    assert_fits(draw,title,font,round(w*.82),role="TITLE")
    draw.text((round(55*sx),round(30*sy)),title,font=font,fill=WHITE)
    draw.line((round(55*sx),round(97*sy),round(905*sx),round(97*sy)),
              fill=FAINT,width=max(1,round(sy)))
    return sx,sy


def draw_code_frame(spec: CodeWalkthrough, graph: SceneGraph, step_index: int, profile: SequenceRenderProfile, progress: float=1.0)->Image.Image:
    if not 0<=step_index<len(spec.steps):
        raise SemanticContractError("V3_07_CODE_FRAME_OUT_OF_RANGE")
    w,h=profile.width,profile.height
    im=Image.new("RGB",(w,h),BLACK)
    d=ImageDraw.Draw(im)
    sx,sy=_header(d,profile,"How the code changes state")
    mono=cmu_font(round(23*sy),mono=True)
    serif=cmu_font(round(23*sy))
    hint=cmu_font(round(17*sy))
    d.text((round(70*sx),round(130*sy)),"CODE",font=serif,fill=GREY)
    d.text((round(635*sx),round(130*sy)),"VARIABLES",font=serif,fill=GREY)
    step=spec.steps[step_index]
    for i,line in enumerate(spec.lines):
        x,y=round(73*sx),round((178+i*34)*sy)
        if y>h-45:raise SemanticContractError("V3_07_CODE_TOO_MANY_LINES")
        assert_fits(d,line.source,mono,round(w*.48),role="CODE")
        if i==step_index:
            d.rectangle((round(62*sx),y-2,round(540*sx),y+round(29*sy)),fill=(25,22,4))
            d.line((round(62*sx),y-2,round(62*sx),y+round(29*sy)),fill=YELLOW,width=max(2,round(4*sx)))
            # Animated progress underline: spans the selected line during the beat.
            bar_end=round((76+450*_ease(progress))*sx)
            d.line((round(76*sx),y+round(30*sy),bar_end,y+round(30*sy)),
                   fill=YELLOW,width=max(2,round(3*sy)))
        d.text((x,y),line.source,font=mono,fill=YELLOW if i==step_index else WHITE if i<step_index else GREY)
    d.line((round(584*sx),round(136*sy),round(584*sx),round(470*sy)),fill=FAINT,width=1)
    for j,(name,value) in enumerate(sorted(step.variables.items())):
        y=round((185+j*49)*sy)
        assert_fits(d,f"{name}  =  {value}",mono,round(w*.29),role="VARIABLE")
        d.text((round(630*sx),y),f"{name}  =  {value}",font=mono,fill=CYAN if j==len(step.variables)-1 else WHITE)
    d.text((round(65*sx),round(496*sy)),f"Step {step_index+1} / {len(spec.steps)}",font=hint,fill=GREY)
    return im


def draw_process_frame(spec: ProcessWalkthrough, graph: SceneGraph, step_index: int, profile: SequenceRenderProfile, progress: float=1.0)->Image.Image:
    if not 0<=step_index<len(spec.steps):
        raise SemanticContractError("V3_07_PROCESS_FRAME_OUT_OF_RANGE")
    coords=layout_process(graph,profile)
    w,h=profile.width,profile.height
    im=Image.new("RGB",(w,h),BLACK)
    d=ImageDraw.Draw(im)
    sx,sy=_header(d,profile,"A process, one state at a time")
    font=cmu_font(round(23*sy))
    small=cmu_font(round(18*sy))
    edge_used={s.via_edge_id for s in spec.steps[1:step_index+1]}
    for rel in graph.relations:
        a,b=coords[rel.source],coords[rel.target]
        active=rel.id in edge_used
        color=GREEN if active else FAINT
        # Route across box edges, not through semantic node labels.
        x1=a[0]+round(72*sx);x2=b[0]-round(72*sx)
        if x2<=x1:
            x1=a[0];x2=b[0]
        d.line((x1,a[1],x2,b[1]),fill=color if rel.id!=spec.steps[step_index].via_edge_id else FAINT,
               width=max(1,round((3 if active else 2)*sy)))
        # Edge traversal is an in-beat animation, not a static slide cut.
        if rel.id==spec.steps[step_index].via_edge_id:
            t=_ease(progress)
            d.line((x1,a[1],round(x1+(x2-x1)*t),round(a[1]+(b[1]-a[1])*t)),
                   fill=YELLOW,width=max(2,round(4*sy)))
        dx=x2-x1;dy=b[1]-a[1]
        mag=max(1,(dx*dx+dy*dy)**.5)
        ux,uy=dx/mag,dy/mag
        tip=(x2,b[1])
        d.polygon((tip,(x2-9*ux-5*uy,b[1]-9*uy+5*ux),
                   (x2-9*ux+5*uy,b[1]-9*uy-5*ux)),fill=color)
    reached={s.active_node_id for s in spec.steps[:step_index+1]}
    current=spec.steps[step_index].active_node_id
    for node in graph.nodes:
        x,y=coords[node.id]
        active=node.id==current
        border=YELLOW if active else GREEN if node.id in reached else GREY
        fill=(27,24,3) if active else BLACK
        rect=(x-round(72*sx),y-round(37*sy),x+round(72*sx),y+round(37*sy))
        d.rounded_rectangle(rect,radius=round(5*sy),fill=fill,outline=border,
                            width=max(2,round((2+2*_ease(progress) if active else 2)*sy)))
        assert_fits(d,node.label,font,round(132*sx),role="PROCESS_NODE")
        d.text((x,y),node.label,font=font,fill=border if active else WHITE,anchor="mm")
    d.text((round(60*sx),round(485*sy)),
           f"Step {step_index+1} / {len(spec.steps)}    Active: {current}",
           font=small,fill=GREY)
    return im


def _encode_mp4(*, family: Literal["CODE_WALKTHROUGH","PROCESS_FLOW"], spec, graph,
                output_path: str|Path, profile: SequenceRenderProfile,
                frame_drawer, stable_centers: dict[str,tuple[int,int]])->MotionEvidence:
    start=time.monotonic()
    count=len(spec.steps)*profile.frames_per_step()
    if count>600:raise SemanticContractError("V3_07_FRAME_BUDGET_EXCEEDED")
    output=Path(output_path).absolute()
    if output.suffix.lower()!=".mp4" or output.exists() or output.is_symlink() or not output.parent.is_dir():
        raise SemanticContractError("V3_07_UNSAFE_OUTPUT_PATH")
    if any(p.is_symlink() for p in (output.parent,*output.parent.parents)):
        raise SemanticContractError("V3_07_SYMLINK_OUTPUT_FORBIDDEN")
    tmp=output.with_name(f".{output.stem}.{compute_content_hash(spec)[:12]}.part.mp4")
    if tmp.exists():raise SemanticContractError("V3_07_TEMP_OUTPUT_EXISTS")
    cmd=["ffmpeg","-hide_banner","-nostdin","-loglevel","error","-y",
         "-f","rawvideo","-pix_fmt","rgb24","-s:v",f"{profile.width}x{profile.height}",
         "-r",str(profile.fps),"-i","pipe:0","-an","-c:v","libx264",
         "-preset","ultrafast","-crf","20","-pix_fmt","yuv420p",
         "-movflags","+faststart","-map_metadata","-1",str(tmp)]
    p=None
    try:
        p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        assert p.stdin
        for i in range(count):
            step=i//profile.frames_per_step()
            phase=(i%profile.frames_per_step()+0.5)/profile.frames_per_step()
            im=frame_drawer(spec,graph,step,profile,phase)
            p.stdin.write(im.tobytes())
        p.stdin.close()
        assert p.stderr
        error=p.stderr.read()
        if p.wait(timeout=120)!=0 or not tmp.is_file() or tmp.stat().st_size<1000:
            raise SemanticContractError("V3_07_FFMPEG_FAILURE:"+error[-150:].decode(errors="replace"))
        indices=tuple(i*profile.frames_per_step()+max(1,profile.frames_per_step()//2)
                      for i in range(len(spec.steps)))
        decoded=[];maes=[];deltas=[];inside=[]
        for i,k in enumerate(indices):
            frame=_ffmpeg_anchor(tmp,at=(k+0.4)/profile.fps,profile=profile)
            phase=(k%profile.frames_per_step()+0.5)/profile.frames_per_step()
            ideal=frame_drawer(spec,graph,i,profile,phase)
            error=_mean_absolute_error(frame,ideal)
            if error>8.0:
                raise SemanticContractError(f"V3_07_DECODED_FRAME_MISMATCH:{family}:{i}:{error:.3f}")
            decoded.append(frame);maes.append(round(error,3))
        roi=(round(profile.width*.04),round(profile.height*.22),
             round(profile.width*.96),round(profile.height*.89))
        for a,b in zip(decoded,decoded[1:]):
            delta=_mean_absolute_error(a,b,rect=roi)
            if delta<1.15:
                raise SemanticContractError(f"V3_07_NO_VISIBLE_STATE_CHANGE:{family}:{delta:.3f}")
            deltas.append(round(delta,3))
        # Independent MP4 decode within the same beat must observe motion,
        # not just the hard cut between two static cards.
        for i in range(len(spec.steps)):
            n=profile.frames_per_step()
            early=i*n+max(1,round(n*.12))
            late=i*n+max(2,round(n*.82))
            a=_ffmpeg_anchor(tmp,at=(early+.4)/profile.fps,profile=profile)
            b=_ffmpeg_anchor(tmp,at=(late+.4)/profile.fps,profile=profile)
            d=_mean_absolute_error(a,b,rect=roi)
            if d<0.035:
                raise SemanticContractError(f"V3_07_NO_WITHIN_BEAT_MOTION:{family}:{i}:{d:.4f}")
            inside.append(round(d,3))
        try:os.link(tmp,output)
        except FileExistsError as exc:raise SemanticContractError("V3_07_OUTPUT_RACE") from exc
        tmp.unlink()
    except Exception:
        if p is not None and p.poll() is None:p.kill()
        if p is not None:p.wait()
        tmp.unlink(missing_ok=True)
        raise
    return MotionEvidence(
        family=family,path=str(output),video_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
        video_bytes=output.stat().st_size,source_hash=compute_content_hash(spec),
        scenegraph_hash=compute_content_hash(graph),frame_count=count,fps=profile.fps,
        duration_seconds=count/profile.fps,sample_frames=indices,
        decoded_mae=tuple(maes),semantic_roi_delta=tuple(deltas),
        within_beat_motion_delta=tuple(inside),stable_object_centers=stable_centers,wall_seconds=round(time.monotonic()-start,3))


def render_code_walkthrough(*, spec: CodeWalkthrough, graph: SceneGraph,
                            output_path: str|Path,
                            profile: SequenceRenderProfile=SequenceRenderProfile())->MotionEvidence:
    verify_code_walkthrough(spec,graph)
    return _encode_mp4(family="CODE_WALKTHROUGH",spec=spec,graph=graph,
                       output_path=output_path,profile=profile,
                       frame_drawer=draw_code_frame,stable_centers={
                           l.line_id:(round(73*profile.width/960),round((178+i*34)*profile.height/540))
                           for i,l in enumerate(spec.lines)})


def render_process_walkthrough(*, spec: ProcessWalkthrough, graph: SceneGraph,
                               output_path: str|Path,
                               profile: SequenceRenderProfile=SequenceRenderProfile())->MotionEvidence:
    verify_process_walkthrough(spec,graph)
    centers=layout_process(graph,profile)
    return _encode_mp4(family="PROCESS_FLOW",spec=spec,graph=graph,
                       output_path=output_path,profile=profile,
                       frame_drawer=draw_process_frame,stable_centers=centers)
