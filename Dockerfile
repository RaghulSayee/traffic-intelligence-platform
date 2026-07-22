FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /build/frontend

COPY frontend/package.json frontend/package-lock.json ./

RUN npm ci

COPY frontend/ ./

RUN mkdir -p public

ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_API_BASE_URL=/api/v1
ENV BACKEND_API_BASE_URL=http://127.0.0.1:8000/api/v1

RUN npm run build


FROM node:22-bookworm-slim AS runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PYTHONUNBUFFERED=1
ENV UV_PYTHON=3.12
ENV UV_LINK_MODE=copy

RUN apt-get update \
    && apt-get install -y \
        --no-install-recommends \
        ca-certificates \
        curl \
        ffmpeg \
        gettext-base \
        libgomp1 \
        nginx \
        tini \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest \
    /uv \
    /uvx \
    /usr/local/bin/

WORKDIR /app/backend

COPY backend/pyproject.toml backend/uv.lock ./

RUN uv python install 3.12 \
    && uv sync \
        --frozen \
        --no-dev \
        --no-install-project

COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./
COPY backend/scripts ./scripts

WORKDIR /app/frontend

COPY --from=frontend-builder \
    /build/frontend/.next/standalone \
    ./

COPY --from=frontend-builder \
    /build/frontend/.next/static \
    ./.next/static

COPY --from=frontend-builder \
    /build/frontend/public \
    ./public

WORKDIR /app

COPY deploy ./deploy

RUN chmod +x \
    /app/deploy/start-production.sh

EXPOSE 10000

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["/app/deploy/start-production.sh"]
