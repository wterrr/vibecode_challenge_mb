#!/usr/bin/env python3
"""Preflight verification script for LearnFlow AI (CP0).

Verifies:
- Python version and core library imports
- FFmpeg and FFprobe binaries
- H.264 encoder availability (libx264)
- Filesystem write permissions for artifacts directory
- Temporary SQLite write/read functionality
- Pillow font selection & Vietnamese sample rendering
- Optional Manim availability
- GEMINI_API_KEY configuration status (without leaking secrets)
- Optional Gemini connectivity smoke check via --check-gemini
"""

import argparse
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import uuid

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def check_imports() -> dict[str, tuple[bool, str]]:
    results = {}

    # FastAPI
    try:
        import fastapi
        results["FastAPI"] = (True, f"v{fastapi.__version__}")
    except Exception as e:
        results["FastAPI"] = (False, str(e))

    # Pydantic
    try:
        import pydantic
        results["Pydantic"] = (True, f"v{pydantic.__version__}")
    except Exception as e:
        results["Pydantic"] = (False, str(e))

    # Pillow
    try:
        import PIL
        results["Pillow"] = (True, f"v{PIL.__version__}")
    except Exception as e:
        results["Pillow"] = (False, str(e))

    # google-genai
    try:
        from google import genai
        results["google-genai"] = (True, "available")
    except Exception as e:
        results["google-genai"] = (False, str(e))

    # edge-tts
    try:
        import edge_tts
        results["edge-tts"] = (True, getattr(edge_tts, "__version__", "available"))
    except Exception as e:
        results["edge-tts"] = (False, str(e))

    return results


def check_artifacts_dir(artifacts_dir: str) -> tuple[bool, str]:
    try:
        target_dir = Path(artifacts_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        test_file = target_dir / f".preflight_test_{uuid.uuid4().hex}.tmp"
        test_content = "learnflow_preflight_check"

        test_file.write_text(test_content, encoding="utf-8")
        read_back = test_file.read_text(encoding="utf-8")
        test_file.unlink()

        if read_back == test_content:
            return True, f"writable ({target_dir.resolve()})"
        return False, "content mismatch on readback"
    except Exception as e:
        return False, f"write failed: {e}"


def check_sqlite_writable() -> tuple[bool, str]:
    temp_dir = tempfile.mkdtemp(prefix="learnflow_db_test_")
    db_path = Path(temp_dir) / "preflight_test.db"
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY);")
        cursor.execute("INSERT INTO test DEFAULT VALUES;")
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM test;")
        row = cursor.fetchone()
        conn.close()

        if row and row[0] == 1:
            return True, "temporary SQLite write/read OK"
        return False, f"unexpected count: {row}"
    except Exception as e:
        return False, f"SQLite error: {e}"
    finally:
        try:
            if db_path.exists():
                db_path.unlink()
            os.rmdir(temp_dir)
        except Exception:
            pass


def check_gemini_smoke(api_key: str, model_name: str) -> tuple[bool, str]:
    if not api_key:
        return False, "GEMINI_API_KEY is not set"
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents="Say 'OK'",
        )
        text = response.text or ""
        return True, f"Connectivity verified with {model_name} (response length: {len(text)})"
    except Exception as e:
        status_code = getattr(e, "code", None) or getattr(e, "status_code", None)
        err_type = type(e).__name__
        msg = "authentication error" if status_code in (401, 403) else ("quota/billing limit" if status_code in (402, 429) else f"error ({err_type})")
        return False, f"Gemini API check failed: {msg}"


def run_preflight(check_gemini: bool = False) -> bool:
    print("=" * 64)
    print("  LearnFlow AI — Preflight Environment & Capabilities Check")
    print("=" * 64)

    all_required_passed = True

    # Python Version
    py_ver = sys.version.split()[0]
    print(f"\n[REQUIRED] Python runtime: {py_ver} ({sys.executable})")

    # Package Imports
    print("\n[REQUIRED] Dependencies Import Check:")
    import_results = check_imports()
    for name, (passed, info) in import_results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  - {name:<14}: [{status}] {info}")
        if not passed:
            all_required_passed = False

    # Import internal capability and config modules
    try:
        from app.config import get_settings
        from app.capabilities import (
            check_ffmpeg,
            check_ffprobe,
            check_h264,
            detect_font,
            check_manim,
        )
    except Exception as e:
        print(f"\n[FAIL] Unable to import app modules: {e}")
        return False

    settings = get_settings()

    # Media Binaries & Codecs
    print("\n[REQUIRED] Media Prerequisites:")
    has_ffmpeg = check_ffmpeg()
    print(f"  - ffmpeg executable : [{'PASS' if has_ffmpeg else 'FAIL'}]")
    if not has_ffmpeg:
        all_required_passed = False

    has_ffprobe = check_ffprobe()
    print(f"  - ffprobe executable: [{'PASS' if has_ffprobe else 'FAIL'}]")
    if not has_ffprobe:
        all_required_passed = False

    has_h264 = check_h264()
    print(f"  - H.264 (libx264)   : [{'PASS' if has_h264 else 'FAIL'}]")
    if not has_h264:
        all_required_passed = False

    # Storage & Filesystem
    print("\n[REQUIRED] Writable Filesystem:")
    art_ok, art_msg = check_artifacts_dir(settings.artifacts_dir)
    print(f"  - Artifacts dir     : [{'PASS' if art_ok else 'FAIL'}] {art_msg}")
    if not art_ok:
        all_required_passed = False

    sql_ok, sql_msg = check_sqlite_writable()
    print(f"  - SQLite writable   : [{'PASS' if sql_ok else 'FAIL'}] {sql_msg}")
    if not sql_ok:
        all_required_passed = False

    # Font & Internationalization
    print("\n[REQUIRED] Typography & Localization:")
    font_path, vn_render_ok = detect_font()
    print(f"  - Font selected     : {font_path or 'None'}")
    print(f"  - Vietnamese render : [{'PASS' if vn_render_ok else 'FAIL'}] sample: 'Giải thích quá trình quang hợp'")
    if not vn_render_ok:
        all_required_passed = False

    # Optional Capabilities
    print("\n[OPTIONAL] Advanced & AI Capabilities:")
    has_manim = check_manim()
    print(f"  - Manim (optional)  : {'available' if has_manim else 'unavailable (informational only)'}")

    key_configured = bool(settings.gemini_api_key and settings.gemini_api_key.strip())
    print(f"  - GEMINI_API_KEY    : {'configured (key hidden)' if key_configured else 'not set (optional for CP0)'}")

    if check_gemini:
        print("\n[OPTIONAL] Gemini API Smoke Test (--check-gemini requested):")
        if not key_configured:
            print("  - Gemini check      : SKIPPED (GEMINI_API_KEY is not configured)")
        else:
            gem_ok, gem_msg = check_gemini_smoke(settings.gemini_api_key, settings.gemini_planner_model)
            print(f"  - Gemini response   : [{'PASS' if gem_ok else 'FAIL'}] {gem_msg}")

    print("\n" + "=" * 64)
    if all_required_passed:
        print("  RESULT: ALL REQUIRED CP0 CHECKS PASSED")
    else:
        print("  RESULT: ONE OR MORE REQUIRED CHECKS FAILED")
    print("=" * 64 + "\n")

    return all_required_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LearnFlow AI preflight checks")
    parser.add_argument(
        "--check-gemini",
        action="store_true",
        help="Perform optional live connectivity check to Gemini API",
    )
    args = parser.parse_args()
    success = run_preflight(check_gemini=args.check_gemini)
    sys.exit(0 if success else 1)
