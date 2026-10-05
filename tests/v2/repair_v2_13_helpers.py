from __future__ import annotations

from learnflow_v2.qa import CriticPatchSuggestion, CriticPatchOp, CriticTargetKind, CriticTargetRef
from learnflow_v2.repair import ArtifactIndex, ArtifactKind, make_artifact_record
from learnflow_v2.scenegraph.enums import NodeKind, RelationKind
from learnflow_v2.scenegraph.schema import SceneGraph, SceneNode, SceneRelation


def scene(scene_id: str) -> SceneGraph:
    return SceneGraph(
        scene_id=scene_id,
        nodes=[
            SceneNode(id="n1", kind=NodeKind.CONCEPT, label="Loss", style_refs=["decoration.glow"]),
            SceneNode(id="n2", kind=NodeKind.TEXT, label="Prediction"),
        ],
        relations=[SceneRelation(id="r1", source="n1", target="n2", kind=RelationKind.FLOW)],
    )


def patch_region(patch_id: str = "p-region") -> CriticPatchSuggestion:
    from learnflow_v2.scenegraph.enums import PreferredRegion
    return CriticPatchSuggestion(
        patch_id=patch_id,
        op=CriticPatchOp.SET_REGION,
        targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
        region=PreferredRegion.RIGHT,
    )


def patch_importance(patch_id: str = "p-importance") -> CriticPatchSuggestion:
    return CriticPatchSuggestion(
        patch_id=patch_id,
        op=CriticPatchOp.CHANGE_IMPORTANCE,
        targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
        normalized_magnitude=0.2,
    )


def build_artifact_index() -> ArtifactIndex:
    idx = ArtifactIndex()
    registry = make_artifact_record(
        artifact_id="registry",
        kind=ArtifactKind.CONCEPT_REGISTRY,
        payload={"concepts": ["loss", "prediction"]},
        created_by_phase="concept_registry",
        compiler_version="1",
    )
    idx.add(registry)

    scene_records = {}
    narration_records = {}
    audio_records = {}
    beats_records = {}
    layout_records = {}
    motion_plan_records = {}
    schedule_records = {}
    rendered_records = {}
    qa_records = {}

    for sid in ("s1", "s2", "s3"):
        sg = make_artifact_record(
            artifact_id=f"scene:{sid}",
            kind=ArtifactKind.SCENE_GRAPH,
            payload={"scene": sid, "nodes": ["n1", "n2"]},
            created_by_phase="scenegraph",
            compiler_version="1",
            inputs=(registry,),
            scene_id=sid,
        )
        idx.add(sg)
        scene_records[sid] = sg

        narr = make_artifact_record(
            artifact_id=f"narration:{sid}",
            kind=ArtifactKind.NARRATION,
            payload=f"narration for {sid}",
            created_by_phase="script",
            compiler_version="1",
            scene_id=sid,
        )
        idx.add(narr)
        narration_records[sid] = narr

        audio = make_artifact_record(
            artifact_id=f"audio:{sid}",
            kind=ArtifactKind.TTS_AUDIO,
            payload=f"audio bytes {sid}".encode(),
            created_by_phase="tts",
            compiler_version="1",
            inputs=(narr,),
            scene_id=sid,
        )
        idx.add(audio)
        audio_records[sid] = audio

        beats = make_artifact_record(
            artifact_id=f"beats:{sid}",
            kind=ArtifactKind.NARRATION_BEATS,
            payload={"beats": [0.0, 1.0], "scene": sid},
            created_by_phase="beats",
            compiler_version="1",
            inputs=(narr, audio),
            scene_id=sid,
        )
        idx.add(beats)
        beats_records[sid] = beats

        layout = make_artifact_record(
            artifact_id=f"layout:{sid}",
            kind=ArtifactKind.LAYOUT_GRAPH,
            payload={"layout": sid},
            created_by_phase="layout",
            compiler_version="1",
            inputs=(sg,),
            scene_id=sid,
        )
        idx.add(layout)
        layout_records[sid] = layout

        motion_plan = make_artifact_record(
            artifact_id=f"motion-plan:{sid}",
            kind=ArtifactKind.MOTION_PLAN,
            payload={"motion": sid},
            created_by_phase="motion-plan",
            compiler_version="1",
            inputs=(sg, beats),
            scene_id=sid,
        )
        idx.add(motion_plan)
        motion_plan_records[sid] = motion_plan

        schedule = make_artifact_record(
            artifact_id=f"schedule:{sid}",
            kind=ArtifactKind.MOTION_SCHEDULE,
            payload={"schedule": sid},
            created_by_phase="motion-schedule",
            compiler_version="1",
            inputs=(motion_plan, beats),
            scene_id=sid,
        )
        idx.add(schedule)
        schedule_records[sid] = schedule

        rendered = make_artifact_record(
            artifact_id=f"render:{sid}",
            kind=ArtifactKind.RENDERED_SCENE,
            payload=f"render-{sid}".encode(),
            created_by_phase="render",
            compiler_version="1",
            inputs=(layout, schedule, audio),
            scene_id=sid,
        )
        idx.add(rendered)
        rendered_records[sid] = rendered

        qa = make_artifact_record(
            artifact_id=f"qa:{sid}",
            kind=ArtifactKind.SCENE_QA,
            payload={"passed": True, "scene": sid},
            created_by_phase="scene-qa",
            compiler_version="1",
            inputs=(rendered,),
            scene_id=sid,
        )
        idx.add(qa)
        qa_records[sid] = qa

    transition_records = {}
    rendered_transition_records = {}
    for tid, left, right in (("t12", "s1", "s2"), ("t23", "s2", "s3")):
        trans = make_artifact_record(
            artifact_id=f"transition-plan:{tid}",
            kind=ArtifactKind.INTER_SCENE_TRANSITION_PLAN,
            payload={"transition": tid},
            created_by_phase="transition-plan",
            compiler_version="1",
            inputs=(registry, layout_records[left], layout_records[right]),
            transition_id=tid,
            from_scene_id=left,
            to_scene_id=right,
        )
        idx.add(trans)
        transition_records[tid] = trans
        rendered_trans = make_artifact_record(
            artifact_id=f"transition-render:{tid}",
            kind=ArtifactKind.RENDERED_TRANSITION,
            payload=f"transition-render-{tid}".encode(),
            created_by_phase="transition-render",
            compiler_version="1",
            inputs=(trans,),
            transition_id=tid,
            from_scene_id=left,
            to_scene_id=right,
        )
        idx.add(rendered_trans)
        rendered_transition_records[tid] = rendered_trans

    assembly_inputs = tuple(rendered_records.values()) + tuple(rendered_transition_records.values())
    assembly = make_artifact_record(
        artifact_id="assembly",
        kind=ArtifactKind.ASSEMBLY,
        payload=b"assembled video",
        created_by_phase="assembly",
        compiler_version="1",
        inputs=assembly_inputs,
    )
    idx.add(assembly)
    video_qa = make_artifact_record(
        artifact_id="video-qa",
        kind=ArtifactKind.VIDEO_QA,
        payload={"passed": True},
        created_by_phase="video-qa",
        compiler_version="1",
        inputs=(assembly,),
    )
    idx.add(video_qa)
    return idx
