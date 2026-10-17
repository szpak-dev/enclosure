# Architecture

Enclosure is a Django application with public REST, Siren, browser, and MCP
interfaces. Application capabilities are grouped by owned domains including
projects, diagrams, records, scaffoldings, languages, and security.

Controllers translate transport input into typed service values. Public facades
coordinate focused injectable services. Repositories keep ORM models behind the
service boundary. The existing autowiring composition discovers injectables and
binds accepted abstract service boundaries.

The accepted tree, UML, and entity diagrams remain the architecture source of
truth. This documentation explains their consequences for readers; it does not
replace or fork them.

Continue with [public interfaces](interfaces.md) and
[security and approval](security-and-approval.md).
