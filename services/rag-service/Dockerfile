# RAG Service Dockerfile
# Port 8012

# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Production stage
FROM python:3.11-slim AS production

WORKDIR /app

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -s /bin/bash appuser && chown -R appuser:appuser /app

USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8012

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8012/health')" || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8012"]
