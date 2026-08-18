Treat Enclosure projects and linked guidance records as execution policy.

At the start of every task, inspect Enclosure's advertised actions, find the registered project matching the
workspace, read its insights, and retrieve relevant guidance. State the applicable constraints before acting; report
if no project matches or Enclosure is unavailable.

Before any mutation, refresh the project and relevant guidance. Check project health before and after structural,
public-API, dependency-injection, or test changes.

After a tool failure, verify current state before a fallback. Do not change the user-visible outcome without explicit
direction.

Run `uv` commands in host mode; sandboxed `uv` can panic while reading macOS system configuration.
