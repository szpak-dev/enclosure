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

After changing its source, build the static files before starting Django or building the image:

```sh
cd browser
npm ci
npm run typecheck
npm run build
```

The built files live in the Django browser adapter's static directory. The production image runs `collectstatic`, and WhiteNoise serves the manifest-versioned assets.

## Isolated scaffolding API

The container runtime reuses the existing PostgreSQL state; it does not create
or own a database service or volume. It reuses the host `DATABASE_URL` already
in the ignored `.env` file. Compose overrides only its network address to
`postgres:5432` because the API joins the external
`modwire-records_default` Docker network. The host configuration remains on
`localhost:5433`; credentials have one source of truth.

Released runtime images are pulled from GHCR. The default is `latest`; pin the
service to one immutable release with `ENCLOSURE_RUNTIME_VERSION`, for example:

```sh
ENCLOSURE_RUNTIME_VERSION=0.2.1 make runtime-up
```

The packages are private. Authenticate GitHub CLI once with `read:packages`;
runtime commands then use its token through a temporary Docker configuration
that is deleted immediately after the pull:

```sh
gh auth refresh -h github.com -s read:packages
```

Each GitHub release publishes `linux/amd64` and `linux/arm64` variants of
`ghcr.io/szpak-dev/enclosure-runtime`. Docker selects the matching image on
Intel Linux, Intel macOS, or Apple Silicon macOS hosts. Local image builds are
an explicit development mode and never occur during normal installation:

```sh
make runtime-build-up
```

Validate and start only the API:

```sh
make runtime-config
make runtime-up
curl --fail http://127.0.0.1:8100/health/
```

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

`make runtime-down` removes the API container only. The external PostgreSQL
container, network, and `modwire-records_postgres_data` volume are untouched.

For non-container development, keep using the host `DATABASE_URL` (currently
the host-side PostgreSQL port) with the original `uv run` commands above. Its
default HTTP port remains `8000`, separate from the container runtime on
`8100`.

## API

The auth-free API entry point is `GET /api/`. Mutating record endpoints use
`X-Actor-Id` and `X-Actor-Type` for attribution; actor types are `user` and
`agent`.
