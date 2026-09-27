"""
app/config.py
=============
Centralised, type-safe configuration powered by pydantic-settings.

pydantic-settings reads values from (in priority order):
  1. Environment variables
  2. A .env file in the working directory (loaded via python-dotenv)

A missing SERPAPI_KEY will raise a ValidationError at import time,
which surfaces a clear error message rather than a silent KeyError later.

Usage
-----
    from app.config import settings
    api_key = settings.SERPAPI_KEY
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-level settings loaded from the environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # SERPAPI_KEY == serpapi_key
        extra="ignore",        # Ignore any extra env vars silently
    )

    SERPAPI_KEY: str
    """SerpApi API key — required.  Get yours at https://serpapi.com/manage-api-key"""


# Module-level singleton — import this throughout the application.
settings = Settings()  # type: ignore[call-arg]
