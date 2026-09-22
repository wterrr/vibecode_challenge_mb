#!/usr/bin/env python3
"""Manual developer smoke test for Gemini image provider (CP6).

Runs against the configured GEMINI_API_KEY environment without leaking secrets.
If unconfigured, exits cleanly with 0.
"""

import asyncio
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.config import get_settings
from app.providers.image.gemini import GeminiImageProvider


async def main() -> None:
    print("=" * 60)
    print("  LearnFlow AI — Gemini Image Provider Manual Smoke Test")
    print("=" * 60)

    settings = get_settings()
    if not settings.gemini_api_key or not settings.gemini_api_key.strip():
        print("[INFO] GEMINI_API_KEY is not configured. Exiting cleanly without error.")
        sys.exit(0)

    model = getattr(settings, "gemini_image_model", "gemini-3.1-flash-image")
    print(f"Model configured: {model}")
    print("Initializing GeminiImageProvider...")

    provider = GeminiImageProvider(
        api_key=settings.gemini_api_key,
        model=model,
        timeout=30.0,
    )

    out_dir = Path("artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "smoke_image.png"

    prompt = (
        "Create a clean educational illustration of computer network packet routing "
        "between a client and server in landscape 16:9 format without text or interface elements."
    )

    print("Requesting image generation...")
    try:
        result = await provider.generate(prompt=prompt, output_path=out_path)
        file_size = out_path.stat().st_size
        ratio_val = result.width / result.height if result.height > 0 else 0.0
        print(f"\n[SUCCESS] Image generated successfully!")
        print(f"  Path        : {result.path}")
        print(f"  Dimensions  : {result.width}x{result.height}")
        print(f"  Aspect Ratio: {result.width}:{result.height} ({ratio_val:.2f}:1, target 16:9 ~ 1.78:1)")
        print(f"  File Size   : {file_size} bytes")
        print(f"  Provider    : {result.provider}")
        print(f"  Model       : {result.model}")
    except Exception as e:
        err_code = getattr(e, "code", type(e).__name__)
        print(f"\n[FAIL] Image smoke test failed with code: {err_code}")
        print(f"  Reason: {getattr(e, 'message', str(e))[:120]}")


if __name__ == "__main__":
    asyncio.run(main())
