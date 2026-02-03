FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (shared across all Python services)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install common Python dependencies (shared by 6+ services)
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    pydantic==2.5.2 \
    pydantic-settings==2.1.0 \
    structlog==23.2.0 \
    httpx==0.25.2 \
    python-jose[cryptography]==3.3.0

# Create non-root user
RUN useradd -m -u 1000 appuser

# Set environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
