# Multi-stage Dockerfile for Python Flask application optimized for Google Cloud Run
FROM python:3.12-alpine AS builder

# Set working directory
WORKDIR /app

# Install build dependencies in single layer
RUN apk add --no-cache \
    gcc \
    g++ \
    make \
    libffi-dev \
    libev-dev \
    binutils

# Copy only production requirements for better caching
COPY requirements-prod.txt .

# Install dependencies — separate RUN so pip failures are never swallowed by || true
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements-prod.txt

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
FROM python:3.12-alpine AS runtime

# Install only essential runtime dependencies (libev, not libev-dev — no headers needed)
RUN apk add --no-cache \
    tini \
    libev

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
    WEB_CONCURRENCY=4

# Copy application code with proper ownership
COPY --chown=appuser:appuser . .

# Create necessary directories and set permissions in single layer
RUN mkdir -p static/swagger static/dist static/css static/typescript templates documentation __pycache__ && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app && \
    # Remove any development files
    rm -rf .git .gitignore .dockerignore .env.example *.md 2>/dev/null || true

# Switch to non-root user
USER appuser

# Expose port (Cloud Run uses PORT env var)
EXPOSE 5000

# Use tini as init system to handle signals properly
ENTRYPOINT ["/sbin/tini", "--"]

# Run with gunicorn optimized for Cloud Run (JSON form avoids shell PATH lookup issues)
CMD ["/opt/venv/bin/gunicorn", \
    "--bind", "0.0.0.0:5000", \
    "--workers", "2", \
    "--worker-class", "gevent", \
    "--worker-connections", "1000", \
    "--max-requests", "1000", \
    "--max-requests-jitter", "100", \
    "--timeout", "120", \
    "--graceful-timeout", "30", \
    "--keep-alive", "5", \
    "--log-level", "info", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "--capture-output", \
    "--enable-stdio-inheritance", \
    "app:app"]