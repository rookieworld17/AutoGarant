# syntax=docker/dockerfile:1

# ─── Base image ───────────────────────────────────────────────
FROM python:3.12-slim AS base

# Keep Python lean and predictable inside containers
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ─── Dependencies (cached layer) ──────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── Application code ─────────────────────────────────────────
COPY . .

# Run as non-root user for safety
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

# Apply DB migrations, then start the bot
CMD ["sh", "-c", "alembic upgrade head && python -m app"]
