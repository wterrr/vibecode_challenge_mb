"""Chromium checks actual same-origin React / → FastAPI job/status and original assets."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

HOST = os.getenv("V397_TEST_URL", "http://127.0.0.1:8000")
ARTIFACT = Path("artifacts")
ARTIFACT.mkdir(exist_ok=True)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        ctx.add_init_script("sessionStorage.setItem('learnflow-opening-seen-v2', '1')")
        page = ctx.new_page()
        script_errors = []
        page.on("pageerror", lambda err: script_errors.append(str(err)))
        home = page.goto(HOST + "/", wait_until="domcontentloaded")
        assert home and home.status == 200, "React index not served by FastAPI"
        page.locator("#learning-prompt").wait_for(timeout=25000)
        # Diagnose codec and media loading instead of assuming a missing asset.
        page.wait_for_timeout(900)
        if page.locator(".hero-motion-video").count() != 1:
            page.screenshot(path=str(ARTIFACT / "v397-browser-video-diagnostic.png"), full_page=True)
            fallback = page.locator(".hero-video-fallback").count()
            raise AssertionError(
                f"Real Chrome did not retain Gemini video (fallback={fallback}); "
                "inspect artifact, codec and server Range responses"
            )
        for path in (
            "mascots/creator.png", "mascots/insight.png",
            "mascots/learner.png", "mascots/research.png",
            "media/learnflow-product-film.mp4",
            "media/learnflow-opening-v2-no-loop.mp4",
        ):
            response = ctx.request.get(HOST + "/static/landing/" + path, timeout=25000)
            assert response.status == 200, f"Media request failed: {path}: {response.status}"
            assert len(response.body()) > 100_000, f"Placeholder or incomplete media: {path}"
        assert not script_errors, script_errors
        page.screenshot(path=str(ARTIFACT / "v397-browser-home.png"), full_page=True)
        topic = "How does the TCP three-way handshake work?"
        page.locator("#learning-prompt").fill(topic)
        with page.expect_response(
            lambda r: "/api/jobs" in r.url and r.request.method == "POST", timeout=25000
        ) as pending:
            page.locator(".composer-submit").click()
        created = pending.value
        assert created.status == 202, f"Browser POST jobs failed: {created.status}"
        result = created.json()
        job_id = result.get("job_id")
        assert job_id and result.get("status_url") == "/api/jobs/" + job_id
        page.locator(".lf-result").wait_for(timeout=25000)
        status = ctx.request.get(HOST + "/api/jobs/" + job_id)
        assert status.status == 200 and status.json()["topic"] == topic
        page.screenshot(path=str(ARTIFACT / "v397-browser-job.png"), full_page=True)
        assert not script_errors, script_errors
        evidence = {
            "gate": "REAL_CHROMIUM_REACT_FASTAPI_JOB_CONTRACT_PASS_NO_MODEL",
            "http_home": home.status, "http_job_create": created.status,
            "http_job_status": status.status, "job_id": job_id,
            "original_asset_count": 8, "paid_provider_requests": 0,
            "human_review": "UNRATED", "production": "BLOCKED"
        }
        (ARTIFACT / "v397-browser-result.json").write_text(json.dumps(evidence, indent=2))
        print(json.dumps(evidence))
        ctx.close()
        browser.close()


if __name__ == "__main__":
    run()
