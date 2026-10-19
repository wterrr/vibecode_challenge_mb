"""V3-94: source-owned geometric timeline layout and exact collision audit.

The real GPT V3-93 model authored only narration + composition/visual choices.
This renderer visualizes 12 stable persistent named squares physically rotating
from a 3x4 left source grid to a 4x3 right destination grid, leaving ONLY
empty origin guides. Ghosts are NOT duplicated teaching objects. Legacy V3-64
rendering remains unchanged for previous experiments (optional callback).
"""
from __future__ import annotations
from math import cos,sin,pi,isfinite
from pathlib import Path
from PIL import Image,ImageDraw
from .v364_heldout_storyboard import accept,UNIT_IDS
from . import v364_native_array_compiler as old

W,H=1280,720
FPS=15
S=76.0
TILE_SIDE=52
TILE_HALF=TILE_SIDE//2
SOURCE_C=(320.0,397.0)
TARGET_C=(952.0,397.0)
SINGLE_C=(640.0,397.0)
STAGE_TOP=230
STAGE_BOTTOM=565
SUBTITLE_DIVIDER=571
MIN_BOX_GAP=1
LABELS={
    "before":"BEFORE  /  3 ROWS x 4 COLUMNS",
    "after":"AFTER  /  4 ROWS x 3 COLUMNS",
    "identity":"Every object retains its own identity",
}
class Collision(ValueError):
    pass

def _need(ok,why):
    if not ok:raise Collision("V394_"+why)

def stage_fraction(beat,progress):
    _need(type(beat) is int and 0<=beat<5,"INVALID_BEAT")
    _need(isinstance(progress,(int,float)) and isfinite(progress) and 0<=progress<=1,
          "INVALID_PROGRESS")
    if beat<2:return 0.0
    if beat>2:return 1.0
    return progress*progress*(3-2*progress)

def centers(candidate,beat,progress):
    """Same 12 IDs follow a single rigid 90 degree rotation+translation."""
    accept(candidate)
    layout=candidate["visual_thinker"]["composition"]
    _need(layout in ("side_by_side","single_stage"),"UNKNOWN_COMPOSITION")
    # Do not silently claim physically staggered unit motion: this audited
    # replacement only represents the original GPT smooth_morph decision.
    _need(candidate["motion_director"]["method"]=="smooth_morph",
          "STAGGERED_MOTION_NOT_IMPLEMENTED_HONESTLY")
    t=stage_fraction(beat,progress)
    angle=t*pi/2
    ca,sa=cos(angle),sin(angle)
    start,end=(SOURCE_C,TARGET_C) if layout=="side_by_side" else (SINGLE_C,SINGLE_C)
    cx=start[0]+(end[0]-start[0])*t
    cy=start[1]+(end[1]-start[1])*t
    out={}
    for i,uid in enumerate(UNIT_IDS):
        col,row=i%4,i//4
        dx=(col-1.5)*S
        dy=(row-1.0)*S
        # Rigid rotation: distances and 12 physical identities are conserved.
        x=cx+dx*ca-dy*sa
        y=cy+dx*sa+dy*ca
        out[uid]=(x,y)
    return out

def source_ghost_centers():
    return {uid:(SOURCE_C[0]+(i%4-1.5)*S,
                 SOURCE_C[1]+(i//4-1)*S) for i,uid in enumerate(UNIT_IDS)}

def box(x,y,half=TILE_HALF):
    return (x-half,y-half,x+half,y+half)

def overlap(a,b,margin=0):
    # Touching boundaries are not overlapping; real glyphs need margin.
    return a[0]<b[2]+margin and a[2]+margin>b[0] and a[1]<b[3]+margin and a[3]+margin>b[1]

def fixed_label_boxes(candidate,beat,draw):
    """Use actual font metrics for dynamically displayed text, not estimated widths."""
    comp=candidate["visual_thinker"]["composition"]
    out={}
    if comp=="side_by_side":
        out["before_heading"]=draw.textbbox((175,197),LABELS["before"],font=old.font(17))
        out["after_heading"]=draw.textbbox((822,197),LABELS["after"],font=old.font(17))
        if beat>=3:
            out["identity"]=draw.textbbox((175,525),LABELS["identity"],font=old.font(21))
    if beat>=3:
        text="3 x 4 = 4 x 3 = 12"
    elif beat==2:
        text="THE SAME SQUARES ARE MOVING"
    else:
        text="PREDICT FIRST  /  NO NEW SQUARES"
    out["center_note"]=draw.textbbox((640,210),text,font=old.font(21),anchor="mm")
    return out

def subtitles(candidate,beat,draw):
    lines=old.line_wrap(draw,candidate["beats"][beat]["caption"],24,max_width=1050)
    _need(len(lines)<=3,"NARRATION_MORE_THAN_3_LINES")
    out=[]
    for i,s in enumerate(lines):
        out.append(draw.textbbox((72,586+30*i),s,font=old.font(24)))
    return lines,out

def audit_frame(candidate,beat,progress):
    """All exact 12 tile boxes vs other tiles and actual text, including subtitle bands."""
    positions=centers(candidate,beat,progress)
    _need(tuple(positions)==UNIT_IDS,"PERSISTENT_ID_COUNT_OR_ORDER_CHANGED")
    im=Image.new("RGB",(W,H))
    draw=ImageDraw.Draw(im)
    labels=fixed_label_boxes(candidate,beat,draw)
    _,subtitle_boxes=subtitles(candidate,beat,draw)
    labels.update({"narration_"+str(i):b for i,b in enumerate(subtitle_boxes)})
    boxes={uid:box(*p) for uid,p in positions.items()}
    for uid,b in boxes.items():
        _need(b[0]>=60 and b[2]<=1220 and b[1]>=STAGE_TOP and
              b[3]<=STAGE_BOTTOM, "TILE_ESCAPE_STAGE_"+uid)
        for name,tb in labels.items():
            _need(not overlap(b,tb,margin=MIN_BOX_GAP),
                  "TILE_HITS_"+name+"_"+uid)
    for i,a in enumerate(UNIT_IDS):
        for b in UNIT_IDS[i+1:]:
            _need(not overlap(boxes[a],boxes[b],margin=MIN_BOX_GAP),
                  "SQUARES_COLLIDE_"+a+"_"+b)
    # Visual editor must keep captions in reserved area regardless of squares.
    for b in subtitle_boxes:
        _need(b[0]>=60 and b[2]<=1220 and b[1]>=SUBTITLE_DIVIDER and
              b[3]<=676,"SUBTITLE_TEXT_OUTSIDE_SAFE_BAND")
    if "identity" in labels:
        ib=labels["identity"]
        _need(ib[3]<SUBTITLE_DIVIDER,"IDENTITY_LABEL_ENTERED_CAPTIONS")
    return {"ids":tuple(positions),
            "top":min(b[1] for b in boxes.values()),
            "bottom":max(b[3] for b in boxes.values()),
            "layout":candidate["visual_thinker"]["composition"],
            "caption_count":len(subtitle_boxes)}

def audit_timeline(candidate,counts):
    accept(candidate)
    _need(len(counts)==5 and all(type(n) is int and n>=15 for n in counts),
          "INVALID_TIMELINE_BEATS")
    _need(candidate["visual_thinker"]["composition"] in ("side_by_side","single_stage"),
          "UNKNOWN_COMPOSITION")
    checked=0
    worst_top=1000.
    worst_bottom=0.
    max_step=0.
    prev=None
    for beat,n in enumerate(counts):
        for frame in range(n):
            p=min(1.,frame/max(1,int(n*.78)))
            a=audit_frame(candidate,beat,p)
            now=centers(candidate,beat,p)
            if prev is not None:
                # A snap between consecutive rendered frames would betray the
                # identity-preserving visual narrative, even if endpoints pass.
                delta=max(((now[uid][0]-prev[uid][0])**2+
                            (now[uid][1]-prev[uid][1])**2)**.5 for uid in UNIT_IDS)
                max_step=max(max_step,delta)
                _need(delta<=36,"TELEPORTING_PERSISTENT_SQUARES")
            prev=now
            checked+=1
            worst_top=min(worst_top,a["top"])
            worst_bottom=max(worst_bottom,a["bottom"])
    # Endpoint orientation is proven against immutable 3x4 source IDs and a
    # 4x3 final matrix, rather than an impressionistic pixel-color score.
    start=centers(candidate,0,0)
    goal=centers(candidate,4,1)
    for i,uid in enumerate(UNIT_IDS):
        col,row=i%4,i//4
        _need(abs(start[uid][1]-(397+(row-1)*S))<1e-6,
              "SOURCE_ROWS_NOT_THREE")
        # 90-degree rotation turns the original 3x4 arrangement into a
        # four-row/three-column lattice while retaining each original ID.
        expected_y=397+(col-1.5)*S
        _need(abs(goal[uid][1]-expected_y)<1e-6,"GOAL_ROWS_NOT_FOUR")
    return {"timeline_frames_audited":checked,"beats":counts,
            "all_12_persistent_ids":True,"exact_rigid_rotation_degrees":90,
            "model_chosen_composition":candidate["visual_thinker"]["composition"],
            "min_tile_top":round(worst_top,2),
            "max_tile_bottom":round(worst_bottom,2),
            "largest_frame_to_frame_step_px":round(max_step,3),
            "geometry_pass":True,"label_tile_collisions":0,
            "tile_tile_collisions":0,"subtitle_band_collisions":0}

def render_corrected(candidate,beat,progress):
    """Draw new source-owned geometry; no covering rectangles/masks/post-hoc frame edits."""
    audit_frame(candidate,beat,progress)
    positions=centers(candidate,beat,progress)
    img=Image.new("RGB",(W,H),old.BG)
    d=ImageDraw.Draw(img)
    old.tx(d,(60,35),"LEARNFLOW  /  WHY THE COUNT DOES NOT CHANGE",21,old.CYAN)
    old.tx(d,(60,80),"Can 3 x 4 become 4 x 3 without losing anything?",38,old.WHITE)
    d.line((60,145,1220,145),fill=old.DARK,width=2)
    old.tx(d,(1214,40),f"{beat+1:02d} / 05",23,old.LIGHT,anchor="ra")
    old.tx(d,(72,169),candidate["beats"][beat]["stage"],20,old.GOLD)
    side=candidate["visual_thinker"]["composition"]=="side_by_side"
    if side:
        old.tx(d,(175,197),LABELS["before"],17,old.LIGHT)
        old.tx(d,(822,197),LABELS["after"],17,old.LIGHT)
        # Transparent references are guide cells, not duplicate physical objects.
        for x,y in source_ghost_centers().values():
            d.rounded_rectangle(box(x,y),radius=8,outline=old.DARK,width=2)
    if beat>=3:
        note="3 x 4 = 4 x 3 = 12"
    elif beat==2:
        note="THE SAME SQUARES ARE MOVING"
    else:
        note="PREDICT FIRST  /  NO NEW SQUARES"
    old.tx(d,(640,210),note,21,old.GOLD if beat>=3 else old.LIGHT,anchor="mm")
    focus=candidate["beats"][beat]["visual_focus"]
    for i,uid in enumerate(UNIT_IDS):
        x,y=positions[uid]
        x,y=int(round(x)),int(round(y))
        on=(focus=="all_twelve" or
            (focus=="highlight_first_row" and i<4) or
            (focus=="track_corner" and i in (0,3,8,11)))
        col=old.CYAN if on else (101,125,146)
        d.rounded_rectangle(box(x,y),radius=9,fill=col,
                            outline=old.WHITE if on else old.DARK,width=2)
        old.tx(d,(x,y),str(i+1),21,old.BG,anchor="mm")
        if focus=="track_corner" and uid=="unit_00":
            # Inner marker, never protrudes into adjacent tile footprints.
            d.rounded_rectangle(box(x,y,23),radius=8,outline=old.GOLD,width=3)
    if side and beat>=3:
        old.tx(d,(175,525),LABELS["identity"],21,old.LIGHT)
    d.line((60,SUBTITLE_DIVIDER,1220,SUBTITLE_DIVIDER),fill=old.DARK,width=2)
    lines,_=subtitles(candidate,beat,d)
    for i,line in enumerate(lines):
        old.tx(d,(72,586+30*i),line,24,old.WHITE)
    for i in range(5):
        x=74+i*231
        d.rounded_rectangle((x,690,x+206,700),radius=3,
            fill=old.CYAN if i<=beat else old.DARK)
    return img
