"""Model-facing schemas for the H-02 LearnFlow Hermes plugin."""

RUN_ID = {
    "type": "string",
    "pattern": "^[0-9a-f]{16}$",
    "description": "Deterministic LearnFlow H-02 run identifier returned by learnflow_create.",
}

LEARNFLOW_CREATE_SCHEMA = {
    "name": "learnflow_create",
    "description": (
        "Create a controlled LearnFlow single-scene run from semantic SceneGraph input. "
        "Do not provide pixel coordinates, renderer code, output paths, codec settings, or other geometry."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "scene_graph": {
                "type": "object",
                "description": "A schema-valid LearnFlow V2 SceneGraph semantic object.",
            },
            "motion_plan": {
                "type": "object",
                "description": (
                    "Optional schema-valid Tier-1 MotionPlan. H-02 accepts only untriggered motion; "
                    "narration beat orchestration arrives in later checkpoints."
                ),
            },
            "scene_duration": {
                "type": "number",
                "minimum": 0.1,
                "maximum": 30.0,
                "description": "Scene duration in seconds. Defaults to 1.0.",
            },
        },
        "required": ["scene_graph"],
        "additionalProperties": False,
    },
}

LEARNFLOW_RUN_SCHEMA = {
    "name": "learnflow_run",
    "description": (
        "Compile a created LearnFlow run through the frozen public Core V2 contracts "
        "(SceneGraph -> LayoutGraph -> scheduled/compiled motion)."
    ),
    "parameters": {
        "type": "object",
        "properties": {"run_id": RUN_ID},
        "required": ["run_id"],
        "additionalProperties": False,
    },
}

LEARNFLOW_RENDER_SCHEMA = {
    "name": "learnflow_render",
    "description": (
        "Render a compiled LearnFlow H-02 run through the frozen public render_scene_video facade. "
        "The output path and render profile are controlled by LearnFlow and cannot be selected by the agent."
    ),
    "parameters": {
        "type": "object",
        "properties": {"run_id": RUN_ID},
        "required": ["run_id"],
        "additionalProperties": False,
    },
}

TOOL_SCHEMAS = (
    LEARNFLOW_CREATE_SCHEMA,
    LEARNFLOW_RUN_SCHEMA,
    LEARNFLOW_RENDER_SCHEMA,
)
