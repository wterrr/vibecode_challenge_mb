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

    planner_provider: Literal["gemini"] = "gemini"
    speech_provider: Literal["edge", "gemini"] = "edge"
    image_provider: Literal["none", "gemini"] = "none"

    tts_voice_vi: str = "vi-VN-NamMinhNeural"
    tts_voice_en: str = "en-US-GuyNeural"

    render_profile: Literal["production", "test"] = "production"
    enable_image_generation: bool = False

    def __repr__(self) -> str:
        data = self.model_dump()
        if data.get("gemini_api_key"):
            data["gemini_api_key"] = "***REDACTED***"
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
