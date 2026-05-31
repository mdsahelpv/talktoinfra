FROM python:3.12-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    dnsutils iputils-ping ssh && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY shared/ ./shared/
COPY agent/ ./agent/
RUN pip install --no-cache-dir ./shared && pip install --no-cache-dir ./agent

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    dnsutils iputils-ping ssh openssh-client && rm -rf /var/lib/apt/lists/*
RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
RUN mkdir -p /app/data && chown -R app:app /app
USER app
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD kill -0 1 || exit 1
CMD ["python", "-m", "src.main"]
