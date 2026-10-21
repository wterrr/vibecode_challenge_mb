"""Secretless Manim runner for Code2Video-generated code.

This service MUST run in a separately isolated, unprivileged container with
NO tokens, NO database access, NO public network egress, read-only filesystem,
tmpfs and CPU/memory/pids quotas. AST checking is defense-in-depth only,
NOT a substitute for container/network/host sandboxing.
"""
from __future__ import annotations

import ast
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import tempfile


MAX_CODE=65_000
MAX_VIDEO=55_000_000
FORBIDDEN_MODULES={
    "os","sys","subprocess","socket","pathlib","requests","httpx","urllib",
    "ctypes","multiprocessing","threading","importlib","shutil","pickle",
    "builtins","site","signal","resource",
}
FORBIDDEN_CALLS={"open","eval","exec","compile","__import__","input","breakpoint"}


def preflight(code: str)->None:
    if not isinstance(code,str) or not 100<=len(code)<=MAX_CODE:
        raise ValueError("invalid source size")
    tree=ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            module=(node.module or "") if isinstance(node,ast.ImportFrom) else ""
            names=([x.name for x in node.names] if isinstance(node,ast.Import) else [module])
            if any(n.split(".")[0] in FORBIDDEN_MODULES for n in names):
                raise ValueError("disallowed module")
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                raise ValueError("disallowed call")
    if not any(isinstance(n,ast.ClassDef) and n.name=="LearnflowScene" for n in tree.body):
        raise ValueError("expected LearnflowScene")


def _limits():
    resource.setrlimit(resource.RLIMIT_CPU,(125,125))
    resource.setrlimit(resource.RLIMIT_FSIZE,(MAX_VIDEO,MAX_VIDEO))
    resource.setrlimit(resource.RLIMIT_NOFILE,(48,48))


def render(code:str)->bytes:
    preflight(code)
    with tempfile.TemporaryDirectory(prefix="c2v-",dir="/tmp") as wd:
        root=Path(wd)
        source=root/"scene.py"
        source.write_text(code,encoding="utf-8")
        cmd=[
            "manim","-ql","--disable_caching",
            "--media_dir",str(root/"out"),str(source),"LearnflowScene",
        ]
        run=subprocess.run(cmd,cwd=root,stdin=subprocess.DEVNULL,timeout=150,
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                           env={
                               "PATH":"/usr/local/bin:/usr/bin:/bin",
                               "HOME":"/tmp",
                               "XDG_CACHE_HOME":"/tmp",
                               "MPLCONFIGDIR":"/tmp",
                           },
                           preexec_fn=_limits,check=False)
        if run.returncode!=0: raise ValueError("manim_render_rejected")
        outputs=list((root/"out").rglob("*.mp4"))
        if len(outputs)!=1: raise ValueError("expected exactly one MP4")
        path=outputs[0]
        if not 1024<=path.stat().st_size<=MAX_VIDEO:
            raise ValueError("rendered MP4 outside size limit")
        data=path.read_bytes()
        if b"ftyp" not in data[:64]:raise ValueError("invalid MP4")
        return data


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path!="/render":return self.fail(404)
        try:
            length=int(self.headers.get("Content-Length","0"))
            if not 1<=length<=MAX_CODE+500:return self.fail(413)
            obj=json.loads(self.rfile.read(length))
            if not isinstance(obj,dict) or set(obj)!={"code"}:return self.fail(400)
            video=render(obj["code"])
            self.send_response(200)
            self.send_header("Content-Type","video/mp4")
            self.send_header("Content-Length",str(len(video)))
            self.end_headers()
            self.wfile.write(video)
        except (OSError,ValueError,TypeError,KeyError,subprocess.SubprocessError,
                SyntaxError):
            self.fail(422)

    def fail(self,status):
        msg=b'{"error":"manim_sandbox_rejected"}'
        self.send_response(status)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(msg)))
        self.end_headers()
        self.wfile.write(msg)

    def log_message(self,*args):pass


if __name__=="__main__":
    # A private internal network, separate filesystem and no credentials are
    # mandatory. Reject anything resembling a production secret in env.
    if any(x in os.environ for x in ("OPENROUTER_API_KEY","DATABASE_URL",
                                     "ADMIN_PASSWORD","AUTH_SECRET_KEY")):
        raise SystemExit("Manim sandbox must not contain application secrets")
    HTTPServer(("0.0.0.0",8788),Handler).serve_forever()
