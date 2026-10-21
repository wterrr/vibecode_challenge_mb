"""Configuration settings for LearnFlow AI."""

from typing import Literal
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def is_real_gemini_key(key: str | None) -> bool:
    """Check if key looks like a real API key rather than a dummy placeholder."""
    if not key:
        return False
    k = key.strip()
    if len(k) < 10:
        return False
    if k.upper() in {
        "MY_GEMINI_API_KEY",
        "YOUR_API_KEY",
        "YOUR_GEMINI_API_KEY",
        "PLACEHOLDER",
        "NONE",
        "DUMMY",
        "TEST_KEY",
    }:
        return False
    if k.startswith("MY_") or k.startswith("YOUR_") or k.startswith("change_me") or k == "demo":
        return False
    return True


class Settings(BaseSettings):
    """Application settings with validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)

    pipeline_mode: Literal["real", "demo", "fake"] = Field(
        default="real",
        validation_alias=AliasChoices("LEARNFLOW_PIPELINE_MODE", "pipeline_mode"),
    )

    database_url: str = Field(
        default="",
        validation_alias=AliasChoices(
            "DATABASE_URL",
            "LEARNFLOW_DATABASE_URL",
            "database_url",
        ),
    )
    db_path: str = Field(
        default="learnflow.db",
        validation_alias=AliasChoices("LEARNFLOW_DB_PATH", "db_path"),
    )
    artifacts_dir: str = Field(
        default="artifacts",
        validation_alias=AliasChoices("ARTIFACTS_DIR", "artifacts_dir"),
    )

    gemini_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "GEMINI_API_KEY",
            "gemini_api_key",
            "GOOGLE_API_KEY",
            "GOOGLE_GENAI_API_KEY",
        ),
    )
    gemini_planner_model: str = "gemini-3.8-flash"
    gemini_image_model: str = "gemini-3.1-flash-image"
    gemini_tts_model: str = "gemini-3.1-flash-tts-preview"

    # Private production planning defaults to the pinned, paid OpenRouter model.
    # Explicit PLANNER_PROVIDER=gemini remains available for non-production uses.
    planner_provider: Literal["gemini", "openrouter"] = "openrouter"
    openrouter_planner_model: str = "openai/gpt-6-luna"
    paid_planner_max_tokens: int = Field(default=12000, ge=3000, le=16000)
    # Opt-in: adds one paid function-calling POST per requested lesson.
    # Disabled unless an isolated Code2Video worker is explicitly configured.
    code2video_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("LEARNFLOW_CODE2VIDEO_ENABLED", "code2video_enabled"),
    )
    code2video_worker_url: str = Field(
        default="",
        validation_alias=AliasChoices("LEARNFLOW_CODE2VIDEO_WORKER_URL","code2video_worker_url"),
    )
    code2video_worker_token: str = Field(
        default="",
        validation_alias=AliasChoices("LEARNFLOW_CODE2VIDEO_WORKER_TOKEN","code2video_worker_token"),
    )
    agentic_visual_tools: bool = Field(
        default=False,
        validation_alias=AliasChoices("LEARNFLOW_AGENTIC_VISUAL_TOOLS", "agentic_visual_tools"),
    )
    auth_enabled: bool = False
    admin_username: str = "admin"
    admin_password: str = Field(default="", repr=False)
    auth_secret_key: str = Field(default="", repr=False)
    public_origin: str = ""
    daily_paid_job_limit: int = Field(default=10, ge=1, le=100)

    speech_provider: Literal["edge", "gemini"] = "edge"
    image_provider: Literal["none", "gemini"] = "none"

    tts_voice_vi: str = "vi-VN-NamMinhNeural"
    tts_voice_en: str = "en-US-GuyNeural"

    render_profile: Literal["production", "test"] = "production"
    enable_image_generation: bool = False
    # V3-18: local, non-publishing developer preview only; DEFAULT OFF.
    # Explicit second gate for locally narrated V3 lessons; default OFF.
    # V3-20: separately pronounced/physically measured semantic event preview.
    v3_event_alignment_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "LEARNFLOW_V3_EVENT_ALIGNMENT", "v3_event_alignment_enabled"
        ),
    )
    v3_narrated_lesson_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "LEARNFLOW_V3_NARRATED_LESSON", "v3_narrated_lesson_enabled"
        ),
    )
    v3_binary_preview_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "LEARNFLOW_V3_BINARY_PREVIEW", "v3_binary_preview_enabled"
        ),
    )
    # V3-95: isolated, explicitly consented local paid GPT preview; default OFF.
    v3_gpt_array_preview_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "LEARNFLOW_V3_GPT_ARRAY_PREVIEW", "v3_gpt_array_preview_enabled"
        ),
    )
    openrouter_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("OPENROUTER_API_KEY", "openrouter_api_key"),
    )

    def __repr__(self) -> str:
        data = self.model_dump()
        if data.get("admin_password"):
            data["admin_password"] = "***REDACTED***"
        if data.get("auth_secret_key"):
            data["auth_secret_key"] = "***REDACTED***"
        if data.get("gemini_api_key"):
            data["gemini_api_key"] = "***REDACTED***"
        if data.get("openrouter_api_key"):
            data["openrouter_api_key"] = "***REDACTED***"
        if data.get("code2video_worker_token"):
            data["code2video_worker_token"] = "***REDACTED***"
        if data.get("database_url"):
            data["database_url"] = "***REDACTED***"
        return f"Settings({data})"

    def __str__(self) -> str:
        return self.__repr__()


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
