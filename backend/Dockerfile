# Backend-only image used for Phase 1.
# Frontend sources remain in the repository for reference but are not part of
# the assessed runtime artifact.

# ---- Stage 1: Install Python dependencies ----
FROM python:3.11-slim AS python-builder
WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ---- Stage 2: Production runtime ----
FROM python:3.11-slim AS production
WORKDIR /app

# Copy installed Python virtualenv from builder
COPY --from=python-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Copy only runtime-owned backend files. Documentation, tests and the optional
# frontend client never enter the Phase 1 image.
COPY backend/src ./src
COPY static ./static

# Security: Create non-root user & ensure directory permissions
RUN useradd -m appuser && \
    mkdir -p /app/data /app/static && \
    chown -R appuser:appuser /app

USER appuser

# Render dynamically binds $PORT (default 8000)
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request, os; port = os.environ.get('PORT', '8000'); urllib.request.urlopen(f'http://localhost:{port}/health')" || exit 1

# Launch Uvicorn with dynamic $PORT support
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
