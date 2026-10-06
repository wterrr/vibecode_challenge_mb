"""Hermes project plugin wiring LearnFlow runtime governance to native lifecycle hooks."""

from runtime_governance.hermes_plugin import (
    on_api_request_error,
    on_post_api_request,
    on_post_tool_call,
    on_pre_tool_call,
    on_session_end,
    on_session_start,
    on_subagent_start,
    on_subagent_stop,
)


def register(ctx) -> None:
    ctx.register_hook("pre_tool_call", on_pre_tool_call)
    ctx.register_hook("post_tool_call", on_post_tool_call)
    ctx.register_hook("post_api_request", on_post_api_request)
    ctx.register_hook("api_request_error", on_api_request_error)
    ctx.register_hook("on_session_start", on_session_start)
    ctx.register_hook("on_session_end", on_session_end)
    ctx.register_hook("subagent_start", on_subagent_start)
    ctx.register_hook("subagent_stop", on_subagent_stop)
