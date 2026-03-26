# Multi-stage Dockerfile for Python Flask application optimized for Google Cloud Run
FROM python:3.12-alpine3.21 AS builder

# Set working directory
WORKDIR /app

# Install build dependencies in single layer
RUN apk add --no-cache build-base \
    && apk add --no-cache \
    gcc \
    g++ \
    make \
    libffi-dev \
    binutils

# Copy only production requirements for better caching
COPY requirements-prod.txt .

# Install dependencies — separate RUN so pip failures are never swallowed by || true
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install --no-cache-dir --no-compile -r requirements-prod.txt && \
    rm -rf /opt/venv/lib/python3.12/site-packages/pip* /opt/venv/lib/python3.12/site-packages/setuptools* /opt/venv/lib/python3.12/site-packages/wheel* && \
    rm -f /opt/venv/bin/pip /opt/venv/bin/pip3 /opt/venv/bin/pip3.12

# Strip and clean in a separate layer (|| true is safe here — these are best-effort)
RUN find /opt/venv -name "*.so" -exec strip --strip-all {} + 2>/dev/null || true && \
    find /opt/venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type d -name "test" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type d -name "docs" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type d -name "doc" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -name "*.pyc" -delete 2>/dev/null || true && \
    find /opt/venv -name "*.pyo" -delete 2>/dev/null || true && \
    find /opt/venv -name "*.pyi" -delete 2>/dev/null || true

# ============================================
# Stage 2: Runtime - Minimal production image
# ============================================
FROM python:3.12-alpine3.21 AS runtime

# Install Redis, supervisord (process manager), and tini
# redis-server is ~1MB on Alpine — acceptable for a cache sidecar
RUN apk add --no-cache \
    tini \
    redis \
    supervisor

# Create non-root user for security
RUN addgroup -S appuser && adduser -S -G appuser -u 1001 appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables for production
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PYTHONHASHSEED=random \
    FLASK_APP=app.py \
    FLASK_ENV=production \
    PORT=5000 \
    MODE=production \
    WEB_CONCURRENCY=4 \
    REDIS_HOST=localhost \
    REDIS_PORT=6379 \
    REDIS_DB=0

# Pre-create directories with correct ownership BEFORE COPY to avoid a
# redundant chown/chmod pass over all copied files (which doubles layer size).
RUN mkdir -p static/swagger static/dist static/css static/typescript templates documentation __pycache__ && \
    chown -R appuser:appuser /app

# Copy application code with proper ownership — --chown sets ownership in one pass,
# no follow-up chown/chmod needed so files are only written to a single layer.
COPY --chown=appuser:appuser . .

# Copy supervisord config
COPY --chown=appuser:appuser supervisord.conf /etc/supervisord.conf

# Remove development files without touching other files (avoids copy-on-write cost)
RUN rm -rf .git .gitignore .dockerignore .env.example *.md 2>/dev/null || true

# Switch to non-root user
USER appuser

# Expose port (Cloud Run uses PORT env var)
EXPOSE 5000

# tini reaps zombies and forwards signals to supervisord
# supervisord then manages both redis-server and gunicorn
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]