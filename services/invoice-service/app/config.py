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

    # Reminder emails (INV-004, ADR-0004). The defaults point at the local Mailpit sink, so
    # nothing reaches a real client until real SMTP settings are configured.
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_starttls: bool = False
    smtp_from_address: str = "accounts@msme-poc.local"
    reminder_sender_name: str = "Accounts Team"
    smtp_timeout_seconds: float = 10

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
