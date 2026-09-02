# Enclosure

Enclosure gives coding agents the context and guardrails they need to work
confidently across projects. It combines reusable project guidance,
architecture checks, diagrams, and scaffolding behind REST, Siren, and MCP.

## Highlights

- Agent-ready workspace guidance and project-health checks
- Architecture contracts backed by Modwire and Mermaiden
- Reusable records and project scaffolding
- A Siren browser for exploring resources and actions
- One machine-wide MCP server for every local project

## Quick start

```sh
uv sync
uv run python manage.py migrate
make mcp
```

The local stack runs on `127.0.0.1:8000`:

| Interface | URL |
| --- | --- |
| Siren browser | `http://127.0.0.1:8000/` |
| REST API | `http://127.0.0.1:8000/api/` |
| Siren API | `http://127.0.0.1:8000/siren/` |
| MCP | `http://127.0.0.1:8000/mcp` |

Use `make dev` when only the standard Django development server is needed.

## Development

Run the complete verification suite before handoff:

```sh
make ci
```

After changing the TypeScript browser, rebuild its checked-in static assets:

```sh
make browser-build
```

Hard-refresh the browser after rebuilding to discard a cached bundle.

## Machine-wide MCP server

The Compose runtime exposes MCP at `http://127.0.0.1:8666/mcp` and keeps the
server running as `enclosure-mcp`. Configure `.env` as needed:

- `ENCLOSURE_IMAGE` selects `latest` or an exact immutable release tag.
- `ENCLOSURE_PROJECTS_DIR` selects the host projects directory mounted into
  the container at the same absolute path.

Start or update the runtime:

```sh
make runtime-config
make runtime-up
curl --fail http://127.0.0.1:8666/health/
```

`runtime-up` migrates with the selected image before starting MCP and retains
the previous image locally as `:previous`. Back up PostgreSQL before deploying
potentially irreversible migrations. Use `make runtime-rollback` to restore
the retained image, and `make runtime-down` to remove only the MCP container.

## Releases

GitHub Release tags are canonical. Stable releases publish SemVer, minor,
`latest`, and commit-traceability image tags; prereleases never move `latest`.
Docker Hub publication requires `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` in
the repository configuration.

## API attribution

The API is auth-free. Mutating record requests use `X-Actor-Id` and
`X-Actor-Type`; supported actor types are `user` and `agent`.
