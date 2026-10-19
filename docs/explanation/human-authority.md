# Human authority and destructive approval

Automation is most dangerous when the ability to call an operation is mistaken
for permission to decide its consequences.

Enclosure classifies public operations as reads, mutations, destructive actions,
approvals, or audit access. After resolving an actor, it constructs an operation
intent, checks the required permission, and records the authorization decision.
Credential-based actors are authenticated; local development may instead use
the configured unauthenticated fallback actor. Denied authorization stops before
execution. For an allowed request, Enclosure also records the execution outcome.
Credential-authentication failures occur before either audit record can be
created.

Destructive operations use a two-step boundary. The first attempt returns an
exact, expiring approval request. An authorized actor may approve or reject that
request. Approval is consumed once when the matching operation is retried; it is
not a reusable permission slip for a similar payload.

The same principle appears in delivery. Design acceptance, implementation
acceptance, verification acceptance, and merge authority are separate decisions.
Enclosure returns caller-visible evidence for those separate human decisions. It
does not route that evidence to a reviewer or collapse the decisions into one
autonomous action.
