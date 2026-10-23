# Compatibility

The checked-out release line requires:

| Component | Contract |
| --- | --- |
| Python | 3.14 or later within the supported release line |
| Package manager | `uv` with the committed lock file |
| Modwire | 12.0.0 |
| Mermaiden | 13.1.0 |
| Mermaid | 12.2.0 |
| Mermaid CLI | 12.0.0 |
| Sirenity | 8.0.2 |
| MCP Python SDK | 2.x (`>=2,<3`) |
| Browser and renderer runtime | Node.js 24.17.0 |
| Database CI | PostgreSQL 18 with pgvector 0.8.2 image |

The exact Python, renderer, and browser dependency graphs are pinned in
`uv.lock`, `package-lock.json`, and `browser/package-lock.json`. Container deployments select an Enclosure release
with a version-specific SemVer image tag. Registry tags can be retargeted. A
generic container deployment can pin a digest for immutable implementation
identity, but the repository's current `runtime-up` and `runtime-rollback`
targets require a tag-form image reference.

Architecture publications, operating-contract revisions, record category schema
versions, scaffolding template revisions, and Mermaiden snapshot envelopes carry
their own compatibility identities. Do not infer compatibility solely from the
current application version.
