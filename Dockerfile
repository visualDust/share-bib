# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Final image
FROM python:3.13-slim

# Install Caddy and supervisor
RUN apt-get update && \
    apt-get install -y --no-install-recommends caddy supervisor && \
    rm -rf /var/lib/apt/lists/*

# Backend
WORKDIR /app/backend
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/ .
# Verify venv works
RUN .venv/bin/python -c "import uvicorn; print('ok')"

# Frontend static files
COPY --from=frontend-build /app/dist /srv

# Caddy config (single-container version, proxies to localhost)
COPY docker/Caddyfile /etc/caddy/Caddyfile

# Supervisor config
COPY docker/supervisord.conf /etc/supervisor/conf.d/app.conf

# Data directory
RUN mkdir -p /data

EXPOSE 80
VOLUME /data

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/app.conf"]
