# Compatibility

The checked-out release line requires:

| Component | Contract |
| --- | --- |
| Python | 3.14 or later within the supported release line |
| Package manager | `uv` with the committed lock file |
| Modwire | 12.0.0 |
| Mermaiden | 11.0.0 |
| Sirenity | 8.0.2 |
| MCP Python SDK | 2.x (`>=2,<3`) |
| Browser CI | Node.js 24 |
| Database CI | PostgreSQL 18 with pgvector 0.8.2 image |

The exact Python and browser dependency graphs are pinned in `uv.lock` and
`browser/package-lock.json`. Container deployments use an immutable Enclosure
SemVer image tag.

Architecture publications, operating-contract revisions, record category schema
versions, scaffolding template revisions, and Mermaiden snapshot envelopes carry
their own compatibility identities. Do not infer compatibility solely from the
current application version.
