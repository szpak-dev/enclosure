# Public contracts

## REST

The OpenAPI document at `/api/openapi.json` is the machine-readable REST contract.
Unknown input fields are rejected by strict request schemas where the operation
uses an Enclosure strict schema. Domain failures are translated at the public
boundary rather than exposing repository or framework exceptions.

## Siren

The Siren root at `/siren/` is a navigable projection of the same application.
Links represent discoverable resources. Actions represent operations currently
available from the response. Follow-up metadata binds identifiers and revisions
from the source response into later operations.

## MCP

The MCP endpoint exposes typed operations backed by the Siren/OpenAPI contract.
Large records, resources, templates, rendered files, diagrams, health findings,
and insight bodies use bounded reads with revision-pinned continuation.

## Browser

The browser follows Siren resources and actions. It is a consumer of the public
contract, not a second application API or route registry.

## Python

Enclosure does not advertise its internal Python packages as a supported SDK.
Application services, repositories, Django models, adapters, and composition are
implementation details unless another published contract explicitly says
otherwise.
