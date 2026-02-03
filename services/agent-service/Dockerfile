# Multi-stage build for Agent Service
# Production-ready Dockerfile with security best practices

# Build stage
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Security: Create non-root user
RUN groupadd -r opsai && useradd -r -g opsai -s /bin/false opsai

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY app/ ./app/
COPY models/ ./models/
COPY db/ ./db/

# Create necessary directories
RUN mkdir -p /app/logs /app/skills /app/data && \
    chown -R opsai:opsai /app

# Security: Set proper permissions
RUN chmod -R 755 /app && \
    chmod -R 777 /app/logs /app/data

# Switch to non-root user
USER opsai

# Expose port
EXPOSE 8006

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8006/health || exit 1

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SERVICE_PORT=8006 \
    SERVICE_NAME=agent-service

# Labels
LABEL maintainer="opsai-team" \
      service="agent-service" \
      version="1.0.0" \
      description="AI-powered agents for infrastructure management"

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006", "--workers", "4"]

# Development stage (for local development)
FROM production as development

# Switch back to root for development
USER root

# Install development dependencies
RUN pip install --no-cache-dir pytest pytest-asyncio black ruff mypy

# Enable hot reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006", "--reload"]
