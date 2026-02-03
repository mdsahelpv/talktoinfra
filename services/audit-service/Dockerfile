FROM talkai-python-base:latest

WORKDIR /app

# Create directories for logs
RUN mkdir -p /data/audit-logs /data/exports && chown -R appuser:appuser /data

# Install service-specific dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set permissions
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8005

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8005/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005", "--reload"]
