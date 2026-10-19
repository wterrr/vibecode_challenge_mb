"""Browser proof: real PostgreSQL session, React job, CSRF, and logout.

Only temporary CI credentials; NEVER connects to a paid model.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=os.environ.get("V399_BROWSER_ORIGIN","http://127.0.0.1:8855")
USER=os.environ["V399_TEST_ADMIN"]
PASSWORD=os.environ["V399_TEST_PASSWORD"]

def main():
    out=Path("artifacts/v399-private-browser")
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True, args=["--no-sandbox"])
        context=browser.new_context(viewport={"width":1366,"height":900})
        page=context.new_page()
        errors=[]
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(ROOT+"/", wait_until="domcontentloaded")
        page.wait_for_url("**/login")
        assert page.locator("#login").count()==1
        assert context.request.get(ROOT+"/api/jobs").status==401
        assert context.request.get(ROOT+"/api/jobs/unauthorized/video").status==401
        page.screenshot(path=str(out/"login.png"), full_page=True)

        page.locator("#u").fill(USER)
        page.locator("#p").fill(PASSWORD)
        with page.expect_response(lambda r:"/api/auth/login" in r.url and r.request.method=="POST") as pending:
            page.locator("#login button").click()
        assert pending.value.status==200
        page.locator("#learning-prompt").wait_for(timeout=30000)
        auth=context.request.get(ROOT+"/api/auth/session")
        assert auth.status==200 and auth.json()["authenticated"] is True
        assert len(auth.json()["csrf_token"])==64
        assert context.request.post(ROOT+"/api/jobs",data={}).status==403

        topic="What is the TCP three-way handshake?"
        page.locator("#learning-prompt").fill(topic)
        with page.expect_response(lambda r:"/api/jobs" in r.url and r.request.method=="POST") as submitted:
            page.locator(".composer-submit").click()
        assert submitted.value.status==202
        receipt=submitted.value.json()
        assert receipt["job_id"]
        lookup=context.request.get(ROOT+receipt["status_url"])
        assert lookup.status==200 and lookup.json()["topic"]==topic
        page.screenshot(path=str(out/"signed-in-job.png"), full_page=True)

        page.get_by_role("button",name="Đăng xuất").click()
        page.wait_for_url("**/login")
        assert context.request.get(ROOT+"/api/jobs").status==401
        assert not errors, errors
        data={"gate":"CHROMIUM_POSTGRES_ADMIN_REACT_JOB_LOGOUT_PASS",
            "login_http":200,"create_http":202,"job_http":200,
            "unauthorized_video_http":401,"csrf_missing_http":403,
            "logout_api_http":401,"provider_posts":0,
            "human_quality":"UNRATED","paid_production":"NOT_RUN"}
        (out/"receipt.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
        print(json.dumps(data))
        context.close()
        browser.close()

if __name__=="__main__":
    main()
