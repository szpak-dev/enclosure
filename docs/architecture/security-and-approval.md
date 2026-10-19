# Security and approval

Every mapped API operation passes through the security permission boundary.
Enclosure first resolves one actor. Session, bearer, and trusted-envelope actors
use credentials; local development may supply the configured unauthenticated
fallback actor. Credential-authentication failures are rejected before an audit
event is created. For a resolved actor, Enclosure classifies the operation,
creates a payload-bound intent, and records the authorization decision. A denial
stops before execution. An allowed request is bound to its actor and intent, and
its execution outcome is then recorded.

Actors may arrive through an authenticated Django session, a bearer token, or a
trusted internal envelope. HTTP local development supplies a configured local
human actor with wildcard permission when `DEBUG=1` or when every allowed host
is local. Because `DEBUG=1` activates that HTTP actor independently of the host
list, it must never be enabled on a remotely reachable runtime.

MCP uses `SECURITY_MCP_AUTH_REQUIRED` directly. Local-development detection only
chooses its default. Explicitly setting it to `0` supplies the unauthenticated
wildcard MCP actor regardless of `DEBUG` or `ALLOWED_HOSTS`; never use that
setting on a remotely reachable runtime.

Operation classes require distinct permissions:

| Classification | Required permission |
| --- | --- |
| Read | `security.invoke_read` |
| Mutation | `security.invoke_mutation` |
| Destructive | `security.invoke_destructive` |
| Approval | `security.approve_operation` |
| Audit | `security.view_audit_event` |

The audit entry is the permission string required by Enclosure's operation
registry. Bearer and trusted actors must carry that exact string; superusers pass
through their wildcard permission. In the current release, Django's automatically
generated session permission is named `security.view_auditevent` and does not
satisfy the registry check for an ordinary session user.

Destructive approval is exact and temporary. The pending request identifies the
actor, operation intent, payload digest, and expiry. Approval is one-time and does
not authorize a changed payload or a later unrelated action.
