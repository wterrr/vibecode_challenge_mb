"""V3-80 bounded evidence-grounded semantic playback protocol.

No new Action kind, LLM-authored Python, source graph edits or numerical
facts. Host-only playback specialization:
  - chart reveal: 0 -> independently host-ledger-verified proportional bar
  - verified FLOW/TRANSFORMS_INTO link: source attention -> directional
    bounded edge draw -> destination attention, without a moving node marker.
All events stay inside the ORIGINAL narration action slot. This is a
finite pedagogical transformation grammar, not arbitrary symbolic algebra.
"""
from __future__ import annotations
import math

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_scene_graph import _edge_route
from learnflow_v3.v375_creative_native_gate import (
    box,_line_hit,REQUIRED_MARGIN,SCALE
)

CAUSAL=frozenset({"FLOW","TRANSFORMS_INTO"})
PHASE_FRACTIONS=(.20,.58,.22)
FPS=15

def check(ok,reason):
    if not ok:raise Blocked("V380_"+reason)

def plan(story,facts,layout,seconds):
    check(len(seconds)==len(story.beats),"BEAT_DURATION_COUNT_DRIFT")
    scenes={s.id:s for s in story.scenes}
    check(set(layout)==set(scenes),"SCENE_GEOMETRY_MISMATCH")
    previous=None
    visible=set()
    events=[];scene_events=[]
    for idx,(beat,period) in enumerate(zip(story.beats,seconds)):
        check(beat.scene_id in scenes,"UNKNOWN_BEAT_SCENE")
        scene=scenes[beat.scene_id]
        nodes={n.id:n for n in scene.nodes}
        rels={r.id:r for r in scene.relations}
        check(set(layout[scene.id])==set(nodes),"NODE_LAYOUT_IDENTITY_DRIFT")
        check(math.isfinite(period) and 3<=period<=24,"INVALID_BEAT_DURATION")
        new_scene=scene.id!=previous
        if new_scene:visible=set();previous=scene.id
        each=min(.80,max(.23,(period-1.0)/len(beat.actions)))
        intro=(.35 if idx and new_scene else 0)+(.25 if new_scene else 0)
        check(intro+each*len(beat.actions)+.05<=period,
              "EVENTS_EXCEED_NARRATION_SLOT")
        begin=sum(seconds[:idx])
        elapsed=intro
        for action in beat.actions:
            if action.kind=="reveal":
                check(action.target in nodes,"REVEAL_UNKNOWN_NODE")
                check(action.target not in visible,"DUPLICATE_REVEAL")
                node=nodes[action.target]
                if node.kind=="CHART":
                    check(node.fact_ref is not None and
                          node.fact_ref in facts["facts"],
                          "CHART_UNVERIFIED_FACT")
                    meta=facts["facts"][node.fact_ref]
                    value=meta.get("bar_value")
                    check(type(value) in (float,int) and math.isfinite(value)
                          and 0<value<=1,"CHART_NOT_POSITIVE_NORMALIZED_HOST_VALUE")
                    check(meta.get("claim") in beat.claims,
                          "CHART_BEAT_CLAIM_UNGROUNDED")
                    # The compiler uses max(.24,1.75*value) for physical
                    # bar height; preserve and attest this exact conversion.
                    events.append({
                        "beat_index":idx,"scene":scene.id,"target":node.id,
                        "kind":"HOST_SCALAR_BAR_GROWTH",
                        "fact_ref":node.fact_ref,"claim":meta["claim"],
                        "host_bar_value":round(value,9),
                        "physical_bar_height_world":round(max(.24,1.75*value),4),
                        "bar_center_world":[
                            round(layout[scene.id][node.id][0],5),
                            round(layout[scene.id][node.id][1]+.15,5)],
                        "bar_width_world":1.20,
                        "animation":"GrowFromEdge(DOWN)+FadeIn(caption)",
                        "slot_start_s":round(begin+elapsed,5),
                        "slot_duration_s":round(each,5),
                        "phases":[round(each,5)],
                        "source":"HOST_VERIFIED_LEDGER"})
                visible.add(action.target)
            elif action.kind=="connect":
                check(action.target in rels,"CONNECT_UNKNOWN_RELATION")
                rel=rels[action.target]
                check(rel.source in visible and rel.target in visible,
                      "CAUSAL_ENDPOINT_NOT_YET_REVEALED")
                if rel.kind in CAUSAL:
                    source,target=nodes[rel.source],nodes[rel.target]
                    check(source.fact_ref is not None and
                          target.fact_ref is not None,
                          "CAUSAL_EDGE_NOT_FACT_GROUNDED")
                    check([source.fact_ref,target.fact_ref,rel.kind]
                          in facts["allowed_edges"],"CAUSAL_RELATION_NOT_LEDGER_APPROVED")
                    claim=facts["facts"][target.fact_ref]["claim"]
                    check(claim in beat.claims,"CAUSAL_TARGET_CLAIM_NOT_IN_BEAT")
                    route=_edge_route(scene,rel,layout[scene.id])
                    check(2<=len(route)<=4,"CAUSAL_NO_EXPORTED_ARROW_ROUTE")
                    px=[(640+x*SCALE,360-y*SCALE) for x,y in route]
                    for a,b in zip(px,px[1:]):
                        for name,node in nodes.items():
                            if name in (rel.source,rel.target):continue
                            check(not _line_hit(a,b,box(node,layout[scene.id][name]),
                                                REQUIRED_MARGIN),
                                  "CAUSAL_ARROW_CROSSES_UNRELATED_NODE")
                    durations=[round(each*x,6) for x in PHASE_FRACTIONS]
                    check(abs(sum(durations)-each)<1e-4,
                          "CAUSAL_PHASE_DURATION_DRIFT")
                    events.append({
                        "beat_index":idx,"scene":scene.id,"target":rel.id,
                        "kind":"LEDGER_GROUNDED_DIRECTIONAL_CAUSAL_FLOW",
                        "relation_kind":rel.kind,"source_node":source.id,
                        "target_node":target.id,"source_fact":source.fact_ref,
                        "target_fact":target.fact_ref,"claim":claim,
                        "arrow_route_world":route,
                        "slot_start_s":round(begin+elapsed,5),
                        "slot_duration_s":round(each,5),
                        "phases":durations,
                        "animation":"Indicate(source)->linear Create(route)->Indicate(target)",
                        "source":"HOST_VERIFIED_LEDGER"})
            elif action.kind=="emphasize":
                check(action.target in visible,"EMPHASIZE_INVISIBLE_NODE")
            elif action.kind in ("hide","move","replace"):
                raise Blocked("V380_UNSUPPORTED_DYNAMIC_ACTION")
            else:
                raise Blocked("V380_UNRECOGNIZED_ACTION")
            elapsed+=each
        scene_events.append({"beat_index":idx,"scene":scene.id,
                             "start_s":round(begin,5),
                             "duration_s":round(period,5),
                             "semantic_event_count":sum(x["beat_index"]==idx
                                                        for x in events)})
    check(events and any(x["kind"]=="HOST_SCALAR_BAR_GROWTH" for x in events),
          "NO_SCALAR_TRANSFORMATION_EVENT")
    check(any(x["kind"]=="LEDGER_GROUNDED_DIRECTIONAL_CAUSAL_FLOW"
              for x in events),"NO_CAUSAL_TRANSFORMATION_EVENT")
    return {
        "checkpoint":"V3-80","status":"HOST_GROUNDED_FINITE_TRANSFORM_CONTRACT",
        "events":events,"beats":scene_events,
        "verified_bar_growth_count":sum(x["kind"]=="HOST_SCALAR_BAR_GROWTH"
                                         for x in events),
        "verified_causal_route_count":sum(x["kind"]=="LEDGER_GROUNDED_DIRECTIONAL_CAUSAL_FLOW"
                                          for x in events),
        "narration_beat_total_seconds":round(sum(seconds),5),
        "all_animation_slots_contained_in_original_beats":True,
        "external_model_python_executed":False,
        "moving_dot_inside_node":False,
        "physical_encoded_frame_identity":"APPROXIMATE_MUST_RECHECK",
        "human_pedagogical_gain":"NOT_MEASURED"}
