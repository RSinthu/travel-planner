"""Settings loaded from environment variables and backend/.env."""

import logging
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"
DEFAULT_DATABASE_URL = f"sqlite+aiosqlite:///{(BACKEND_DIR / 'travel_planner.db').as_posix()}"

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "production"] = "development"

    # SQLite works with no setup; use PostgreSQL in production, e.g.
    # postgresql+asyncpg://user:password@localhost:5432/travel_planner
    database_url: str = DEFAULT_DATABASE_URL

    # Tokens from the frontend's Better Auth (EdDSA, verified with its public keys).
    # Empty AUTH_JWKS_URL = only the HS256 tokens below are accepted.
    auth_jwks_url: str = ""  # e.g. http://localhost:3000/api/auth/jwks
    auth_issuer: str = "http://localhost:3000"
    auth_audience: str = "travel-planner-api"

    # HS256 tokens signed with JWT_SECRET: dev tokens, tests, or a trusted gateway.
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_audience: str = "travel-planner"
    dev_token_minutes: int = 12 * 60

    # Comma-separated list of frontend origins allowed to call the API.
    cors_origins: str = "http://localhost:3000"

    # Each planning message costs ~10 Gemini requests, so keep these low on the free tier.
    rate_limit_per_minute: int = 5
    rate_limit_per_day: int = 40
    max_message_chars: int = 2000
    max_llm_calls: int = 30  # per message, across the coordinator and all sub-agents

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @field_validator("database_url")
    @classmethod
    def _default_database(cls, value: str) -> str:
        return value.strip() or DEFAULT_DATABASE_URL  # "DATABASE_URL=" in .env means the default

    @model_validator(mode="after")
    def _check_secret(self) -> "Settings":
        if len(self.jwt_secret) >= 32:
            return self
        if self.app_env == "production":
            if self.auth_jwks_url:  # Better Auth tokens only; HS256 tokens are refused
                self.jwt_secret = ""
                return self
            raise ValueError("Set AUTH_JWKS_URL, or JWT_SECRET (at least 32 characters), in production.")
        # Development: a random secret, so tokens stop working when the server restarts.
        self.jwt_secret = secrets.token_urlsafe(48)
        logger.warning("JWT_SECRET is not set; using a temporary secret for this run.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
