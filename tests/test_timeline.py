"""Unit tests for media timeline building, duration probing, padding, and subtitle allocation."""

import json
from pathlib import Path
import wave
import pytest

from app.domain.enums import JobStage
from app.domain.errors import PipelineExecutionError
from app.domain.timeline import ResolvedTimeline, SubtitleCue
from app.pipeline.timeline import (
    TimelineBuilder,
    generate_fallback_subtitle_cues,
    pad_audio,
    probe_duration,
    split_sentences_with_punctuation,
)
from app.providers.speech.base import (
    SpeechProvider,
    SpeechProviderError,
    SpeechResult,
)
from app.storage.local import LocalArtifactStore
from tests.test_plan_validator import make_valid_tcp_plan


def create_pcm_wav(path: Path, duration_seconds: float, sample_rate: int = 48000) -> Path:
    """Generate a valid silent PCM WAV audio fixture using Python's stdlib wave."""
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    num_frames = int(sample_rate * duration_seconds)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_frames)
    return path


class FakeSpeechProvider(SpeechProvider):
    """Test fake speech provider copying predefined WAV fixtures."""

    def __init__(
        self,
        duration_seconds: float = 1.0,
        subtitle_cues: list[SubtitleCue] | None = None,
        fail: bool = False,
    ):
        self.duration_seconds = duration_seconds
        self.subtitle_cues = subtitle_cues or []
        self.fail = fail
        self.synthesize_calls = 0

    async def synthesize(
        self,
        text: str,
        output_path: Path,
        language: str,
    ) -> SpeechResult:
        self.synthesize_calls += 1
        if self.fail:
            raise SpeechProviderError(
                code="speech_provider_error",
                message="Simulated speech synthesis failure",
                retryable=False,
            )
        create_pcm_wav(output_path, self.duration_seconds)
        return SpeechResult(
            path=str(output_path),
            provider="fake",
            duration_seconds=self.duration_seconds,
            subtitle_cues=self.subtitle_cues,
        )


@pytest.mark.asyncio
async def test_probe_duration_measures_real_wav(tmp_path: Path) -> None:
    """probe_duration accurately measures a generated PCM WAV fixture."""
    wav_path = create_pcm_wav(tmp_path / "sample.wav", duration_seconds=1.5)
    duration = await probe_duration(wav_path)
    assert abs(duration - 1.5) < 0.02


@pytest.mark.asyncio
async def test_probe_duration_rejects_missing_file(tmp_path: Path) -> None:
    """probe_duration raises speech_invalid_audio on missing files."""
    missing = tmp_path / "non_existent.wav"
    with pytest.raises(SpeechProviderError) as exc_info:
        await probe_duration(missing)
    assert exc_info.value.code == "speech_invalid_audio"


@pytest.mark.asyncio
async def test_probe_duration_rejects_empty_file(tmp_path: Path) -> None:
    """probe_duration raises speech_invalid_audio on empty (0-byte) files."""
    empty = tmp_path / "empty.wav"
    empty.touch()
    with pytest.raises(SpeechProviderError) as exc_info:
        await probe_duration(empty)
    assert exc_info.value.code == "speech_invalid_audio"


@pytest.mark.asyncio
async def test_probe_duration_rejects_corrupted_file(tmp_path: Path) -> None:
    """probe_duration raises speech_invalid_audio on corrupted binary content."""
    corrupted = tmp_path / "bad.wav"
    corrupted.write_bytes(b"NOT_A_VALID_AUDIO_CONTAINER_OR_HEADER")
    with pytest.raises(SpeechProviderError) as exc_info:
        await probe_duration(corrupted)
    assert exc_info.value.code == "speech_invalid_audio"


@pytest.mark.asyncio
async def test_pad_audio_expands_duration_accurately(tmp_path: Path) -> None:
    """pad_audio creates a valid padded audio file matching target duration."""
    raw_path = create_pcm_wav(tmp_path / "raw.wav", duration_seconds=0.8)
    padded_path = tmp_path / "padded.wav"

    target_duration = 1.6
    measured = await pad_audio(raw_path, padded_path, target_duration)

    assert padded_path.exists()
    assert padded_path.stat().st_size > raw_path.stat().st_size
    assert abs(measured - target_duration) < 0.05


def test_split_sentences_preserves_punctuation() -> None:
    """Sentence splitting accurately segments Vietnamese text and retains punctuation."""
    text = "TCP là giao thức tin cậy. Nó dùng 3 bước bắt tay! Server sẵn sàng chưa?"
    sentences = split_sentences_with_punctuation(text)
    assert len(sentences) == 3
    assert sentences[0] == "TCP là giao thức tin cậy."
    assert sentences[1] == "Nó dùng 3 bước bắt tay!"
    assert sentences[2] == "Server sẵn sàng chưa?"


def test_fallback_subtitles_single_sentence() -> None:
    """A single sentence spans from scene start to raw audio duration, ending before silence."""
    cues = generate_fallback_subtitle_cues(
        narration="Chỉ có một câu duy nhất.",
        scene_start=2.0,
        audio_duration=1.4,
    )
    assert len(cues) == 1
    assert cues[0].start_seconds == 2.0
    assert cues[0].end_seconds == 3.4
    assert cues[0].text == "Chỉ có một câu duy nhất."


def test_fallback_subtitles_proportional_allocation() -> None:
    """Multiple sentences are allocated proportionally without extending into padding silence."""
    narration = "Câu một ngắn. Câu hai có độ dài dài hơn rất nhiều so với câu một!"
    scene_start = 5.0
    audio_duration = 4.0

    cues = generate_fallback_subtitle_cues(
        narration=narration,
        scene_start=scene_start,
        audio_duration=audio_duration,
    )
    assert len(cues) == 2
    assert cues[0].start_seconds == 5.0
    assert cues[0].end_seconds < 7.0  # Shorter sentence gets less duration
    assert cues[1].start_seconds == cues[0].end_seconds
    assert cues[1].end_seconds == pytest.approx(9.0, abs=0.01)  # Ends at scene_start + audio_duration


@pytest.mark.asyncio
async def test_timeline_builder_minimum_render_duration(tmp_path: Path) -> None:
    """When audio is short (e.g. 0.4s), render duration is clamped to minimum 1.0s."""
    store = LocalArtifactStore(tmp_path / "artifacts")
    # 0.4s audio + 0.30s buffer = 0.7s -> clamped to 1.0s
    speech = FakeSpeechProvider(duration_seconds=0.4)
    builder = TimelineBuilder(speech_provider=speech, artifact_store=store)

    plan = make_valid_tcp_plan()
    job_id = "job_test_min_duration"

    timeline = await builder.build(job_id=job_id, plan=plan)

    for scene in timeline.scenes:
        assert scene.audio_duration_seconds == pytest.approx(0.4, abs=0.02)
        assert scene.render_duration_seconds == 1.0


@pytest.mark.asyncio
async def test_timeline_builder_buffer_rule_and_continuity(tmp_path: Path) -> None:
    """Render duration is audio_duration + 0.30s when > 1.0s, with strict time continuity."""
    store = LocalArtifactStore(tmp_path / "artifacts")
    # 1.2s audio + 0.30s = 1.5s render duration
    speech = FakeSpeechProvider(duration_seconds=1.2)
    builder = TimelineBuilder(speech_provider=speech, artifact_store=store)

    plan = make_valid_tcp_plan()
    job_id = "job_test_continuity"

    timeline = await builder.build(job_id=job_id, plan=plan)

    assert len(timeline.scenes) == 3
    # Scene 1: 0.0 -> 1.5
    assert timeline.scenes[0].start_seconds == 0.0
    assert timeline.scenes[0].render_duration_seconds == 1.5
    assert timeline.scenes[0].end_seconds == 1.5

    # Scene 2: 1.5 -> 3.0
    assert timeline.scenes[1].start_seconds == 1.5
    assert timeline.scenes[1].render_duration_seconds == 1.5
    assert timeline.scenes[1].end_seconds == 3.0

    # Scene 3: 3.0 -> 4.5
    assert timeline.scenes[2].start_seconds == 3.0
    assert timeline.scenes[2].render_duration_seconds == 1.5
    assert timeline.scenes[2].end_seconds == 4.5

    assert timeline.total_duration_seconds == 4.5


@pytest.mark.asyncio
async def test_timeline_builder_persists_timeline_json_atomically(tmp_path: Path) -> None:
    """TimelineBuilder writes timeline.json which can be loaded back into ResolvedTimeline."""
    store = LocalArtifactStore(tmp_path / "artifacts")
    speech = FakeSpeechProvider(duration_seconds=1.0)
    builder = TimelineBuilder(speech_provider=speech, artifact_store=store)

    plan = make_valid_tcp_plan()
    job_id = "job_test_json"

    timeline = await builder.build(job_id=job_id, plan=plan)

    timeline_json_path = store.get_path(job_id, "timeline.json")
    assert timeline_json_path.exists()

    content = json.loads(timeline_json_path.read_text(encoding="utf-8"))
    loaded = ResolvedTimeline.model_validate(content)

    assert len(loaded.scenes) == len(timeline.scenes)
    assert loaded.total_duration_seconds == timeline.total_duration_seconds


@pytest.mark.asyncio
async def test_timeline_builder_stops_and_fails_on_speech_error(tmp_path: Path) -> None:
    """If speech synthesis fails for any scene, TimelineBuilder stops with PipelineExecutionError."""
    store = LocalArtifactStore(tmp_path / "artifacts")
    failing_speech = FakeSpeechProvider(fail=True)
    builder = TimelineBuilder(speech_provider=failing_speech, artifact_store=store)

    plan = make_valid_tcp_plan()
    job_id = "job_test_speech_failure"

    with pytest.raises(PipelineExecutionError) as exc_info:
        await builder.build(job_id=job_id, plan=plan)

    assert exc_info.value.stage == JobStage.AUDIO
    assert exc_info.value.code == "speech_provider_error"

    # timeline.json should NOT have been published
    timeline_path = store.get_path(job_id, "timeline.json")
    assert not timeline_path.exists()
