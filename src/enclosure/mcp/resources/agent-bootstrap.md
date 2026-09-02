# Enclosure

Enclosure is the project-aware control plane exposed to agents through MCP. It provides compact
workspace context, architecture checks, records, scaffoldings, and diagrams while keeping REST as
the application authority.

## Working contract

- On the first task in a registered workspace, call `get_workspace_context(root, task)` once.
- Treat returned mandatory guidance and required checks as policy for the task.
- Run GitHub and environment-sensitive CLI commands in host-equivalent mode.
- Run applicable focused tests while developing, then the full configured tests and Ruff.
- Check project health after structural source, public API, dependency-injection, or architecture changes.
- After an ambiguous mutating-tool failure, verify state before retrying.
- Preserve unrelated workspace changes and report every unrun or failing check.
