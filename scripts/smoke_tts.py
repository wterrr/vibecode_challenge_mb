#!/usr/bin/env python3
"""Manual developer smoke test for Edge TTS and duration probing (CP4).

Tests real Edge TTS synthesis, file persistence, ffprobe duration, and clean removal.
"""

import asyncio
from pathlib import Path
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.config import get_settings
from app.pipeline.timeline import probe_duration
from app.providers.speech.edge import EdgeSpeechProvider


async def main() -> None:
    print("=" * 60)
    print("  LearnFlow AI — Edge TTS Manual Smoke Test")
    print("=" * 60)

    settings = get_settings()
    provider = EdgeSpeechProvider(
        voice_vi=settings.tts_voice_vi,
        voice_en=settings.tts_voice_en,
    )

    test_text = "Chào bạn, đây là kiểm tra giọng đọc tiếng Việt của LearnFlow AI."
    print(f"Voice selected: {settings.tts_voice_vi}")
    print(f"Text sample   : '{test_text}'")

    with tempfile.TemporaryDirectory(prefix="learnflow_tts_smoke_") as tmp_dir:
        out_path = Path(tmp_dir) / "smoke_vi.mp3"
        print(f"Synthesizing to: {out_path.name}...")

        try:
            result = await provider.synthesize(
                text=test_text,
                output_path=out_path,
                language="vi",
            )
            file_size = out_path.stat().st_size
            duration = await probe_duration(out_path)

            print("\n[SUCCESS] Edge TTS synthesized and verified successfully!")
            print(f"  Voice Used    : {settings.tts_voice_vi}")
            print(f"  File Size     : {file_size} bytes")
            print(f"  Audio Duration: {duration:.2f} seconds")
            print(f"  Subtitle Cues : {len(result.subtitle_cues)}")
            for idx, cue in enumerate(result.subtitle_cues, start=1):
                print(f"    - Cue {idx}: [{cue.start_seconds:.2f}s -> {cue.end_seconds:.2f}s] {cue.text}")

        except Exception as e:
            err_code = getattr(e, "code", type(e).__name__)
            print(f"\n[FAIL] TTS smoke test failed with code: {err_code}")
            print(f"  Reason: {getattr(e, 'message', str(e))[:120]}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
