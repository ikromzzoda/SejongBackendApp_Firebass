# ── Stage 1: dependencies ────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy project source (credentials excluded via .dockerignore)
COPY . .

# Expose the port Cloud Run uses
EXPOSE 8080

# On startup:
#   1. collectstatic — needs credentials mounted (Cloud Run secret)
#   2. gunicorn     — 2 workers × 8 threads = handles concurrent requests well
CMD exec gunicorn \
      --bind 0.0.0.0:$PORT \
      --workers 2 \
      --threads 8 \
      --timeout 120 \
      --access-logfile - \
      config.wsgi:application
