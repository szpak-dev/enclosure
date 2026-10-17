# Interfaces

## Development runtime

| Interface | URL |
| --- | --- |
| Siren browser | `http://127.0.0.1:8000/` |
| REST API root | `http://127.0.0.1:8000/api/` |
| OpenAPI document | `http://127.0.0.1:8000/api/openapi.json` |
| OpenAPI browser | `http://127.0.0.1:8000/api/docs` |
| Siren API root | `http://127.0.0.1:8000/siren/` |
| MCP endpoint | `http://127.0.0.1:8000/mcp` |
| Liveness | `http://127.0.0.1:8000/health/` |

## Machine-wide runtime

The default Compose mapping exposes the same application through
`http://127.0.0.1:8666`. The MCP endpoint is therefore
`http://127.0.0.1:8666/mcp`.

## Contract relationship

REST operation IDs and JSON Schemas originate in the application controllers and
schema types. Sirenity projects application results into Siren entities, links,
and actions. MCP exposes the permitted action contract as typed tools and adds
bounded presentation for large content.

The [generated operation reference](api.md) lists the current REST paths,
operation IDs, tags, summaries, and named transport schemas.
