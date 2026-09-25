from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "contract-service"
    service_version: str = "0.1.0"
    api_prefix: str = "/api/contracts"
    log_level: str = "INFO"
    app_timezone: str = "Asia/Kolkata"

    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "msme"
    db_user: str = "contract_svc"
    db_password: SecretStr = SecretStr("")
    db_schema: str = "contracts"

    uploads_dir: str = "/data/uploads/contracts"
    contract_at_risk_days: int = 3

    anthropic_api_key: SecretStr = SecretStr("")
    contract_llm_model: str = "claude-sonnet-5"
    contract_llm_effort: Literal["low", "medium", "high", "xhigh", "max"] = "high"
    # "claude" in real use; "fake" gives deterministic results without the API (tests, e2e).
    contract_extractor: Literal["claude", "fake"] = "claude"
    # How many contracts are read at the same time.
    contract_max_concurrent: int = 2

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+asyncpg",
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
