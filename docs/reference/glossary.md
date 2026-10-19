# Glossary

## Accepted architecture publication

An immutable project publication that assigns accepted diagram evidence and
coverage to architecture units.

## Actor

The human or agent identity bound to a public operation. It may be authenticated
by session or bearer credentials, trusted through an internal envelope, or
supplied as the configured unauthenticated local-development fallback.

## Architecture attestation

Digest-backed evidence identifying the expected contract, observed implementation,
configured checks, and conformance result for one project-health execution.

## Diagram set

A collection of typed diagrams describing one coherent topic. Tree, UML, and
entity diagrams in the same architecture unit must agree.

## Guidance record

A typed record whose content may become mandatory through an operating contract
or eligible through a project guidance scope.

## MCP

Model Context Protocol, the tool interface through which agents discover and
invoke Enclosure operations. Actor permission is checked when an operation is
invoked.

## Operating contract

A stable authority with immutable published revisions of mandatory guidance.

## Project

The logical Enclosure resource that owns architecture configuration, operating-
contract binding, guidance routing, scaffolding selection, and workspaces.

## Project health

A bounded execution of configured architecture, guidance, and conformance checks
for one project and workspace.

## Record

Schema-validated engineering knowledge with tags, revisions, and optional source
resources that can carry supporting material.

## Scaffolding

A revisioned collection of source templates and typed rendering variables.

## Siren

The hypermedia format Enclosure uses to expose resources, links, and
response-scoped actions.

## Workspace binding

The explicit association between one normalized local checkout path and one
logical project.

## Workspace context

The task-specific response containing readiness, effective authority, selected
guidance, coverage, receipt, required checks, and stop condition for a registered
workspace.
