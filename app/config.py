"""Application configuration loaded from environment variables and .env file."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for EvenG2-to-Gem-BYOA proxy."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Client-to-Bridge Security
    PROXY_API_KEY: str = Field(
        default="",
        description="Shared secret token required in Authorization: Bearer <token>",
    )

    # Gemini settings
    GEMINI_API_KEY: str = Field(
        default="",
        description="Google AI Studio API Key",
    )
    GEMINI_MODEL: str = "gemini-2.5-flash"
    MOCK_GEMINI: bool = False

    # HUD Tuning
    HUD_MAX_CHARACTERS: int = 300
    HUD_SYSTEM_PROMPT: str = (
        "You are an AI assistant displayed on Even Realities G2 smart glasses. "
        "Keep your responses extremely concise (1 to 3 short sentences maximum). "
        "Respond in plain text only. Never use markdown formatting, bullet points, "
        "asterisks, headers, or bold text."
    )


settings = Settings()
