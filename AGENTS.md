Run architecture health checks only through the registered Enclosure MCP
`check_project_health` operation. Do not invoke Modwire through its CLI.

Run `uv` commands in host mode; sandboxed `uv` can panic while reading macOS system configuration.
