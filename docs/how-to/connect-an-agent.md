# Connect a coding agent

Configure the agent's MCP client to use one Enclosure endpoint:

- development: `http://127.0.0.1:8000/mcp`
- machine-wide runtime: `http://127.0.0.1:8666/mcp`

Install the repository instruction contract through
`install_workspace_agent_instructions`, or maintain an equivalent `AGENTS.md`
that requires this first call:

```text
enclosure-mcp.get_workspace_context(root, task)
```

Pass the exact absolute checkout path and a task description concrete enough to
select relevant optional guidance. Call it once at the beginning of the task and
obey its readiness, coverage, selected guidance, required checks, and stop
condition.

Do not replace this with a broad record search. Workspace context combines the
registered project, active operating contract, guidance graph, task selection,
budget, and receipt into one authoritative response.

Production-like runtimes require MCP bearer authentication by default. Local
development permits the configured local actor when all allowed hosts are local.
See [security and approval](../architecture/security-and-approval.md).
