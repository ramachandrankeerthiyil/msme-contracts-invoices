from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "assistant-service"
    service_version: str = "0.1.0"
    api_prefix: str = "/api/assistant"
    log_level: str = "INFO"
    app_timezone: str = "Asia/Kolkata"

    # The services the assistant looks things up in (read-only, internal network).
    invoice_api_url: str = "http://invoice-service:8002"
    contract_api_url: str = "http://contract-service:8001"
    lookup_timeout_seconds: float = 15.0

    anthropic_api_key: SecretStr = SecretStr("")
    # "claude" in real use; "fake" answers deterministically without the API (tests, e2e).
    assistant_llm: Literal["claude", "fake"] = "claude"
    assistant_llm_model: str = "claude-sonnet-5"
    assistant_llm_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    # The small, fast model that checks every question before the main one (AST-002, ADR-0005).
    assistant_guard_model: str = "claude-haiku-4-5-20251001"
    # The at-risk windows, from the same variables the invoice and contract services use, so the
    # app guide and instructions never state an outdated number (AST-002 AC8).
    invoice_at_risk_days: int = 5
    contract_at_risk_days: int = 3
    # Seconds between words from the fake model, so "Stop" can be exercised in e2e runs.
    fake_word_delay: float = 0.03

    max_lookups: int = 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
