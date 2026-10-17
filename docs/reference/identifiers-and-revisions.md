# Identifiers and revisions

Enclosure distinguishes identity, mutable resource revision, and immutable
publication version.

## Identifiers

Projects, workspace bindings, records, record categories, record tags,
scaffoldings, diagram sets, diagrams, operating contracts, publications, approval
requests, and executions carry opaque identifiers. Clients must not derive type,
order, or ownership from their spelling.

## Revisions

Content-bearing resources expose revisions so a later read or mutation can name
the state on which it is based. Bounded continuation reads repeat the expected
revision; a changed revision is a conflict, not an invitation to concatenate two
different documents.

Diagram updates and command batches use optimistic concurrency. Record content,
resources, category schemas, scaffolding templates, rendered files, architecture
configuration, workspace bindings, health evidence, and insights expose the
revision appropriate to their contract.

## Versions and publications

Operating-contract revisions and accepted architecture-contract publications are
immutable. A project binding selects an operating-contract version and update
policy. Changing accepted intent creates a new publication; it does not mutate
the evidence behind an earlier decision.
