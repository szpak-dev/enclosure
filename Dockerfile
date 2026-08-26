FROM python:3.14-slim AS builder
ENV UV_CACHE_DIR=/tmp/uv-cache UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --no-dev
RUN uv run --no-dev python manage.py collectstatic --noinput --skip-checks

FROM python:3.14-slim AS runtime
ARG ENCLOSURE_RUNTIME_VERSION=0.0.0+dev
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 VIRTUAL_ENV="/app/.venv" PYTHONPATH="/app/src:/app" ENCLOSURE_RUNTIME_VERSION="$ENCLOSURE_RUNTIME_VERSION"
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends dumb-init nodejs \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app /app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health/?format=json', timeout=4).read()"
ENTRYPOINT ["dumb-init", "--"]
CMD ["gunicorn", "enclosure.core.asgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--worker-class", "uvicorn_worker.UvicornWorker", "--access-logfile", "-", "--error-logfile", "-"]
