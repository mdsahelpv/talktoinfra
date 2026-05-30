FROM python:3.12-slim AS builder
WORKDIR /build
COPY shared/ ./shared/
COPY cli/ ./cli/
RUN pip install --no-cache-dir ./shared && pip install --no-cache-dir ./cli

FROM python:3.12-slim
RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
USER app
ENTRYPOINT ["talktoinfra"]
CMD ["--help"]
