"""Unit tests for EdgeSpeechProvider with mocked network boundaries."""

import asyncio
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.providers.speech.base import SpeechProviderError
from app.providers.speech.edge import EdgeSpeechProvider


@pytest.mark.asyncio
async def test_edge_provider_voice_mapping_by_language(tmp_path: Path) -> None:
    """Correct voice is selected according to language parameter."""
    provider = EdgeSpeechProvider(
        voice_vi="vi-VN-NamMinhNeural",
        voice_en="en-US-GuyNeural",
    )

    out_file = tmp_path / "test.mp3"

    async def fake_stream():
        yield {"type": "audio", "data": b"\xff\xfb\x90\x00" * 50}

    mock_comm = MagicMock()
    mock_comm.stream = fake_stream

    with patch("edge_tts.Communicate", return_value=mock_comm) as mock_init:
        res = await provider.synthesize("Xin chào thế giới.", out_file, language="vi")
        assert res.provider == "edge"
        mock_init.assert_called_once_with(text="Xin chào thế giới.", voice="vi-VN-NamMinhNeural")

    mock_init.reset_mock()
    with patch("edge_tts.Communicate", return_value=mock_comm) as mock_init:
        res = await provider.synthesize("Hello world.", out_file, language="en")
        mock_init.assert_called_once_with(text="Hello world.", voice="en-US-GuyNeural")


@pytest.mark.asyncio
async def test_edge_provider_unsupported_language_raises_error(tmp_path: Path) -> None:
    """Unsupported language raises speech_provider_error immediately."""
    provider = EdgeSpeechProvider()
    out_file = tmp_path / "test.mp3"

    with pytest.raises(SpeechProviderError) as exc_info:
        await provider.synthesize("Bonjour", out_file, language="fr")

    assert exc_info.value.code == "speech_provider_error"
    assert exc_info.value.retryable is False


@pytest.mark.asyncio
async def test_edge_provider_empty_narration_raises_error(tmp_path: Path) -> None:
    """Empty or whitespace-only narration raises speech_invalid_audio."""
    provider = EdgeSpeechProvider()
    out_file = tmp_path / "test.mp3"

    with pytest.raises(SpeechProviderError) as exc_info:
        await provider.synthesize("   \n  ", out_file, language="vi")

    assert exc_info.value.code == "speech_invalid_audio"
    assert exc_info.value.retryable is False


@pytest.mark.asyncio
async def test_edge_provider_empty_audio_stream_raises_error(tmp_path: Path) -> None:
    """Stream yielding no audio data raises speech_empty_audio."""
    provider = EdgeSpeechProvider()
    out_file = tmp_path / "test.mp3"

    async def empty_stream():
        # Only non-audio chunks or empty
        yield {"type": "SentenceBoundary", "offset": 0, "duration": 1000, "text": "Hi"}

    mock_comm = MagicMock()
    mock_comm.stream = empty_stream

    with patch("edge_tts.Communicate", return_value=mock_comm):
        with pytest.raises(SpeechProviderError) as exc_info:
            await provider.synthesize("Hello", out_file, language="en")

        assert exc_info.value.code == "speech_empty_audio"
        assert exc_info.value.retryable is False


@pytest.mark.asyncio
async def test_edge_provider_parses_valid_sentence_cues(tmp_path: Path) -> None:
    """Sentence boundary metadata is converted to SubtitleCue objects."""
    provider = EdgeSpeechProvider()
    out_file = tmp_path / "test.mp3"

    async def stream_with_cues():
        yield {
            "type": "SentenceBoundary",
            "offset": 10_000_000,  # 1.0s
            "duration": 20_000_000,  # 2.0s
            "text": "Câu thứ nhất.",
        }
        yield {"type": "audio", "data": b"\xff\xfb\x90\x00" * 100}

    mock_comm = MagicMock()
    mock_comm.stream = stream_with_cues

    with patch("edge_tts.Communicate", return_value=mock_comm):
        result = await provider.synthesize("Câu thứ nhất.", out_file, language="vi")
        assert len(result.subtitle_cues) == 1
        cue = result.subtitle_cues[0]
        assert cue.start_seconds == 1.0
        assert cue.end_seconds == 3.0
        assert cue.text == "Câu thứ nhất."


@pytest.mark.asyncio
async def test_edge_provider_retries_transient_timeout(tmp_path: Path) -> None:
    """Transient timeout retries once and raises speech_timeout on second failure."""
    provider = EdgeSpeechProvider()
    out_file = tmp_path / "test.mp3"

    attempts = 0

    def mock_communicate_factory(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        mock = MagicMock()
        async def failing_stream():
            raise TimeoutError("Socket timeout")
            yield {}
        mock.stream = failing_stream
        return mock

    with patch("edge_tts.Communicate", side_effect=mock_communicate_factory):
        with pytest.raises(SpeechProviderError) as exc_info:
            await provider.synthesize("Hello retry", out_file, language="en")

        assert exc_info.value.code == "speech_timeout"
        assert exc_info.value.retryable is True
        assert attempts == 2  # Exactly 2 attempts (1 initial + 1 retry)


@pytest.mark.asyncio
async def test_edge_provider_does_not_leak_secrets(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Raw exception details or secrets are not exposed in logs or errors."""
    secret_token = "SECRET_TTS_KEY_VALUE_123"
    provider = EdgeSpeechProvider()
    out_file = tmp_path / "test.mp3"

    class LeakyTTSError(Exception):
        def __str__(self) -> str:
            return f"Unauthorized token {secret_token}"

    def mock_factory(*args, **kwargs):
        mock = MagicMock()
        async def leaky_stream():
            raise LeakyTTSError("Leaky error")
            yield {}
        mock.stream = leaky_stream
        return mock

    with caplog.at_level(logging.DEBUG):
        with patch("edge_tts.Communicate", side_effect=mock_factory):
            with pytest.raises(SpeechProviderError) as exc_info:
                await provider.synthesize("Testing secret leak", out_file, language="en")

    assert secret_token not in str(exc_info.value)
    assert secret_token not in exc_info.value.message

    for record in caplog.records:
        assert secret_token not in record.message


@pytest.mark.asyncio
async def test_edge_provider_asyncio_timeout_cleans_tmp_and_retries(tmp_path: Path) -> None:
    """A streaming hang triggers asyncio.timeout, cleans up temp file, and retries."""
    provider = EdgeSpeechProvider(timeout=0.05)
    out_file = tmp_path / "timeout_test.mp3"
    attempts = 0

    def mock_factory(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        mock = MagicMock()

        async def hanging_stream():
            # First write a partial chunk to verify temp file cleanup
            yield {"type": "audio", "data": b"\xff\xfb\x90\x00" * 10}
            await asyncio.sleep(0.5)  # Longer than provider.timeout (0.05s)
            yield {"type": "audio", "data": b"\xff\xfb\x90\x00" * 10}

        mock.stream = hanging_stream
        return mock

    with patch("edge_tts.Communicate", side_effect=mock_factory):
        with pytest.raises(SpeechProviderError) as exc_info:
            await provider.synthesize("Hanging narration text", out_file, language="en")

    assert exc_info.value.code == "speech_timeout"
    assert exc_info.value.retryable is True
    assert attempts == 2

    # Verify no leaked temporary files in directory
    leftovers = list(tmp_path.glob("*.tmp*"))
    assert len(leftovers) == 0
    assert not out_file.exists()

