# Enclosure

> **The faster code is written, the more important it becomes to remember who said yes.**

AI can produce code faster than a team can inspect it. That is not the same as
progress.

Enclosure keeps architectural intent, project guidance, implementation evidence,
and human acceptance in one governed loop. It gives coding agents the context to
act, checks whether implementation still honors the accepted promise, and leaves
the final decision with a person.

Mermaiden models intent. Modwire measures implementation. Sirenity exposes
permitted action. Enclosure governs the agreement between them.

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
| [Sirenity](https://github.com/szpak-dev/sirenity) | Exposes the actions currently permitted by an application response. |
| **Enclosure** | Governs context, agreement, evidence, and acceptance across them. |

## Start Enclosure

Enclosure requires Python 3.14, `uv`, Node.js for the browser build, and a
PostgreSQL database with `pgvector`.

```console
uv sync --locked
uv run python manage.py migrate
make mcp
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

Run the complete verification suite before handoff:

```console
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
