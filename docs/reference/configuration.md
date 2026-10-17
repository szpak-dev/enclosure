# Configuration

Environment variables configure one Enclosure runtime. Values shown as defaults
come from the checked-out source; deployment configuration may require an explicit
value even when development has a fallback.

## Application

| Variable | Default | Meaning |
| --- | --- | --- |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated Django hosts. All-local hosts enable local-development behavior. |
| `DATABASE_URL` | local SQLite path in development | Django database URL. The Compose runtime requires an explicit PostgreSQL URL. |
| `DATABASE_HOST` | database URL value | Optional host override. |
| `DATABASE_PORT` | database URL value | Optional port override. |
| `DEBUG` | `0` | Enables Django debug mode when set to `1`. |
| `ENCLOSURE_RUNTIME_VERSION` | `0.0.0+dev` | Version reported by the API and MCP runtime. |
| `LOG_LEVEL` | `INFO` | Root structured logging level. |
| `SECRET_KEY` | development-only fallback | Django secret. Compose requires an explicit value. |

## Records

| Variable | Default | Meaning |
| --- | --- | --- |
| `RECORDS_EMBEDDINGS_ENABLED` | `1` | Enables semantic record embeddings. |
| `RECORDS_EMBEDDING_PROVIDER` | `deterministic` | Selected embedding provider. |

The stored embedding dimension is 384 in the current release line.

## Project health

| Variable | Default | Meaning |
| --- | --- | --- |
| `MODWIRE_CACHE_DIRECTORY` | `.dev/modwire-cache` | Modwire scan and analysis cache. |
| `MODWIRE_CACHE_MAX_BYTES` | `1073741824` | Maximum Modwire cache size. |
| `PROJECT_HEALTH_CACHE_DIRECTORY` | `.dev/health-cache` | Validated project-health stage cache. |
| `PROJECT_HEALTH_CACHE_MAX_BYTES` | `1073741824` | Maximum project-health cache size. |
| `PROJECT_HEALTH_MAX_CONCURRENCY` | `1` | Maximum simultaneous health worker processes per runtime. |
| `PROJECT_HEALTH_TIMEOUT_SECONDS` | `60` | Complete health execution timeout. |
| `PROJECT_HEALTH_WORKER_READY_TIMEOUT_SECONDS` | `15` | Worker bootstrap timeout. |

Failed, cancelled, and timed-out health executions are not cached.

## Security

| Variable | Default | Meaning |
| --- | --- | --- |
| `SECURITY_APPROVAL_TTL_SECONDS` | `900` | Lifetime of a pending destructive approval request. |
| `SECURITY_BEARER_MAX_AGE_SECONDS` | `3600` | Maximum accepted bearer-token age. |
| `SECURITY_LOCAL_ACTOR_ID` | `local-development` | Actor identifier used by the local-development fallback. |
| `SECURITY_MCP_AUTH_REQUIRED` | local: `0`; otherwise: `1` | Requires MCP bearer authentication. |
| `SECURITY_MCP_ISSUER_URL` | `https://localhost/` | Expected bearer issuer. |
| `SECURITY_MCP_RESOURCE_URL` | `https://localhost/mcp` | Expected bearer resource. |

## Compose runtime

| Variable | Default | Meaning |
| --- | --- | --- |
| `ENCLOSURE_IMAGE` | required | Exact released container image and immutable tag. |
| `ENCLOSURE_MCP_PORT` | `8666` | Host loopback port for the machine-wide server. |
| `ENCLOSURE_PROJECTS_DIR` | `/Users/gorky/Projects` in the repository Compose file | Host project directory mounted at the same absolute path. |

Set `ENCLOSURE_PROJECTS_DIR` explicitly outside the repository author's machine.
