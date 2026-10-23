FROM python:3.14-slim AS builder
ENV UV_CACHE_DIR=/tmp/uv-cache UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --no-dev
RUN uv run --no-dev python manage.py collectstatic --noinput --skip-checks

FROM node:24.17.0-slim AS renderer
WORKDIR /opt/enclosure-renderer
COPY package.json package-lock.json ./
RUN PUPPETEER_SKIP_DOWNLOAD=true npm ci

FROM python:3.14-slim AS runtime
ARG ENCLOSURE_RUNTIME_VERSION=0.0.0+dev
ENV PATH="/opt/enclosure-renderer/node_modules/.bin:/app/.venv/bin:$PATH" PUPPETEER_CACHE_DIR="/opt/puppeteer" HOME="/home/enclosure" XDG_CONFIG_HOME="/tmp/.chromium" XDG_CACHE_HOME="/tmp/.chromium" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 VIRTUAL_ENV="/app/.venv" PYTHONPATH="/app/src:/app" ENCLOSURE_RUNTIME_VERSION="$ENCLOSURE_RUNTIME_VERSION"
COPY --from=renderer /usr/local/bin/node /usr/local/bin/node
COPY --from=renderer /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
COPY --from=renderer /opt/enclosure-renderer /opt/enclosure-renderer
WORKDIR /opt/enclosure-renderer
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates dumb-init unzip \
    && npx puppeteer browsers install --install-deps \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 enclosure \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin enclosure \
    && mkdir -p /var/cache/enclosure/health /var/cache/enclosure/modwire \
    && chown -R 10001:10001 /var/cache/enclosure
WORKDIR /app
COPY --chown=10001:10001 --from=builder /app /app
USER enclosure
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health/?format=json', timeout=4).read()"
ENTRYPOINT ["dumb-init", "--"]
CMD ["gunicorn", "enclosure.core.asgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--worker-class", "uvicorn_worker.UvicornWorker", "--access-logfile", "-", "--error-logfile", "-"]
