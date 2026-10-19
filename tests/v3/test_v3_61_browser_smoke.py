"""V3-61 real Chromium smoke: masked UI responds, no server or remote requests.

The test DOES NOT generate or submit human reviewer scores.
"""
from __future__ import annotations

import argparse
import csv
import tempfile
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


def run(kit: Path):
    browser_path = shutil.which("google-chrome") or shutil.which("chromium")
    if browser_path is None:
        raise AssertionError("V361_BROWSER_MISSING: use a real installed Chromium/Chrome")
    pages = [kit / f"reviewer_{i:02d}.html" for i in range(1, 4)]
    assert all(p.is_file() for p in pages), "V361_FORM_MISSING"
    remote = []
    first_ids = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=browser_path, headless=True,
                                    args=["--no-sandbox", "--disable-gpu"])
        for path in pages:
            page = browser.new_page(accept_downloads=True)
            page.on("request", lambda request: remote.append(request.url)
                    if request.url.startswith(("http://", "https://")) else None)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(path.resolve().as_uri(), wait_until="load")
            page.locator("#clip-id").wait_for()
            page.wait_for_function(
                "() => document.querySelector('#clip-id').textContent.endsWith('.mp4')",
                timeout=10000)
            first_ids.append(page.locator("#clip-id").inner_text())
            assert page.locator("video").count() == 1
            assert page.locator("#rating-fields select").count() == 6
            assert page.locator("video").get_attribute("src").startswith("media/")
            assert page.locator("#export").is_hidden()
            page.locator("#next").click()
            assert "Play this clip to the end" in page.locator("#message").inner_text()
            assert "Clip 1 of 9" in page.locator("#progress").inner_text()
            if path == pages[0]:
                # TEST-ONLY simulation: synthetic DOM timeupdate events and ratings.
                # This validates the browser export path, NOT actual human viewing.
                page.locator("#rater-id").fill("TEST_ONLY_BROWSER")
                for i in range(9):
                    page.evaluate("""() => {
                        const v = document.querySelector("#clip-video");
                        let pos = 0;
                        Object.defineProperty(v, "duration", {configurable:true,get:()=>10});
                        Object.defineProperty(v, "currentTime", {configurable:true,get:()=>pos});
                        Object.defineProperty(v, "seeking", {configurable:true,get:()=>false});
                        for (let sec=0;sec<10;sec++) {
                            pos=sec+.1;
                            v.dispatchEvent(new Event("timeupdate"));
                        }
                        v.dispatchEvent(new Event("ended"));
                    }""")
                    for field in ("clarity", "causal_witness", "semantic_continuity",
                                  "legibility", "pacing", "confidence"):
                        page.locator(f'select[name="{field}"]').select_option("3")
                    page.locator("#attest-full").check()
                    if i < 8:
                        page.locator("#next").click()
                        assert f"Clip {i+2} of 9" in page.locator("#progress").inner_text()
                    else:
                        with page.expect_download(timeout=10000) as pending:
                            page.locator("#next").click()
                        download = pending.value
                        with tempfile.TemporaryDirectory() as temp:
                            target = Path(temp)/download.suggested_filename
                            download.save_as(target)
                            with target.open(encoding="utf-8", newline="") as source:
                                review = list(csv.DictReader(source))
                            assert len(review) == 9
                            assert all(row["rater_id"] == "TEST_ONLY_BROWSER" for row in review)
                            assert all(row["watched_full_video"] == "YES" for row in review)
                            assert all(row["causal_witness"] == "3" for row in review)
                        assert page.locator("#export").is_visible()
            assert not errors, f"V361_BROWSER_SCRIPT_ERROR: {errors}"
            page.close()
        browser.close()
    assert len(set(first_ids)) == 3, "V361_FORM_ROTATION_FAILED"
    assert not remote, f"V361_EXTERNAL_REQUEST: {remote}"
    return {"browser_smoke":"PASS_REAL_CHROMIUM", "forms_tested":3,
            "blocked_premature_advances":3, "test_only_browser_csv_export":"PASS", "remote_requests":0,
            "human_ratings_created":0, "pedagogical_quality":"UNRATED"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--kit", type=Path, required=True)
    args = parser.parse_args()
    print(run(args.kit))
