# Dockerfile for Cloud Run
FROM python:3.11-slim

# system deps for google clients
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy lockfile and pyproject.toml
COPY pyproject.toml uv.lock /app/

# Install dependencies via uv
# --frozen: use uv.lock
# --no-dev: exclude dev dependencies
RUN uv sync --frozen --no-dev

# Place the virtualenv in the path
ENV PATH="/app/.venv/bin:$PATH"

COPY . /app

# Use gunicorn for production
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 120 app:app
