"""Verified Newtonian central-force motion as a reusable production renderer.

A generic idealized two-body lesson family for orbits, satellites and comets.
Model controls only one bounded physical input (eccentricity) and one teaching
mode. Positions, velocities, acceleration vectors, energy and angular momentum
are host-computed with velocity-Verlet, independently checked against Kepler
invariants. No model-authored physics answers or frame geometry.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import math
from pathlib import Path
import subprocess
import time

from PIL import Image, ImageDraw

from app.domain.lesson import CentralForceMotionSpec, ScenePlan
from app.domain.timeline import ResolvedSceneTiming
from app.rendering.base import RenderResult, SceneRenderer
from app.rendering.typography import get_system_font

BG=(5,8,17)
SUN=(250,191,73)
PLANET=(93,217,246)
VEL=(76,224,192)
GRAVITY=(250,110,129)
MUTED=(139,156,185)
TRACE=(91,116,160)
TEXT=(230,239,252)
MU=1.0


@dataclass(frozen=True)
class PhysicsState:
    t: float
    x: float
    y: float
    vx: float
    vy: float


def energy(s: PhysicsState) -> float:
    return .5*(s.vx*s.vx+s.vy*s.vy)-MU/math.hypot(s.x,s.y)


def angular_momentum(s: PhysicsState) -> float:
    return s.x*s.vy-s.y*s.vx


def orbital_states(spec: CentralForceMotionSpec, points: int = 1440) -> tuple[PhysicsState,...]:
    """Integrate a full bound orbit and independently check invariants.

    r_peri=1, mu=1, v_peri=sqrt(1+e). For e<1 the analytical
    energy=-.5*(1-e), angular momentum=sqrt(1+e), and the period follows
    Kepler's third law. Velocity-Verlet is symplectic and stable at this dt.
    """
    if points < 360 or points > 2400:
        raise ValueError("Physics sample budget invalid")
    validated=CentralForceMotionSpec.model_validate(spec.model_dump(mode="json"))
    e=validated.eccentricity
    period=2*math.pi/(1-e)**1.5
    dt=period/points
    x,y,vx,vy=1.,0.,0.,math.sqrt(1+e)
    output=[PhysicsState(0,x,y,vx,vy)]
    for i in range(points):
        rr=(x*x+y*y)**1.5
        ax,ay=-x/rr,-y/rr
        nx=x+vx*dt+.5*ax*dt*dt
        ny=y+vy*dt+.5*ay*dt*dt
        nr=(nx*nx+ny*ny)**1.5
        nax,nay=-nx/nr,-ny/nr
        nvx=vx+.5*(ax+nax)*dt
        nvy=vy+.5*(ay+nay)*dt
        x,y,vx,vy=nx,ny,nvx,nvy
        output.append(PhysicsState((i+1)*dt,x,y,vx,vy))
    expected_energy=-.5*(1-e)
    expected_h=math.sqrt(1+e)
    for i in range(0,len(output),max(1,points//16)):
        s=output[i]
        if abs(energy(s)-expected_energy)>3e-3:
            raise ValueError("Orbital energy invariant failed")
        if abs(angular_momentum(s)-expected_h)>3e-3:
            raise ValueError("Orbital angular-momentum invariant failed")
    if math.hypot(output[-1].x-1,output[-1].y)>.025:
        raise ValueError("Keplerian orbit fails to close")
    return tuple(output)


def motion_at(states: tuple[PhysicsState,...], u: float, kind: str) -> PhysicsState:
    """Sample deterministic motion, no invented model frame positions."""
    u=min(1.,max(0.,u))
    initial=states[0]
    if kind=="inertia_only":
        # Gravity OFF: this is the linear continuation of the same tangential
        # initial velocity; a counterfactual rather than a second real orbit.
        t=1.35*u
        return PhysicsState(t,initial.x,initial.vy*t,initial.vx,initial.vy)
    final_fraction=.28 if kind=="gravity_deflection" else .96
    idx=min(len(states)-1,round(u*final_fraction*(len(states)-1)))
    return states[idx]


def _arrow(draw: ImageDraw.ImageDraw, start: tuple[float,float],
           end: tuple[float,float], color: tuple[int,int,int], width:int) -> None:
    sx,sy=start; ex,ey=end
    dx,dy=ex-sx,ey-sy
    norm=math.hypot(dx,dy)
    if norm<.1: return
    ux,uy=dx/norm,dy/norm
    head=8+width*1.5
    draw.line((sx,sy,ex,ey),fill=color,width=width)
    draw.polygon([(ex,ey),
                  (ex-ux*head-uy*.44*head,ey-uy*head+ux*.44*head),
                  (ex-ux*head+uy*.44*head,ey-uy*head-ux*.44*head)],fill=color)


class CentralForceMotionRenderer(SceneRenderer):
    def __init__(self,width:int=1280,height:int=720,fps:int=24):
        self.width,self.height,self.fps=width,height,fps

    def _frame(self,scene:ScenePlan,spec:CentralForceMotionSpec,
               progress:float,states:tuple[PhysicsState,...]) -> Image.Image:
        w,h=self.width,self.height
        scale=w/1280
        frame=Image.new("RGB",(w,h),BG)
        d=ImageDraw.Draw(frame)
        headline=get_system_font(max(14,round(25*scale)))
        body=get_system_font(max(11,round(17*scale)))
        d.text((round(.05*w),round(.058*h)),scene.title[:65],font=headline,fill=TEXT)

        apo=(1+spec.eccentricity)/(1-spec.eccentricity)
        unit=min(.27*h/max(1.0,apo),.27*w)
        cx,cy=.49*w,.43*h
        def xy(x:float,y:float) -> tuple[int,int]:
            return (round(cx+x*unit),round(cy-y*unit))
        # Reference: faint host-computed full bound orbit, made of real
        # numerical points and NOT an invented ideal circle.
        if spec.motion_kind=="bound_orbit":
            poly=[xy(s.x,s.y) for s in states[::4]]
            d.line(poly,fill=(38,60,89),width=max(1,round(2*scale)))
        if spec.motion_kind in ("gravity_deflection","inertia_only"):
            # Counterfactual straight tangent, visually distinct from the
            # actual curved trajectory.
            x0,y0=xy(1.,0.)
            x1,y1=xy(1.,1.35*states[0].vy)
            for i in range(0,24,2):
                f0=i/24;f1=(i+1)/24
                d.line((x0+(x1-x0)*f0,y0+(y1-y0)*f0,
                        x0+(x1-x0)*f1,y0+(y1-y0)*f1),
                       fill=(73,95,119),width=max(1,round(2*scale)))
        # Animated trajectory: no screenshot / card state substitution.
        moving=motion_at(states,progress,spec.motion_kind)
        if spec.motion_kind=="inertia_only":
            pts=[xy(1.,1.35*states[0].vy*progress*i/80) for i in range(81)]
        else:
            idx=max(1,round(progress*(.28 if spec.motion_kind=="gravity_deflection" else .96)*(len(states)-1)))
            pts=[xy(s.x,s.y) for s in states[:idx:3]]+[xy(moving.x,moving.y)]
        if len(pts)>1:
            d.line(pts,fill=TRACE,width=max(2,round(3*scale)),joint="curve")
        sx,sy=xy(0,0)
        sr=max(11,round(22*scale))
        d.ellipse((sx-sr*1.6,sy-sr*1.6,sx+sr*1.6,sy+sr*1.6),fill=(60,37,19))
        d.ellipse((sx-sr,sy-sr,sx+sr,sy+sr),fill=SUN)
        d.text((sx+sr+5,sy-sr-14),"M",font=body,fill=SUN)

        px,py=xy(moving.x,moving.y)
        r=max(6,round(10*scale))
        d.ellipse((px-r,py-r,px+r,py+r),fill=PLANET)
        d.ellipse((px-r*.5,py-r*.5,px+r*.5,py+r*.5),fill=(182,240,252))
        vnorm=math.hypot(moving.vx,moving.vy)
        if vnorm>0:
            end=(px+moving.vx/vnorm*min(80*scale,.18*w),
                 py-moving.vy/vnorm*min(80*scale,.18*w))
            _arrow(d,(px,py),end,VEL,max(2,round(3*scale)))
            d.text((end[0]+8,end[1]-10),"v",font=body,fill=VEL)
        if spec.motion_kind!="inertia_only":
            dx,dy=sx-px,sy-py
            n=math.hypot(dx,dy)
            ex=px+dx/n*min(76*scale,n*.72)
            ey=py+dy/n*min(76*scale,n*.72)
            _arrow(d,(px,py),(ex,ey),GRAVITY,max(2,round(3*scale)))
            d.text((ex+6,ey+7),"F",font=body,fill=GRAVITY)
        # A small visually separate legend, not the lesson's main content.
        legend={
            "inertia_only":"F = 0   •   chuyển động thẳng theo quán tính",
            "gravity_deflection":"F hướng tâm   •   v tiếp tuyến   •   quỹ đạo cong",
            "bound_orbit":"Lực hấp dẫn đổi hướng v   •   quỹ đạo liên tục",
        }[spec.motion_kind]
        d.text((round(.07*w),round(.72*h)),legend,font=body,fill=MUTED)
        d.line((round(.06*w),round(.785*h),round(.94*w),round(.785*h)),fill=(39,49,68),width=2)
        return frame

    def _render_sync(self,scene:ScenePlan,timing:ResolvedSceneTiming,path:Path)->None:
        if not isinstance(scene.visual_spec,CentralForceMotionSpec):
            raise ValueError("Central force renderer requires typed model")
        spec=CentralForceMotionSpec.model_validate(scene.visual_spec.model_dump(mode="json"))
        states=orbital_states(spec)
        path.parent.mkdir(parents=True,exist_ok=True)
        frames=max(self.fps,int(round(timing.render_duration_seconds*self.fps)))
        cmd=["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
             "-f","rawvideo","-pix_fmt","rgb24","-s:v",f"{self.width}x{self.height}",
             "-r",str(self.fps),"-i","pipe:0","-an","-c:v","libx264",
             "-preset","ultrafast","-threads","2","-crf","23",
             "-pix_fmt","yuv420p","-movflags","+faststart",str(path)]
        start=time.monotonic()
        budget=max(180,min(600,round(timing.render_duration_seconds*9+60)))
        proc=None
        try:
            proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
            assert proc.stdin is not None
            for i in range(frames):
                if time.monotonic()-start>budget:
                    raise TimeoutError("Physical motion exceeded bounded encoder budget")
                frame=self._frame(scene,spec,i/max(1,frames-1),states)
                proc.stdin.write(frame.tobytes())
            proc.stdin.close()
            if proc.wait(timeout=max(1,budget-(time.monotonic()-start)))!=0:
                raise RuntimeError("Central force H264 encoder failed")
            if not path.exists() or path.stat().st_size<1000:
                raise RuntimeError("Central force H264 output missing")
        except (OSError,ValueError,TimeoutError,RuntimeError):
            if proc is not None and proc.poll() is None: proc.kill()
            if proc is not None: proc.wait()
            path.unlink(missing_ok=True)
            raise

    async def render(self,scene:ScenePlan,timing:ResolvedSceneTiming,
                     output_path:Path)->RenderResult:
        await asyncio.to_thread(self._render_sync,scene,timing,Path(output_path))
        return RenderResult(path=str(output_path),width=self.width,height=self.height,
                            duration_seconds=timing.render_duration_seconds,warnings=[])
