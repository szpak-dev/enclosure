# Run Enclosure locally

Install the locked Python environment, migrate the configured database, and start
the ASGI development server:

```console
uv sync --locked
uv run python manage.py migrate
make mcp
```

`make mcp` runs Django's system check and starts Uvicorn with reload on
`127.0.0.1:8000`. Use `make dev` when only the conventional Django development
server is needed.

Verify the two distinct health surfaces:

```console
curl --fail http://127.0.0.1:8000/health/
curl --fail http://127.0.0.1:8000/api/
```

`/health/` is application liveness. Project health is evaluated through
`check_project_health` for one registered workspace and carries architecture and
guidance evidence.

The local interfaces are listed in the [interface reference](../reference/interfaces.md).
