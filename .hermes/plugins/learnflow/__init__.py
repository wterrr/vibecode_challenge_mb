"""Hermes project plugin exposing the bounded LearnFlow H-02 capability surface."""

from .schemas import (
    LEARNFLOW_CREATE_SCHEMA,
    LEARNFLOW_RENDER_SCHEMA,
    LEARNFLOW_RUN_SCHEMA,
)
from .tools import handle_create, handle_render, handle_run


def register(ctx) -> None:
    """Register exactly the three H-02 capability tools under one toolset."""
    ctx.register_tool(
        name="learnflow_create",
        toolset="learnflow",
        schema=LEARNFLOW_CREATE_SCHEMA,
        handler=handle_create,
    )
    ctx.register_tool(
        name="learnflow_run",
        toolset="learnflow",
        schema=LEARNFLOW_RUN_SCHEMA,
        handler=handle_run,
    )
    ctx.register_tool(
        name="learnflow_render",
        toolset="learnflow",
        schema=LEARNFLOW_RENDER_SCHEMA,
        handler=handle_render,
    )
