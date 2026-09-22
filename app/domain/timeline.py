"""Timeline models for scene and video audio/render synchronization."""

from pydantic import BaseModel, Field, model_validator


class SubtitleCue(BaseModel):
    """A timed subtitle segment for narration sync."""

    start_seconds: float = Field(ge=0.0)
    end_seconds: float
    text: str

    @model_validator(mode="after")
    def validate_cue(self) -> "SubtitleCue":
        if not self.text.strip():
            raise ValueError("Subtitle cue text cannot be blank")
        if self.end_seconds <= self.start_seconds:
            raise ValueError(
                f"end_seconds ({self.end_seconds}) must be greater than start_seconds ({self.start_seconds})"
            )
        return self


class ResolvedSceneTiming(BaseModel):
    """Timing coordinates and intermediate audio paths for a resolved scene."""

    scene_id: str

    raw_audio_path: str
    padded_audio_path: str

    audio_duration_seconds: float = Field(gt=0)
    render_duration_seconds: float = Field(ge=1.0)

    start_seconds: float = Field(ge=0.0)
    end_seconds: float

    subtitle_cues: list[SubtitleCue] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_timing_constraints(self) -> "ResolvedSceneTiming":
        if self.end_seconds <= self.start_seconds:
            raise ValueError(
                f"end_seconds ({self.end_seconds}) must be greater than start_seconds ({self.start_seconds})"
            )

        # Allow small floating point tolerance (1ms)
        diff = self.end_seconds - self.start_seconds
        if abs(diff - self.render_duration_seconds) > 1e-3:
            raise ValueError(
                f"Scene span ({diff:.4f}s) must equal render_duration_seconds ({self.render_duration_seconds:.4f}s)"
            )

        if self.render_duration_seconds < (self.audio_duration_seconds - 1e-3):
            raise ValueError(
                f"render_duration_seconds ({self.render_duration_seconds}) must be >= audio_duration_seconds ({self.audio_duration_seconds})"
            )

        return self


class ResolvedTimeline(BaseModel):
    """Complete assembled media timeline with strict continuity."""

    scenes: list[ResolvedSceneTiming] = Field(min_length=1)
    total_duration_seconds: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_continuity(self) -> "ResolvedTimeline":
        seen_ids = set()
        prev_end = 0.0

        for idx, scene in enumerate(self.scenes):
            if scene.scene_id in seen_ids:
                raise ValueError(f"Duplicate scene id '{scene.scene_id}' in timeline")
            seen_ids.add(scene.scene_id)

            if idx == 0:
                if abs(scene.start_seconds - 0.0) > 1e-3:
                    raise ValueError(
                        f"First scene must start at 0.0s (got {scene.start_seconds}s)"
                    )
            else:
                if abs(scene.start_seconds - prev_end) > 1e-3:
                    raise ValueError(
                        f"Scene {scene.scene_id} start ({scene.start_seconds}s) does not match previous end ({prev_end}s)"
                    )

            prev_end = scene.end_seconds

        last_scene = self.scenes[-1]
        if abs(last_scene.end_seconds - self.total_duration_seconds) > 1e-3:
            raise ValueError(
                f"Total duration ({self.total_duration_seconds}s) does not match final scene end ({last_scene.end_seconds}s)"
            )

        return self
