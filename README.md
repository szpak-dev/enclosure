# Enclosure

> **The faster code is written, the more important it becomes to remember who said yes.**

AI can produce code faster than a team can inspect it. That is not the same as
progress.

Enclosure keeps architectural intent, project guidance, and implementation
evidence connected through one governed loop. It gives coding agents the context
to act, checks whether implementation still honors the accepted promise, and
returns evidence for a human decision.

Mermaiden models intent. Modwire measures implementation. Sirenity exposes
what can happen next. Enclosure governs the agreement between them.

## The first evidence is the system itself

Enclosure, Mermaiden, Modwire, and Sirenity use Enclosure-registered workspace
instructions in their own development. The dated, bounded evidence—and what it
does not prove—is documented in [The gang uses its own machinery](docs/evidence/dogfooding.md).

## What Enclosure governs

Enclosure turns a coding task into a traceable sequence:

1. Resolve the checkout to its registered project.
2. Select the guidance relevant to the task.
3. Keep accepted diagrams and operating contracts authoritative.
4. Check implementation against architecture and project rules.
5. Return evidence for human acceptance.

It does not grant an agent authority merely because the agent can act. It makes
the applicable authority, constraints, and evidence visible at the point of work.

## The three engines

| Engine | Responsibility |
| --- | --- |
| [Mermaiden](https://github.com/szpak-dev/mermaiden) | Models diagram intent as typed, versioned state. |
| [Modwire](https://github.com/szpak-dev/modwire) | Measures implementation against executable architecture rules. |
| [Sirenity](https://github.com/szpak-dev/sirenity) | Exposes response-scoped actions and typed navigation. |
| **Enclosure** | Connects context, agreement, and evidence to a human decision. |

## Start Enclosure

Enclosure requires Python 3.14 and `uv`. Without `DATABASE_URL`, the local quick
start uses SQLite. SQLite supports basic local operation but not the `pgvector`
queries used by semantic record search and guidance ranking, so embeddings must
be disabled in that mode. The complete Compose and production path uses
PostgreSQL with `pgvector`. Node.js is required for browser build and
verification and when project health analyzes TypeScript or JavaScript. Project
health also requires a PHP executable when it analyzes PHP.

```console
uv sync --locked
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput
RECORDS_EMBEDDINGS_ENABLED=0 make mcp
```

The local development stack listens on `127.0.0.1:8000`:

| Interface | URL |
| --- | --- |
| Siren browser | `http://127.0.0.1:8000/` |
| REST API | `http://127.0.0.1:8000/api/` |
| OpenAPI | `http://127.0.0.1:8000/api/openapi.json` |
| Siren API | `http://127.0.0.1:8000/siren/` |
| MCP | `http://127.0.0.1:8000/mcp` |

The [first governed project tutorial](docs/tutorials/first-governed-project.md)
continues from a running instance. Use the
[machine-wide MCP guide](docs/how-to/run-machine-wide-mcp.md) for the persistent
Compose runtime on `127.0.0.1:8666`.

## Documentation

- [Documentation entrance](docs/index.md)
- [Evidence](docs/evidence/index.md)
- [Tutorials](docs/tutorials/index.md)
- [How-to guides](docs/how-to/index.md)
- [Explanation](docs/explanation/index.md)
- [Architecture](docs/architecture/index.md)
- [Technical reference](docs/reference/index.md)

## Development

The complete verification suite requires PostgreSQL 18 with `pgvector` 0.8.2;
SQLite cannot satisfy its semantic-search coverage. After `uv sync --locked`,
start that database, set its URL, and install the browser dependencies and
Playwright Chromium:

```console
export DATABASE_URL=postgres://postgres:postgres@127.0.0.1:5432/postgres
npm --prefix browser ci
(cd browser && npx playwright install --with-deps chromium)
make ci
```

Build the documentation and validate every local link:

```console
make docs-check
```

After changing the TypeScript browser, rebuild its checked-in static assets:

```console
make browser-build
```

Hard-refresh the browser after rebuilding to discard a cached bundle.

## Releases

GitHub Release tags are canonical. Stable releases publish SemVer, minor,
`latest`, and commit-traceability image tags; prereleases never move `latest`.
Docker Hub publication requires `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` in
the repository configuration.

## License

Copyright (c) 2026 Tomasz Szpak. All rights reserved. Enclosure is proprietary
software; see the [LICENSE](LICENSE) file for the complete terms.
