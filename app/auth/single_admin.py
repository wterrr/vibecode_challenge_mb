"""Single-admin Postgres sessions and fail-closed same-origin security.

No public registration or password reset endpoints. Password/bootstrap key exist
only in deployment secrets, never in source or browser responses.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import pbkdf2_hmac, sha256
import hmac
import os
import secrets
from urllib.parse import urlsplit

import psycopg
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, Field
from psycopg.rows import dict_row
from starlette.middleware.base import BaseHTTPMiddleware

COOKIE = "learnflow_session"
ITERATIONS = 600_000
SESSION_HOURS = 12
router = APIRouter(tags=["private-admin-auth"])


def password_hash(password: str, salt: bytes) -> str:
    return pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS).hex()


def session_fingerprint(token: str) -> str:
    return sha256(token.encode("ascii")).hexdigest()


def csrf_token(token: str, key: str) -> str:
    return hmac.new(key.encode("utf-8"), ("csrf:" + token).encode("utf-8"), "sha256").hexdigest()


class PostgresSingleAdmin:
    def __init__(self, database_url: str, username: str, password: str):
        from app.repositories.postgres import normalize_database_url
        self.url = normalize_database_url(database_url)
        self.username = username
        self._initialize(password)

    def _connection(self):
        return psycopg.connect(self.url, connect_timeout=10, row_factory=dict_row)

    def _initialize(self, bootstrap_password: str):
        with self._connection() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS private_admin (
                id INTEGER PRIMARY KEY CHECK (id=1),
                username TEXT NOT NULL UNIQUE,
                salt TEXT NOT NULL,
                password_digest TEXT NOT NULL,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until TIMESTAMPTZ
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS admin_sessions (
                token_hash TEXT PRIMARY KEY,
                admin_id INTEGER NOT NULL REFERENCES private_admin(id) ON DELETE CASCADE,
                expires_at TIMESTAMPTZ NOT NULL
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS daily_paid_job_limits (
                day DATE PRIMARY KEY,
                total INTEGER NOT NULL CHECK(total >= 0)
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS admin_sessions_expiry ON admin_sessions(expires_at)")
            row = conn.execute("SELECT username FROM private_admin WHERE id=1 FOR UPDATE").fetchone()
            if row is None:
                salt = os.urandom(16)
                conn.execute(
                    "INSERT INTO private_admin(id,username,salt,password_digest) VALUES(1,%s,%s,%s)",
                    (self.username, salt.hex(), password_hash(bootstrap_password, salt)),
                )
            elif row["username"] != self.username:
                raise RuntimeError("ADMIN_USERNAME_MISMATCH_EXISTING_DATABASE")
            # Never overwrite the password on restart. Rotation requires a separate authorized operation.

    def authenticate(self, username: str, password: str) -> str | None:
        now = datetime.now(timezone.utc)
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM private_admin WHERE id=1 FOR UPDATE").fetchone()
            if row is None:
                return None
            if row["locked_until"] and row["locked_until"] > now:
                return None
            salt = bytes.fromhex(row["salt"])
            valid_digest = hmac.compare_digest(password_hash(password, salt), row["password_digest"])
            valid_username = hmac.compare_digest(username.encode(), row["username"].encode())
            if not (valid_digest and valid_username):
                failures = row["failed_attempts"] + 1
                lock = now + timedelta(minutes=15) if failures >= 5 else None
                conn.execute(
                    "UPDATE private_admin SET failed_attempts=%s, locked_until=%s WHERE id=1",
                    (0 if lock else failures, lock),
                )
                return None
            conn.execute("UPDATE private_admin SET failed_attempts=0,locked_until=NULL WHERE id=1")
            token = secrets.token_urlsafe(48)
            conn.execute("DELETE FROM admin_sessions WHERE expires_at<=%s", (now,))
            conn.execute(
                "INSERT INTO admin_sessions(token_hash,admin_id,expires_at) VALUES(%s,1,%s)",
                (session_fingerprint(token), now + timedelta(hours=SESSION_HOURS)),
            )
            # Keep at most 8 active sessions.
            conn.execute("""DELETE FROM admin_sessions WHERE token_hash IN
               (SELECT token_hash FROM admin_sessions WHERE admin_id=1
                ORDER BY expires_at DESC OFFSET 8)""")
            return token

    def verify(self, token: str) -> bool:
        if len(token) < 30 or len(token) > 128 or not token.isascii():
            return False
        with self._connection() as conn:
            return conn.execute(
                "SELECT 1 FROM admin_sessions WHERE token_hash=%s AND expires_at>now()",
                (session_fingerprint(token),),
            ).fetchone() is not None

    def revoke(self, token: str) -> None:
        with self._connection() as conn:
            conn.execute("DELETE FROM admin_sessions WHERE token_hash=%s", (session_fingerprint(token),))

    def reserve_paid_job(self, daily_limit: int) -> bool:
        """Transactional, per-day global cap for this single-admin deployment."""
        with self._connection() as conn:
            row = conn.execute("""INSERT INTO daily_paid_job_limits(day,total)
                VALUES(CURRENT_DATE,1) ON CONFLICT(day)
                DO UPDATE SET total=daily_paid_job_limits.total+1
                WHERE daily_paid_job_limits.total<%s
                RETURNING total""", (daily_limit,)).fetchone()
            return row is not None


class AdminGuard(BaseHTTPMiddleware):
    def __init__(self, app, *, key: str, origin: str, store, secure: bool, daily_limit: int):
        super().__init__(app)
        self.key = key
        self.origin = origin.rstrip("/")
        self.store = store
        self.secure = secure
        self.daily_limit = daily_limit

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method.upper()
        # Static assets are public, but authenticated pages / API / MP4s are not.
        if path in ("/healthz", "/login", "/api/auth/login", "/favicon.ico") or path.startswith("/static/"):
            if path == "/api/auth/login" and method != "POST":
                return JSONResponse({"detail": "Method not allowed"}, status_code=405)
            if path == "/api/auth/login" and method == "POST" and request.headers.get("origin") != self.origin:
                return JSONResponse({"detail":"Origin denied"}, status_code=403)
            response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["X-Frame-Options"] = "DENY"
            return response
        raw = request.cookies.get(COOKIE, "")
        if not raw or not self.store.verify(raw):
            # Vibe Host probes GET / without an HTML Accept header. Keep browser
            # navigation redirected to /login, but return a minimal 2xx health
            # response for non-HTML root probes. Never expose the private UI.
            if path == "/" and method in ("GET", "HEAD") and "text/html" not in request.headers.get("accept", "").lower():
                headers = {
                    "Cache-Control": "no-store",
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                    "Referrer-Policy": "no-referrer",
                    "Vary": "Accept, Cookie",
                }
                if method == "HEAD":
                    return Response(status_code=200, headers=headers)
                return JSONResponse({"status": "ok"}, status_code=200, headers=headers)
            if method in ("GET", "HEAD") and not path.startswith("/api/") and "text/html" in request.headers.get("accept", ""):
                return RedirectResponse(url="/login", status_code=303)
            return JSONResponse({"detail":"Authentication required"}, status_code=401)
        request.state.admin_authenticated = True
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            if request.headers.get("origin") != self.origin:
                return JSONResponse({"detail":"Origin denied"}, status_code=403)
            supplied = request.headers.get("x-csrf-token", "")
            if not hmac.compare_digest(supplied, csrf_token(raw, self.key)):
                return JSONResponse({"detail":"Invalid CSRF token"}, status_code=403)
            if method == "POST" and path == "/api/jobs":
                if not self.store.reserve_paid_job(self.daily_limit):
                    return JSONResponse({"detail":"Daily paid job limit reached"}, status_code=429)
        result = await call_next(request)
        if path.startswith("/api/") or path.startswith("/jobs/"):
            result.headers["Cache-Control"] = "private, no-store"
        result.headers["X-Content-Type-Options"] = "nosniff"
        result.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        result.headers["X-Frame-Options"] = "DENY"
        return result


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page() -> HTMLResponse:
    # No registration UI. Content does not contain any credential or token.
    html = """<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Đăng nhập — LearnFlow</title><style>
*{box-sizing:border-box}body{margin:0;font:16px system-ui;background:#f7f5ff;color:#242137;display:grid;place-items:center;min-height:100vh}
main{background:white;border:1px solid #e4e1f3;border-radius:20px;padding:36px;width:min(92vw,410px);box-shadow:0 12px 42px #30265a12}
h1{margin:0 0 8px;font-size:29px}p{color:#686478}label{display:block;margin:18px 0 6px;font-weight:600}
input{width:100%;padding:13px;border:1px solid #cbc7df;border-radius:10px;font:inherit}
button{width:100%;margin-top:22px;background:#6650d5;color:white;padding:13px;border:0;border-radius:10px;font:inherit;font-weight:700;cursor:pointer}
#error{min-height:20px;color:#b52b4b;font-size:13px}</style></head><body><main>
<h1>LearnFlow ✳</h1><p>Studio riêng tư · Chỉ tài khoản quản trị</p>
<form id="login"><label for="u">Tài khoản</label><input id="u" autocomplete="username" required>
<label for="p">Mật khẩu</label><input id="p" type="password" autocomplete="current-password" required>
<button type="submit">Đăng nhập</button><p id="error" role="alert"></p></form></main>
<script>document.querySelector('#login').addEventListener('submit',async e=>{
 e.preventDefault();const btn=document.querySelector('button');btn.disabled=true;
 const resp=await fetch('/api/auth/login',{method:'POST',credentials:'same-origin',
 headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.querySelector('#u').value,
 password:document.querySelector('#p').value})}).catch(()=>null);
 if(resp&&resp.ok){location.replace('/');return;}
 document.querySelector('#error').textContent=resp&&resp.status===429?'Thử lại sau 15 phút.':'Không thể đăng nhập. Kiểm tra thông tin đăng nhập.';
 btn.disabled=false;
});</script></body></html>"""
    return HTMLResponse(html, headers={"Cache-Control":"no-store","X-Frame-Options":"DENY"})


@router.post("/api/auth/login")
def login(payload: LoginRequest, request: Request):
    store = request.app.state.auth_store
    if store is None:
        raise HTTPException(status_code=404, detail="Auth not enabled")
    token = store.authenticate(payload.username, payload.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials or temporarily locked")
    response = JSONResponse({"authenticated":True, "username":request.app.state.settings.admin_username})
    response.set_cookie(COOKIE,token,httponly=True,secure=request.app.state.auth_secure,
                        samesite="lax",path="/",max_age=SESSION_HOURS*3600)
    response.headers["Cache-Control"]="no-store"
    return response


@router.get("/api/auth/session")
def auth_session(request: Request):
    store = request.app.state.auth_store
    if store is None:
        return {"auth_required":False, "authenticated":False, "csrf_token":""}
    token = request.cookies.get(COOKIE, "")
    if not token or not store.verify(token):
        raise HTTPException(status_code=401, detail="Authentication required")
    return {"auth_required":True,"authenticated":True,
            "username":request.app.state.settings.admin_username,
            "csrf_token":csrf_token(token,request.app.state.auth_key)}


@router.post("/api/auth/logout")
def logout(request: Request):
    store=request.app.state.auth_store
    if store is not None:
        token=request.cookies.get(COOKIE,"")
        if token:
            store.revoke(token)
    response=JSONResponse({"authenticated":False})
    response.delete_cookie(COOKIE,path="/")
    response.headers["Cache-Control"]="no-store"
    return response
