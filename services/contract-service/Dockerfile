FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    RUFF_CACHE_DIR=/tmp/.ruff_cache \
    PORT=8001

WORKDIR /app

# Dependencies first, for layer caching. Dev tools (pytest, ruff) are included so tests
# can run inside the container: this is a POC image, not a production one.
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-install-project

COPY . .

RUN useradd --system --uid 10001 app \
    && mkdir -p /data/uploads \
    && chown app /data/uploads
USER app

EXPOSE 8001
CMD ["sh", "./entrypoint.sh"]
