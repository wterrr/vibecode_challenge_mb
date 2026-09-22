"""Gemini image generation provider using Google GenAI SDK."""

import asyncio
import base64
import logging
import os
from pathlib import Path
from typing import Any
import uuid

from google import genai
from PIL import Image

from app.providers.image.base import ImageGenerationResult, ImageProvider, ImageProviderError

logger = logging.getLogger(__name__)


def _map_gemini_exception(exc: Exception) -> ImageProviderError:
    """Map raw provider exceptions to sanitized, structured ImageProviderError without leaking secrets."""
    if isinstance(exc, ImageProviderError):
        return exc

    exc_type = type(exc).__name__
    status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    err_str = str(exc).lower()

    if (
        isinstance(exc, (TimeoutError, asyncio.TimeoutError))
        or "timeout" in err_str
        or "deadline" in err_str
    ):
        return ImageProviderError(
            code="image_timeout",
            message="Image provider request timed out.",
            retryable=True,
        )

    if (
        status_code in (401, 403)
        or "unauthenticated" in err_str
        or "permission_denied" in err_str
        or "api_key" in err_str
        or "auth" in err_str
    ):
        return ImageProviderError(
            code="image_auth_error",
            message="Authentication failed with the image provider.",
            retryable=False,
        )

    if (
        status_code in (429, 402)
        or "resource_exhausted" in err_str
        or "quota" in err_str
        or "rate_limit" in err_str
        or "rate limit" in err_str
    ):
        return ImageProviderError(
            code="image_rate_limited",
            message="Image provider rate limit or quota exceeded.",
            retryable=True,
        )

    if "unavailable" in err_str or "503" in err_str or "bad gateway" in err_str or "502" in err_str:
        return ImageProviderError(
            code="image_provider_error",
            message=f"Image provider service is temporarily unavailable ({exc_type}).",
            retryable=True,
        )

    return ImageProviderError(
        code="image_provider_error",
        message=f"Image provider encountered an error ({exc_type}).",
        retryable=False,
    )


class GeminiImageProvider(ImageProvider):
    """Generates educational concept illustrations using Gemini image models."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-3.1-flash-image",
        timeout: float = 30.0,
    ):
        if not api_key or not api_key.strip():
            raise ValueError("api_key must be non-empty")
        if not model or not model.strip():
            raise ValueError("model must be non-empty")
        if timeout <= 0:
            raise ValueError("timeout must be positive")

        self._api_key = api_key
        self.model = model
        self.timeout = timeout
        self._client = genai.Client(api_key=api_key)

    def _extract_image_bytes(self, interaction: Any) -> bytes:
        """Extract and base64-decode raw image bytes from an interaction response."""
        output_image = getattr(interaction, "output_image", None)

        b64_data: str | None = None
        if output_image is not None:
            if isinstance(output_image, dict):
                b64_data = output_image.get("data")
            else:
                b64_data = getattr(output_image, "data", None)

        if not b64_data and hasattr(interaction, "steps"):
            steps = getattr(interaction, "steps") or []
            for step in reversed(steps):
                content = getattr(step, "content", None) if not isinstance(step, dict) else step.get("content")
                if isinstance(content, list):
                    for item in reversed(content):
                        item_type = getattr(item, "type", None) if not isinstance(item, dict) else item.get("type")
                        if item_type == "image":
                            b64_data = getattr(item, "data", None) if not isinstance(item, dict) else item.get("data")
                            if b64_data:
                                break
                if b64_data:
                    break

        if not b64_data:
            raise ImageProviderError(
                code="image_invalid_output",
                message="Gemini interaction response contained no image payload.",
                retryable=False,
            )

        try:
            raw_bytes = base64.b64decode(b64_data)
        except Exception:
            raise ImageProviderError(
                code="image_invalid_output",
                message="Failed to decode base64 image data from provider.",
                retryable=False,
            ) from None

        if len(raw_bytes) == 0:
            raise ImageProviderError(
                code="image_invalid_output",
                message="Image provider returned an empty byte stream.",
                retryable=False,
            )

        return raw_bytes

    async def generate(
        self,
        *,
        prompt: str,
        output_path: Path,
    ) -> ImageGenerationResult:
        """Generate an image from prompt and atomically save validated RGB PNG to output_path."""
        max_attempts = 2
        last_error: ImageProviderError | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                def _call() -> bytes:
                    interaction = self._client.interactions.create(
                        model=self.model,
                        input=prompt,
                        response_format={
                            "type": "image",
                            "aspect_ratio": "16:9",
                            "image_size": "1K",
                        },
                        timeout=self.timeout,
                    )
                    return self._extract_image_bytes(interaction)

                raw_bytes = await asyncio.to_thread(_call)

                # Output file safety: write to temporary file in same directory first
                output_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path = output_path.parent / f"{output_path.name}.tmp_{os.getpid()}_{uuid.uuid4().hex[:8]}"

                try:
                    with open(tmp_path, "wb") as f:
                        f.write(raw_bytes)

                    # Validate with Pillow
                    try:
                        with Image.open(tmp_path) as img:
                            img.verify()
                        # Re-open after verify to check dimensions and convert
                        with Image.open(tmp_path) as img:
                            w, h = img.size
                            if w <= 0 or h <= 0:
                                raise ImageProviderError(
                                    code="image_invalid_output",
                                    message="Generated image has invalid dimensions (<=0).",
                                    retryable=False,
                                )
                            rgb_img = img.convert("RGB")
                            rgb_img.save(tmp_path, format="PNG")
                    except Exception as img_err:
                        if isinstance(img_err, ImageProviderError):
                            raise img_err
                        raise ImageProviderError(
                            code="image_invalid_output",
                            message="Provider output is not a valid, decodable image.",
                            retryable=False,
                        ) from None

                    # Atomic replacement to target path
                    os.replace(tmp_path, output_path)

                    return ImageGenerationResult(
                        path=str(output_path),
                        provider="gemini",
                        model=self.model,
                        width=w,
                        height=h,
                    )

                finally:
                    if tmp_path.exists():
                        try:
                            tmp_path.unlink()
                        except Exception:
                            pass

            except Exception as exc:
                mapped = _map_gemini_exception(exc)
                logger.warning(
                    "Gemini image provider error provider=gemini model=%s code=%s attempt=%d/%d",
                    self.model,
                    mapped.code,
                    attempt,
                    max_attempts,
                )
                last_error = mapped

                if mapped.retryable and attempt < max_attempts:
                    await asyncio.sleep(0.5)
                    continue

                raise mapped from None

        if last_error:
            raise last_error
        raise ImageProviderError(
            code="image_provider_error",
            message="Image generation failed after retry attempts.",
            retryable=False,
        )
