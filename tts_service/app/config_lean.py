"""Lean configuration for TTS API proxy service."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class LeanSettings(BaseSettings):
    """Lean settings for TTS API proxy service."""

    # Server configuration
    tts_host: str = "0.0.0.0"
    tts_port: int = 8000
    tts_workers: int = 1

    # Remote TTS service configuration
    tts_remote_url: str = ""  # Remote index-tts-vllm service URL
    tts_api_key: str = ""     # Optional API key for remote service

    # Proxy behavior
    strict_duration: bool = False
    max_retries: int = 3
    retry_delay_seconds: float = 2.0
    request_timeout_seconds: float = 30.0

    # Audio settings
    default_sample_rate: int = 22050
    default_format: str = "wav"

    # Concurrency settings
    max_concurrent_requests: int = 20  # Higher for proxy mode

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Lean settings instance
lean_settings = LeanSettings()