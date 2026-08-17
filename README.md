# enclosure

Django API scaffold with JSON logs, dotenv settings, health checks, and auto-discovered Django Ninja Extra controllers.

```sh
uv sync
uv run python manage.py migrate
make dev
```

`make dev` keeps the standard Django development server. To run the complete
local ASGI stack with automatic reload, use:

```sh
make mcp
```

This serves the Siren browser at `/`, REST at `/api`, Siren at `/siren`, and
the MCP Streamable HTTP endpoint at `/mcp`, all on `127.0.0.1:8000`. Local
static files are served automatically when Django debug mode is enabled; no
development `collectstatic` step is required.

## Siren browser

The TypeScript Siren browser is available at `GET /`. It starts from `/siren/`, follows advertised links, and renders forms for advertised actions.

After changing its source, rebuild the static files deterministically from the repository root before starting Django or building the image:

```sh
make browser-build
```

Restarting Django does not rebuild or invalidate the browser bundle. After the
build finishes, hard-refresh the open page (`Cmd+Shift+R` on macOS or
`Ctrl+Shift+R` elsewhere) to replace a cached `browser.js`.

The built files live in the Django browser adapter's static directory. The production image runs `collectstatic`, and WhiteNoise serves the manifest-versioned assets.

## Machine-wide MCP server

This repository owns the Compose definition for the machine-wide Enclosure
server. Compose builds `enclosure:mcp`, runs it as `enclosure-mcp`, and restarts
it automatically with Docker. The existing `resumed-db` PostgreSQL container
continues to own the database and its data; Enclosure only joins its external
`resumed-api_default` network.

The host Projects directory is mounted read/write at the same absolute path in
the container. This preserves discovered project paths and allows Enclosure to
generate files in any project. Set `ENCLOSURE_PROJECTS_DIR` in `.env` if the
Projects directory is somewhere other than `/Users/gorky/Projects`.

Validate, build, and start the server:

```sh
make runtime-config
make runtime-up
curl --fail http://127.0.0.1:8666/health/
```

The Streamable HTTP MCP endpoint is available to every local project at
`http://127.0.0.1:8666/mcp`.

Container startup never applies migrations. Before a migration, create a
PostgreSQL backup and capture the exact Django migration plan:

```sh
make runtime-db-prepare
```

Review both paths printed by that command. Apply the reviewed plan only by
passing those same artifacts through the guarded command:

```sh
CONFIRM_EXISTING_DATABASE_MIGRATION=reviewed \
MODWIRE_DATABASE_BACKUP=.dev/database-safety/modwire-records-TIMESTAMP.dump \
MODWIRE_DATABASE_MIGRATION_PLAN=.dev/database-safety/migration-plan-TIMESTAMP.txt \
make runtime-db-migrate
```

`make runtime-down` removes only `enclosure-mcp`. The external `resumed-db`
container, its network, and its bind-mounted PostgreSQL data are untouched.

For non-container development, keep using the host `DATABASE_URL` (currently
port 5432) with the original `uv run` commands above. Its
default HTTP port remains `8000`, separate from the container runtime on
`8666`.

## API

The auth-free API entry point is `GET /api/`. Mutating record endpoints use
`X-Actor-Id` and `X-Actor-Type` for attribution; actor types are `user` and
`agent`.
