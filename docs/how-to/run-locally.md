# Run Enclosure locally

Install the locked Python environment, migrate the configured database, and start
the ASGI development server. Without `DATABASE_URL`, this path uses SQLite,
which cannot execute the `pgvector` queries used by semantic record search and
guidance ranking. Disable embeddings for that limited local mode:

```console
uv sync --locked
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput
RECORDS_EMBEDDINGS_ENABLED=0 make mcp
```

Use PostgreSQL with `pgvector` when semantic record search and guidance ranking
are required. With embeddings disabled, applicable optional guidance retains
project-scope order.

`make mcp` runs Django's system check and starts Uvicorn with reload on
`127.0.0.1:8000`. When only the conventional Django development server is
needed in SQLite mode, use `RECORDS_EMBEDDINGS_ENABLED=0 make dev`. Plain
`make dev` retains the configured database and embedding settings.

Verify the two distinct health surfaces:

```console
curl --fail http://127.0.0.1:8000/health/
curl --fail http://127.0.0.1:8000/api/
```

`/health/` is application liveness. Project health is evaluated through
`check_project_health` for one registered workspace and carries architecture and
guidance evidence.

The local interfaces are listed in the [interface reference](../reference/interfaces.md).
