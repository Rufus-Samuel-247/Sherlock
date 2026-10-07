"""
SHERLOCK Backend — Configuration
Pydantic-based settings loaded from environment variables / .env file.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # ── App ─────────────────────────────────────────────
    APP_NAME: str = "SHERLOCK"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # ── Server ──────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── CORS ────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["*"]

    # ── Data / ML ───────────────────────────────────────
    SYNTHETIC_TXN_COUNT: int = 10_000
    FRAUD_RATIO: float = 0.03
    MODEL_PATH: Optional[str] = None

    # ── WebSocket ───────────────────────────────────────
    WS_BROADCAST_INTERVAL: float = 2.0  # seconds between WS pushes

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()
