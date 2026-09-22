"""Unit tests for ImageProvider base contract, GeminiImageProvider, and prompt builder."""

import asyncio
import base64
import io
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image
import pytest

from app.domain.enums import VisualIntent
from app.domain.lesson import IllustrationSpec, ScenePlan
from app.providers.image.base import ImageGenerationResult, ImageProvider, ImageProviderError
from app.providers.image.gemini import GeminiImageProvider, _map_gemini_exception
from app.providers.image.prompts import build_illustration_prompt


def make_test_png_bytes(width: int = 320, height: int = 180, color: tuple = (50, 100, 150)) -> bytes:
    """Generate in-memory valid PNG bytes."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class FakeImageProvider(ImageProvider):
    """Test fake for ImageProvider with configurable behavior and invocation tracking."""

    def __init__(
        self,
        image_bytes: bytes | None = None,
        error: Exception | None = None,
        width: int = 640,
        height: int = 360,
    ):
        self.image_bytes = image_bytes or make_test_png_bytes(width, height)
        self.error = error
        self.width = width
        self.height = height
        self.calls: list[dict] = []

    async def generate(self, *, prompt: str, output_path: Path) -> ImageGenerationResult:
        self.calls.append({"prompt": prompt, "output_path": output_path})
        if self.error:
            raise self.error

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(self.image_bytes)

        return ImageGenerationResult(
            path=str(output_path),
            provider="fake",
            model="fake-image-model",
            width=self.width,
            height=self.height,
        )


def test_gemini_image_init_validation() -> None:
    """GeminiImageProvider rejects empty API key, empty model, or non-positive timeout."""
    with pytest.raises(ValueError, match="api_key must be non-empty"):
        GeminiImageProvider(api_key="", model="gemini-3.1-flash-image")
    with pytest.raises(ValueError, match="api_key must be non-empty"):
        GeminiImageProvider(api_key="   ", model="gemini-3.1-flash-image")
    with pytest.raises(ValueError, match="model must be non-empty"):
        GeminiImageProvider(api_key="valid-key", model="")
    with pytest.raises(ValueError, match="timeout must be positive"):
        GeminiImageProvider(api_key="valid-key", model="gemini-3.1-flash-image", timeout=0)
    with pytest.raises(ValueError, match="timeout must be positive"):
        GeminiImageProvider(api_key="valid-key", model="gemini-3.1-flash-image", timeout=-5.0)

    # Valid initialization
    provider = GeminiImageProvider(api_key="test-key", model="gemini-3.1-flash-image", timeout=25.0)
    assert provider.model == "gemini-3.1-flash-image"
    assert provider.timeout == 25.0


@pytest.mark.asyncio
async def test_gemini_image_generation_success(tmp_path: Path) -> None:
    """GeminiImageProvider generates, validates, and atomically writes image."""
    png_bytes = make_test_png_bytes(320, 180)
    b64_str = base64.b64encode(png_bytes).decode("ascii")

    provider = GeminiImageProvider(api_key="fake-test-key", model="gemini-3.1-flash-image", timeout=20.0)

    mock_interaction = MagicMock()
    mock_output_img = MagicMock()
    mock_output_img.data = b64_str
    mock_interaction.output_image = mock_output_img

    target_file = tmp_path / "out" / "concept_1.png"

    with patch.object(provider._client.interactions, "create", return_value=mock_interaction) as mock_create:
        result = await provider.generate(prompt="A network router diagram", output_path=target_file)

        mock_create.assert_called_once()
        _, kwargs = mock_create.call_args
        assert kwargs["model"] == "gemini-3.1-flash-image"
        assert kwargs["input"] == "A network router diagram"
        assert kwargs["timeout"] == 20.0
        assert kwargs["response_format"] == {
            "type": "image",
            "aspect_ratio": "16:9",
            "image_size": "1K",
        }

        assert result.provider == "gemini"
        assert result.model == "gemini-3.1-flash-image"
        assert result.width == 320
        assert result.height == 180
        assert Path(result.path).exists()
        assert Path(result.path).stat().st_size > 0

        # Verify no temp files remain in target directory
        temp_files = list(target_file.parent.glob("*.tmp_*"))
        assert len(temp_files) == 0


@pytest.mark.asyncio
async def test_gemini_image_enforces_16_9_and_1k_response_format(tmp_path: Path) -> None:
    """SDK boundary contract test: interactions.create MUST receive explicit response_format for 16:9 1K image."""
    png_bytes = make_test_png_bytes(320, 180)
    b64_str = base64.b64encode(png_bytes).decode("ascii")

    configured_timeout = 25.0
    provider = GeminiImageProvider(api_key="fake-key", model="gemini-3.1-flash-image", timeout=configured_timeout)

    mock_interaction = MagicMock()
    mock_output_img = MagicMock()
    mock_output_img.data = b64_str
    mock_interaction.output_image = mock_output_img

    target_file = tmp_path / "test_16_9.png"

    with patch.object(provider._client.interactions, "create", return_value=mock_interaction) as mock_create:
        await provider.generate(prompt="Landscape network diagram", output_path=target_file)

        mock_create.assert_called_once()
        _, kwargs = mock_create.call_args
        assert kwargs["model"] == "gemini-3.1-flash-image"
        assert kwargs["timeout"] == configured_timeout
        assert kwargs["response_format"] == {
            "type": "image",
            "aspect_ratio": "16:9",
            "image_size": "1K",
        }


@pytest.mark.asyncio
async def test_gemini_image_generation_from_dict_or_steps(tmp_path: Path) -> None:
    """GeminiImageProvider handles output_image as dict or inside interaction.steps."""
    png_bytes = make_test_png_bytes(200, 100)
    b64_str = base64.b64encode(png_bytes).decode("ascii")

    provider = GeminiImageProvider(api_key="fake-key")

    # Dict format for output_image
    mock_interaction_dict = MagicMock()
    mock_interaction_dict.output_image = {"data": b64_str}
    target_dict = tmp_path / "img_dict.png"

    with patch.object(provider._client.interactions, "create", return_value=mock_interaction_dict):
        res = await provider.generate(prompt="test dict", output_path=target_dict)
        assert res.width == 200
        assert res.height == 100

    # Fallback to steps format
    mock_interaction_steps = MagicMock()
    mock_interaction_steps.output_image = None
    mock_interaction_steps.steps = [
        {"type": "model_output", "content": [{"type": "image", "data": b64_str}]}
    ]
    target_steps = tmp_path / "img_steps.png"

    with patch.object(provider._client.interactions, "create", return_value=mock_interaction_steps):
        res2 = await provider.generate(prompt="test steps", output_path=target_steps)
        assert res2.width == 200
        assert res2.height == 100


@pytest.mark.asyncio
async def test_gemini_image_rejects_empty_payload(tmp_path: Path) -> None:
    """Empty or missing image payload maps to non-retryable image_invalid_output."""
    provider = GeminiImageProvider(api_key="fake-key")

    mock_interaction = MagicMock()
    mock_interaction.output_image = None
    mock_interaction.steps = []

    target_file = tmp_path / "missing.png"

    with patch.object(provider._client.interactions, "create", return_value=mock_interaction):
        with pytest.raises(ImageProviderError) as exc_info:
            await provider.generate(prompt="test empty", output_path=target_file)

        assert exc_info.value.code == "image_invalid_output"
        assert exc_info.value.retryable is False
        assert not target_file.exists()


@pytest.mark.asyncio
async def test_gemini_image_rejects_corrupted_image(tmp_path: Path) -> None:
    """Corrupted bytes that cannot be verified by Pillow map to image_invalid_output."""
    provider = GeminiImageProvider(api_key="fake-key")

    b64_corrupt = base64.b64encode(b"NOT_A_VALID_IMAGE_BYTES").decode("ascii")
    mock_interaction = MagicMock()
    mock_output_img = MagicMock()
    mock_output_img.data = b64_corrupt
    mock_interaction.output_image = mock_output_img

    target_file = tmp_path / "corrupt.png"

    with patch.object(provider._client.interactions, "create", return_value=mock_interaction):
        with pytest.raises(ImageProviderError) as exc_info:
            await provider.generate(prompt="test corrupt", output_path=target_file)

        assert exc_info.value.code == "image_invalid_output"
        assert not target_file.exists()
        # Verify temporary file cleaned up
        assert len(list(tmp_path.glob("*.tmp_*"))) == 0


@pytest.mark.asyncio
async def test_gemini_image_timeout_mapping_and_retry(tmp_path: Path) -> None:
    """Timeout error triggers retry up to 2 attempts then raises image_timeout."""
    provider = GeminiImageProvider(api_key="fake-key")
    target_file = tmp_path / "timeout.png"

    with patch.object(provider._client.interactions, "create", side_effect=TimeoutError("Request timed out")) as mock_create:
        with pytest.raises(ImageProviderError) as exc_info:
            await provider.generate(prompt="test timeout", output_path=target_file)

        assert exc_info.value.code == "image_timeout"
        assert exc_info.value.retryable is True
        assert mock_create.call_count == 2
        assert not target_file.exists()


@pytest.mark.asyncio
async def test_gemini_image_rate_limit_retry(tmp_path: Path) -> None:
    """429 Rate limit error triggers retry up to 2 attempts then raises image_rate_limited."""
    provider = GeminiImageProvider(api_key="fake-key")
    target_file = tmp_path / "rate_limit.png"

    class MockHttpError(Exception):
        code = 429

    with patch.object(provider._client.interactions, "create", side_effect=MockHttpError("RESOURCE_EXHAUSTED")) as mock_create:
        with pytest.raises(ImageProviderError) as exc_info:
            await provider.generate(prompt="test 429", output_path=target_file)

        assert exc_info.value.code == "image_rate_limited"
        assert exc_info.value.retryable is True
        assert mock_create.call_count == 2
        assert not target_file.exists()


@pytest.mark.asyncio
async def test_gemini_image_transient_retry_success(tmp_path: Path) -> None:
    """First attempt fails with 503 unavailable, second attempt succeeds."""
    provider = GeminiImageProvider(api_key="fake-key")
    target_file = tmp_path / "retry_success.png"

    png_bytes = make_test_png_bytes(300, 150)
    b64_str = base64.b64encode(png_bytes).decode("ascii")
    mock_interaction = MagicMock()
    mock_interaction.output_image = {"data": b64_str}

    call_count = 0

    def _mock_call(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("503 Service Unavailable")
        return mock_interaction

    with patch.object(provider._client.interactions, "create", side_effect=_mock_call):
        res = await provider.generate(prompt="test retry", output_path=target_file)
        assert call_count == 2
        assert res.width == 300
        assert target_file.exists()


@pytest.mark.asyncio
async def test_gemini_image_auth_error_no_retry(tmp_path: Path) -> None:
    """401/403 Auth error does NOT retry (fails on first attempt)."""
    provider = GeminiImageProvider(api_key="fake-key")
    target_file = tmp_path / "auth_fail.png"

    class MockAuthError(Exception):
        code = 403

    with patch.object(provider._client.interactions, "create", side_effect=MockAuthError("PERMISSION_DENIED")) as mock_create:
        with pytest.raises(ImageProviderError) as exc_info:
            await provider.generate(prompt="test auth", output_path=target_file)

        assert exc_info.value.code == "image_auth_error"
        assert exc_info.value.retryable is False
        assert mock_create.call_count == 1


def test_gemini_image_error_sanitization() -> None:
    """Sanitizer never leaks secret keys, authorization headers, or base64 blobs into message."""
    secret = "AIzaSySecretApiKey123456789"
    raw_error = Exception(f"Failed Authorization: Bearer {secret} with b64 payload {base64.b64encode(b'secret').decode()}")

    mapped = _map_gemini_exception(raw_error)
    assert secret not in mapped.message
    assert "Bearer" not in mapped.message
    assert mapped.code in ("image_auth_error", "image_provider_error")


def test_build_illustration_prompt() -> None:
    """Prompt builder structures landscape 16:9 framing, educational focus, and strict text avoidance."""
    spec = IllustrationSpec(
        prompt="A client computer transmitting an initial network packet towards a server.",
        fallback_heading="SYN Packet Transmission",
        fallback_points=["Client selects ISN", "Sends SYN bit set", "State transitions to SYN_SENT"],
    )
    scene = ScenePlan(
        scene_id="s02_syn_packet",
        title="Three-Way Handshake SYN Packet",
        concept="TCP SYN Transmission",
        narration="Client initiates connection by sending a SYN segment.",
        key_points=["Client selects ISN", "Sends SYN bit set"],
        visual_intent=VisualIntent.ILLUSTRATION,
        visual_spec=spec,
    )

    prompt = build_illustration_prompt(scene, spec)
    assert "TCP SYN Transmission" in prompt
    assert "A client computer transmitting" in prompt
    assert "landscape 16:9" in prompt
    assert "no logos or watermarks" in prompt
    assert "Avoid:" in prompt
    assert "no interface elements" in prompt
