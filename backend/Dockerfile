# Backend-only image for Phase 1. Build from the repository root:
#   docker build -f backend/Dockerfile -t vinfast-showroom-backend .
# The frontend client is not part of the assessed runtime artifact.

# ---- Stage 1: install locked Python dependencies ----
FROM python:3.11-slim AS python-builder
WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

COPY backend/requirements.txt backend/constraints.txt ./
RUN pip install -r requirements.txt -c constraints.txt

# ---- Stage 2: production runtime ----
FROM python:3.11-slim AS production
WORKDIR /app

COPY --from=python-builder /opt/venv /opt/venv

# Every runtime path is explicit. The code never derives locations from its own
# file path, which used to resolve to "/" inside this image.
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    DATABASE_URL=sqlite+aiosqlite:////app/data/vinfast.db \
    STATIC_DIR=/app/static \
    SEED_DATA_DIR=/app/seed/catalog \
    FRONTEND_DIST_DIR=/app/no-frontend

RUN useradd --create-home --uid 10001 appuser

# Runtime-owned files only: application code, reviewable seed data and media.
COPY --chown=appuser:appuser backend/src ./src
COPY --chown=appuser:appuser data/catalog ./seed/catalog
COPY --chown=appuser:appuser static ./static
RUN mkdir -p /app/data && chown appuser:appuser /app/data

USER appuser
VOLUME ["/app/data"]
EXPOSE 8000

# /health returns 503 when the database is unreachable, so urlopen raises and the
# container is reported unhealthy instead of falsely healthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/health', timeout=4)" || exit 1

CMD ["sh", "-c", "exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
