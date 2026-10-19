# Public interfaces

One application contract is projected through several interfaces.

The REST API owns operation IDs, request schemas, response schemas, and HTTP
status behavior. Sirenity compiles that OpenAPI contract and combines application
responses with explicit capabilities to produce navigable Siren documents. The
browser follows those links and actions instead of maintaining a parallel route
map. The MCP server exposes the available operation catalogue as typed tools and
formats large results into bounded, followable representations. Enclosure checks
the actor's permission when an advertised operation is invoked.

This arrangement creates a useful direction of dependency:

1. application domains own behavior and typed values;
2. REST controllers expose the public operation contract;
3. Sirenity adds response-bound navigation and actions;
4. MCP and the browser consume that navigable contract.

An internal service class is not public merely because Python can import it. The
supported boundary is the runtime contract described by OpenAPI, Siren, and MCP.
The [generated API reference](../reference/api.md) is checked against the current
OpenAPI document so operation drift cannot pass silently.
