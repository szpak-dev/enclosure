# Limits and non-goals

Enclosure governs declared contracts. It cannot recover intent that nobody
recorded.

Current boundaries include:

- architecture conformance is limited to facts represented by accepted diagrams,
  compiled manifests, and configured Modwire analyzers;
- project health is not a replacement for behavioral, security, performance, or
  usability testing;
- a complete context receipt proves selection and provenance, not that every
  organizational belief is correct;
- an empty installation contains no organization-specific operating contract;
- local workspace paths must be available to the runtime at the same absolute
  location;
- public REST, Siren, and MCP contracts are supported interfaces; internal Python
  service modules are not a general-purpose SDK;
- design, implementation, verification, and delivery acceptance belong to the
  repository workflow; Enclosure neither persists them as typed acceptance
  artifacts nor verifies that the repository captured them;
- context receipts are returned, while successful architecture-evaluation stages,
  findings, and attestations may be reused from a bounded, evictable filesystem
  cache; the combined project-health report is rebuilt rather than persisted as
  a durable evidence record;
- the current release does not provision the audit registry permission for
  ordinary Django session users because its name differs from Django's generated
  codename;
- a passed approval gate proves that an authorized actor accepted one exact
  operation, not that the operation was wise.

Enclosure is not an autonomous engineering manager, a general workflow engine, or
a substitute for repository review. Its job is narrower: keep agreement, context,
evidence, and authority connected while software changes.
