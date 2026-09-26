FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    RUFF_CACHE_DIR=/tmp/.ruff_cache \
    PORT=8003

WORKDIR /app

# Dependencies first, for layer caching. Dev tools (pytest, ruff) are included so tests
# can run inside the container: this is a POC image, not a production one.
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-install-project

COPY . .

RUN useradd --system --uid 10001 app
USER app

EXPOSE 8003
# No database, so no migrations: start the API directly.
CMD ["sh", "-c", "exec python -m uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT} --no-access-log --proxy-headers"]
