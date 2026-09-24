from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "invoice-service"
    service_version: str = "0.1.0"
    api_prefix: str = "/api/invoices"
    log_level: str = "INFO"
    app_timezone: str = "Asia/Kolkata"

    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "msme"
    db_user: str = "invoice_svc"
    db_password: SecretStr = SecretStr("")
    db_schema: str = "invoices"

    uploads_dir: str = "/data/uploads/invoices"
    invoice_at_risk_days: int = 5

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
