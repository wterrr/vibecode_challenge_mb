"""Paid OpenRouter planner for the existing validated V2 lesson pipeline.

Not a claim of 3Blue1Brown parity or generalized V3 Manim creative rendering.
No free model, no fallback model/provider, no retry on ambiguous paid POST.
"""
from __future__ import annotations
from typing import Any
import logging

import httpx
from pydantic import ValidationError

from app.domain.lesson import LearningRequest,LessonPlan
from app.planning.prompts import build_lesson_plan_prompt,build_repair_prompt
from app.providers.llm.base import LessonPlanner,PlannerProviderError

log=logging.getLogger(__name__)


class OpenRouterPaidLessonPlanner(LessonPlanner):
    def __init__(self, *, api_key:str, model:str="openai/gpt-6-luna", tokens:int=12000):
        if not api_key or len(api_key)<16:
            raise ValueError("OPENROUTER_API_KEY is required")
        if not model.startswith("openai/") or model.endswith(":free"):
            raise ValueError("Paid OpenAI model required; no free models")
        self.api_key=api_key
        self.model=model
        self.tokens=tokens

    async def _complete(self,prompt:str)->LessonPlan:
        payload={
          "model":self.model,
          "messages":[{"role":"user","content":prompt}],
          "max_tokens":self.tokens,
          "provider":{"allow_fallbacks":False,"require_parameters":True},
          "response_format":{"type":"json_schema","json_schema":{
              "name":"learnflow_lesson_plan","strict":True,"schema":LessonPlan.model_json_schema()
          }},
          "stream":False,
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(75.0,connect=10.0)) as client:
                response=await client.post("https://openrouter.ai/api/v1/chat/completions",
                   headers={"Authorization":"Bearer "+self.api_key,
                            "Content-Type":"application/json","X-OpenRouter-Title":"LearnFlow Private Studio"},
                   json=payload)
                response.raise_for_status()
                obj=response.json()
            if obj.get("model")!=self.model:
                raise ValueError("Unexpected model response: deny fallback")
            choice=(obj.get("choices") or [])[0]
            if choice.get("finish_reason")!="stop":
                raise ValueError("Incomplete model response")
            body=choice["message"]["content"]
            if not isinstance(body,str):
                raise ValueError("Non-text model completion")
            return LessonPlan.model_validate_json(body)
        except (httpx.HTTPError,ValueError,KeyError,IndexError,ValidationError) as exc:
            # Never include raw provider content, response, prompt, secret or URL in error logs.
            log.warning("Paid planner rejected response: %s",type(exc).__name__)
            raise PlannerProviderError("paid_planner_failed",
                "Paid planner failed or returned unverified JSON; no automatic provider retry.",
                retryable=False) from None

    async def create_plan(self,request:LearningRequest)->LessonPlan:
        return await self._complete(build_lesson_plan_prompt(request))

    async def repair_plan(self,request:LearningRequest,invalid_plan:LessonPlan,
                          errors:list[Any])->LessonPlan:
        # Existing PlanRepairer allows one explicit semantic repair POST per job.
        return await self._complete(build_repair_prompt(request,invalid_plan,errors))
