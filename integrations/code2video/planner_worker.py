"""Code2Video Planner/Coder adapter, a separate process with LLM credentials.

Uses the **pinned upstream Code2Video get_prompt3_code + TeachingScene base**
without executing the returned Python. The model has a single paid generation
call (no retries). A separate secretless renderer service executes the script.
No unrestricted source paths, shell commands or user-supplied URL inputs.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
from threading import BoundedSemaphore
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

from prompts import base_class, get_prompt3_code  # PINNED showlab/Code2Video

MAX_REQUEST=5000
MAX_CODE=65_000
MAX_OUTPUT=55_000_000
BUSY=BoundedSemaphore(1)


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    lecture_lines: list[str]
    animations: list[str]


def _json_request(url: str, body: dict, *, bearer: str | None = None, timeout:int=60):
    headers={"Content-Type":"application/json"}
    if bearer is not None: headers["Authorization"]="Bearer "+bearer
    req=Request(url,data=json.dumps(body,ensure_ascii=False).encode(),headers=headers,method="POST")
    with urlopen(req,timeout=timeout) as response:
        return response.read(MAX_OUTPUT+1)


def create_manim_code(scene:dict) -> str:
    title=scene["title"]
    narration=scene["narration"]
    goal=scene["visual_goal"]
    if not all(isinstance(x,str) for x in [title,narration,goal]):
        raise ValueError("invalid scene text")
    if not 3<=len(title)<=110 or not 10<=len(narration)<=1200 or not 12<=len(goal)<=500:
        raise ValueError("scene text outside budget")
    s=Section(id="learnflow",title=title,lecture_lines=[narration],
              animations=[goal])
    prompt=get_prompt3_code("",s,base_class)
    prompt+=("\\nLearnFlow constraint: One brief narrated section; emphasize "
             "continuous animated visual changes, not a static table. "
             "Use the exact class name LearnflowScene and only Manim APIs. "
             "Return Python code only.")
    response=_json_request(
        "https://openrouter.ai/api/v1/chat/completions",
        {"model":os.environ["CODE2VIDEO_MODEL"],
         "messages":[{"role":"user","content":prompt}],
         "max_tokens":4000,"stream":False,
         "provider":{"allow_fallbacks":False}},
        bearer=os.environ["OPENROUTER_API_KEY"],timeout=80,
    )
    obj=json.loads(response)
    content=obj["choices"][0]["message"]["content"]
    if not isinstance(content,str):raise ValueError("model returned no source")
    match=re.search(r"```(?:python)?\s*([\s\S]*?)```",content)
    code=(match.group(1) if match else content).strip()
    if not 100<=len(code)<=MAX_CODE:raise ValueError("model code outside budget")
    # The isolated renderer interprets this code; never exec or import here.
    if "class LearnflowScene(" not in code:
        raise ValueError("model did not emit required Manim scene")
    return code


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path!="/render":
            return self.fail(404)
        token=os.environ.get("CODE2VIDEO_WORKER_TOKEN","")
        received=self.headers.get("Authorization","")
        if len(token)<24 or not hmac.compare_digest(received,"Bearer "+token):
            return self.fail(401)
        if not BUSY.acquire(blocking=False):return self.fail(429)
        try:
            if self.headers.get("Content-Type","").split(";")[0]!="application/json":
                return self.fail(415)
            length=int(self.headers.get("Content-Length","0"))
            if not 1<=length<=MAX_REQUEST:return self.fail(413)
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict) or set(body)!={"title","narration","visual_goal","duration_seconds","language"}:
                return self.fail(400)
            if body["language"] not in ("vi","en","auto") or not 1<=body["duration_seconds"]<=40:
                return self.fail(400)
            code=create_manim_code(body)
            # This renderer has no OpenRouter token or app auth secrets.
            data=_json_request(
                os.environ.get("CODE2VIDEO_RENDERER_URL","http://code2video-renderer:8788")+"/render",
                {"code":code},timeout=185,
            )
            if len(data)>MAX_OUTPUT or b"ftyp" not in data[:64]:
                return self.fail(502)
            self.send_response(200)
            self.send_header("Content-Type","video/mp4")
            self.send_header("Content-Length",str(len(data)))
            self.send_header("Cache-Control","no-store")
            self.end_headers()
            self.wfile.write(data)
        except (ValueError,KeyError,TypeError,json.JSONDecodeError,
                URLError,HTTPError,TimeoutError,ConnectionError,IndexError):
            self.fail(502)
        finally:
            BUSY.release()

    def fail(self,code:int):
        payload=b'{"error":"code2video_worker_unavailable"}'
        self.send_response(code)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(payload)))
        self.send_header("Cache-Control","no-store")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self,fmt,*args):
        # No prompt/code/LLM exception text in worker HTTP logs.
        pass


if __name__=="__main__":
    if len(os.environ.get("CODE2VIDEO_WORKER_TOKEN",""))<24:
        raise SystemExit("CODE2VIDEO_WORKER_TOKEN not configured")
    if len(os.environ.get("OPENROUTER_API_KEY",""))<16:
        raise SystemExit("Code2Video model key missing")
    if not os.environ.get("CODE2VIDEO_MODEL","").startswith("openai/"):
        raise SystemExit("Require an explicitly configured paid OpenAI model")
    ThreadingHTTPServer(("0.0.0.0",8765),Handler).serve_forever()
