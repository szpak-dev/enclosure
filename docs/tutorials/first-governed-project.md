# Your first governed project

This tutorial begins with a configured Enclosure instance. An empty installation
contains the engine but no organization-specific guidance, architecture contract,
or project scaffolding. An operator must install those authorities before a
project can be governed.

You will connect an MCP client, resolve one registered checkout, request the
guidance for a concrete task, run a current project-health evaluation, and
inspect its report.

## 1. Start the development runtime

This local path uses SQLite with record embeddings disabled. It supports the
governed loop below, but semantic record search and semantic guidance ranking
require PostgreSQL with `pgvector`. With embeddings disabled, applicable
optional guidance retains project-scope order.

```console
uv sync --locked
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput
RECORDS_EMBEDDINGS_ENABLED=0 make mcp
```

Check the application before continuing:

```console
curl --fail http://127.0.0.1:8000/health/
curl --fail http://127.0.0.1:8000/api/
```

The health endpoint proves that the application and database are reachable. It
does not evaluate a project's architecture; that is a separate operation.

## 2. Connect the MCP client

Point the client at `http://127.0.0.1:8000/mcp`. For a persistent runtime, use
`http://127.0.0.1:8666/mcp` and follow the
[machine-wide MCP guide](../how-to/run-machine-wide-mcp.md).

The server advertises operations derived from Enclosure's public application
contract. The exact operation inventory for the checked-out source appears in
the [generated API reference](../reference/api.md).

## 3. Resolve the checkout

Call `resolve_workspace` with the checkout's absolute path:

```json
{
  "root": "/absolute/path/to/project"
}
```

A successful response contains a logical project and an explicit workspace
binding. Failure means the path is not registered; it is not silently associated
with a similarly named project.

## 4. Request task-specific context

Call `get_workspace_context` once with the same root and a concrete task:

```json
{
  "root": "/absolute/path/to/project",
  "task": "Add a repository method and expose it through the existing public service"
}
```

Stop if readiness is not `ready` or coverage is incomplete. A successful result
identifies the authority and revision behind the selected guidance, explains why
each record applies, and lists the checks required before delivery.

Changing the task may change the optional guidance selection. It does not change
the mandatory operating contract.

## 5. Read project health

Call `check_project_health` with the project and workspace identifiers returned by
resolution. The result separates failures from advisories and links bounded
follow-up reads for findings and the architecture attestation.

A green result means that the configured checks passed for the attested inputs.
It does not mean that tests passed, the design was accepted, or the software has
no defects.

You now have the essential governed loop: exact workspace, task-selected context,
configured checks, and evidence with a human decision still outstanding.
