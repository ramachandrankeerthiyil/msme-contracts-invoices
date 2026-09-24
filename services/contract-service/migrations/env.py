import asyncio

from alembic import context
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.service_name, settings.log_level)

# Set to the service's declarative Base.metadata once models exist (INV-001).
target_metadata = None


def _run(connection: Connection) -> None:
    connection.execute(text(f'SET search_path TO "{settings.db_schema}"'))
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=settings.db_schema,
        include_schemas=False,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as connection:
        await connection.run_sync(_run)
        await connection.commit()
    await engine.dispose()


if context.is_offline_mode():
    raise SystemExit("Offline migrations are not supported; run against a database.")

asyncio.run(run_migrations_online())
