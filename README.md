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
server. GitHub Actions builds a multi-platform immutable image for each GitHub
Release and publishes it to Docker Hub. Compose pulls the configured image,
runs it as `enclosure-mcp`, and restarts it automatically with Docker. The
existing `resumed-db` PostgreSQL container continues to own the database and
its data; Enclosure only joins its external `resumed-api_default` network.

The host Projects directory is mounted read/write at the same absolute path in
the container. This preserves discovered project paths and allows Enclosure to
generate files in any project. Set `ENCLOSURE_PROJECTS_DIR` in `.env` if the
Projects directory is somewhere other than `/Users/gorky/Projects`.

Set `ENCLOSURE_IMAGE` in `.env` to
`docker.io/9orky/enclosure:latest` to follow the most recent stable release.
`make runtime-up` retains the prior image locally as `:previous`, so the
previous release remains available while older Enclosure tags and dangling
images are pruned. Set an exact SemVer tag instead (for example
`docker.io/9orky/enclosure:1.2.3`) when a deployment must remain pinned.

Validate, pull, and start the server:

```sh
make runtime-config
make runtime-up
curl --fail http://127.0.0.1:8666/health/
```

The Streamable HTTP MCP endpoint is available to every local project at
`http://127.0.0.1:8666/mcp`.

### MCP application boundary

`enclosure.mcp` owns MCP protocol lifecycle, tool exposure, and agent-facing
presentation. REST and Siren remain the authority for authorization, operation
dispatch, and domain decisions; MCP consumes their results and does not import
project services to recompute them. Operation-specific Markdown and compact
receipts are package Jinja templates rendered by the injectable
`enclosure.shared.TemplateService`, so other applications can use the same
renderer without duplicating Jinja configuration.

`get_workspace_context` emits the packaged agent bootstrap once, before the
ordered project guidance. Its receipt keeps operational facts and counts while
the Markdown retains guidance, checks, omissions, diagnostics, readiness, and
mandatory or optional classification supplied by REST. `check_project_health`
separates healthy, gating-failure, and advisory results and includes affected
targets and next actions. Agent presentations are limited to 16 KiB of text and
8 KiB of structured content; an oversized result fails explicitly as
`presentation_budget_exceeded` instead of truncating guidance.

Run the complete local verification contract before handoff:

```sh
make ci
```

Container startup itself never applies migrations. Instead, `make runtime-up`
pulls the configured image, runs its one-off `migrate` service against the
local `resumed-db` container, and starts the MCP service only when migration
succeeds. The migration and runtime therefore always use the same immutable
image tag. Take a PostgreSQL backup before running `make runtime-up` when a
migration is potentially irreversible.

`make runtime-down` removes only `enclosure-mcp`. The external `resumed-db`
container, its network, and its bind-mounted PostgreSQL data are untouched.

### Releases and image versions

The GitHub Release tag is the canonical version. A stable release such as
`v1.2.3` publishes `1.2.3`, `1.2`, `latest`, and a traceability tag beginning
with `sha-`; a prerelease never moves `latest`. The release workflow delegates
the build, metadata, Docker Hub publication, SBOM, and provenance attestation
to a reusable workflow. Before publishing, configure the repository variable
`DOCKERHUB_USERNAME` and the repository secret `DOCKERHUB_TOKEN` (a Docker Hub
access token with permission to push the public repository).

For development, continue using `make dev` or `make mcp`: both execute the
checked-out source directly and are intentionally separate from the immutable
runtime-image path.

For non-container development, keep using the host `DATABASE_URL` (currently
port 5432) with the original `uv run` commands above. Its
default HTTP port remains `8000`, separate from the container runtime on
`8666`.

## API

The auth-free API entry point is `GET /api/`. Mutating record endpoints use
`X-Actor-Id` and `X-Actor-Type` for attribution; actor types are `user` and
`agent`.
