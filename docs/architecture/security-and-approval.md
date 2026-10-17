# Security and approval

Every mapped API operation passes through the security permission boundary.
Enclosure authenticates one actor, classifies the operation, creates a payload-
bound intent, enforces the required permission, and records the execution outcome.

Actors may arrive through an authenticated Django session, a bearer token, or a
trusted internal envelope. Local development supplies a configured local human
actor only when the runtime is limited to local hosts. Production-like MCP
runtime configuration requires bearer authentication by default.

Operation classes require distinct permissions:

| Classification | Required permission |
| --- | --- |
| Read | `security.invoke_read` |
| Mutation | `security.invoke_mutation` |
| Destructive | `security.invoke_destructive` |
| Approval | `security.approve_operation` |
| Audit | `security.view_audit_event` |

Destructive approval is exact and temporary. The pending request identifies the
actor, operation intent, payload digest, and expiry. Approval is one-time and does
not authorize a changed payload or a later unrelated action.
