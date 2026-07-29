FROM python:3.12.11-slim-bookworm

LABEL org.opencontainers.image.title="Generation Attribution Protocol" \
      org.opencontainers.image.version="1.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/implementation

RUN groupadd --system --gid 10001 gap \
    && useradd --system --uid 10001 --gid gap --home-dir /app gap

WORKDIR /app
COPY implementation/requirements.txt /tmp/requirements.txt
COPY implementation/requirements-docker.txt /tmp/requirements-docker.txt
RUN pip install --no-cache-dir --requirement /tmp/requirements-docker.txt

COPY --chown=gap:gap implementation/app implementation/app
COPY --chown=gap:gap scripts scripts
COPY --chown=gap:gap docker/entrypoint.sh /usr/local/bin/gap-entrypoint
RUN chmod 0555 /usr/local/bin/gap-entrypoint \
    && mkdir -p /data/runtime /data/backups /keys \
    && chown -R gap:gap /data

USER 10001:10001
EXPOSE 8000
VOLUME ["/data/runtime", "/data/backups", "/keys"]
HEALTHCHECK --interval=15s --timeout=3s --start-period=15s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2)"]
ENTRYPOINT ["/usr/local/bin/gap-entrypoint"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
