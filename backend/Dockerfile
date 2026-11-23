# syntax=docker/dockerfile:1
# Idea Hub backend (FastAPI). Build context: backend/
#   docker build -t ideahub-api backend/

FROM python:3.11-slim AS builder

# uv binary from the official image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

# Dependencies first (cached unless pyproject/uv.lock change).
# README.md is required because pyproject.toml declares it as the package readme.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Then the application itself.
COPY app ./app
RUN uv sync --frozen --no-dev


FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    UPLOAD_DIR=/data/uploads

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data/uploads \
    && chown -R appuser /data

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/app ./app
# Alembic is a runtime dependency: migrations run from this same image.
COPY alembic.ini ./
COPY alembic ./alembic

USER appuser

# Cloud Run injects PORT (default 8080); fall back to 8000 for local use.
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
