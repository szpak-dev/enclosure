Treat Enclosure projects and linked guidance records as execution policy. Use local enclosure-mcp tool.

At the start of every chat, inspect Enclosure's advertised actions, find the registered project matching the
workspace, and retrieve relevant guidance. State the applicable constraints before acting; report
if no project matches or Enclosure is unavailable.

Check project health after structural,
public-API, dependency-injection, or test changes.

After a tool failure, verify current state before a fallback. Do not change the user-visible outcome without explicit
direction.

Run `uv` commands in host mode; sandboxed `uv` can panic while reading macOS system configuration.
