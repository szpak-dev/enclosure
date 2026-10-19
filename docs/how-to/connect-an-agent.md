# Connect a coding agent

Configure the agent's MCP client to use one Enclosure endpoint:

- development: `http://127.0.0.1:8000/mcp`
- machine-wide runtime: `http://127.0.0.1:8666/mcp`

`install_workspace_agent_instructions` overwrites the root `AGENTS.md` as a
normal mutation. Inspect and preserve any existing repository instructions before
calling it. When the file already contains governed project knowledge, merge the
required contract manually instead of replacing it.

The installed or manually maintained `AGENTS.md` must require this first call:

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

Production-like runtimes require MCP bearer authentication by default. The
repository does not currently expose a public credential-issuance command. Local
development detection sets `SECURITY_MCP_AUTH_REQUIRED=0` by default, but that
setting controls MCP directly: explicitly setting it to `0` permits the
configured unauthenticated wildcard actor regardless of `DEBUG` or
`ALLOWED_HOSTS`. Never use that setting on a remotely reachable runtime. See
[security and approval](../architecture/security-and-approval.md).
