# Configuration

Environment variables configure one Enclosure runtime. Values shown as defaults
come from the checked-out source; deployment configuration may require an explicit
value even when development has a fallback.

## Application

| Variable | Default | Meaning |
| --- | --- | --- |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated Django hosts. All-local hosts enable local-development behavior even when `DEBUG=0`. |
| `DATABASE_URL` | local SQLite path in development | Django database URL. The Compose runtime requires an explicit PostgreSQL URL. |
| `DATABASE_HOST` | database URL value | Optional host override. |
| `DATABASE_PORT` | database URL value | Optional port override. |
| `DEBUG` | `0` | Enables Django debug mode and local-development behavior when set to `1`, regardless of `ALLOWED_HOSTS`. Never enable it on a remotely reachable runtime. |
| `ENCLOSURE_RUNTIME_VERSION` | `0.0.0+dev` | Version reported by the API and MCP runtime. |
| `LOG_LEVEL` | `INFO` | Root structured logging level. |
| `SECRET_KEY` | development-only fallback | Django secret. Compose requires an explicit value. |

## Records

| Variable | Default | Meaning |
| --- | --- | --- |
| `RECORDS_EMBEDDINGS_ENABLED` | `1` | Enables semantic record embeddings, search, and guidance ranking. SQLite requires `0`; optional guidance then retains project-scope order. |
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
| `PROJECT_HEALTH_TIMEOUT_SECONDS` | `60` | Overall architecture-worker deadline covering bootstrap and evaluation. Guidance checks, summarization, and final input verification run afterward. |
| `PROJECT_HEALTH_WORKER_READY_TIMEOUT_SECONDS` | `15` | Additional worker-bootstrap cap within the overall architecture-worker deadline. |

The cache stores successful architecture-worker stages and completed
architecture results. Failed, cancelled, and timed-out worker evaluations do not
commit their deferred cache writes. Guidance checks, final input verification,
and the combined project-health report are evaluated outside that reusable
architecture result.

## Security

Local-development behavior supplies an unauthenticated local human actor with
wildcard permission to HTTP requests. It is active when `DEBUG=1` or when every
configured `ALLOWED_HOSTS` entry is local. `DEBUG=1` activates it independently
of the host list, so a debug runtime must never be remotely reachable. MCP uses
`SECURITY_MCP_AUTH_REQUIRED` directly; local-development behavior only chooses
that setting's default.

| Variable | Default | Meaning |
| --- | --- | --- |
| `SECURITY_APPROVAL_TTL_SECONDS` | `900` | Lifetime of a pending destructive approval request. |
| `SECURITY_BEARER_MAX_AGE_SECONDS` | `3600` | Maximum accepted bearer-token age. |
| `SECURITY_LOCAL_ACTOR_ID` | `local-development` | Actor identifier used by the local-development fallback. |
| `SECURITY_MCP_AUTH_REQUIRED` | local: `0`; otherwise: `1` | Requires MCP bearer authentication. Explicit `0` enables the unauthenticated wildcard MCP actor regardless of `DEBUG` or `ALLOWED_HOSTS`; never use it remotely. |
| `SECURITY_MCP_ISSUER_URL` | `https://localhost/` | Expected bearer issuer. |
| `SECURITY_MCP_RESOURCE_URL` | `https://localhost/mcp` | Expected bearer resource. |

## Compose runtime

| Variable | Default | Meaning |
| --- | --- | --- |
| `ENCLOSURE_IMAGE` | required | Released container image reference. The repository runtime targets require a tag-form reference; use a version-specific SemVer tag. |
| `ENCLOSURE_MCP_PORT` | `8666` | Host loopback port for the machine-wide server. |
| `ENCLOSURE_PROJECTS_DIR` | `/Users/gorky/Projects` in the repository Compose file | Host project directory mounted at the same absolute path. |

Set `ENCLOSURE_PROJECTS_DIR` explicitly outside the repository author's machine.
